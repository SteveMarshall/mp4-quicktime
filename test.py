#!/usr/bin/env python
# encoding: utf-8

import os, glob
from mp4file import Mp4File
from atom import Atom

def print_atom(a, indent='  '):
    children = []
    if 1 < len(a):
        for child in a:
            if type(child) is Atom:
                children.append( print_atom( child, indent=indent + '  ' ) )
        return """{indent}{atom.type}: [
{children}
{indent}]""".format( 
            atom=a,
            indent=indent,
            children=',\n'.join( children )
        )
    return "%s%s" % (indent, a)

path = './'
for mp4 in glob.glob( os.path.join(path, '*.mp4') ):
    print os.path.basename(mp4)
    mp4file = Mp4File( mp4 )
    for a in mp4file:
        print print_atom( a ) + ','
