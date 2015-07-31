#!/usr/bin/env python
# encoding: utf-8

__author__ = "Steve Marshall (steve@nascentguruism.com)"
__copyright__ = "Copyright (c) 2008 Steve Marshall"
__license__ = "Python"

import os
import StringIO
from struct import calcsize, pack, unpack
import tempfile


ATOM_HEADER = {
    # Mandatory big-endian unsigned long followed by 4 character string
    #                      (   size    )             (      type      )
    'basic': '>L4s',
    # Optional big-endian long long
    #          (    64bit size    )
    # Only used if basic size == 1
    'large': '>L4sQ',
}
# Define known atom types
ATOM_CONTAINER_TYPES = [
    'aaid', 'akid', '\xa9alb', 'apid', 'aART', '\xa9ART', 'atid', 'clip',
    '\xa9cmt', '\xa9com', 'covr', 'cpil', 'cprt', '\xa9day', 'dinf', 'disk',
    'edts', 'geid', 'gnre', '\xa9grp', 'hinf', 'hnti', 'ilst', 'matt',
    'mdia', 'minf', 'moof', 'moov', '\xa9nam', 'pinf', 'plid', 'rtng',
    'schi', 'sinf', 'stbl', 'stik', 'tmpo', '\xa9too', 'traf', 'trak', 'trkn',
    'udta', '\xa9wrt',
]
# Special containers with their own internal structures
ATOM_SPECIAL_CONTAINER_TYPES = {
    'stsd': {
        'padding': 8
    },
    'mp4a': {
        'padding': 28
    },
    'drms': {
        'padding': 28
    },
    'meta': {
        'padding': 4
    },
}
ATOM_NONCONTAINER_TYPES = [
    'chtb', 'ctts', 'data', 'esds', 'free', 'frma', 'ftyp', '\xa9gen', 'hmhd',
    'iviv', 'key ', 'mdat', 'mdhd', 'mp4s', 'mpv4', 'mvhd', 'name',
    'priv', 'rtp', 'sign', 'stco', 'stsc', 'stp', 'stts', 'tfhd',
    'tkhd', 'tref', 'trun', 'user', 'vmhd', 'wide',
]

def get_header_size(content_size):
    if 2**32 <= content_size:
        return calcsize(ATOM_HEADER['large'])
    return calcsize(ATOM_HEADER['basic'])

def render_atom_header(atom_type, content_size):
    """Build an MP4 atom header for a given <type> and
       <content_size> (bytes).
    """
    header_size = get_header_size(content_size)
    atom_size = header_size + content_size
    
    # If we have a large (64bit) atom, render using the 'large data' flag
    if calcsize(ATOM_HEADER['large']) == header_size :
        rendered_header = pack( \
            ATOM_HEADER['large'], \
            1, atom_type, atom_size)
    else:
        rendered_header = pack( \
            ATOM_HEADER['basic'], \
            atom_size, atom_type)
    
    return rendered_header

def parse_atom_header(stream, offset=0):
    """Parse an atom header from a particular <offset> within a
       file-like object
    """
    basic_header = calcsize(ATOM_HEADER['basic'])
    large_header = calcsize(ATOM_HEADER['large'])
    
    header_size = large_header
    
    # Attempt to read the atom's large header
    # If the atom isn't large, we can discard the false large size later
    stream.seek(offset)
    atom_header = stream.read(header_size)
    
    # If we have enough data to unpack as a large atom, try that
    if len(atom_header) == large_header:
        (atom_size, atom_type, large_atom_size) = \
            unpack(ATOM_HEADER['large'], atom_header)
    else:
        (atom_size, atom_type) = \
            unpack(ATOM_HEADER['basic'], \
                          atom_header[:basic_header])
    
    # If we have a large atom, use the large size in place of the size
    if 1 == atom_size:
        atom_size = large_atom_size
        # Adjust the header size to take account of the large size
        header_size = large_header
    else:
        header_size = basic_header

    if 0 == atom_size:
        stream.seek(0, os.SEEK_END)
    else:
        # Remove the header from the size we use
        atom_size -= header_size
    
        # Jump back to the end of the actual header because we will have overrun into
        # the content, if we have a basic header)
        offset_fix = -(len(atom_header) - header_size)
        stream.seek(offset_fix, os.SEEK_CUR)
    
    return (atom_type, atom_size)


