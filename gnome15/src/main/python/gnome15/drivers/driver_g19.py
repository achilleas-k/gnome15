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
Main implementation of a G19 Driver that uses g19d to control and query the
keyboard
"""

from cStringIO import StringIO
from gnome15.g15exceptions import NotConnectedException
from threading import RLock, Thread
import cairo
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15globals as g15globals
import gconf
import socket
import gtk
import os.path
import struct
import sys
import traceback
import logging
logger = logging.getLogger("driver")

# Driver information (used by driver selection UI)
name="G19D"
id="g19"
description="For use with the Logitech G19 only, this driver uses <i>G19D</i>, " + \
            "a sub-project of Gnome15. The g19daemon service must be running when " + \
            "starting Gnome15. This method is intended as a temporary measure until " + \
            "kernel support is available for this keyboard."
has_preferences=True

DEFAULT_PORT=15551
MAX_X=320
MAX_Y=240

CLIENT_CMD_KB_BACKLIGHT = "BL"

KEY_MAP = {
        0: g15driver.G_KEY_LIGHT,
        1: g15driver.G_KEY_M1,
        2: g15driver.G_KEY_M2,
        3: g15driver.G_KEY_M3,
        4: g15driver.G_KEY_MR,
        5: g15driver.G_KEY_G1,
        6: g15driver.G_KEY_G2,
        7: g15driver.G_KEY_G3,
        8: g15driver.G_KEY_G4,
        9: g15driver.G_KEY_G5,
        10: g15driver.G_KEY_G6,
        11: g15driver.G_KEY_G7,
        12: g15driver.G_KEY_G8,
        13: g15driver.G_KEY_G9,
        14: g15driver.G_KEY_G10,
        15: g15driver.G_KEY_G11,
        16: g15driver.G_KEY_G12,
        17: g15driver.G_KEY_BACK,
        18: g15driver.G_KEY_DOWN,
        19: g15driver.G_KEY_LEFT,
        20: g15driver.G_KEY_MENU,
        21: g15driver.G_KEY_OK,
        22: g15driver.G_KEY_RIGHT,
        23: g15driver.G_KEY_SETTINGS,
        24: g15driver.G_KEY_UP,
        25: g15driver.G_KEY_WINKEY_SWITCH,
        26: g15driver.G_KEY_NEXT,
        27: g15driver.G_KEY_PREV,
        28: g15driver.G_KEY_STOP,
        29: g15driver.G_KEY_PLAY,
        30: g15driver.G_KEY_MUTE,
        31: g15driver.G_KEY_VOL_UP,
        32: g15driver.G_KEY_VOL_DOWN
    }

"""
"""

def show_preferences(device, parent, gconf_client):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "driver_g19.glade"))
    g15util.configure_spinner_from_gconf(gconf_client, "/apps/gnome15/%s/g19d_port" % device.uid, "Port", DEFAULT_PORT, widget_tree, False)
    return widget_tree.get_object("DriverComponent")

class EventReceive(Thread):
    def __init__(self, socket, callback, on_error):
        Thread.__init__(self)
        self.name = "KeyboardReceiveThread"
        self.socket = socket;
        self.callback = callback;
        self.setDaemon(True)
        self.on_error = on_error
        
    def run(self):
        self.running = True        
        try :
            while self.running:
                try :
                    received = self.socket.recv(1)
                    if received != "":
                        keys = ord(received)
                        key_vals = []
                        for i in range(0, keys):
                            val = KEY_MAP[struct.unpack("<L",self.socket.recv(4))[0]]
                            key_vals.append(val)
                        if len(key_vals):
                            self.callback(key_vals, g15driver.KEY_STATE_DOWN)
                            
                        key_vals = []                    
                        keys = ord(self.socket.recv(1))
                        for i in range(0, keys):
                            val = KEY_MAP[struct.unpack("<L",self.socket.recv(4))[0]]
                            key_vals.append(val)
                        if len(key_vals):
                            self.callback(key_vals, g15driver.KEY_STATE_UP)
                except socket.timeout:
                    pass
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            self.on_error(e)
            
            
# Controls
mkeys_control = g15driver.Control("mkeys", "Memory Bank Keys", 0, 0, 15, hint=g15driver.HINT_MKEYS)
keyboard_backlight_control = g15driver.Control("backlight_colour", "Keyboard Backlight Colour", (0, 0, 0), hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
default_keyboard_backlight_control = g15driver.Control("default_backlight_colour", "Boot Keyboard Backlight Colour", (0, 0, 0))
lcd_brightness_control = g15driver.Control("lcd_brightness", "LCD Brightness", 100, 0, 100, hint = g15driver.HINT_SHADEABLE)
foreground_control = g15driver.Control("foreground", "Default LCD Foreground", (255, 255, 255), hint = g15driver.HINT_FOREGROUND | g15driver.HINT_VIRTUAL)
background_control = g15driver.Control("background", "Default LCD Background", (0, 0, 0), hint = g15driver.HINT_BACKGROUND | g15driver.HINT_VIRTUAL)
highlight_control = g15driver.Control("highlight", "Default Highlight Color", (255, 0, 0), hint=g15driver.HINT_HIGHLIGHT | g15driver.HINT_VIRTUAL)
controls = [ mkeys_control, keyboard_backlight_control, default_keyboard_backlight_control, lcd_brightness_control, foreground_control, background_control, highlight_control ]


class Driver(g15driver.AbstractDriver):

    def __init__(self, device, on_close = None):
        g15driver.AbstractDriver.__init__(self, "g19")
        self.init_string="GBUF"
        self.device = device
        self.change_timer = None
        self.socket = None
        self.on_close = on_close
        self.lock = RLock()
        self.thread = None
        self.conf_client = gconf.client_get_default()
    
    def get_antialias(self):
        return cairo.ANTIALIAS_SUBPIXEL
        
    def get_size(self):
        return (MAX_X, MAX_Y)
        
    def get_bpp(self):
        return self.device.bpp
    
    def get_controls(self):
        return controls
    
    def get_action_keys(self):
        return self.device.action_keys
    
    def get_key_layout(self):
        return self.device.key_layout
    
    def process_svg(self, document):
        pass
    
    def on_update_control(self, control):
        self.lock.acquire()
        try :
            self._do_update_control(control)
        finally:
            self.lock.release()
            
    def get_name(self):
        return "G19D Network Daemon Driver"
    
    def get_model_names(self):
        return [ g15driver.MODEL_G19 ]
    
    def get_model_name(self):
        return self.device.model_id
        
    def connect(self):          
        if self.is_connected():
            raise Exception("Already connected")
        
        port = DEFAULT_PORT
        e = self.conf_client.get("/apps/gnome15/%s/g19d_port" % self.device.uid)
        if e:
            port = e.get_int()
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30.0)
        s.connect(("127.0.0.1", port))
        self.socket = s
        for control in self.get_controls():
            self._do_update_control(control)
        
        self.notify_handle = self.conf_client.notify_add("/apps/gnome15/%s/g19d_port" % self.device.uid, self.config_changed, None)
        
    def config_changed(self, client, connection_id, entry, args):
        if self.change_timer != None:
            self.change_timer.cancel()
        self.change_timer = g15util.schedule("ChangeG15DaemonConfiguration", 3.0, self.update_conf)
            
    def update_conf(self):
        logger.info("Configuration changed")
        if self.is_connected():
            logger.info("Reconnecting")
            self.disconnect()
            self.connect()
            
    def on_disconnect(self):  
        if self.is_connected():  
            if self.thread != None:
                self.thread.running = False
                self.thread = None
            self.socket.close()
            self.socket = None
            if self.on_close != None:
                self.on_close(self)
        else:
            raise Exception("Not connected")
        
    def reconnect(self):
        if self.is_connected():
            self.disconnect()
        self.connect()
        
    def on_receive_error(self, exception):
        if self.is_connected():
            self.disconnect()
        
    def grab_keyboard(self, callback):
        if self.thread == None:
            self.thread = EventReceive(self.socket, callback, self.on_receive_error)
            self.thread.start()
        else:
            raise Exception("Already grabbing keyboard")
        self.write_out("GK")
        
    def is_connected(self):
        return self.socket != None 
    
    def write_out(self, buf):         
        self.lock.acquire()
        try :
            if not self.is_connected():
                raise NotConnectedException()
            self.socket.sendall(buf)
        except Exception:
            if self.is_connected():
                self.disconnect()
            raise
        finally:
            self.lock.release()
        
    def paint(self, img):     
        if not self.is_connected():
            return
                
        width = img.get_width()
        height = img.get_height()
        
        # Create a new flipped, rotated image. The G19 expects the image to scan vertically, but
        # the cairo image surface will be horizontal. Rotating then flipping the image is the
        # quickest way to convert this. 16 bit color (5-6-5) is also required. Unfortunately this format
        # was disabled for a long time, as was only re-enabled in version 1.8.6.
        try:
            back_surface = cairo.ImageSurface (4, height, width)
        except:
            # Earlier version of Cairo
            back_surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, height, width)
        
        back_context = cairo.Context (back_surface)        
        g15util.rotate_around_center(back_context, width, height, 270)
        g15util.flip_horizontal(back_context, width, height)
        back_context.set_source_surface(img, 0, 0)
        back_context.set_operator (cairo.OPERATOR_SOURCE);
        back_context.paint()
        
        if back_surface.get_format() == cairo.FORMAT_ARGB32:
            file_str = StringIO()
            data = back_surface.get_data()
            for i in range(0, len(data), 4):
                r = ord(data[i + 2])
                g = ord(data[i + 1])
                b = ord(data[i + 0])
                file_str.write(self.rgb_to_uint16(r, g, b))                
            buf = file_str.getvalue()
        else:   
            buf = str(back_surface.get_data())     
            
                  
        expected_size = MAX_X * MAX_Y * ( self.get_bpp() / 8 )
        if len(buf) != expected_size:
            logger.warning("Invalid buffer size, expected %d, got %d" % ( expected_size, len(buf) ) )
        else:
            self.write_out("I" + str(buf))
            
    def rgb_to_uint16(self, r, g, b):
        rBits = r * 32 / 255
        gBits = g * 64 / 255
        bBits = b * 32 / 255

        rBits = rBits if rBits <= 31 else 31
        gBits = gBits if gBits <= 63 else 63
        bBits = bBits if bBits <= 31 else 31        

        valueH = (rBits << 3) | (gBits >> 3)
        valueL = (gBits << 5) | bBits

        return chr(valueL & 0xff) + chr(valueH & 0xff)
    
    def _do_update_control(self, control):
        if control == keyboard_backlight_control: 
            self.write_out("B" + chr(control.value[0]) + chr(control.value[1]) + chr(control.value[2]));
        elif control == default_keyboard_backlight_control: 
            self.write_out("C" + chr(control.value[0]) + chr(control.value[1]) + chr(control.value[2]));
        elif control == lcd_brightness_control:
            self.write_out("L" + chr(control.value) );
        elif control == mkeys_control:
            self._set_mkey_lights(control.value)
        
    def _set_mkey_lights(self, lights):
        val = 0
        if lights & g15driver.MKEY_LIGHT_1 != 0:
            val += 0x80
        if lights & g15driver.MKEY_LIGHT_2 != 0:
            val += 0x40
        if lights & g15driver.MKEY_LIGHT_3 != 0:
            val += 0x20
        if lights & g15driver.MKEY_LIGHT_MR != 0:
            val += 0x10
        self.write_out("M" + chr(val))
            
