#!/usr/bin/env python
############################################################################
##
## Copyright (C), all rights reserved:
##      2010 Brett Smith <tanktarta@blueyonder.co.uk>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License version 2
##
## Gnome15 - Suite of GNOME applications that work with the logitech G15
##           keyboard
##
############################################################################

 
from cStringIO import StringIO
from pyinputevent.uinput import UInputDevice
from pyinputevent.pyinputevent import InputEvent, SimpleDevice
from pyinputevent.keytrans import *
from threading import Thread

import select
import pyinputevent.scancodes as S
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15globals as g15globals
import gconf
import fcntl
import os
import gtk
import cairo
import re
import usb
import fb
import Image
import ImageMath
import array
import time
import dbus
import gobject

# Logging
import logging
logger = logging.getLogger("driver")

# Driver information (used by driver selection UI)
id = "kernel"
name = "Kernel Drivers"
description = "Requires ali123's Logitech Kernel drivers. This method requires no other " + \
            "daemons to be running, and works with the G13, G15, G19 and G110 keyboards. " 
has_preferences = True

g19_key_map = {
               "191" : g15driver.G_KEY_M1,
               "192" : g15driver.G_KEY_M2,
               "193" : g15driver.G_KEY_M3,
               "194" : g15driver.G_KEY_MR,
               "139" : g15driver.G_KEY_MENU,
               "103" : g15driver.G_KEY_UP,
               "108" : g15driver.G_KEY_DOWN,
               "105" : g15driver.G_KEY_LEFT,
               "106" : g15driver.G_KEY_RIGHT,
               "352" : g15driver.G_KEY_OK,
               "158" : g15driver.G_KEY_BACK,
               "159" : g15driver.G_KEY_SETTINGS,
               "228" : g15driver.G_KEY_LIGHT,
               "59" : g15driver.G_KEY_G1,
               "60" : g15driver.G_KEY_G2,
               "61" : g15driver.G_KEY_G3,
               "62" : g15driver.G_KEY_G4,
               "63" : g15driver.G_KEY_G5,
               "64" : g15driver.G_KEY_G6,
               "65" : g15driver.G_KEY_G7,
               "66" : g15driver.G_KEY_G8,
               "67" : g15driver.G_KEY_G9,
               "68" : g15driver.G_KEY_G10,
               "87" : g15driver.G_KEY_G11,
               "88" : g15driver.G_KEY_G12
               }

g15_key_map = {
               "191" : g15driver.G_KEY_M1,
               "192" : g15driver.G_KEY_M2,
               "193" : g15driver.G_KEY_M3,
               "194" : g15driver.G_KEY_MR,
               "30" : g15driver.G_KEY_L1,
               "48" : g15driver.G_KEY_L2,
               "46" : g15driver.G_KEY_L3,
               "32" : g15driver.G_KEY_L4,
               "18" : g15driver.G_KEY_L5,
               "33" : g15driver.G_KEY_LIGHT,
               }