class Atom(list):
    def __init__(self, stream=None, offset=0, type=None):
        if stream is not None:
            (self.type, self.__size) = parse_atom_header(stream, offset)
            self.__offset = stream.tell()
            self.__source_stream = stream
            
            # Recursively build the tree; don't try to skip containers, 
            # as their leaf data atoms will do all the skipping for us
            if self.is_special_container():
                padding = ATOM_SPECIAL_CONTAINER_TYPES[self.type]['padding']
                self.__source_stream.seek(padding, os.SEEK_CUR)
                self.__load_children()
            elif self.is_container():
                self.__load_children()
            
            # Skip over the rest of the atom
            self.__source_stream.seek(self.__offset + self.__size)
        elif type is not None:
            self.type = type
    
    def __load_children(self):
        # If we don't have enough data left for another atom, abort
        while calcsize(ATOM_HEADER['basic']) <= (self.__size - self.tell()):
            child = Atom(stream=self.__source_stream, offset=self.__source_stream.tell())
            self.append(child)
    
    def __del__(self):
        if hasattr(self, '_Atom__data'):
            self.__data.close()
            self.__data = None
    
    def is_container(self):
        return self.is_special_container() or self.type in ATOM_CONTAINER_TYPES
    
    def is_special_container(self):
        return self.type in ATOM_SPECIAL_CONTAINER_TYPES
    
    def __repr__(self):
        if not self.is_container():
            return self.type
        
        repr = '%s: %s' % (self.type, super(Atom, self).__repr__())
        return repr
    
    def __eq__(self, other):
        equal = False
        
        # If types match on a container, delegate checking to the base
        # If types match for a data atom, delegate to __data if it exists
        # TODO: Equality for loaded data atoms
        if other.type != self.type:
            equal = False
        if (other.type == self.type) and self.is_container():
            equal = super(Atom, self).__eq__(other)
        elif (other.type == self.type) \
         and hasattr(self, '_Atom__data') \
         and hasattr(other, '_Atom__data'):
            equal = (self.__data == other.__data)
        elif (other.type == self.type) \
         and not hasattr(self, '_Atom__data') \
         and not hasattr(other, '_Atom__data'):
            equal = True
        
        return equal
    
    # Container/Sequence behaviours
    
    # NOTE: Early type-checking kinda breaks duck-typing and isn't very
    #       Pythonesque. Maybe we should only check this stuff on saving?
    
    def append(self, x):
        if not self.is_container():
            raise ValueError, 'Cannot append items to non-container atoms'
        elif not isinstance(x, Atom):
            raise TypeError, 'an Atom is required'
        
        super(Atom, self).append(x)
    
    def insert(self, i, x):
        if not self.is_container():
            raise ValueError, 'Cannot insert items into non-container atoms'
        elif not isinstance(x, Atom):
            raise TypeError, 'an Atom is required'
        
        super(Atom, self).insert(i, x)
    
    def __setitem__(self, key, value):
        # NOTE: No need to check if self.is_container() because self[0] et al.
        #       are invalid; the only ways to load items are append(),
        #       insert(), and __setslice__()
        if not isinstance(value, Atom):
            raise TypeError, 'an Atom is required'
        
        super(Atom, self).__setitem__(key, value)
    
    def __setslice__(self, i, j, sequence):
        if not self.is_container():
            raise ValueError, 'Cannot set slices of non-container atoms'
        
        if 0 < len([item for item in sequence if not isinstance(item, Atom)]):
                raise TypeError, 'all items in slice are required to be Atoms'
        
        super(Atom, self).__setslice__(i, j, sequence)
    
    
    def get_all_descendants(self):
        # TODO: Is there a faster way to do this?
        descendants = []
        if self.is_container():
            for child in self:
                descendants.append(child)
                descendants += child.get_all_descendants()
        
        return descendants
    
    def get_children_of_type(self, type):
        children = []
        if self.is_container():
            [children.append(child) for child in self if child.type == type]
        
        return children
    
    def get_descendants_of_type(self, type):
        descendants = []
        if self.is_container():
            for child in self:
                if child.type == type:
                    descendants.append(child)
                descendants += child.get_descendants_of_type(type)
        
        return descendants
    
    
    # File-like behaviours
    
    def next(self):
        if hasattr(self, '_Atom__data'):
            return self.__data.next()
        return ''
    
    def tell(self):
        if hasattr(self, '_Atom__data'):
            return self.__data.tell()
        elif hasattr(self, '_Atom__source_stream'):
            return self.__source_stream.tell() - self.__offset
        return 0
    
    def read(self, size=-1):
        if hasattr(self, '_Atom__data'):
            return self.__data.read(size)
        elif hasattr(self, '_Atom__source_stream'):
            if 0 == self.tell():
                self.seek(0)
            elif self.tell() == self.__size:
                self.seek(0, os.SEEK_END)
            
            return self.__source_stream.read(self.__size - self.tell())
        return ''
    
    def readline(self, size=-1):
        if hasattr(self, '_Atom__data'):
            return self.__data.readline(size)
        return ''
    
    def readlines(self, size=0):
        if hasattr(self, '_Atom__data'):
            return self.__data.readlines(size)
        return []
    
    def seek(self, offset, whence=os.SEEK_SET):
        if hasattr(self, '_Atom__data'):
            self.__data.seek(offset, whence)
        elif hasattr(self, '_Atom__source_stream') \
        and os.SEEK_SET == whence:
            self.__source_stream.seek(self.__offset + offset, whence)
        elif hasattr(self, '_Atom__source_stream') \
        and os.SEEK_END == whence:
            source_offset = self.__offset + self.__size + offset
            self.__source_stream.seek(source_offset)
        elif hasattr(self, '_Atom__source_stream') \
        and os.SEEK_CUR == whence:
            source_offset = self.__offset + self.tell() + offset
            self.__source_stream.seek(source_offset)
    
    def truncate(self, size=None):
        if size is None:
            size = self.tell()
        if hasattr(self, '_Atom__data'):
            self.__data.truncate(size)
    
    def write(self, str):
        if self.is_container():
            raise ValueError, 'Cannot write data to container atoms'
        
        if not hasattr(self, '_Atom__data'):
            # Store starting location in case we already have content
            initial_location = self.tell()
            
            # Store in a file in case of large data
            self.__data = tempfile.TemporaryFile()
            
            # Copy old data to tempfile
            if hasattr(self, '_Atom__source_stream'):
                self.__source_stream.seek(get_header_size(self.__size))
                self.__data.write(self.__source_stream.read(self.__size))
                self.__data.seek(0)
                self.seek(initial_location)
        
        self.__data.write(str)
    
    def writelines(self, sequence):
        if self.is_container():
            raise ValueError, 'Cannot write data to container atoms'
        
        if not hasattr(self, '_Atom__data'):
            # Store in a file in case of large data
            self.__data = tempfile.TemporaryFile()
        
        self.__data.writelines(sequence)
    
    # Sequence and file-like behaviours
    
    def __iter__(self):
        if not self.is_container() and hasattr(self, '_Atom__data'):
            return iter(self.__data)
        elif not self.is_container() and hasattr(self, '_Atom__source_stream'):
            # HACK: Slurp data into a temporary stream
            iterable_stream = StringIO.StringIO()
            prior_pos = self.__source_stream.tell()
            self.seek(0)
            iterable_stream.write(self.read())
            iterable_stream.seek(0)
            self.__source_stream.seek(prior_pos)
            return iter(iterable_stream)
        
        return super(Atom, self).__iter__()
    
    # Storage
    
    def save(self, stream):
        # HACK: Dumping into content allows us to use len() to get content
        #       size easily, but will fall over for large content
        content = ''
        
        # Get content for this atom
        if self.is_container():
            content_stream = StringIO.StringIO()
            [atom.save(content_stream) for atom in self]
            
            content_stream.seek(0)
            content = content_stream.read()
        elif hasattr(self, '_Atom__data') \
        or hasattr(self, '_Atom__source_stream'):
            # Store the initial position so we can seek back to there for
            # other users of our data
            initial_position = self.tell()
            
            self.seek(0)
            content = self.read()
            
            self.seek(initial_position)
        
        stream.write(render_atom_header(self.type, len(content)))
        if 0 < len(content):
            stream.write(content)
    

