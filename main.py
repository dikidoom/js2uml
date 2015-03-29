# uml-painter
#
# create a .dot file for graphviz rendering of a .js program flowchart
# hacker: philipp dikmann
# date: 30-03-2015

# TODO pass 'last found'-index to climb & re.search only after that point -- to retain absolute indices for next step
# TODO store the start/end (span) indices of re.search inside the nodes
# TODO use indices and re.match to find the blocks' preceding statements and figure out their type and name
# TODO 

import re
    
file = open( "test-files/main.js" )
full = file.read()

fake = "oone{ foo bar twoo{ baz } qux } outside{ again }"
#lst = re.findall( "({[^{}]*})", fake )
#lst = re.findall( "{", fake )
#print( lst )

def climb( string ):
    m = re.search( "([{}])", string )
    if not m:
        return
    if m.group( 0 ) == '{':
        print( "open" )
    else:
        print( "close" )
    climb( string[ m.end() : ])

def climb2( string, parent ):
    m = re.search( "([{}])", string )
    if not m:
        return
    if m.group( 0 ) == '{':
        print( "open" )
        newChild = { "name": "foo", "parent": parent, "children": [] }
        parent['children'].append( newChild )
    else:
        print( "close" )
        newChild = parent['parent']
    climb2( string[ m.end() : ], newChild )

def climb3( string, parent ):
    m = re.search( "([{}])", string )
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
    climb3( string[ m.end() : ], nextBlock )

root = { "name": "root", 
         "parent": None,
         "children": [] }
climb3( fake, root )
# 