g19_keyboard_backlight_control = g15driver.Control("backlight_colour", "Keyboard Backlight Colour", (0, 0, 0), hint=g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
g19_lcd_brightness_control = g15driver.Control("lcd_brightness", "LCD Brightness", 100, 0, 100, hint=g15driver.HINT_SHADEABLE)
g19_foreground_control = g15driver.Control("foreground", "Default LCD Foreground", (255, 255, 255), hint=g15driver.HINT_FOREGROUND)
g19_background_control = g15driver.Control("background", "Default LCD Background", (0, 0, 0), hint=g15driver.HINT_BACKGROUND)
g19_controls = [ g19_keyboard_backlight_control, g19_lcd_brightness_control, g19_foreground_control, g19_background_control]
g110_controls = [ g19_keyboard_backlight_control ]

g15_backlight_control = g15driver.Control("keyboard_backlight", "Keyboard Backlight Level", 0, 0, 2, hint=g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
g15_lcd_backlight_control = g15driver.Control("lcd_backlight", "LCD Backlight", 0, 0, 2, hint=g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
#g15_lcd_backlight_control = g15driver.Control("lcd_backlight", "LCD Backlight", 0, 0, 1, hint=g15driver.HINT_SWITCH)
g15_lcd_contrast_control = g15driver.Control("lcd_contrast", "LCD Contrast", 0, 0, 48, hint=g15driver.HINT_SHADEABLE)
g15_invert_control = g15driver.Control("invert_lcd", "Invert LCD", 0, 0, 1, hint=g15driver.HINT_SWITCH)
g15_controls = [ g15_backlight_control, g15_invert_control, g15_lcd_backlight_control, g15_lcd_contrast_control ]  
g11_controls = [ g15_backlight_control ]

class DeviceInfo:
    def __init__(self, leds, controls, key_map, led_prefix, keydev_pattern):
        self.leds = leds
        self.controls = controls
        self.key_map = key_map
        self.led_prefix = led_prefix 
        self.keydev_pattern = keydev_pattern
        
device_info = {
               g15driver.MODEL_G19: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "red:mr" ], g19_controls, g19_key_map, "g19", "Logitech_G19_Gaming_Keyboard.*if*"), 
               g15driver.MODEL_G11: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "blue:mr" ], g11_controls, g15_key_map, "g15", "G15_Keyboard_G15.*if*"), 
               g15driver.MODEL_G15_V1: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "blue:mr" ], g15_controls, g15_key_map, "g15", "G15_Keyboard_G15.*if*"), 
               g15driver.MODEL_G15_V2: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "blue:mr" ], g15_controls, g15_key_map, "g15", "G15_Keyboard_G15.*if*"),
               g15driver.MODEL_G13: DeviceInfo(["red:m1", "red:m2", "red:m3", "blue:mr" ], g15_controls, g15_key_map, "g13", "G13_Keyboard_G13.*if*"),
               g15driver.MODEL_G110: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "red:mr" ], g110_controls, g19_key_map, "g110", "G110_Keyboard_G15.*if*")
               }
        

# Other constants
EVIOCGRAB = 0x40044590

def show_preferences(device, parent, gconf_client):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "driver_kernel.glade"))  
    device_model = widget_tree.get_object("DeviceModel")
    device_model.clear()
    device_model.append(["auto"])
    for dir in os.listdir("/dev"):
        if dir.startswith("fb"):
            device_model.append(["/dev/" + dir])    
    g15util.configure_combo_from_gconf(gconf_client, "/apps/gnome15/%s/fb_device" % device.uid, "DeviceCombo", "auto", widget_tree)
    return widget_tree.get_object("DriverComponent")
    
class KeyboardReceiveThread(Thread):
    def __init__(self, device):
        Thread.__init__(self)
        self._run = True
        self.name = "KeyboardReceiveThread-%s" % device.uid
        self.setDaemon(True)
        self.devices = []
        
    def deactivate(self):
        self._run = False
        for dev in self.devices:
            logger.info("Ungrabbing %d" % dev.fileno())
            try :
                fcntl.ioctl(dev.fileno(), EVIOCGRAB, 0)
            except Exception as e:
                print "Failed ungrab.",e
            logger.info("Closing %d" % dev.fileno())
            try :
                self.fds[dev.fileno()].close()
            except Exception as e:
                print "Failed close.",e
            logger.info("Stopped %d" % dev.fileno())
        logger.info("Stopped all input devices")
        
    def run(self):        
        self.poll = select.poll()
        self.fds = {}
        for dev in self.devices:
            self.poll.register(dev, select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLNVAL | select.POLLERR)
            fcntl.ioctl(dev.fileno(), EVIOCGRAB, 1)
            self.fds[dev.fileno()] = dev
        while self._run:
            for x, e in self.poll.poll(1000):
                dev = self.fds[x]
                try :
                    dev.read()
                except OSError as e:
                    # Ignore this error if deactivated
                    if self._run:
                        raise e
        logger.info("Thread left")

