#!/usr/bin/env python
# encoding: utf-8

__author__ = "Steve Marshall (steve@nascentguruism.com)"
__copyright__ = "Copyright (c) 2008 Steve Marshall"
__license__ = "Python"

from atom import Atom
import os

class Mp4File(list):
    def __init__(self, file):
        fh = open(file, 'rb')
        size = os.stat(file).st_size
        while fh.tell() < size:
            root_atom = Atom( stream=fh, offset=fh.tell() )
            root_atom.seek( 0, os.SEEK_END )
            self.append( root_atom )
    

