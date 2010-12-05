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
import gnome15.g15_util as g15util
import gnome15.g15_globals as pglobals
import gconf
import fcntl
import os
import gtk
import cairo
import re
import usb
import fb


# Driver information (used by driver selection UI)
id="kernel"
name="Kernel Drivers"
description="Requires ali123's Logitech Kernel drivers. This method requires no other " + \
            "daemons to be running, and works with the G13, G15 and G19 keyboards. " 
has_preferences=True

# Key layouts
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
g19_key_layout = [
              [ g15driver.G_KEY_G1, g15driver.G_KEY_G7 ],
              [ g15driver.G_KEY_G2, g15driver.G_KEY_G8 ],
              [ g15driver.G_KEY_G3, g15driver.G_KEY_G9 ],
              [ g15driver.G_KEY_G4, g15driver.G_KEY_G10 ],
              [ g15driver.G_KEY_G5, g15driver.G_KEY_G11 ],
              [ g15driver.G_KEY_G6, g15driver.G_KEY_G12 ],
              [ g15driver.G_KEY_G6, g15driver.G_KEY_G12 ],
              [ g15driver.G_KEY_UP ],
              [ g15driver.G_KEY_LEFT, g15driver.G_KEY_OK, g15driver.G_KEY_RIGHT ],
              [ g15driver.G_KEY_DOWN ],
              [ g15driver.G_KEY_MENU, g15driver.G_KEY_BACK, g15driver.G_KEY_SETTINGS ],
              [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ],
              ]

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
               "88" : g15driver.G_KEY_G12,
               }

# Controls

