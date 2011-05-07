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
import gnome15.g15_driver as g15driver
import gnome15.g15_devices as g15devices
import gnome15.g15_util as g15util
import gnome15.g15_globals as g15globals
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
import logging

logger = logging.getLogger("driver")

# Driver information (used by driver selection UI)
id = "kernel"
name = "Kernel Drivers"
description = "Requires ali123's Logitech Kernel drivers. This method requires no other " + \
            "daemons to be running, and works with the G13, G15 and G19 keyboards. " 
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

g15_backlight_control = g15driver.Control("keyboard_backlight", "Keyboard Backlight Level", 0, 0, 2, hint=g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
g15_lcd_backlight_control = g15driver.Control("lcd_backlight", "LCD Backlight", 0, 0, 2, hint=g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
#g15_lcd_backlight_control = g15driver.Control("lcd_backlight", "LCD Backlight", 0, 0, 1, hint=g15driver.HINT_SWITCH)
g15_lcd_contrast_control = g15driver.Control("lcd_contrast", "LCD Contrast", 0, 0, 48, hint=g15driver.HINT_SHADEABLE)
g15_invert_control = g15driver.Control("invert_lcd", "Invert LCD", 0, 0, 1, hint=g15driver.HINT_SWITCH)
g15_controls = [ g15_backlight_control, g15_invert_control, g15_lcd_backlight_control, g15_lcd_contrast_control ]  

class DeviceInfo:
    def __init__(self, leds, controls, key_map, led_prefix, keydev_pattern):
        self.leds = leds
        self.controls = controls
        self.key_map = key_map
        self.led_prefix = led_prefix 
        self.keydev_pattern = keydev_pattern
        
device_info = {
               g15driver.MODEL_G19: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "red:mr" ], g19_controls, g19_key_map, "g19", "Logitech_G19_Gaming_Keyboard.*if*"), 
               g15driver.MODEL_G15_V1: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "blue:mr" ], g15_controls, g15_key_map, "g15", "G15_Keyboard_G15.*if*"), 
               g15driver.MODEL_G15_V2: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "blue:mr" ], g15_controls, g15_key_map, "g15", "G15_Keyboard_G15.*if*"),
               g15driver.MODEL_G13: DeviceInfo(["red:m1", "red:m2", "red:m3", "blue:mr" ], g15_controls, g15_key_map, "g13", "G13_Keyboard_G13.*if*"),
               g15driver.MODEL_G110: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "red:mr" ], g15_controls, g15_key_map, "g110", "G110_Keyboard_G15.*if*")
               }
        

# Other constants
EVIOCGRAB = 0x40044590

def show_preferences(parent, gconf_client):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "driver_kernel.glade"))    
    dialog = widget_tree.get_object("DriverDialog")
    dialog.set_transient_for(parent)  
    device_model = widget_tree.get_object("DeviceModel")
    device_model.clear()
    device_model.append(["auto"])
    for dir in os.listdir("/dev"):
        if dir.startswith("fb"):
            device_model.append(["/dev/" + dir])    
    g15util.configure_combo_from_gconf(gconf_client, "/apps/gnome15/fb_device", "DeviceCombo", "/dev/fb0", widget_tree)
    g15util.configure_combo_from_gconf(gconf_client, "/apps/gnome15/fb_mode", "ModeCombo", "auto", widget_tree)
    dialog.run()
    dialog.hide()
    
class KeyboardReceiveThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._run = True
        self.name = "KeyboardReceiveThread"
        self.setDaemon(True)
        self.devices = []
        
    def deactivate(self):
        self._run = False
        for dev in self.devices:
            try :
                fcntl.ioctl(dev.fileno(), EVIOCGRAB, 0)
            except Exception as e:
                print e
            self.fds[dev.fileno()].close()
        
    def run(self):        
        poll = select.poll()
        self.fds = {}
        for dev in self.devices:
            poll.register(dev, select.POLLIN | select.POLLPRI)
            fcntl.ioctl(dev.fileno(), EVIOCGRAB, 1)
            self.fds[dev.fileno()] = dev
        while self._run:
            for x, e in poll.poll():
                dev = self.fds[x]
                dev.read()

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
            logging.debug(" --> %r" % event)
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
            print "WARNING: Unhandled event: %s" % event
            
    def _event(self, event, state):
        key = str(event.ecode)
        if key in self.key_map:
            self.callback([self.key_map[key]], state)
        else:
            print "WARNING: Unmapped key for event: %s" % event

