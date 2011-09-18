#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) Brett Smith <tanktarta@blueyonder.co.uk>                      |
#        |                                                                             |
#        | This program is free software; you can redistribute it and/or               |
#        | modify it under the terms of the GNU General Public License                 |
#        | as published by the Free Software Foundation; either version 2              |
#        | of the License, or (at your option) any later version.                      |
#        |                                                                             |
#        | This program is distributed in the hope that it will be useful,             |
#        | but WITHOUT ANY WARRANTY; without even the implied warranty of              |
#        | MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               |
#        | GNU General Public License for more details.                                |
#        |                                                                             |
#        | You should have received a copy of the GNU General Public License           |
#        | along with this program; if not, write to the Free Software                 |
#        | Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA. |
#        +-----------------------------------------------------------------------------+

from ctypes import *
libatasmart = cdll.LoadLibrary("libatasmart.so.4")

class SkDisk(Structure):
    _fields_ = [ ("name", c_char_p),
                 ("type", c_int),
                                  
                 ("t_size", c_uint64),
                 
                 ("identify", c_uint8),
                 ("smart_data", c_uint8),
                 ("smart_thresholds", c_uint8),
                 
                 ("smart_initialized", c_uint),
                 
                 ("identify_valid", c_uint),
                 ("smart_data_valid", c_uint),
                 ("smart_thresholds", c_uint),
                 
                 ("blob_smart_status", c_uint),
                 ("blob_smart_status_valid", c_uint),
                 
                 ("attribute_verification", c_uint),
                 
                 ("identify_parsed_data", c_uint),
                 ("smart_parsed_data", c_uint),
                 
                 ("blob", c_void_p),
                  ]
    
libatasmart.sk_disk_open.argtypes = [ c_char_p, POINTER(POINTER(SkDisk)) ]
    
def sk_disk_open(name):
    d = SkDisk()
    ret = libatasmart.sk_disk_open(POINTER(c_char)(), byref(POINTER(d)))
    if ret != 0:
        raise Exception("Error %d" % ret)
    return d

#def sk_disk_set_blob(sk_disk, blob):    
#    pi = c_char_p(blob)
#    return libatasmart.sk_disk_set_blob(pointer(sk_disk), pi , len(blob))
#
#def sk_disk_smart_get_temperature(sk_disk):
#    kelvin = c_uint64()
#    ret = libatasmart.sk_disk_smart_get_temperature(pointer(sk_disk), pointer(kelvin))
##    if ret != 0:
##        raise Exception("Error %d" % ret)
#    return kelvin.value