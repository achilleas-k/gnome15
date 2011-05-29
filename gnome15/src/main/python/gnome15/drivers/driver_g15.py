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

import gnome15.g15driver as g15driver
import gnome15.g15devices as g15devices
import gnome15.g15globals as g15globals
import socket
import cairo
import ImageMath
import Image
from threading import Thread
from threading import Lock
import struct
import time
import logging
import asyncore
import traceback
import sys
logger = logging.getLogger("driver")

# Driver information (used by driver selection UI)
name="G15Daemon"
id="g15"
description="For use with the Logitech G15v1, G15v2, G13, G510 and G110. This driver uses g15daemon, available from " + \
            "<a href=\"http://www.g15tools.com/\">g15tools</a>. The g15deaemon service " + \
            "must be installed and running when starting Gnome15. Note, you may have to patch " + \
            "g15daemon and tools for support for newer models."
has_preferences=False


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
CLIENT_CMD_KB_BACKLIGHT_COLOR = ord('r')

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


color_backlight_control = g15driver.Control("backlight_colour", "Keyboard Backlight Colour", (0, 0, 0), hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
backlight_control = g15driver.Control("keyboard_backlight", "Keyboard Backlight Level", 0, 0, 2, hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
lcd_backlight_control = g15driver.Control("lcd_backlight", "LCD Backlight Level", 0, 0, 2, hint = g15driver.HINT_SHADEABLE)
lcd_contrast_control = g15driver.Control("lcd_contrast", "LCD Contrast", 0, 0, 7)
invert_control = g15driver.Control("invert_lcd", "Invert LCD", 0, 0, 1, hint = g15driver.HINT_SWITCH )

controls = {
  g15driver.MODEL_G15_V1 : [ backlight_control, lcd_contrast_control, lcd_backlight_control, invert_control ], 
  g15driver.MODEL_G15_V2 : [ backlight_control, lcd_backlight_control, invert_control ],
  g15driver.MODEL_G13 : [ backlight_control, lcd_backlight_control, invert_control ],
  g15driver.MODEL_G510 : [ color_backlight_control, invert_control ],
  g15driver.MODEL_Z10 : [ backlight_control, lcd_backlight_control, invert_control ],
  g15driver.MODEL_G110 : [ color_backlight_control ],
            }   

def fix_sans_style(root):
    for element in root.iter():
        style = element.get("style")
        if style != None:
            element.set("style", style.replace("font-family:Sans","font-family:%s" % g15globals.fixed_size_font_name))
            
class G15Dispatcher(asyncore.dispatcher):
    def __init__(self, map,  conn, callback = None):
        self.key_stage = 0
        self.out_buffer  = ""
        self.oob_buffer  = ""
        self.recv_buffer = ""
        self.callback = callback;
        self.reverse_map = {}
        for k in KEY_MAP.keys():
            self.reverse_map[KEY_MAP[k]] = k
        self.received_handshake = False
        asyncore.dispatcher.__init__(self, sock=conn, map = map)
        
    def wait_for_handshake(self):
        while not self.received_handshake:
            time.sleep(0.5)
        
    def handle_close(self):
        self.received_handshake = True
        
    def handle_expt(self):
        data = self.socket.recv(1, socket.MSG_OOB)
        if len(data) > 0:
            val = ord(data[0])
            if val & CLIENT_CMD_BACKLIGHT:
                level = val - CLIENT_CMD_BACKLIGHT
            elif val & CLIENT_CMD_KB_BACKLIGHT:
                level = val - CLIENT_CMD_KB_BACKLIGHT
            elif val & CLIENT_CMD_CONTRAST:
                logger.warning("Ignoring contrast command")
            else:
                logger.warning("Ignoring unknown OOB command")
            
    def handle_key(self, data):
        if self.key_stage == 0:
            self.last_key  = struct.unpack("<L",data)[0]            
            self.callback(self.convert_from_g15daemon_code(self.last_key), g15driver.KEY_STATE_DOWN)
            self.key_stage = 1
        elif self.key_stage == 1:
            # The next 4 bytes should be zero?
            val = struct.unpack("<L",data)[0]
            if val != 0:
                logger.warning("Expected zero keyboard event")
            else:
                self.key_stage = 2
        elif self.key_stage == 2:
            # If the next 4 bytes are zero, then this is a normal key press / release, if not,
            # a second key was pressed before the first was releaseval_3 = struct.unpack("<L",received)[0]
            # This will loop until zero is received
            val = struct.unpack("<L",data)[0]
            if val == 0:
                # Break out
                self.key_stage = 3
            else: 
                self.last_key = val
                self.callback(self.convert_from_g15daemon_code(self.last_key), g15driver.KEY_STATE_UP)
                # Repeat
                self.key_stage == 1
        elif self.key_stage == 3:
            # Final value should be zero, indicating key release             
            val = struct.unpack("<L", data)[0]
            if val != 0:
                logger.warning("Expected zero keyboard event")
                
            self.callback(self.convert_from_g15daemon_code(self.last_key), g15driver.KEY_STATE_UP)
            self.key_stage = 0

    def handle_read(self):
        try :
            
            if len(self.recv_buffer) == 0:
                received = self.recv(8192)
                if len(received) >0:
                    self.recv_buffer += received
            
            # Have we collected enough for a key? 
            # TODO is this even neccesary, will we always get those 4 bytes when they are available
            if self.received_handshake:
                while len(self.recv_buffer) > 3:
                    data = self.get_data(4)
                    if data:
                        self.handle_key(data)
            else:
                data = self.get_data(16)
                if data:
                    if data != "G15 daemon HELLO":
                        raise Exception("Excepted G15 daemon handshake.")
                    self.out_buffer = "GBUF"
                    self.received_handshake = True
        except Exception as e:
            self.oob_buffer = ""
            self.out_buffer = ""
            traceback.print_exc(file=sys.stderr)
            raise e
        
    def get_data(self, required_length):
        if len(self.recv_buffer) >= required_length:
            data = self.recv_buffer[0:required_length]
            self.recv_buffer = self.recv_buffer[required_length:]
            return data
                
    def writable(self):
        return len(self.oob_buffer) > 0 or len(self.out_buffer) > 0
    
    def send_with_options(self, buffer, options = 0):
        try:
            return self.socket.send(buffer, options)
        except socket.error, why:
            self.oob_buffer = ""
            if why.args[0] == EWOULDBLOCK:
                return 0
            elif why.args[0] in (ECONNRESET, ENOTCONN, ESHUTDOWN, ECONNABORTED):
                self.handle_close()
                return 0
            else:
                raise

    def handle_write(self):
        if len(self.out_buffer) > 0:
            sent = self.send(self.out_buffer)
            self.out_buffer = self.out_buffer[sent:]
            return sent
        elif len(self.oob_buffer) > 0:
            s = 0
            for c in self.oob_buffer:
                s += self.send_with_options(c, socket.MSG_OOB)
            self.oob_buffer = self.oob_buffer[s:]
            
    def convert_from_g15daemon_code(self, code):
        keys = []
        for key in self.reverse_map:
            if code & key != 0:
                keys.append(self.reverse_map[key])
        return keys   

class G15Async(Thread):
    def __init__(self, map):
        Thread.__init__(self)
        self.name = "G15Async"
        self.setDaemon(True)
        self.map = map
        
    def run(self):  
        asyncore.loop(timeout = 0.01, map = self.map)

class Driver(g15driver.AbstractDriver):

    def __init__(self, host = 'localhost', port= 15550, on_close = None):
        g15driver.AbstractDriver.__init__(self, "g15")
        self.remote_host=host
        self.lock = Lock()
        self.remote_port=port
        self.dispatcher = None
        self.on_close = on_close
        self.socket = None
        self.connected = False
        self._init_driver()
        self.async = None
        
    def get_size(self):
        return self.device.lcd_size
        
    def get_bpp(self):
        return self.device.bpp
    
    def get_controls(self):
        return controls[self.device.model_name]
    
    def get_antialias(self):
        return cairo.ANTIALIAS_NONE
    
    def get_key_layout(self):
        return self.device.key_layout
    
    def send(self, data, opt = None):
        if opt == socket.MSG_OOB:
            self.dispatcher.oob_buffer += data
        else:
            self.dispatcher.out_buffer += data
    
    def on_update_control(self, control):
        level = control.value
        if control == backlight_control:
            self.check_control(control)
            self.send(chr(CLIENT_CMD_KB_BACKLIGHT  + level),socket.MSG_OOB)
        elif control == lcd_backlight_control:
            self.check_control(control)
            self.send(chr(CLIENT_CMD_BACKLIGHT + level),socket.MSG_OOB)
        elif control == lcd_contrast_control:
            self.check_control(control)
            self.send(chr(CLIENT_CMD_CONTRAST + level),socket.MSG_OOB)
        elif control == color_backlight_control:
            self.lock.acquire()        
            try :           
                self.send(chr(CLIENT_CMD_KB_BACKLIGHT_COLOR),socket.MSG_OOB)
                time.sleep(0.1);
                self.send(chr(level[0]),socket.MSG_OOB)
                time.sleep(0.1);
                self.send(chr(level[1]),socket.MSG_OOB)
                time.sleep(0.1);
                self.send(chr(level[2]),socket.MSG_OOB)
            finally:
                self.lock.release()
                
    def check_control(self, control):
        if control.value > control.upper:
            control.value = control.upper
        elif control.value < control.lower:
            control.value = control.lower
            
    def get_name(self):
        return "g15daemon driver"
    
    def get_model_names(self):
        return [ g15driver.MODEL_G15_V1, g15driver.MODEL_G15_V2, g15driver.MODEL_G110, g15driver.MODEL_G510, g15driver.MODEL_G13 ]
    
    def get_model_name(self):
        return self.device.model_name
    
    def disconnect(self):
        if not self.is_connected():
            raise Exception("Already disconnected")
        self.connected = False
        if self.dispatcher != None:
            self.dispatcher.running = False
        self.socket.close()
        self.socket = None
        self.dispatcher = None
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
        
        self._init_driver()
        
        map = {}
            
        self.socket  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5.0)
        self.socket.connect((self.remote_host, self.remote_port))
        
        self.dispatcher = G15Dispatcher(map, self.socket)
        self.async = G15Async(map).start()   
        self.dispatcher.wait_for_handshake()  
        self.connected = True
        
    def set_mkey_lights(self, lights):
        self.send(chr(CLIENT_CMD_MKEY_LIGHTS  + lights),socket.MSG_OOB)
        
    def grab_keyboard(self, callback):
        self.dispatcher.callback = callback
        self.send(chr(CLIENT_CMD_KEY_HANDLER),socket.MSG_OOB)
            
    def process_svg(self, document):  
        fix_sans_style(document.getroot())
        
    def paint(self, img):
        if not self.is_connected():
            return
        
        # Just return if the device has no LCD
        if self.device.bpp == 0:
            return None
             
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
            
            invert_control = self.get_control("invert_lcd")
            if invert_control.value == 0:            
                pil_img = pil_img.point(lambda i: 1^i)
    
            # Covert image buffer to string
            buf = ""
            for x in list(pil_img.getdata()): 
                buf += chr(x)
                
            if len(buf) != self.device.lcd_size[0] * self.device.lcd_size[1]:
                logger.warning("Invalid buffer size")
            else:
                try : 
                    self.send(buf)
                except IOError as (errno, strerror):
                    logger.error("Failed to send buffer. %d: %s" % ( errno, strerror ) )                    
                    traceback.print_exc(file=sys.stderr)
                    self.disconnect()
        finally:
            self.lock.release()
            
    def _init_driver(self):        
        self.device = g15devices.find_device(self.get_model_names())
        if self.device == None:
            raise Exception("No device supported by the g15daemon driver could be found.")