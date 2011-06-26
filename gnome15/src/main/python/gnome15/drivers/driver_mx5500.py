#!/usr/bin/env python
from gnome15.drivers.driver_g15 import invert_control
 
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
import gnome15.g15globals as g15globals
import gnome15.g15util as g15util
import gtk
import os.path
import socket
import cairo
import gconf
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
name="MX5500"
id="mx5500"
description="For use with the Logitech G15v1, G15v2, G13, G510 and G110. This driver uses mx5500tools, available from " + \
            "<a href=\"http://download.gna.org/mx5000tools/\">mx5500tools</a>. The mx5500d service " + \
            "must be installed and running when starting Gnome15."
has_preferences=True

DEFAULT_PORT=15550

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


invert_control = g15driver.Control("invert_lcd", "Invert LCD", 0, 0, 1, hint = g15driver.HINT_SWITCH )

def show_preferences(device, parent, gconf_client):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "driver_g15.glade"))
    g15util.configure_spinner_from_gconf(gconf_client, "/apps/gnome15/%s/g15daemon_port" % device.uid, "Port", DEFAULT_PORT, widget_tree, False)
    return widget_tree.get_object("DriverComponent")

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

    def __init__(self, device, on_close = None):
        g15driver.AbstractDriver.__init__(self, "g15")
        self.device = device
        self.lock = Lock()
        self.dispatcher = None
        self.on_close = on_close
        self.socket = None
        self.connected = False
        self.async = None
        self.change_timer = None
        self.conf_client = gconf.client_get_default()
        
    def get_size(self):
        return self.device.lcd_size
        
    def get_bpp(self):
        return self.device.bpp
    
    def get_controls(self):
        return [ invert_control ]
    
    def get_antialias(self):
        return cairo.ANTIALIAS_NONE
    
    def get_action_keys(self):
        return self.device.action_keys
    
    def get_key_layout(self):
        return self.device.key_layout
    
    def send(self, data, opt = None):
        if opt == socket.MSG_OOB:
            self.dispatcher.oob_buffer += data
        else:
            self.dispatcher.out_buffer += data
    
    def on_update_control(self, control):
        pass
                
    def get_name(self):
        return "mx5500tools driver"
    
    def get_model_names(self):
        return [ g15driver.MODEL_MX5500 ]
    
    def get_model_name(self):
        return self.device.model_id
    
    def on_disconnect(self):
        if not self.is_connected():
            raise Exception("Already disconnected")
        self.conf_client.notify_remove(self.notify_handle)
        self.connected = False
        if self.dispatcher != None:
            self.dispatcher.running = False
        self.socket.close()
        self.socket = None
        self.dispatcher = None
        if self.on_close != None:
            self.on_close(self)
    
    def is_connected(self):
        return self.connected
        
    def reconnect(self):
        if self.is_connected():
            self.disconnect()
        self.connect()
        
    def connect(self):
        if self.is_connected():
            raise Exception("Already connected")
        
        
        port = 15550
        e = self.conf_client.get("/apps/gnome15/%s/g15daemon_port" % self.device.uid)
        if e:
            port = e.get_int()
        
        map = {}
            
        self.socket  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5.0)
        self.socket.connect(("127.0.0.1", port))
        
        self.dispatcher = G15Dispatcher(map, self.socket)
        self.async = G15Async(map).start()   
        self.dispatcher.wait_for_handshake()  
        self.connected = True
        
        self.notify_handle = self.conf_client.notify_add("/apps/gnome15/%s/g15daemon_port" % self.device.uid, self.config_changed, None)
        
    def config_changed(self, client, connection_id, entry, args):
        if self.change_timer != None:
            self.change_timer.cancel()
        self.change_timer = g15util.schedule("ChangeG15DaemonConfiguration", 3.0, self.update_conf)
        
    def update_conf(self):
        logger.info("Configuration changed")
        if self.connected:
            logger.info("Reconnecting")
            self.disconnect()
            self.connect()
        
    def set_mkey_lights(self, lights):
        self.lights = lights
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