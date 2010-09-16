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


class EventReceive(Thread):
    def __init__(self, socket, callback):
        Thread.__init__(self)
        self.name = "KeyboardReceiveThread"
        self.socket = socket;
        self.callback = callback;
        self.setDaemon(True)
        
    def run(self):
        self.running = True
        while self.running:
            val = struct.unpack("<L",self.socket.recv(4))[0]            
            self.callback(val, g15driver.KEY_STATE_DOWN)
            while True:
                # The next 4 bytes should be zero?
                val_2 = struct.unpack("<L",self.socket.recv(4))[0]
                if val_2 != 0:
                    print "WARNING: Expected zero keyboard event"
                
                # If the next 4 bytes are zero, then this is a normal key press / release, if not, a second key was pressed before the first was release
                received = self.socket.recv(4)              
                val_3 = struct.unpack("<L",received)[0]
                if val_3 == 0:
                    break
                val = val_3                        
                self.callback(val, g15driver.KEY_STATE_UP)
            
            # Final value should be zero, indicating key release             
            val_4 = struct.unpack("<L",self.socket.recv(4))[0]
            if val_4 != 0:
                print "WARNING: Expected zero keyboard event"
            self.callback(val, g15driver.KEY_STATE_UP)            
            
#            if received:              
#                val = struct.unpack("<L",received)[0]
#                
#                # Discard this, i've no idea why we get it        
#                received = self.socket.recv(12)         
#
#                self.jobqueue.run(self.callback, val, g15driver.KEY_STATE_DOWN)
#                
#                received = self.socket.recv(16)   
#                # Discard this, i've no idea why we get it
#                                
#                self.jobqueue.run(self.callback, val, g15driver.KEY_STATE_UP)
#            else:
#                self.running = False

class G15Daemon(g15driver.AbstractDriver):

    def __init__(self, host = 'localhost', port= 15550):
        self.init_string="GBUF"
        self.remote_host=host
        self.lock = Lock()
        self.remote_port=port
        self.thread = None
        self.connect()
        
    def get_size(self):
        return (MAX_X, MAX_Y)
        
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.remote_host, self.remote_port))
        if self.socket.recv(16) != "G15 daemon HELLO":
            raise Exception("Communication error with server")
        self.socket.send(self.init_string)
        
    def reconnect(self):
        self.socket.close()
        self.connect()
        
    def __del__(self):
        self.socket.close()

    def switch_priorities(self):
        self.socket.send(chr(CLIENT_CMD_SWITCH_PRIORITIES),socket.MSG_OOB)
    
    def is_foreground(self):
        self.socket.send(chr(CLIENT_CMD_IS_FOREGROUND),socket.MSG_OOB)
        received = self.socket.recv(1,socket.MSG_OOB)         
        return received == "1"
    
    def never_user_selected(self):
        self.socket.send(chr(CLIENT_CMD_NEVER_SELECT),socket.MSG_OOB)
    
    def is_user_selected(self):
        self.socket.send(chr(CLIENT_CMD_IS_USER_SELECTED),socket.MSG_OOB)       
        user_selected = self.socket.recv(1,socket.MSG_OOB)         
        return user_selected == "1"
    
    def set_lcd_backlight(self, level):
        self.socket.send(chr(CLIENT_CMD_BACKLIGHT + level),socket.MSG_OOB)
            
    def set_contrast(self, level):
        self.socket.send(chr(CLIENT_CMD_CONTRAST + level),socket.MSG_OOB)
            
    def set_keyboard_backlight(self, level):
        if level > 2:
            level = 2
        elif level < 0:
            level = 0
        self.socket.send(chr(CLIENT_CMD_KB_BACKLIGHT  + level),socket.MSG_OOB)
            
    def set_mkey_lights(self, lights):
        self.socket.send(chr(CLIENT_CMD_MKEY_LIGHTS  + lights),socket.MSG_OOB)
        
    def grab_keyboard(self, callback):
        if self.thread == None:
            self.thread = EventReceive(self.socket, callback)
            self.thread.start()
        else:
            self.thread.callback = callback
        self.socket.send(chr(CLIENT_CMD_KEY_HANDLER),socket.MSG_OOB)

    def paint(self, img):     
        self.lock.acquire()
        try :           
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
                self.socket.sendall(buf)
        finally:
            self.lock.release()