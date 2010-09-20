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

"""
Main implementation of a G15Driver that uses g15daemon to control and query the
keyboard
"""

import socket
import time
import ImageMath
from threading import Thread
from threading import Lock
import asyncore
import struct
import g15_driver as g15driver

MAX_X=160
MAX_Y=43

CLIENT_CMD_KB_BACKLIGHT = 0x08
CLIENT_CMD_CONTRAST = 0x40
CLIENT_CMD_BACKLIGHT = 0x80
CLIENT_CMD_GET_KEYSTATE = ord('k')
CLIENT_CMD_KEY_HANDLER = 0x10
CLIENT_CMD_MKEY_LIGHTS = 0x20
CLIENT_CMD_SWITCH_PRIORITIES = ord('p')
CLIENT_CMD_NEVER_SELECT = ord('n')
CLIENT_CMD_IS_FOREGROUND = ord('v')
CLIENT_CMD_IS_USER_SELECTED = ord('u')

class AsyncClient(asyncore.dispatcher):

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect( (host, port) )
        self.buffer = ""
        self.callback = None
        self.hello_received = False
        self.init_sent = False
        self.oob_buffer = ""

    def handle_connect(self):
        pass
    
    def handle_expt(self):
        print "OOB data arrived"
        data = self.socket.recv(1, socket.MSG_OOB)
        print data

    def handle_close(self):
        self.close()

    def handle_read(self):
        if not self.hello_received:
            if self.recv(16) != "G15 daemon HELLO":
                raise Exception("Communication error with server")
            self.hello_received = True
        elif self.init_sent:
            buf = self.recv(4)
            print "Received",buf,len(buf)
            val = struct.unpack("<L",buf)[0]            
            self.callback(val, g15driver.KEY_STATE_DOWN)
            while True:
                # The next 4 bytes should be zero?
                val_2 = struct.unpack("<L",self.recv(4))[0]
                if val_2 != 0:
                    print "WARNING: Expected zero keyboard event"
                
                # If the next 4 bytes are zero, then this is a normal key press / release, if not, a second key was pressed before the first was release
                received = self.recv(4)              
                val_3 = struct.unpack("<L",received)[0]
                if val_3 == 0:
                    break
                val = val_3                        
                self.callback(val, g15driver.KEY_STATE_UP)
            
            # Final value should be zero, indicating key release             
            val_4 = struct.unpack("<L",self.recv(4))[0]
            if val_4 != 0:
                print "WARNING: Expected zero keyboard event"
            self.callback(val, g15driver.KEY_STATE_UP)   
            
    def buffer_text(self, val):
        print "Buffering", len(val),val
        self.buffer += val  
        
    def buf_oob(self, val): 
        print "Buffering OOB", len(val),val
        self.oob_buffer += val     

    def writable(self):
        return (len(self.buffer) > 0) or ( self.hello_received and not self.init_sent ) or len(self.oob_buffer) > 0

    def handle_write(self):
        if len(self.oob_buffer) > 0:
            ch = self.oob_buffer[:1]
            sent = self.socket.send(ch, socket.MSG_OOB)
            print "Sent",sent,"bytes"
            print "Written %d, %d bytes"  % ( ord(ch) ,sent )
            self.oob_buffer = self.oob_buffer[sent:]
        elif self.hello_received and not self.init_sent:
            self.send("GBUF")
            self.init_sent = True
        else:
            sent = self.send(self.buffer)
            print "Written '" + self.buffer[:sent] + "'",sent
            self.buffer = self.buffer[sent:]


class G15Daemon(g15driver.AbstractDriver):

    def __init__(self, host = 'localhost', port= 15550):
        self.init_string="GBUF"
        self.remote_host=host
        self.lock = Lock()
        self.remote_port=port
        self.thread = None
        
    def get_size(self):
        return (MAX_X, MAX_Y)
        
    def get_bpp(self):
        return 1
    
    def get_keyboard_backlight_colours(self):
        return 3
    
    def get_gkeys(self):
        # TODO how to tell difference between old g15 and new g15
        return 18
    
    def get_gkey_layout(self):
        return (3, 3, 3, 3, 3, 3)
    
    def set_keyboard_color(self, color):
        raise NotImplementedError( "Not implemented" )
        
    def connect(self):
        self.handler = AsyncClient(self.remote_host, self.remote_port)
        
    def reconnect(self):
        self.handler.close()
        self.connect()
        
    def __del__(self):
        self.handler.close()

    def switch_priorities(self):
        self.handler.buf_oob(chr(CLIENT_CMD_SWITCH_PRIORITIES))
    
    def is_foreground(self):
        self.handler.buf_oob(chr(CLIENT_CMD_IS_FOREGROUND))
#        received = self.handler.recv(1,socket.MSG_OOB)         
#        return received == "1"
        return True
    
    def never_user_selected(self):
        self.handler.buf_oob(chr(CLIENT_CMD_NEVER_SELECT))
    
    def is_user_selected(self):
        self.handler.buf_oob(chr(CLIENT_CMD_IS_USER_SELECTED))       
#        user_selected = self.socket.recv(1,socket.MSG_OOB)         
#        return user_selected == "1"
        return True
    
    def set_lcd_backlight(self, level):
        self.handler.buf_oob(chr(CLIENT_CMD_BACKLIGHT + level))    
#        level = self.socket.recv(1,socket.MSG_OOB)                  
        return level
            
    def set_contrast(self, level):
        print "Setting contrast",level
        self.handler.buf_oob(chr(CLIENT_CMD_CONTRAST + level))     
#        level = self.handler.recv(1,socket.MSG_OOB)         
        return level
            
    def set_keyboard_backlight(self, level):
        if level > 2:
            level = 2
        elif level < 0:
            level = 0
        self.handler.buf_oob(chr(CLIENT_CMD_KB_BACKLIGHT  + level)) 
            
    def set_mkey_lights(self, lights):
        self.handler.buf_oob(chr(CLIENT_CMD_MKEY_LIGHTS  + lights))
        
    def grab_keyboard(self, callback):
        self.handler.callback = callback
        self.handler.buf_oob(chr(CLIENT_CMD_KEY_HANDLER))

    def paint(self, img):  
        # Convert to black and white and invert        
        img = ImageMath.eval("convert(img,'1')",img=img)
        img = ImageMath.eval("convert(img,'P')",img=img)
        img = img.point(lambda i: i >= 250,'1')
        img = img.point(lambda i: 1^i)

        # Covert image buffer to string
        buf = ""
        for x in list(img.getdata()): 
            buf += chr(x)
            
        if len(buf) != MAX_X * MAX_Y:
            print "Invalid buffer size"
        else:
            self.handler.buffer_text(buf)