'''
SimpleDevice implementation that translates kernel input events
into Gnome15 key events and forwards them to the registered 
Gnome15 keyboard callback.
'''
class ForwardDevice(SimpleDevice):
    def __init__(self, callback, key_map, *args, **kwargs):
        SimpleDevice.__init__(self, *args, **kwargs)
        self.callback = callback
        self.key_map = key_map
        self.ctrl = False
        self.alt = False
        self.shift = False
        self.state = None
        self.doq = False # queue keystrokes for processing?
        self.mouseev = []
        self.keyev = []

    def send_all(self, events):
        for event in events:
            logger.debug(" --> %r" % event)
            self.udev.send_event(event)

    @property
    def modcode(self):
        code = 0
        if self.shift:
            code += 1
        if self.ctrl:
            code += 2
        if self.alt:
            code += 4
        return code
    
    def receive(self, event):
        if event.etype == S.EV_KEY:
            if event.evalue == 2:
                # Drop auto repeat for now
                return
            else:
                self._event(event, g15driver.KEY_STATE_DOWN if event.evalue == 0 else g15driver.KEY_STATE_UP)
        elif event.etype == 0:
            return
        else:
            logger.warning("Unhandled event: %s" % event)
            
    def _event(self, event, state):
        key = str(event.ecode)
        if key in self.key_map:
            self.callback([self.key_map[key]], state)
        else:
            logger.warning("Unmapped key for event: %s" % event)

