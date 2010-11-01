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

import gnome15.g15_driver as g15driver
import socket
import cairo
import ImageMath
import Image
from threading import Thread
from threading import Lock
import struct

# Driver information (used by driver selection UI)
name="G15Daemon"
id="g15"
description="For use with the Logitech G15, this driver uses g15daemon, available from " + \
            "<a href=\"http://www.g15tools.com/\">g15tools</a>. The g15deaemon service " + \
            "must be installed and running when starting Gnome15."
has_preferences=False


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

KEY_MAP = {
        g15driver.G_KEY_G1  : 1<<0,
        g15driver.G_KEY_G2  : 1<<1,
        g15driver.G_KEY_G3  : 1<<2,
        g15driver.G_KEY_G4  : 1<<3,
        g15driver.G_KEY_G5  : 1<<4,
        g15driver.G_KEY_G6  : 1<<5,
        g15driver.G_KEY_G7  : 1<<6,
        g15driver.G_KEY_G8  : 1<<7,
        g15driver.G_KEY_G9  : 1<<8,
        g15driver.G_KEY_G10 : 1<<9,
        g15driver.G_KEY_G11 : 1<<10,
        g15driver.G_KEY_G12 : 1<<11,
        g15driver.G_KEY_G13 : 1<<12,
        g15driver.G_KEY_G14 : 1<<13,
        g15driver.G_KEY_G15 : 1<<14,
        g15driver.G_KEY_G16 : 1<<15,
        g15driver.G_KEY_G17 : 1<<16,
        g15driver.G_KEY_G18 : 1<<17,
        
        g15driver.G_KEY_M1  : 1<<18,
        g15driver.G_KEY_M2  : 1<<19,
        g15driver.G_KEY_M3  : 1<<20,
        g15driver.G_KEY_MR  : 1<<21,
        
        g15driver.G_KEY_L1  : 1<<22,
        g15driver.G_KEY_L2  : 1<<23,
        g15driver.G_KEY_L3  : 1<<24,
        g15driver.G_KEY_L4  : 1<<25,
        g15driver.G_KEY_L5  : 1<<26,
        
        g15driver.G_KEY_LIGHT : 1<<27
        }


def fix_sans_style(root):
    for element in root.iter():
        style = element.get("style")
        if style != None:
            element.set("style", style.replace("font-family:Sans","font-family:Fixed"))

class EventReceive(Thread):
    def __init__(self, socket, callback):
        Thread.__init__(self)
        self.name = "KeyboardReceiveThread"
        self.socket = socket;
        self.callback = callback;
        self.setDaemon(True)
        self.reverse_map = {}
        for k in KEY_MAP.keys():
            self.reverse_map[KEY_MAP[k]] = k
        
    def run(self):
        self.running = True
        while self.running:
            try :
                val = struct.unpack("<L",self.socket.recv(4))[0]            
                self.callback(self.convert_from_g15daemon_code(val), g15driver.KEY_STATE_DOWN)
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
                    self.callback(self.convert_from_g15daemon_code(val), g15driver.KEY_STATE_UP)
                
                # Final value should be zero, indicating key release             
                val_4 = struct.unpack("<L",self.socket.recv(4))[0]
                if val_4 != 0:
                    print "WARNING: Expected zero keyboard event"
                self.callback(self.convert_from_g15daemon_code(val), g15driver.KEY_STATE_UP) 
            except socket.timeout:
                # Timeout, allow another pass
                pass
            
    def convert_from_g15daemon_code(self, code):
        keys = []
        for key in self.reverse_map:
            if code & key != 0:
                keys.append(self.reverse_map[key])
        return keys


backlight_control = g15driver.Control("keyboard-backlight", "Keyboard Backlight Level", 0, 0, 2, hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
invert_control = g15driver.Control("invert-lcd", "Invert LCD", 0, 0, 1, hint = g15driver.HINT_SWITCH )
controls = [ backlight_control, invert_control ]  

g15v1_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3 ],
                  [ g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6 ],
                  [ g15driver.G_KEY_G7, g15driver.G_KEY_G8, g15driver.G_KEY_G9 ],
                  [ g15driver.G_KEY_G10, g15driver.G_KEY_G11, g15driver.G_KEY_G12 ],
                  [ g15driver.G_KEY_G13, g15driver.G_KEY_G14, g15driver.G_KEY_G15 ],
                  [ g15driver.G_KEY_G16, g15driver.G_KEY_G17, g15driver.G_KEY_G18 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4,  g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]

g15v2_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3 ],
                  [ g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4,  g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]          

