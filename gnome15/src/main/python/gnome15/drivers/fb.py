#!/usr/bin/env python
 
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
from fcntl import ioctl
import mmap
import os

FBIOGET_VSCREENINFO=0x4600
FBIOPUT_VSCREENINFO=0x4601
FBIOGET_FSCREENINFO=0x4602

class fb_fix_screeninfo(Structure):
    _fields_ = [
                ("id", c_char * 16),
                ("smem_start", c_ulong), 
                ("smem_len", c_int, 32), 
                ("type", c_int, 32),
                ("type_aux", c_int, 32),
                ("visual", c_int, 32),
                ("xpanstep", c_int, 16),
                ("ypanstep", c_int, 16),
                ("ywrapstep", c_int, 16),
                ("line_length", c_int, 32),
                ("mmio_start", c_ulong),
                ("mmio_len", c_int, 32),
                ("accel", c_int, 32),
                ("reserved", c_ushort * 3),
                ]
    
class fb_bitfield(Structure):
    _fields_ = [
                ("offset", c_int, 32),
                ("length", c_int, 32),
                ("msb_right", c_int, 32),
                ]
    
    def __repr__(self):
        return "bitfield [ offset = %d, length = %d, msb_right = %d ]" % ( self.offset, self.length, self.msb_right )
    
class fb_var_screeninfo(Structure):
    _fields_ = [
                ( "xres", c_int, 32),
                ( "yres", c_int, 32),
                ( "xres_virtual", c_int, 32),
                ( "yres_virtual", c_int, 32),
                ( "xoffset", c_int, 32),
                ( "yoffset", c_int, 32),
                ( "bits_per_pixel", c_int, 32),
                ( "grayscale", c_int, 32),
                ( "red", fb_bitfield),
                ( "green", fb_bitfield),
                ( "blue", fb_bitfield),
                ( "transp", fb_bitfield),
                ( "nonstd", c_int, 32),
                ( "activate", c_int, 32),
                ( "height", c_int, 32),
                ( "width", c_int, 32),
                ( "accel_flags", c_int, 32),
                ( "pixclock", c_int, 32),
                ( "left_margin", c_int, 32),
                ( "right_margin", c_int, 32),
                ( "upper_margin", c_int, 32),
                ( "lower_margin", c_int, 32),
                ( "hsync_len", c_int, 32),
                ( "vsync_len", c_int, 32),
                ( "sync", c_int, 32),
                ( "vmode", c_int, 32),
                ( "rotate", c_int, 32),
                ( "reserved", c_ulong * 5),
                ]
    
class fb_device():
    def __init__(self, device_name, mode = os.O_RDWR):
        self.device_file = os.open(device_name, os.O_RDWR)
        self.buffer = None
        self.invalidate()
        
    def invalidate(self):
        if self.buffer != None:
            self.buffer().close()
        self.buffer = mmap.mmap(self.device_file, self.get_screen_size(), mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
        
    def get_fixed_info(self):
        fixed_info = fb_fix_screeninfo()
        if ioctl(self.device_file, FBIOGET_FSCREENINFO, fixed_info):
            raise Exception("Error reading fixed information.\n")
        return fixed_info
    
    def get_var_info(self):
        variable_info = fb_var_screeninfo()
        if ioctl(self.device_file, FBIOGET_VSCREENINFO, variable_info):
            raise Exception("Error reading variable information.\n")
        return variable_info
    
    def close(self):
        if self.buffer != None:
            self.buffer.close()
            self.buffer = None
        os.close(self.device_file)
    
    def __del__(self):
        self.close()
    
    def get_screen_size(self):
        variable_info = self.get_var_info()
        return variable_info.xres * variable_info.yres * variable_info.bits_per_pixel / 8
    
    def dump(self):
        
        fixed_info = self.get_fixed_info()
        
        print "--------------" 
        print "Fixed"
        print "--------------"
        print "id:", fixed_info.id
        print "smem_start:", fixed_info.smem_start
        print "smem_len:", fixed_info.smem_len
        print "type:", fixed_info.type
        print "type_aux:", fixed_info.type_aux
        print "visual:", fixed_info.visual
        print "xpanstep:", fixed_info.xpanstep
        print "ypanstep:", fixed_info.ypanstep
        print "ywrapstep:", fixed_info.ywrapstep
        print "line_length:", fixed_info.line_length
        print "mmio_start:", fixed_info.mmio_start
        print "mmio_len:", fixed_info.mmio_len
        print "accel:", fixed_info.accel
        
        
        variable_info = self.get_var_info()
               
        print "--------------" 
        print "Variable"
        print "--------------"
        print "xres:",variable_info.xres
        print "yres:",variable_info.yres
        print "xres_virtual:",variable_info.xres_virtual
        print "yres_virtual:",variable_info.yres_virtual
        print "xoffset:",variable_info.xoffset
        print "yoffset:",variable_info.yoffset
        print "bits_per_pixel:",variable_info.bits_per_pixel
        print "grayscale:",variable_info.grayscale
        print "red:",variable_info.red
        print "green:",variable_info.green
        print "blue:",variable_info.blue
        print "transp:",variable_info.transp
        print "activate:",variable_info.activate
        print "height:",variable_info.height
        print "width:",variable_info.width
        print "accel_flags:",variable_info.accel_flags
        print "pixclock:",variable_info.pixclock
        print "left_margin:",variable_info.left_margin
        print "right_margin:",variable_info.right_margin
        print "update_margin:",variable_info.upper_margin
        print "lower_margin:",variable_info.lower_margin
        print "hsync_len:",variable_info.hsync_len
        print "vsync_len:",variable_info.vsync_len
        print "sync:",variable_info.sync
        print "vmode:",variable_info.vmode
        print "rotate:",variable_info.rotate
   
   
if __name__ == "__main__":     
        
    device = fb_device("/dev/fb1")
    print "Screen bytes: " + str(device.get_screen_size())
    device.dump()