class Driver(g15driver.AbstractDriver):

    def __init__(self, device, on_close=None):
        g15driver.AbstractDriver.__init__(self, "kernel")
        self.fb = None
        self.var_info = None
        self.on_close = on_close
        self.key_thread = None
        self.device = device
        self.device_info = None
        self.conf_client = gconf.client_get_default()
    
    def get_antialias(self):         
        if self.device.bpp != 1:
            return cairo.ANTIALIAS_DEFAULT
        else:
            return cairo.ANTIALIAS_NONE
        
    def disconnect(self):
        if not self.is_connected():
            raise Exception("Not connected")
        self._stop_receiving_keys()
        self.fb.__del__()
        self.fb = None
        if self.on_close != None:
            g15util.schedule("Close", 0, self.on_close, self)
        self.system_service.__del__()
        
    def is_connected(self):
        return self.fb != None
    
    def get_model_names(self):
        return device_info.keys()
            
    def get_name(self):
        return "Linux Logitech Kernel Driver"
    
    def get_model_name(self):
        return self.device.model_id if self.device != None else None
    
    def simulate_key(self, widget, key, state):
        if self.callback != None:
            keys = []
            keys.append(key)
            self.callback(keys, state)
        
    def get_key_layout(self):
        return self.device.key_layout
        
    def connect(self):
        if self.is_connected():
            raise Exception("Already connected")
        
        # Check hardware again
        self._init_driver()

        # Sanity check        
        if not self.device:
            raise usb.USBError("No supported logitech keyboards found on USB bus")
        if self.device == None:
            raise usb.USBError("WARNING: Found no " + self.model + " Logitech keyboard, Giving up")
        if self.fb_mode == None or self.device_name == None:
            raise usb.USBError("No matching framebuffer device found")
        if self.fb_mode != self.framebuffer_mode:
            raise usb.USBError("Unexpected framebuffer mode %s, expected %s for device %s" % (self.fb_mode, self.framebuffer_mode, self.device_name))
        
        # Open framebuffer
        logger.info("Using framebuffer %s"  % self.device_name)
        self.fb = fb.fb_device(self.device_name)
        if logger.isEnabledFor(logging.DEBUG):
            self.fb.dump()
        self.var_info = self.fb.get_var_info()
                
        # Create an empty string buffer for use with monochrome LCD
        self.empty_buf = ""
        for i in range(0, self.fb.get_fixed_info().smem_len):
            self.empty_buf += chr(0)
            
        # Connect to DBUS        
        system_bus = dbus.SystemBus()
        system_service_object = system_bus.get_object('org.gnome15.SystemService', '/org/gnome15/SystemService')     
        self.system_service = dbus.Interface(system_service_object, 'org.gnome15.SystemService')      
        
    def get_size(self):
        return self.device.lcd_size
        
    def get_bpp(self):
        return self.device.bpp
    
    def get_controls(self):
        return self.device_info.controls if self.device_info != None else None
    
    def paint(self, img):   
        width = img.get_width()
        height = img.get_height()
        character_width = width / 8
        fixed = self.fb.get_fixed_info()
        padding = fixed.line_length - character_width
        file_str = StringIO()
        
        if self.get_model_name() == g15driver.MODEL_G19:
            try:
                back_surface = cairo.ImageSurface (4, width, height)
            except:
                # Earlier version of Cairo
                back_surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, width, height)
            back_context = cairo.Context (back_surface)
            back_context.set_source_surface(img, 0, 0)
            back_context.set_operator (cairo.OPERATOR_SOURCE);
            back_context.paint()
                
            if back_surface.get_format() == cairo.FORMAT_ARGB32:
                """
                If the creation of the type 4 image failed (i.e. earlier version of Cairo)
                then we have to have ourselves. This is slow.
                """
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
        else:
            width, height = self.get_size()
            arrbuf = array.array('B', self.empty_buf)
            
            argb_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            argb_context = cairo.Context(argb_surface)
            argb_context.set_source_surface(img)
            argb_context.paint()
            
            '''
            Now convert the ARGB to a PIL image so it can be converted to a 1 bit monochrome image, with all
            colours dithered. It would be nice if Cairo could do this :( Any suggestions?
            ''' 
            pil_img = Image.frombuffer("RGBA", (width, height), argb_surface.get_data(), "raw", "RGBA", 0, 1)
            pil_img = ImageMath.eval("convert(pil_img,'1')",pil_img=pil_img)
            pil_img = ImageMath.eval("convert(pil_img,'P')",pil_img=pil_img)
            pil_img = pil_img.point(lambda i: i >= 250,'1')
            
            # Invert the screen if required
            if g15_invert_control.value == 0:            
                pil_img = pil_img.point(lambda i: 1^i)
            
            # Data is 160x43, 1 byte per pixel. Will have value of 0 or 1.
            width, height = self.get_size()
            data = list(pil_img.getdata())
            fixed = self.fb.get_fixed_info()
            v = 0
            b = 1
            for row in range(0, height):
                for col in range(0, width):
                    if data[( row * width ) + col]:
                        v += b
                    b = b << 1
                    if b == 256:
                        # Full byte
                        b = 1          
                        i = row * fixed.line_length + col / 8
                        
                        if row > 7 and col < 96:
                            '''
                            ????? This was discovered more by trial and error rather than any 
                            understanding of what is going on
                            '''
                            i -= 12 + ( 7 * fixed.line_length )
                            
                        arrbuf[i] = v   
                        v = 0 
            buf = arrbuf.tostring()
                
        if self.fb and self.fb.buffer:
            self.fb.buffer[0:len(buf)] = buf
            
    def process_svg(self, document):  
        if self.get_bpp() == 1:
            for element in document.getroot().iter():
                style = element.get("style")
                if style != None:
                    element.set("style", style.replace("font-family:Sans", "font-family:%s" % g15globals.fixed_size_font_name))
                    
    def on_update_control(self, control):
        if control == g19_keyboard_backlight_control:
            self._write_to_led("red:bl", control.value[0])
            self._write_to_led("green:bl", control.value[1])
            self._write_to_led("blue:bl", control.value[2])            
        elif control == g15_backlight_control:
            self._write_to_led("blue:keys", control.value)          
        elif control == g15_lcd_backlight_control:
            self._write_to_led("white:screen", control.value)          
        elif control == g15_lcd_contrast_control:
            self._write_to_led("contrast:screen", control.value)
        elif control == g15_invert_control:
            pass
        else:
            logger.warning("Setting the control " + control.id + " is not yet supported on this model. " + \
                           "Please report this as a bug, providing the contents of your /sys/class/led" + \
                           "directory and the keyboard model you use.")
    
    def set_mkey_lights(self, lights):
        self.lights = lights
        if self.device_info.leds:
            leds = self.device_info.leds
            self._write_to_led(leds[0], lights & g15driver.MKEY_LIGHT_1 != 0)        
            self._write_to_led(leds[1], lights & g15driver.MKEY_LIGHT_2 != 0)        
            self._write_to_led(leds[2], lights & g15driver.MKEY_LIGHT_3 != 0)        
            self._write_to_led(leds[3], lights & g15driver.MKEY_LIGHT_MR != 0)
        else:
            logger.warning(" Setting MKey lights on " + self.device.model_id + " not yet supported. " + \
            "Please report this as a bug, providing the contents of your /sys/class/led" + \
            "directory and the keyboard model you use.")
    
    def grab_keyboard(self, callback):
        if self.key_thread != None:
            raise Exception("Keyboard already grabbed")      
        self.key_thread = KeyboardReceiveThread(self.device)
        for devpath in self.keyboard_devices:
            self.key_thread.devices.append(ForwardDevice(callback, self.device_info.key_map, devpath, devpath))
        self.key_thread.start()
        
    '''
    Private
    '''
    
    def _stop_receiving_keys(self):
        if self.key_thread != None:
            self.key_thread.deactivate()
            self.key_thread = None
            
    def _do_write_to_led(self, name, value):
        logger.info("Writing %d to LED %s" % (value, name ))
        self.system_service.SetLight(self.device.uid, name, value)
    
    def _write_to_led(self, name, value):
        gobject.idle_add(self._do_write_to_led, name, value)