g19_keyboard_backlight_control = g15driver.Control("backlight-colour", "Keyboard Backlight Colour", (0, 0, 0), hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
g19_lcd_brightness_control = g15driver.Control("lcd-brightness", "LCD Brightness", 100, 0, 100, hint = g15driver.HINT_SHADEABLE)
g19_foreground_control = g15driver.Control("foreground", "Default LCD Foreground", (255, 255, 255), hint = g15driver.HINT_FOREGROUND)
g19_background_control = g15driver.Control("background", "Default LCD Background", (0, 0, 0), hint = g15driver.HINT_BACKGROUND)
g19_controls = [ g19_keyboard_backlight_control, g19_lcd_brightness_control, g19_foreground_control, g19_background_control]

g15_backlight_control = g15driver.Control("keyboard-backlight", "Keyboard Backlight Level", 0, 0, 2, hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
g15_invert_control = g15driver.Control("invert-lcd", "Invert LCD", 0, 0, 1, hint = g15driver.HINT_SWITCH )
g15_controls = [ g15_backlight_control, g15_invert_control ]  

# Other constants
EVIOCGRAB = 0x40044590

def show_preferences(parent, gconf_client):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(pglobals.glade_dir, "driver_kernel.glade"))    
    dialog = widget_tree.get_object("DriverDialog")
    dialog.set_transient_for(parent)  
    device_model = widget_tree.get_object("DeviceModel")
    device_model.clear()
    for dir in os.listdir("/dev"):
        if dir.startswith("fb"):
            device_model.append(["/dev/" + dir])    
    g15util.configure_combo_from_gconf(gconf_client,"/apps/gnome15/fb_device", "DeviceCombo", "/dev/fb0", widget_tree)
    g15util.configure_combo_from_gconf(gconf_client,"/apps/gnome15/fb_mode", "ModeCombo", "auto", widget_tree)
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
        print "Ungrabbing keys"
        for dev in self.devices:
            try :
                fcntl.ioctl(dev.fileno(), EVIOCGRAB, 0)
            except Exception as e:
                print e
            self.fds[dev.fileno()].close()
        
    def run(self):        
        poll = select.poll()
        self.fds = {}
        print "Grabbing keys"
        for dev in self.devices:
            poll.register(dev, select.POLLIN | select.POLLPRI)
            fcntl.ioctl(dev.fileno(), EVIOCGRAB, 1)
            self.fds[dev.fileno()] = dev
        print "Waiting for key events"
        while self._run:
            for x,e in poll.poll():
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

    def __init__(self, on_close = None):
        g15driver.AbstractDriver.__init__(self, "kernel")
        self.fb = None
        self.on_close = on_close
        self.key_thread = None
        self.conf_client = gconf.client_get_default()
        self._init_driver()
    
    def get_antialias(self):        
        if self.mode == g15driver.MODEL_G15_V1 or self.mode == g15driver.MODEL_G15_V2 or self.mode == g15driver.MODEL_G13: 
            return cairo.ANTIALIAS_NONE
        else:
            return cairo.ANTIALIAS_DEFAULT
        
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
    
    def get_model_name(self):
        return self.mode
    
    def simulate_key(self, widget, key, state):
        if self.callback != None:
            keys = []
            keys.append(key)
            self.callback(keys, state)
        
    def get_key_layout(self):
        return self.key_layout
        
    def get_zoomed_size(self):
        size = self.get_size()
        zoom = self.get_zoom()
        return ( size[0] * zoom, size[1] * zoom )
        
    def get_zoom(self):
        if self.mode == g15driver.MODEL_G19:
            return 1
        else:
            return 3
        
    def connect(self):
        if self.is_connected():
            raise Exception("Already connected")      
        self.notify_h = self.conf_client.notify_add("/apps/gnome15/fb_mode", self._mode_changed);
        self._init_driver()
         
        self.device_name = self.conf_client.get_string("/apps/gnome15/fb_device")
        if self.device_name == None or self.device_name == "":
            self.device_name = "/dev/fb0"
        self.device_name = "/dev/fb1"
        print "Opening",self.device_name
        self.fb = fb.fb_device(self.device_name)
        print "Opened",self.device_name
        self.fb.dump() 
        self.var_info = self.fb.get_var_info()
        print "Screen bytes: " + str( self.fb.get_screen_size())    
        
    def get_name(self):
        return "Linux Kernel Driver"
        
    def get_size(self):
        return ( self.var_info.xres, self.var_info.yres )
        
    def get_bpp(self):
        return self.var_info.bits_per_pixel
    
    def get_controls(self):
        return self.controls
    
    def paint(self, img):   
        
        width = img.get_width()
        height = img.get_height()

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

        self.fb.buffer[0:] = buf
            
    def process_svg(self, document):  
        if self.get_bpp() == 1:
            for element in document.getroot().iter():
                style = element.get("style")
                if style != None:
                    element.set("style", style.replace("font-family:Sans","font-family:Fixed"))
                    
    def update_control(self, control):
        if control == g19_keyboard_backlight_control:
            self._write_to_led("red:bl", control.value[0])
            self._write_to_led("green:bl", control.value[1])
            self._write_to_led("blue:bl", control.value[2])
    
    def set_mkey_lights(self, lights):
        self.lights = lights      
        if self.mode == g15driver.MODEL_G19:  
            self._write_to_led("orange:m1", lights & g15driver.MKEY_LIGHT_1 != 0)        
            self._write_to_led("orange:m2", lights & g15driver.MKEY_LIGHT_2 != 0)        
            self._write_to_led("orange:m3", lights & g15driver.MKEY_LIGHT_3 != 0)        
            self._write_to_led("red:mr", lights & g15driver.MKEY_LIGHT_MR != 0)
        else:
            print "WARNING: Setting MKey lights on keyboards other than G19 not yet supported."
    
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
        path = self.led_path_prefix + name + "/brightness"
        try :
            file = open(path, "w")
            try :
                file.write("%d\n" % value)
            finally :
                file.close()            
        except IOError:
            print "WARNING: Failed to write to LED device. This is probably a permissions problem. Check that %s is writable by your user." % path

    @staticmethod
    def _find_device(idVendor, idProduct):
        for bus in usb.busses():
            for dev in bus.devices:
                if dev.idVendor == idVendor and \
                        dev.idProduct == idProduct:
                    return dev
        return None
    
    def _handle_bound_key(self, key):
        print "G key - %d", key
        return True
        
    def _mode_changed(self, client, connection_id, entry, args):
        if self.is_connected():
            self.disconnect()
        else:
            print "WARNING: Mode change would cause disconnect when already connected.", entry
        
    def _init_driver(self):      
        self.mode = self.conf_client.get_string("/apps/gnome15/fb_mode")
        if self.mode == None or self.mode == "" or self.mode == "auto":
            device = self._find_device(0x046d, 0xc229)
            print "Looking for G19"
            if not device:
                print "No recognised devices, G19 giving up"
                raise usb.USBError("No logitech keyboards found on USB bus")
            else:
                self.mode = g15driver.MODEL_G19
        
        self.key_map = None
        if self.mode == g15driver.MODEL_G15_V1 or self.mode == g15driver.MODEL_G15_V2 or self.mode == g15driver.MODEL_G13:
            self.controls = g15_controls
            if self.mode == g15driver.MODEL_G15_V1:
                self.key_layout = g15v1_key_layout
            elif self.mode == g15driver.MODEL_G15_V2:
                self.key_layout = g15v2_key_layout
            elif self.mode == g15driver.MODEL_G13:
                self.key_layout = g13_key_layout
        else:            
            self.controls = g19_controls
            self.key_layout = g19_key_layout
            self.key_map = g19_key_map
            
        keydev_pattern = "Logitech_" + self.mode.upper() + "_Gaming_Keyboard"
            
        # Try and find the paths for the LED devices.
        # Note :-
        # 1) 'mode' might not be the right thing to use here. Need to check what the prefix is for other devices
        # 2) I am told these files may be in different places on different kernels / distros
        # 3) Currently permissions are likely to be wrong and must be manually adjusted         
        self.led_path_prefix = self._find_led_path_prefix(self.mode)
        if self.led_path_prefix == None:
            print "WARNING: Could not find control files for LED lights. Some features won't work"
        else:
            print "Control files for LED lights are prefixed with " + self.led_path_prefix
            
        # Try and find the paths for the keyboard devices
        self.keyboard_devices = []
        dir = "/dev/input/by-id"
        for p in os.listdir(dir):
            if re.search(keydev_pattern, p):
                self.keyboard_devices.append(dir + "/" + p)
        print "Keyboard devices =",self.keyboard_devices
                        
    def _find_led_path_prefix(self, led_model):
        if led_model != None:
            for dir in ["/sys/class/leds" ]: 
                for p in os.listdir(dir):
                    if p.startswith(led_model + "_"):
                        number = p.split("_")[1].split(":")[0]
                        return dir + "/" + led_model + "_" + number + ":"
                
        