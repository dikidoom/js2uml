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
# [ ] identify all necessary js blocks by regexp
# [ ] find a better python representation than dictionaries
# [ ] remove uninteresting blocks (if, for, return, ...)
# [ ] .dot helper functions
# [ ] build .dot representation
# [ ] shell out to graphviz
# [ ] profit

import re
    
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

def climb3( string, 
            parent, 
            search_offset=0 ):
    # generate scope tree by recursively matching curly braces
    match = curlybraces_re.search( string, search_offset )
    if not match:
        return
    if match.group( 0 ) == '{':
        # print( "open" )
        nextBlock = { "name": "UNKNOWN",
                      "type": "UNKNOWN",
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

def pretty_print( root, indent = 0 ):
    # print the scope tree using meaningful indentation
    print( " " * indent, 
           root['name'],
           "(", root['type'], ")",
           root['start'], root['end'],
           sep = " " )
    for e in root['children']:
        pretty_print( e, indent + 4 )

# -----------------------------------------------------------------------------
# usage

file = open( "test-files/mini.js" )
#file = open( "test-files/main.js" )
full = file.read()

# remove comments
full = inlinecomments_re.sub( "", full )
full = comments_re.sub( "", full )

# build scope tree
climb3( full, root )
#pretty_print( root )

#print( 'all named functions', functions_re.findall( full ))
#print( 'all anonymous functions', lambdas_re.findall( full ))
#print( 'all objects', objects_re.findall( full ))

# identify scopes
# misc & imprecise
identify( full, throwaway_lambdas_re, 'function (anon)' )
identify( full, if_re,                'if-clause' )
identify( full, else_re,              'else-clause' )
identify( full, for_re,               'for-loop' )
identify( full, return_re,            'object (anon)' )
# precise (after imprecise because of overwrites :P)
identify( full, functions_re,         'function' )
identify( full, lambdas_re,           'function (anon, assigned)' )
identify( full, objects_re,           'object' )

pretty_print( root )