class Driver(g15driver.AbstractDriver):

    def __init__(self, on_close=None):
        g15driver.AbstractDriver.__init__(self, "kernel")
        self.fb = None
        self.var_info = None
        self.on_close = on_close
        self.key_thread = None
        self.device = None
        self.device_info = None
        self.conf_client = gconf.client_get_default()
        
        try :
            self._init_driver()
        except Exception as e:
            logger.warning("Failed to initialise driver properly. %s" % str(e))
    
    def get_antialias(self):         
        if self.device.bpp != 1:
            return cairo.ANTIALIAS_DEFAULT
        else:
            return cairo.ANTIALIAS_NONE
        
    def disconnect(self):
        if not self.is_connected():
            raise Exception("Not connected")
        self._stop_receiving_keys()
        self.conf_client.notify_remove(self.notify_h)
        self.fb.__del__()
        self.fb = None
        if self.on_close != None:
            g15util.schedule("Close", 0, self.on_close)
        
    def is_connected(self):
        return self.fb != None
        
    def window_closed(self, window, evt):
        if self.on_close != None:
            self.on_close(retry=False)
    
    def get_model_names(self):
        return [ g15driver.MODEL_G15_V1, g15driver.MODEL_G15_V2, g15driver.MODEL_G13, g15driver.MODEL_G19 ]
            
    def get_name(self):
        return "Linux Logitech Kernel Driver"
    
    def get_model_name(self):
        return self.device.model_name if self.device != None else None
    
    def simulate_key(self, widget, key, state):
        if self.callback != None:
            keys = []
            keys.append(key)
            self.callback(keys, state)
        
    def get_key_layout(self):
        return self.device.key_layout
        
    def get_zoomed_size(self):
        size = self.get_size()
        zoom = self.get_zoom()
        return (size[0] * zoom, size[1] * zoom)
        
    def get_zoom(self):
        if self.mode == g15driver.MODEL_G19:
            return 1
        else:
            return 3
        
    def connect(self):
        if self.is_connected():
            raise Exception("Already connected")
        self.notify_h = self.conf_client.notify_add("/apps/gnome15/fb_mode", self._mode_changed);
        
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
            raise usb.USBError("Unexpected framebuffer mode %s, expected %s" % (self.fb_mode, self.framebuffer_mode))
        
        # Open framebuffer
        print "Using framebuffer",self.device_name
        self.fb = fb.fb_device(self.device_name)
        self.fb.dump()
        self.var_info = self.fb.get_var_info()
        
    def get_name(self):
        return "Linux Kernel Driver"
        
    def get_size(self):
        if self.var_info is None:
            return (0,0)
        return (self.var_info.xres, self.var_info.yres)
        
    def get_bpp(self):
        if self.var_info is None:
            return 0
        return self.var_info.bits_per_pixel
    
    def get_controls(self):
        return self.device_info.controls if self.device_info != None else None
    
    def paint(self, img):   
        
        width = img.get_width()
        height = img.get_height()
        
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
            size = self.get_size()
            
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
            
            if g15_invert_control.value == 0:            
                pil_img = pil_img.point(lambda i: 1^i)
#            pil_img = pil_img.convert("L")
                
#            data = list(pil_img.getdata())
#            data_len = len(data)
#            print "Data",data_len,data
#            buf = ""
#            for x in range(0, data_len, 8):
#                v = 0
#                i = 128 
#                for y in range(x + 7, -1, -1):
#                    j = data[y]
#                    v += i if j == 1 else 0
#                    i /= 2                    
#                buf += chr(v)
#            buf = str(pil_img.getdata())

            buf = ""
#            for x in range(0, len(self.fb.buffer)):
#                if x < 100: 
#                    buf += chr(255)
#                else:
#                    buf += chr(0)
                   
            l = len(self.fb.buffer)
            for x in range(0, l - 1):
                buf += chr(255)
#                if x < l / 2: 
#                    buf += chr(85)
#                else: 
#                    buf += chr(170)

