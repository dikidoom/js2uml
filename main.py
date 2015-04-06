# js2uml
#
# creates a flowchart (graphviz .dot file) from a .js program
# hacker: philipp dikmann
# start-date: 30-03-2015

# TODOS
# [x] pass 'last found'-index to climb & continue re.search only after that point -- to retain absolute indices for next step
# [x] store the start/end (span) indices of re.search inside the nodes
# [x] use indices and re.match to find the blocks' preceding statements and figure out their type and name
# [x] strip comments from file before parsing
# [x] identify all necessary js blocks by regexp
# [x] remove uninteresting blocks (if, for, return, ...)

# [ ] resolve 'this.'-references (both as names and as calls)
# [ ] generate symbols for callable blocks
# [ ] parse 'called known functions' from block body
# [ ] correlate called fns with gensyms

# [ ] find a better python representation than dictionaries

# [ ] profit

import re
import subprocess
import graphviz
    
# -----------------------------------------------------------------------------
# variables

# regular expressions
# comments
inlinecomments_re    = re.compile( "//.*?$", re.M )
comments_re          = re.compile( "/\*.*?\*/", re.S )

# block structure
curlybraces_re       = re.compile( "([{}])" )

# things we care about ...
functions_re         = re.compile( "function\s*([^\(]+?)\s*\(.*?\)\s*{" )
lambdas_re           = re.compile( "([^\s]*?)\s*[=:]\s*function.*?{" )
objects_re           = re.compile( "([^\s]*?)\s*[=:]\s*{" ) 

# ... and things we don't
throwaway_lambdas_re = re.compile( "[^=:]\s*(function).*?{" )
if_re                = re.compile( "(if)\s*\(.*?\)\s*{" )
else_re              = re.compile( "}\s*(else)\s*{" )
for_re               = re.compile( "(for)\s*\(.*?\)\s*{" )
return_re            = re.compile( "(return)\s*{" )

# scope tree root
root = { "name": "root",
         "type": "top",
         "start": None,
         "end": None,
         "parent": None,
         "children": [] }

# -----------------------------------------------------------------------------
# functions

# -------------------------------------
# tree
def climb3( string, 
            parent, 
            search_offset=0 ):
    # generate scope tree by recursively matching curly braces
    match = curlybraces_re.search( string, search_offset )
    if not match:
        return
    if match.group( 0 ) == '{':
        # print( "open" )
        nextBlock = { "name": None,
                      "type": None,
                      "start": match.start(), # including '{'
                      "parent": parent,
                      "children": [] }
        parent['children'].append( nextBlock )
    else:
        # print( "close" )
        parent['end'] = match.end() # including '}'
        nextBlock = parent['parent']
    climb3( string,
            nextBlock,
            match.end() )

def identify( string, regex, kind, offset=0 ):
    # identify entries in the scope tree by matching for preceding strings
    match = regex.search( string, offset )
    if not match:
        return
    entry = find_entry_where( root, 'start', match.end()-1 )
    if entry:
        entry['name'] = match.group( 1 )
        entry['type'] = kind
    identify( string, regex, kind, match.end() )

def descend( root, *names ):
    if len( names ) == 0:
        return root
    for c in root['children']:
        if c['name'] == names[0]:
            return descend( c, *names[1:] )
    return None

def find_entry_where( root, key, value ):
    # search the scope tree recursively for a particular entry
    if root[ key ] == value:
        return root
    else:
        for child in root['children']:
            found = find_entry_where( child, key, value )
            if found:
                return found
        return None

def find_upwards( root, key, value ):
    # search the tree *upwards* until the top is found
    for child in root['children']:
        if child[ key ] == value:
            return child
    if root['type'] == 'top':
        return None
    else:
        return find_upwards( root['parent'], key, value )

def resolve_dot_refs( root ):
    # recur for children first!
    mark_delete = [ c for c in root['children'] if resolve_dot_refs( c )]
    #print( 'name is', root['name'] )
    #print([ x['name'] for x in mark_delete ])
    for c in mark_delete:
        root['children'].remove( c )
    # split name
    if '.' in root['name']:
        print( 'going for', root['name'] )
        split = root['name'].split('.')
        # crawl scope upwards until first name is found
        # (if name is not found, sprawl entire tree until it is found)
        new_parent = find_upwards( root['parent'], 'name', split[0])
        if not new_parent:
            print( 'fuck - no parent found!' )
            return
        # assign to new parent
        # root['parent']['children'].remove( root )
        new_parent['children'].append( root )
        new_name = str.join( '.', split[1:] )
        root['name'] = new_name
        # recur for new parent
        resolve_dot_refs( new_parent )
        # mark for deletion
        return True
    else:
        return False
    
def remove_nones( root ):
    # remove all un-identified objects from graph
    # NB: might remove un-identified objects with identified children
    root['children'] = [ c for c in root['children'] if c['name'] is not None ]
    for c in root['children']:
        remove_nones( c )

# -------------------------------------
# graph
gensym_counter = 0

def add_gensym( root ):
    global gensym_counter
    root['gensym'] = 'gensym' + str( gensym_counter )
    gensym_counter += 1
    for child in root['children']:
        add_gensym( child )

def add_nodes( root, graph ):
    if root['name'] == None:
        return
    #print( root['name'] )
    if root['type'] == 'object':
        graph.attr( 'node', shape='box' )
    else:
        graph.attr( 'node', shape='ellipse' )
    graph.node( root['gensym'], root['name'] )
    for child in root['children']:
        add_nodes( child, graph )
    return graph

def add_edges( root, graph ):
    graph.attr( 'edge', arrowhead='odot')
    for child in root['children']:
        if child['name'] == None:
            continue
        graph.edge( root['gensym'], child['gensym'] )
        add_edges( child, graph )
    return graph

# -------------------------------------
# misc
def pretty_print( root, indent = 0 ):
    # print the scope tree using meaningful indentation
    print( " " * indent, 
           root['name'],
           "(", root['type'], ")",
           #root['start'], root['end'],
           sep = " " )
    for e in root['children']:
        pretty_print( e, indent + 4 )

# -----------------------------------------------------------------------------
# usage

#file = open( "test-files/mini.js" )
file = open( "test-files/main.js" )
full = file.read()

# remove comments
full = inlinecomments_re.sub( "", full )
full = comments_re.sub( "", full )

# build scope tree
climb3( full, root )

# identify scopes

# misc & imprecise
# identify( full, throwaway_lambdas_re, 'function (anon)' )
# identify( full, if_re,                'if-clause' )
# identify( full, else_re,              'else-clause' )
# identify( full, for_re,               'for-loop' )
# identify( full, return_re,            'object (anon)' )

# precise (after imprecise because of overwrites :P)
identify( full, functions_re,         'function' )
identify( full, lambdas_re,           'function (anon, assigned)' )
identify( full, objects_re,           'object' )

#pretty_print( root )

#print( "----------------" )

remove_nones( root )
#pretty_print( root )

#print( "----------------" )

resolve_dot_refs( root )
#pretty_print( root )

# build dot
dot = graphviz.Digraph()
add_gensym( root )
add_nodes( root, dot )
add_edges( root, dot )
dot.save( 'dot.dot' )
# subprocess.call(['dot', '-V']) # won't work because of emacs/python path fu
