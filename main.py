# uml-painter
#
# create a .dot file for graphviz rendering of a .js program flowchart
# hacker: philipp dikmann
# date: 30-03-2015

# [x] TODO pass 'last found'-index to climb & continue re.search only after that point -- to retain absolute indices for next step
# [x] TODO store the start/end (span) indices of re.search inside the nodes
# [ ] TODO use indices and re.match to find the blocks' preceding statements and figure out their type and name
# [ ] TODO strip comments from file before parsing

import re
    
file = open( "test-files/mini.js" )
full = file.read()

fake = "oone{ foo bar twoo{ baz } qux } outside{ again }"

myregex = re.compile( "([{}])" )

def climb3( string, 
            parent, 
            search_offset=0 ):
    m = myregex.search( string, search_offset )
    if not m:
        return
    if m.group( 0 ) == '{':
        print( "open" )
        nextBlock = { "name": "UNKNOWN",
                      "start": m.start(), # including '{'
                      "parent": parent,
                      "children": [] }
        parent['children'].append( nextBlock )
    else:
        print( "close" )
        parent['end'] = m.end() # including '}'
        nextBlock = parent['parent']
    climb3( string,
            nextBlock,
            m.end() )

def pretty_print( root, indent = 0 ):
    print( " " * indent, 
           root['name'],
           root['start'], root['end'],
           sep = " " )
    for e in root['children']:
        pretty_print( e, indent + 4 )

root = { "name": "root",
         "start": None,
         "end": None,
         "parent": None,
         "children": [] }
climb3( full, root )
pretty_print( root )
# 