#        print "Buffer len",len(buf),"expect",len(self.fb.buffer)
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
            print "WARNING: Setting the control " + control.id + " is not yet supported on this model. " + \
            "Please report this as a bug, providing the contents of your /sys/class/led" + \
            "directory and the keyboard model you use."
    
    def set_mkey_lights(self, lights):
        self.lights = lights
        if self.mode in led_light_names:
            leds = led_light_names[self.mode] 
            self._write_to_led(leds[0], lights & g15driver.MKEY_LIGHT_1 != 0)        
            self._write_to_led(leds[1], lights & g15driver.MKEY_LIGHT_2 != 0)        
            self._write_to_led(leds[2], lights & g15driver.MKEY_LIGHT_3 != 0)        
            self._write_to_led(leds[3], lights & g15driver.MKEY_LIGHT_MR != 0)
        else:
            print "WARNING: Setting MKey lights on " + self.mode + " not yet supported. " + \
            "Please report this as a bug, providing the contents of your /sys/class/led" + \
            "directory and the keyboard model you use."
    
    def grab_keyboard(self, callback):
        if self.key_thread != None:
            raise Exception("Keyboard already grabbed")      
        self.key_thread = KeyboardReceiveThread()
        for devpath in self.keyboard_devices:
            self.key_thread.devices.append(ForwardDevice(callback, self.key_map, devpath, devpath))
        self.key_thread.start()
        
    '''
    Private
    '''
    
    def _stop_receiving_keys(self):
        if self.key_thread != None:
            self.key_thread.deactivate()
            self.key_thread = None
    
    def _write_to_led(self, name, value):
        print "Writing",value,"to LED",name
        path = self.led_path_prefix[0] + "/" + self.led_path_prefix[1] + name + "/brightness"
        try :
            file = open(path, "w")
            try :
                file.write("%d\n" % value)
            finally :
                file.close()            
        except IOError:
            # Fallback to lgsetled
            os.system("lgsetled -s -f %s %d" % (self.led_path_prefix[1] + name, value))

    
    def _handle_bound_key(self, key):
        print "G key - %d", key
        return True
        
    def _mode_changed(self, client, connection_id, entry, args):
        if self.is_connected():
            self.disconnect()
        else:
            print "WARNING: Mode change would cause disconnect when already connected.", entry
        
    def _init_driver(self):
        mode = self.conf_client.get_string("/apps/gnome15/fb_mode")
        
        # Find the first device if auto mode
        if mode == None or mode == "" or mode == "auto":
            mode = ""
            devices = g15devices.find_all_devices()
            if len(devices) > 0:
                mode = devices[0].model_name
                
        # Find the selected device
        self.device = g15devices.find_device(mode)
        if not self.device:      
            self.device = None
            self.device_info = None
            raise Exception("Could not find any device for model %s" % mode)
        
        if self.device.bpp == 1:
            self.framebuffer_mode = "GFB_MONO"
        else:
            self.framebuffer_mode = "GFB_QVGA"
            
        self.device_info = device_info[mode]
                    
        # Try and find the paths for the LED devices.
        # Note, I am told these files may be in different places on different kernels / distros. Will
        # just have to see how it goes for now
        self.led_path_prefix = self._find_led_path_prefix(self.device_info.led_prefix)
        if self.led_path_prefix == None:
            print "WARNING: Could not find control files for LED lights. Some features won't work"
            
        # Try and find the paths for the keyboard devices
        self.keyboard_devices = []
        dir = "/dev/input/by-id"
        for p in os.listdir(dir):
            if re.search(self.device_info.keydev_pattern, p):
                self.keyboard_devices.append(dir + "/" + p)
                
        # Determine the framebuffer device to use
        self.device_name = self.conf_client.get_string("/apps/gnome15/fb_device")
        self.fb_mode = None
        if self.device_name == None or self.device_name == "" or self.device_name == "auto":
            for fb in os.listdir("/sys/class/graphics"):
                if fb != "fbcon":
                    f = open("/sys/class/graphics/" + fb + "/name", "r")
                    try :
                        fb_mode = f.readline().replace("\n", "")
                        if fb_mode == self.framebuffer_mode:
                            self.fb_mode = fb_mode
                            self.device_name = "/dev/" + fb
                            break
                    finally :
                        f.close() 
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
                
        
