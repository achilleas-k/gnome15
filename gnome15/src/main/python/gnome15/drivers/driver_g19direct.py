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
Alternative implementation of a G19 Driver that uses pylibg19 to communicate directly
with the keyboard 
"""

from cStringIO import StringIO
from gnome15.g15exceptions import NotConnectedException
from threading import RLock, Thread
import cairo
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15util as g15util
import gnome15.g15devices as g15devices
import sys
import os
import gconf
import gtk
import re
import usb
import traceback 
import logging
logger = logging.getLogger("driver")

# Import from local version of pylibg19 if available
if g15globals.dev:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "..", "pylibg19"))    

from g19.g19 import G19



# Driver information (used by driver selection UI)
name="G19 Direct"
id="g19direct"
description="For use with the Logitech G19 only, this driver communicates directly, " + \
            "with the keyboard and so is more efficient than the G19D driver. Note, " + \
            "you will have to ensure the permissions of the USB devices are read/write " + \
            "for your user."
has_preferences=True

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
            
            
# Controls
keyboard_backlight_control = g15driver.Control("backlight_colour", "Keyboard Backlight Colour", (0, 0, 0), hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
default_keyboard_backlight_control = g15driver.Control("default_backlight_colour", "Boot Keyboard Backlight Colour", (0, 0, 0))
lcd_brightness_control = g15driver.Control("lcd_brightness", "LCD Brightness", 100, 0, 100, hint = g15driver.HINT_SHADEABLE)
foreground_control = g15driver.Control("foreground", "Default LCD Foreground", (255, 255, 255), hint = g15driver.HINT_FOREGROUND)
background_control = g15driver.Control("background", "Default LCD Background", (0, 0, 0), hint = g15driver.HINT_BACKGROUND)
controls = [ keyboard_backlight_control, default_keyboard_backlight_control, lcd_brightness_control, foreground_control, background_control]

def show_preferences(parent, gconf_client):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "driver_g19direct.glade"))    
    dialog = widget_tree.get_object("DriverDialog")
    dialog.set_transient_for(parent)
    g15util.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/reset_usb", "Reset", False, widget_tree, True)
    g15util.configure_spinner_from_gconf(gconf_client, "/apps/gnome15/timeout", "Timeout", 10000, widget_tree, False)
    g15util.configure_spinner_from_gconf(gconf_client, "/apps/gnome15/reset_wait", "ResetWait", 0, widget_tree, False)
    dialog.run()
    dialog.hide()

class Driver(g15driver.AbstractDriver):

    def __init__(self, on_close = None):
        g15driver.AbstractDriver.__init__(self, "g19direct")
        self.on_close = on_close
        self.lock = RLock()
        self._init_driver()
        self.connected = False
        self.conf_client = gconf.client_get_default()
    
    def get_antialias(self):
        return cairo.ANTIALIAS_SUBPIXEL
        
    def get_size(self):
        return (MAX_X, MAX_Y)
        
    def get_bpp(self):
        return self.device.bpp
    
    def get_controls(self):
        return controls
    
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
        return self.device.model_name
        
    def connect(self):          
        if self.is_connected():
            raise Exception("Already connected")
        
        self._init_driver()
        self.callback = None
        
        # TODO Enable UINPUT if multimedia key support is required?
        reset = self.conf_client.get_bool("/apps/gnome15/reset_usb")
        timeout = 10000
        reset_wait = 0
        e = self.conf_client.get("/apps/gnome15/timeout")
        if e:
            timeout = e.get_int()
        e = self.conf_client.get("/apps/gnome15/reset_wait")
        if e:
            reset_wait = e.get_int()
        
        self.lg19 = G19(reset, False, timeout, reset_wait)
        self.connected = True
        
        # Start listening for keys
        self.lg19.add_input_processor(self)  

        for control in self.get_controls():
            self._do_update_control(control)
            
    def disconnect(self):  
        if self.is_connected():  
            self.lg19.stop_event_handling()
            self.connected = False
            if self.on_close != None:
                self.on_close()
        else:
            raise Exception("Not connected")
        
    def reconnect(self):
        if self.is_connected():
            self.disconnect()
        self.connect()
        
    def set_mkey_lights(self, lights):
        val = 0
        if lights & g15driver.MKEY_LIGHT_1 != 0:
            val += 0x80
        if lights & g15driver.MKEY_LIGHT_2 != 0:
            val += 0x40
        if lights & g15driver.MKEY_LIGHT_3 != 0:
            val += 0x20
        if lights & g15driver.MKEY_LIGHT_MR != 0:
            val += 0x10
        self.lg19.set_enabled_m_keys(val)
        
    def on_receive_error(self, exception):
        if self.is_connected():
            self.disconnect()
        
    def grab_keyboard(self, callback):    
        self.callback = callback    
        self.lg19.start_event_handling()
        
    def is_connected(self):
        return self.connected 
        
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
                file_str.write(self._rgb_to_uint16(r, g, b))                
            buf = file_str.getvalue()
        else:   
            buf = str(back_surface.get_data())     
            
                  
        expected_size = MAX_X * MAX_Y * ( self.get_bpp() / 8 )
        if len(buf) != expected_size:
            logger.warning("Invalid buffer size, expected %d, got %d" % ( expected_size, len(buf) ) )
        else:
            try:
                self.lg19.send_frame(buf)
            except usb.USBError as e:
                traceback.print_exc(file=sys.stderr)
                self.on_receive_error(e)
    
    def process_input(self, event):
        if self.callback == None:
            logger.debug("Ignoring key input, keyboard not grabbed")
            return
            
        keys_down = event.keysDown
        keys_up = event.keysUp
        
        logger.info("Processing input, keys_down = %d, keys_up = %d" % ( len(keys_down), len(keys_up)))
            
        if len(keys_up) > 0:
            c = []
            for key in keys_up:
                c.append(KEY_MAP[key])
            self.callback(c, g15driver.KEY_STATE_UP)
            
        if len(keys_down) > 0:
            c = []
            for key in keys_down:
                c.append(KEY_MAP[key])
            self.callback(c, g15driver.KEY_STATE_DOWN)
            
    def _do_update_control(self, control):
        try:
            if control == keyboard_backlight_control:
                self.lg19.set_bg_color(control.value[0], control.value[1], control.value[2])
            elif control == default_keyboard_backlight_control: 
                self.lg19.save_default_bg_color(control.value[0], control.value[1], control.value[2])
            elif control == lcd_brightness_control: 
                self.lg19.set_display_brightness(control.value)
        except usb.USBError as e:
            traceback.print_exc(file=sys.stderr)
            self.on_receive_error(e)
            
    def _init_driver(self):        
        self.device = g15devices.find_device([g15driver.MODEL_G19])
        if self.device == None:
            raise Exception("Could not find a G19 keyboard. This may be caused by incorrect device permissions. The files for the USB devices must be readable and writeable by the current user.")
            
    def _rgb_to_uint16(self, r, g, b):
        rBits = r * 32 / 255
        gBits = g * 64 / 255
        bBits = b * 32 / 255

        rBits = rBits if rBits <= 31 else 31
        gBits = gBits if gBits <= 63 else 63
        bBits = bBits if bBits <= 31 else 31        

        valueH = (rBits << 3) | (gBits >> 3)
        valueL = (gBits << 5) | bBits

        return chr(valueL & 0xff) + chr(valueH & 0xff)
