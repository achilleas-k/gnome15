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
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("gnome15-drivers").ugettext

from threading import RLock
import cairo
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15util as g15util
import gnome15.g15uinput as g15uinput
import gnome15.g15exceptions as g15exceptions
import sys
import os
import gconf
import gtk
import traceback 
import logging
import ImageMath
import Image
import uinput
import array
load_error = None
try :
    import pylibg15
except Exception as a:
    load_error = a
logger = logging.getLogger("driver")

# Import from local version of pylibg19 if available
if g15globals.dev:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "..", "pylibg19"))    

# Driver information (used by driver selection UI)
name=_("G15 Direct")
id="g15direct"
description=_("For use with the G15 based devices only, this driver communicates directly, " + \
            "with the keyboard and so is more efficient than the g15daemon driver. Note, " + \
            "you will have to ensure the permissions of the USB devices are read/write " + \
            "for your user.")
has_preferences=True



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

EXT_KEY_MAP = {        
        g15driver.G_KEY_G19 : 1<<1,
        g15driver.G_KEY_G20 : 1<<2,
        g15driver.G_KEY_G21 : 1<<3,
        g15driver.G_KEY_G22 : 1<<4,
        
        g15driver.G_KEY_JOY_LEFT  : 1<<5,
        g15driver.G_KEY_JOY_DOWN  : 1<<6,
        g15driver.G_KEY_JOY_CENTER  : 1<<7,
        g15driver.G_KEY_JOY : 1<<8
        }

REVERSE_KEY_MAP = {}
for k in KEY_MAP.keys():
    REVERSE_KEY_MAP[KEY_MAP[k]] = k
EXT_REVERSE_KEY_MAP = {}
for k in EXT_KEY_MAP.keys():
    EXT_REVERSE_KEY_MAP[EXT_KEY_MAP[k]] = k

mkeys_control = g15driver.Control("mkeys", _("Memory Bank Keys"), 1, 0, 15, hint=g15driver.HINT_MKEYS)
color_backlight_control = g15driver.Control("backlight_colour", _("Keyboard Backlight Colour"), (0, 255, 0), hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
red_blue_backlight_control = g15driver.Control("backlight_colour", _("Keyboard Backlight Colour"), (255, 0, 0), hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE | g15driver.HINT_RED_BLUE_LED)
backlight_control = g15driver.Control("keyboard_backlight", _("Keyboard Backlight Level"), 2, 0, 2, hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
lcd_backlight_control = g15driver.Control("lcd_backlight", _("LCD Backlight Level"), 2, 0, 2, hint = g15driver.HINT_SHADEABLE)
lcd_contrast_control = g15driver.Control("lcd_contrast", _("LCD Contrast"), 22, 0, 2)
invert_control = g15driver.Control("invert_lcd", _("Invert LCD"), 0, 0, 1, hint = g15driver.HINT_SWITCH )

controls = {
  g15driver.MODEL_G11 : [ mkeys_control, backlight_control ],
  g15driver.MODEL_G15_V1 : [ mkeys_control, backlight_control, lcd_contrast_control, lcd_backlight_control, invert_control ], 
  g15driver.MODEL_G15_V2 : [ mkeys_control, backlight_control, lcd_backlight_control, invert_control ],
  g15driver.MODEL_G13 : [ mkeys_control, color_backlight_control, invert_control ],
  g15driver.MODEL_G510 : [ mkeys_control, color_backlight_control, invert_control ],
  g15driver.MODEL_Z10 : [ backlight_control, lcd_backlight_control, invert_control ],
  g15driver.MODEL_G110 : [ mkeys_control, red_blue_backlight_control ],
            }   

G15_LCD = 1
G15_KEYS = 2
G15_DEVICE_IS_SHARED = 4
G15_DEVICE_5BYTE_RETURN = 8
G15_DEVICE_G13 = 16
G15_DEVICE_G510 = 32
G15_KEY_READ_LENGTH = 9
G510_STANDARD_KEYBOARD_INTERFACE = 0x0

# Error codes
G15_NO_ERROR = 0
G15_ERROR_OPENING_USB_DEVICE = 1
G15_ERROR_WRITING_PIXMAP = 2
G15_ERROR_TIMEOUT = 3
G15_ERROR_READING_USB_DEVICE = 4
G15_ERROR_TRY_AGAIN = 5
G15_ERROR_WRITING_BUFFER = 6
G15_ERROR_UNSUPPORTED = 7

# Debug levels
G15_LOG_INFO = 1
G15_LOG_WARN = 0

def show_preferences(device, parent, gconf_client):
    g15locale.get_translation("driver_g15direct")
    widget_tree = gtk.Builder()
    widget_tree.set_translation_domain("driver_g15direct")
    widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "driver_g15direct.glade"))  
    g15util.configure_spinner_from_gconf(gconf_client, "/apps/gnome15/%s/timeout" % device.uid, "Timeout", 10000, widget_tree, False)  
    g15util.configure_combo_from_gconf(gconf_client, "/apps/gnome15/%s/joymode" % device.uid, "JoyModeCombo", "macro", widget_tree)
    widget_tree.get_object("JoyModeCombo").set_sensitive(device.model_id == g15driver.MODEL_G13)
    widget_tree.get_object("JoyModeLabel").set_sensitive(device.model_id == g15driver.MODEL_G13)
    return widget_tree.get_object("DriverComponent")

