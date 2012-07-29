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

import time
from ctypes import *
from threading import Thread
libg15 = cdll.LoadLibrary("libg15.so.1")

# Default kKey read timeout. Too low and keys will be missed (very obvious in a VM)
KEY_READ_TIMEOUT = 100

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
G15_ERROR_READING_USB_DEVICE=4
G15_TRY_AGAIN = 5
G15_ERROR_NOENT = -2
G15_ERROR_NODEV = -19

# Debug levels
G15_LOG_INFO = 1
G15_LOG_WARN = 0

class KeyboardReceiveThread(Thread):
    def __init__(self, callback, key_read_timeout, on_error):
        Thread.__init__(self)
        self._run = True
        self.name = "KeyboardReceiveThread"
        self.callback = callback
        self.on_exit = None
        self.on_unplug = None
        self.key_read_timeout = key_read_timeout
        self.on_error = on_error
        
    def deactivate(self):
        if self._run:
            self._run = False
        
    def run(self):      
        pressed_keys = c_int(0)
        try:
            while self._run:
                err = libg15.getPressedKeys(byref(pressed_keys), 10)
                code = 0
                ext_code = 0
                if err == G15_NO_ERROR:
                    if is_ext_key(pressed_keys.value):
                        ext_code = int(pressed_keys.value)
                        ext_code &= ~(1<<28)
                        err = libg15.getPressedKeys(byref(pressed_keys), 10)
                        if err == G15_NO_ERROR:
                            code = pressed_keys.value
                        elif err in [ G15_TRY_AGAIN, G15_ERROR_READING_USB_DEVICE ]:
                            pass
                        elif err == G15_ERROR_NODEV:
                            # Device unplugged
                            self._run = False
                            if self.on_unplug is not None:
                                self.on_unplug()
                        else:
                            if  self.on_error is not None:
                                self.on_error(err)
                            break
                    else:
                        code = pressed_keys.value
                        
                    self.callback(code, ext_code)
                elif err in [ G15_TRY_AGAIN, G15_ERROR_READING_USB_DEVICE ] :
                    continue
                elif err == G15_ERROR_NODEV:
                    # Device unplugged
                    self._run = False
                    if self.on_unplug is not None:
                        self.on_unplug()
                else:
                    if  self.on_error is not None:
                        self.on_error(err)
                    break
                    
        finally:
            if self.on_exit is not None:
                self.on_exit()
            self._run = True
            
class libg15_devices_t(Structure):
    _fields_ = [ ("name", c_char_p),
                 ("vendorid", c_int),
                 ("productid", c_int),
                 ("caps", c_int) ]
    
def is_ext_key(code):
    """
    Get if the key code provide is an "Extended Key". Extended keys are used
    to cope with libg15's restriction on the number of available codes,
    which the G13 exceeds.
    
    Keyword arguments:
    code        --    code to test if extended
    """
    return code & (1<<28) != 0
    
def grab_keyboard(callback, key_read_timeout = KEY_READ_TIMEOUT, on_error = None):
    """
    Start polling for keyboard events. Device must be initialised. The thread
    returned can be stopped by calling deactivate().
    
    The callback is invoked with two arguments. The first being the bit mask
    of any pressed non-extended codes. The second is the mask of any extended
    key presses. 
    
    Keyword arguments:
    callback        -- function to call on key event
    key_read_timeout -- timeout for reading key presses. too low and keys will be missed
    """
    t = KeyboardReceiveThread(callback, key_read_timeout, on_error)
    t.start()
    return t
    
def init(init_usb = True, vendor_id = 0, product_id = 0):
    """
    This one return G15_NO_ERROR on success, something
    else otherwise (for instance G15_ERROR_OPENING_USB_DEVICE
    """
    return libg15.setupLibG15(vendor_id, product_id, 1 if init_usb else 0)

def reinit():
    """ re-initialise a previously unplugged keyboard ie ENODEV was returned at some point """
    return libg15.re_initLibG15()
    

def exit():
    return libg15.exitLibG15()

def set_debug(level):
    """
    Keyword arguments:
    level        -- level, one of G15_LOG_INFO or G15_LOG_WARN
    """
    libg15.libg15Debug(level)
    
def write_pixmap(data):
    libg15.writePixmapToLCD(data)
    
def set_contrast(level):
    return libg15.setLCDContrast(level)
    
def set_leds(leds):
    return libg15.setLEDs(leds)
    
def set_lcd_brightness(level):
    return libg15.setLCDBrightness(level)
    
def set_keyboard_brightness(level):
    return libg15.setKBBrightness(level)
    
def set_keyboard_color(color):
    val =  libg15.setG510LEDColor(color[0], color[1], color[2])
    return val

def get_joystick_position():
    return ( libg15.getJoystickX(), libg15.getJoystickY() )

def __handle_key(code):
    print "Got %d" %code