#        path = self.led_path_prefix[0] + "/" + self.led_path_prefix[1] + name + "/brightness"
#        try :
#            file = open(path, "w")
#            try :
#                file.write("%d\n" % value)
#            finally :
#                file.close()            
#        except IOError:
#            # Fallback to lgsetled
#            os.system("lgsetled -s -f %s %d" % (self.led_path_prefix[1] + name, value))

    
    def _handle_bound_key(self, key):
        logger.info("G key - %d", key)
        return True
        
    def _mode_changed(self, client, connection_id, entry, args):
        if self.is_connected():
            self.disconnect()
        else:
            logger.warning("WARNING: Mode change would cause disconnect when already connected.", entry)
        
    def _init_driver(self):
        
        if self.device.bpp == 1:
            self.framebuffer_mode = "GFB_MONO"
        else:
            self.framebuffer_mode = "GFB_QVGA"
        logger.info("Using %s frame buffer mode" % self.framebuffer_mode)
            
        self.device_info = device_info[self.device.model_id]
                    
        # Try and find the paths for the LED devices.
        # Note, I am told these files may be in different places on different kernels / distros. Will
        # just have to see how it goes for now
        self.led_path_prefix = self._find_led_path_prefix(self.device_info.led_prefix)
        if self.led_path_prefix == None:
            logger.warning("Could not find control files for LED lights. Some features won't work")
            
        # Try and find the paths for the keyboard devices
        self.keyboard_devices = []
        dir = "/dev/input/by-id"
        for p in os.listdir(dir):
            if re.search(self.device_info.keydev_pattern, p):
                self.keyboard_devices.append(dir + "/" + p)
                
        # Determine the framebuffer device to use
        self.device_name = self.conf_client.get_string("/apps/gnome15/%s/fb_device" % self.device.uid)
        self.fb_mode = None
        if self.device_name == None or self.device_name == "" or self.device_name == "auto":
            
            # Find the first framebuffer device that matches the mode
            for fb in os.listdir("/sys/class/graphics"):
                if fb != "fbcon":
                    try:
                        f = open("/sys/class/graphics/" + fb + "/name", "r")
                        try :
                            fb_mode = f.readline().replace("\n", "")
                            if fb_mode == self.framebuffer_mode:
                                self.fb_mode = fb_mode
                                self.device_name = "/dev/" + fb
                                break
                        finally :
                            f.close() 
                    except Exception as e:
                        logger.warning("Could not open %s. %s" %(self.device_name, str(e)))
        else:
            f = open("/sys/class/graphics/" + os.path.basename(self.device_name) + "/name", "r")
            try :
                self.fb_mode = f.readline().replace("\n", "")
            finally :
                f.close()
        
                        
    def _find_led_path_prefix(self, led_model):
        if led_model != None:
            if os.path.exists("/sys/class/leds"):
                for dir in ["/sys/class/leds" ]: 
                    if os.path.isdir(dir):
                        for p in os.listdir(dir):
                            if p.startswith(led_model + "_"):
                                number = p.split("_")[1].split(":")[0]
                                return (dir, led_model + "_" + number + ":")