def fix_sans_style(root):
    for element in root.iter():
        style = element.get("style")
        if style != None:
            element.set("style", style.replace("font-family:Sans","font-family:%s" % g15globals.fixed_size_font_name))
    
        
class Driver(g15driver.AbstractDriver):

    def __init__(self, device, on_close = None):      
        if load_error is not None:
            raise load_error  
        g15driver.AbstractDriver.__init__(self, "g15direct")
        self.on_close = on_close
        self.device = device
        self.timer = None
        self.joy_mode = None
        self.lock = RLock()
        self.down = []
        self.move_x = 0
        self.move_y = 0
        self.connected = False
        self.conf_client = gconf.client_get_default()
        self.last_keys = None
    
    def get_antialias(self):
        return cairo.ANTIALIAS_NONE
        
    def get_size(self):
        return self.device.lcd_size
        
    def get_bpp(self):
        return self.device.bpp
    
    def get_controls(self):
        return controls[self.device.model_id]
    
    def get_key_layout(self):
        if self.get_model_name() == g15driver.MODEL_G13 and "macro" == self.conf_client.get_string("/apps/gnome15/%s/joymode" % self.device.uid):
            """
            This driver with the G13 supports some additional keys
            """
            l = list(self.device.key_layout)
            l.append([ g15driver.G_KEY_UP ])
            l.append([ g15driver.G_KEY_JOY_LEFT, g15driver.G_KEY_LEFT, g15driver.G_KEY_JOY_CENTER, g15driver.G_KEY_RIGHT ])
            l.append([ g15driver.G_KEY_JOY_DOWN, g15driver.G_KEY_DOWN ])
            return l
        else:
            return self.device.key_layout
    
    def get_action_keys(self):
        return self.device.action_keys
    
    def process_svg(self, document):
        fix_sans_style(document.getroot())
    
    def on_update_control(self, control):
        self.lock.acquire()
        try :
            self._do_update_control(control)
        finally:
            self.lock.release()
            
    def get_name(self):
        return _("G15 Direct")
    
    def get_model_names(self):
        return [ g15driver.MODEL_G11, g15driver.MODEL_G15_V1, g15driver.MODEL_G15_V2, g15driver.MODEL_G110, g15driver.MODEL_G510, g15driver.MODEL_G13 ]
    
    def get_model_name(self):
        return self.device.model_id
        
    def connect(self):  
        if self.is_connected():
            raise Exception("Already connected")
          
        self.thread = None  
        self.callback = None
        self.notify_handles = [] 
                
        # Create an empty string buffer for use with monochrome LCD
        self.empty_buf = ""
        for i in range(0, 861):
            self.empty_buf += chr(0)
        
        # TODO Enable UINPUT if multimedia key support is required?
        self.timeout = 10000
        e = self.conf_client.get("/apps/gnome15/%s/timeout" % self.device.uid)
        if e:
            self.timeout = e.get_int()
        
        logger.info("Initialising pylibg15, looking for %s:%s" % ( hex(self.device.controls_usb_id[0]), hex(self.device.controls_usb_id[1]) ))
        if logger.level < logging.WARN and logger.level != logging.NOTSET:
            pylibg15.set_debug(pylibg15.G15_LOG_INFO)
        err = pylibg15.init(False, self.device.controls_usb_id[0], self.device.controls_usb_id[1])
        if err != G15_NO_ERROR:
            raise g15exceptions.NotConnectedException("libg15 returned error %d " % err)
        logger.info("Initialised pylibg15")
        self.connected = True

        for control in self.get_controls():
            self._do_update_control(control)
        
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/%s/joymode" % self.device.uid, self._config_changed, None))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/%s/timeout" % self.device.uid, self._config_changed, None))
            
        self.calibration = 20   
        self._load_configuration()
        
    def _load_configuration(self):
        self.joy_mode = self.conf_client.get_string("/apps/gnome15/%s/joymode" % self.device.uid)
            
    def _config_changed(self, client, connection_id, entry, args):
        self._load_configuration()
            
    def on_disconnect(self):  
        if self.is_connected():
            for h in self.notify_handles:
                self.conf_client.notify_remove(h)
            logger.info("Exiting pylibg15")
            self.connected = False
            if self.thread is not None:
                self.thread.on_exit = pylibg15.exit
                self.thread.deactivate()
            else:
                pylibg15.exit()
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
        self.callback = callback
        self.last_keys = None
        self.thread = pylibg15.grab_keyboard(self._handle_key_event)
        
    def is_connected(self):
        return self.connected 
        
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
                # TODO Replace with C routine
                arrbuf = array.array('B', self.empty_buf)
                width, height = self.get_size() 
                max_byte_offset = 0
                for x in range(0, width):
                    for y in range(0, height):
                        pixel_offset = y * width + x;
                        byte_offset = pixel_offset / 8;
                        max_byte_offset =  max(max_byte_offset, byte_offset)
                        bit_offset = 7-(pixel_offset % 8);
                        val = ord(buf[x+(y*160)])
                        pv = arrbuf[byte_offset]
                        if val > 0:
                            arrbuf[byte_offset] = pv | 1 << bit_offset
                        else:
                            arrbuf[byte_offset] = pv &  ~(1 << bit_offset)
                buf = arrbuf.tostring()
                try :
                    if logger.level == logging.DEBUG:
                        logger.debug("Writing buffer of %d byts" % len(buf))
                    pylibg15.write_pixmap(buf)
                except IOError as (errno, strerror):
                    logger.error("Failed to send buffer. %d: %s" % ( errno, strerror ) )                    
                    traceback.print_exc(file=sys.stderr)
                    self.disconnect()
        finally:
            self.lock.release()
  
    """
    Private
    """
            
    def _convert_from_g15daemon_code(self, code):
        keys = []
        if code & (1<<28) != 0:
            for key in EXT_REVERSE_KEY_MAP:
                if code & key != 0:
                    keys.append(EXT_REVERSE_KEY_MAP[key])
        else:
            for key in REVERSE_KEY_MAP:
                if code & key != 0:
                    keys.append(REVERSE_KEY_MAP[key])
        return keys   
        
    def _handle_key_event(self, code):
        
        if not self.is_connected() or self.disconnecting:
            return
        
        if logger.level == logging.DEBUG:
            logger.debug("Key code %d" % code)
        this_keys = [] if code == 0 else self._convert_from_g15daemon_code(code)
        
                    
        # For now, emulate a digital joystick
        if self.get_model_name() == g15driver.MODEL_G13:
            low_val = 128 - self.calibration
            high_val = 128 + self.calibration
            max_step = 5
                
            if g15driver.G_KEY_JOY in this_keys:
                this_keys.remove(g15driver.G_KEY_JOY)
            pos = pylibg15.get_joystick_position()
            
            if logger.level == logging.DEBUG:
                logger.debug("Joystick at %s" % str(pos))
            
            if self.joy_mode == "joystick":
                self._abs_joystick(this_keys, pos)
            elif self.joy_mode == "mouse":
                self._rel_mouse(this_keys, pos, low_val, high_val, max_step)                 
            else:
                self._emit_macro_keys(this_keys, pos, low_val, high_val)            
        
        up = []
        down = []
        
        for k in this_keys:
            if self.last_keys is None or not k in self.last_keys:
                down.append(k)
                
        if self.last_keys is not None:
            for k in self.last_keys:
                if not k in this_keys and not k in down:
                    up.append(k)
                
        if len(down) > 0:         
            print "Down %s" % down   
            self.callback(down, g15driver.KEY_STATE_DOWN)
        if len(up) > 0:            
            print "Up %s" % up   
            self.callback(up, g15driver.KEY_STATE_UP)
        
        self.last_keys = this_keys
        
    def _emit_macro_keys(self, this_keys, pos, low_val, high_val):
        if pos[0] < low_val:
            this_keys.append(g15driver.G_KEY_LEFT)                    
        elif pos[0] > high_val:
            this_keys.append(g15driver.G_KEY_RIGHT)                    
        elif pos[1] < low_val:
            this_keys.append(g15driver.G_KEY_UP)
        elif pos[1] > high_val:
            this_keys.append(g15driver.G_KEY_DOWN) 
            
    def _check_js_buttons(self, this_keys):        
        self._check_buttons(g15uinput.JOYSTICK, this_keys, g15driver.G_KEY_JOY_LEFT, uinput.BTN_1)
        self._check_buttons(g15uinput.JOYSTICK, this_keys, g15driver.G_KEY_JOY_DOWN, uinput.BTN_2)
        self._check_buttons(g15uinput.JOYSTICK, this_keys, g15driver.G_KEY_JOY_CENTER, uinput.BTN_3)
            
    def _check_mouse_buttons(self, this_keys):        
        self._check_buttons(g15uinput.MOUSE, this_keys, g15driver.G_KEY_JOY_LEFT, uinput.BTN_MOUSE)
        self._check_buttons(g15uinput.MOUSE, this_keys, g15driver.G_KEY_JOY_DOWN, uinput.BTN_RIGHT)
        self._check_buttons(g15uinput.MOUSE, this_keys, g15driver.G_KEY_JOY_CENTER, uinput.BTN_MIDDLE)
        
    def _rel_mouse(self, this_keys, pos, low_val, high_val, max_step):
        self._check_mouse_buttons(this_keys)
        
        relx = 0    
        rely = 0
        
        if pos[0] < low_val:
            relx = ( low_val - pos[0] ) * -1                    
        elif pos[0] > high_val:
            relx = pos[0] - high_val                    
        if pos[1] < low_val:
            rely = ( low_val - pos[1] ) * -1
        elif pos[1] > high_val:
            rely = pos[1] - high_val
            
        relx = -max_step if relx < -max_step else ( max_step if relx > max_step else relx)
        rely = -max_step if rely < -max_step else ( max_step if rely > max_step else rely)
            
        self.move_x = relx
        self.move_y = rely
        if relx != 0 or rely != 0:
            self._mouse_move() 
        else:
            if self.timer is not None:                    
                self.timer.cancel()
        
    def _abs_joystick(self, this_keys, pos):
        self._check_js_buttons(this_keys) 
        g15uinput.emit(g15uinput.JOYSTICK, uinput.ABS_X, pos[0], syn=False)
        g15uinput.emit(g15uinput.JOYSTICK, uinput.ABS_Y, pos[1])
        
    def _check_buttons(self, target, this_keys, key, button):        
        if key in this_keys:
            this_keys.remove(key)
            if not key in self.down:
                g15uinput.emit(target, button, 1)
                self.down.append(key)
        elif key in self.down:
            g15uinput.emit(target, button, 0)
            self.down.remove(key)
        
    def _mouse_move(self):
        if self.move_x != 0 or self.move_y != 0:        
            if self.move_x != 0:
                g15uinput.emit(g15uinput.MOUSE, uinput.REL_X, self.move_x)        
            if self.move_y != 0:
                g15uinput.emit(g15uinput.MOUSE, uinput.REL_Y, self.move_y)
            self.timer = g15util.schedule("MouseMove", 0.05, self._mouse_move)
        
    def _do_update_control(self, control):
        level = control.value
        logger.debug("Updating control %s to %s" % (str(control.id), str(control.value)))
        if control.id == backlight_control.id:
            self.check_control(control)
            pylibg15.set_keyboard_brightness(level)
        elif control.id == lcd_backlight_control.id:
            self.check_control(control)
            pylibg15.set_lcd_brightness(level)
        elif control.id == lcd_contrast_control.id:
            self.check_control(control)
            pylibg15.set_contrast(level)
        elif control.id == color_backlight_control.id or control.id == red_blue_backlight_control.id:
            pylibg15.set_keyboard_color(level)
        elif control.id == mkeys_control.id:
            pylibg15.set_leds(level)