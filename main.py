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

# [x] resolve 'this.'-references (both as names and as calls)
# [x] generate symbols for callable blocks

# [x] parse 'called known functions' from block body
# [x] correlate called fns with gensyms

# [ ] find a better python representation than dictionaries
#  ?  what happens when 'this.foo = function(){...' occurs inside a function?
# [ ] uniquify ['calls-found'] property of nodes

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
call_re              = re.compile( "([^-+*/\(,\s]*?)\s*\([^\(\)]*?\)\s*[^{]" )

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
         "children": [],
         "calls": [],
         "calls-found": [] }

# -----------------------------------------------------------------------------
# functions

# -------------------------------------
# tree
def scope_tree( string, 
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
                      "children": [],
                      "calls": [],
                      "calls-found": [] }
        parent['children'].append( nextBlock )
    else:
        # print( "close" )
        parent['end'] = match.end() # including '}'
        nextBlock = parent['parent']
    scope_tree( string,
            nextBlock,
            match.end() )

def scope_contains( scope, start, end ):
    # check wether start & end are within scope span
    return scope['start'] <= start and scope['end'] >= end

def best_containing_scope( root, start, end ):
    # return best fitting child or self if not better fit is found
    for c in root['children']:
        if scope_contains( c, start, end ):
            return best_containing_scope( c, start, end )
    return root

def find_calls( string, root, offset=0 ):
    # match call signatures in source string and assign to 
    match = call_re.search( string, offset )
    if not match:
        return
    scope = best_containing_scope( root, match.start(), match.end() )
    scope['calls'].append( match.group( 1 ))
    find_calls( string, root, match.end() )

def top( root ):
    if root['type'] == 'top':
        return root
    else:
        return top( root['parent'] )

def find_call( root, call ):
    tip = top( root )
    if '.' in call:
        split = call.split('.')
        if split[0] == 'this':
            # refers to parent object or function
            return select( root['parent'], *split[1:] )
        else:
            # refers to some other object
            return select( tip, *split )
    else:
        # single name, just look for it everywhere
        return find_down( tip, 'name', call )

def register_call( root, call ):
    address = find_call( root, call )
    if not address:
        return
    root['calls-found'].append( address['gensym'] )

def address_calls( root ):
    # try to find the gensym's of a scope's calls
    # so we can draw arrows into the graph
    for child in root['children']:
        address_calls( child )
    for call in root['calls']:
        register_call( root, call )

def identify( string, regex, kind, offset=0 ):
    # identify entries in the scope tree by matching for preceding strings
    match = regex.search( string, offset )
    if not match:
        return
    entry = find_down( root, 'start', match.end()-1 )
    if entry:
        entry['name'] = match.group( 1 )
        entry['type'] = kind
    identify( string, regex, kind, match.end() )

def select( root, *names ):
    # try to find the child with name `names[0]` (recursively)
    # usage: select( root, 'a', 'b' ) --> return child with name 'b' of child with name 'a' of root
    if len( names ) == 0:
        return root
    for c in root['children']:
        if c['name'] == names[0]:
            return select( c, *names[1:] )
    return None

def find_down( root, key, value ):
    # search the scope tree recursively for a particular entry
    if root[ key ] == value:
        return root
    else:
        for child in root['children']:
            found = find_down( child, key, value )
            if found:
                return found
        return None

def find_up( root, key, value ):
    # search the tree *upwards* until the top is found
    for child in root['children']:
        if child[ key ] == value:
            return child
    if root['type'] == 'top':
        return None
    else:
        return find_up( root['parent'], key, value )

def resolve_dot_refs( root ):
    # properly parent all 'a.b.c' children in the tree
    # recur for children first!
    mark_delete = [ c for c in root['children'] if resolve_dot_refs( c )]
    for c in mark_delete:
        root['children'].remove( c )
    # split name
    if '.' in root['name']:
        print( 'going for', root['name'] )
        split = root['name'].split('.')
        # crawl scope upwards until first name is found
        # (if name is not found, sprawl entire tree until it is found)
        new_parent = find_up( root['parent'], 'name', split[0])
        if not new_parent:
            # TODO fix this condition by searching the entire tree
            print( 'ERROR: no parent found!' )
            return
        # assign to new parent
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
    for child in root['children']:
        add_nodes( child, graph )
    if root['name'] == None:
        return
    #print( root['name'] )
    if root['type'] == 'object':
        graph.attr( 'node', shape='box' )
    else:
        graph.attr( 'node', shape='ellipse' )
    graph.node( root['gensym'], root['name'] )
    return graph

def add_edges( root, graph ):
    for child in root['children']:
        add_edges( child, graph )
        if child['name'] == None:
            continue
        if root['type'] == 'top':
            continue
        graph.attr( 'edge', arrowhead='none', arrowtail='odot', dir='both')
        graph.edge( root['gensym'], child['gensym'] )
    for call in root['calls-found']:
        graph.attr( 'edge', arrowhead='normal', dir='forward' )
        graph.edge( root['gensym'], call )
    return graph

# -------------------------------------
# misc
def pretty_print( root, indent = 0 ):
    # print the scope tree using meaningful indentation
    print( " " * indent, 
           root['name'],
           "(", root['type'], ")",
           #root['start'], root['end'],
           root['calls'],
           root['calls-found'],
           sep = " " )
    for e in root['children']:
        pretty_print( e, indent + 4 )

# -----------------------------------------------------------------------------
# usage

def add_file( root, full ):
    # remove comments
    full = inlinecomments_re.sub( "", full )
    full = comments_re.sub( "", full )
    
    # build scope tree
    scope_tree( full, root )
    
    # identify scopes
    
    # misc & imprecise
    # identify( full, throwaway_lambdas_re, 'function (anon)' )
    # identify( full, if_re,                'if-clause' )
    # identify( full, else_re,              'else-clause' )
    # identify( full, for_re,               'for-loop' )
    # identify( full, return_re,            'object (anon)' )
    
    # precise (after imprecise because of overwrites :P)
    identify( full, functions_re,         'function' )
    identify( full, lambdas_re,           'function' ) # anonymous but assigned
    identify( full, objects_re,           'object' )
    
    # tree shaking
    remove_nones( root )
    # tree massaging
    resolve_dot_refs( root )
    # unique adresses
    add_gensym( root )
    
    # regexp-search for calls within scopes
    find_calls( full, root )
    # resolve call gensyms
    address_calls( root )
    
#file = open( "test-files/mini.js" )
file = open( "test-files/main.js" )
full = file.read()

add_file( root, full )
pretty_print( root )

# build dot
dot = graphviz.Digraph()
dot.attr( 'graph', splines='ortho' )
add_nodes( root, dot )
add_edges( root, dot )
dot.save( 'dot.dot' )
# subprocess.call(['dot', '-V']) # won't work because of emacs/python path fu