g13_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3, g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6, g15driver.G_KEY_G7 ],
                  [ g15driver.G_KEY_G8, g15driver.G_KEY_G9, g15driver.G_KEY_G10, g15driver.G_KEY_G11, g15driver.G_KEY_G12, g15driver.G_KEY_G13, g15driver.G_KEY_G14 ],
                  [ g15driver.G_KEY_G15, g15driver.G_KEY_G16, g15driver.G_KEY_G17, g15driver.G_KEY_G18, g15driver.G_KEY_G19 ],
                  [ g15driver.G_KEY_G20, g15driver.G_KEY_G21, g15driver.G_KEY_G22 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4,  g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]          
          

class Driver(g15driver.AbstractDriver):

    def __init__(self, host = 'localhost', port= 15550, on_close = None):
        g15driver.AbstractDriver.__init__(self, "g15")
        self.init_string="GBUF"
        self.remote_host=host
        self.lock = Lock()
        self.remote_port=port
        self.thread = None
        self.on_close = on_close
        self.socket = None
        self.connected = False
        
    def get_size(self):
        return (MAX_X, MAX_Y)
        
    def get_bpp(self):
        return 1
    
    def get_controls(self):
        return controls
    
    def get_antialias(self):
        return cairo.ANTIALIAS_NONE
    
    def get_key_layout(self):
        return g15v1_key_layout
    
    def update_control(self, control):
        if control == backlight_control: 
            level = control.value
            if level > 2:
                level = 2
            elif level < 0:
                level = 0
            self.socket.send(chr(CLIENT_CMD_KB_BACKLIGHT  + level),socket.MSG_OOB)
    
    def get_model_names(self):
        return [ g15driver.MODEL_G15_V1 ]
    
    def get_model_name(self):
        return g15driver.MODEL_G15_V1
    
    def disconnect(self):
        if not self.is_connected():
            raise Exception("Already disconnected")
        self.connected = False
        if self.thread != None:
            self.thread.running = False
        self.socket.close()
        self.socket = None
        self.thread = None
        if self.on_close != None:
            self.on_close()
    
    def is_connected(self):
        return self.connected
        
    def reconnect(self):
        if self.is_connected():
            self.disconnect()
        self.connect()
        
    def connect(self):
        if self.is_connected():
            raise Exception("Already connected")
        self.socket  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5.0)
        self.socket.connect((self.remote_host, self.remote_port))
        if self.socket.recv(16) != "G15 daemon HELLO":
            raise Exception("Communication error with server")
        self.socket.send(self.init_string)        
        self.connected = True
        
    def set_mkey_lights(self, lights):
        self.socket.send(chr(CLIENT_CMD_MKEY_LIGHTS  + lights),socket.MSG_OOB)
        
    def grab_keyboard(self, callback):
        if self.thread == None:
            self.thread = EventReceive(self.socket, callback)
            self.thread.start()
        else:
            self.thread.callback = callback
        self.socket.send(chr(CLIENT_CMD_KEY_HANDLER),socket.MSG_OOB)
            
    def process_svg(self, document):  
        fix_sans_style(document.getroot())
        
    def paint(self, img):
        if not self.is_connected():
            return
             
        self.lock.acquire()
        try :           
            size = self.get_size()
            
            # Paint to 565 image provided into an ARGB image surface for PIL's benefit. PIL doesn't support 565?
            argb_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size[0], size[1])
            argb_context = cairo.Context(argb_surface)
            argb_context.set_source_surface(img)
            argb_context.paint()
            
            # Now convert the ARGB to a PIL image so it can be converted to a 1 bit monochrome image, with all
            # colours dithered. It would be nice if Cairo could do this :( Any suggestions? 
            pil_img = Image.frombuffer("RGBA", size, argb_surface.get_data(), "raw", "RGBA", 0, 1)
            pil_img = ImageMath.eval("convert(pil_img,'1')",pil_img=pil_img)
            pil_img = ImageMath.eval("convert(pil_img,'P')",pil_img=pil_img)
            pil_img = pil_img.point(lambda i: i >= 250,'1')
            
            invert_control = self.get_control("invert-lcd")
            if invert_control.value == 0:            
                pil_img = pil_img.point(lambda i: 1^i)
    
            # Covert image buffer to string
            buf = ""
            for x in list(pil_img.getdata()): 
                buf += chr(x)
                
            if len(buf) != MAX_X * MAX_Y:
                print "Invalid buffer size"
            else:
                self.socket.sendall(buf)
        finally:
            self.lock.release()