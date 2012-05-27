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

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("gnome15-drivers").ugettext

from threading import Thread
from pyinputevent.pyinputevent import SimpleDevice

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

# Logging
import logging
logger = logging.getLogger("driver")

# Driver information (used by driver selection UI)
id = "g930"
name = _("G930/G35 Driver")
description = _("Simple driver that supports the keys on the G930 and G35 headphones. ")
has_preferences = True


"""
This dictionaries map the default codes emitted by the input system to the
Gnome15 codes.
"""  
g930_key_map = {
               S.KEY_PREVIOUSSONG : g15driver.G_KEY_G1,
               S.KEY_PLAYPAUSE : g15driver.G_KEY_G2,
               S.KEY_NEXTSONG : g15driver.G_KEY_G3,
               S.KEY_MUTE : g15driver.G_KEY_MUTE,
               S.KEY_VOLUMEDOWN : g15driver.G_KEY_VOL_DOWN,
               S.KEY_VOLUMEUP  : g15driver.G_KEY_VOL_UP
               }

# Other constants
EVIOCGRAB = 0x40044590

def show_preferences(device, parent, gconf_client):
    prefs = G930DriverPreferences(device, gconf_client)
    return prefs.component

class G930DriverPreferences():
    
    def __init__(self, device, gconf_client):
        self.device = device
        
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "driver_g930.glade"))
        
        self.grab_multimedia = widget_tree.get_object("GrabMultimedia")
        g15util.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/%s/grab_multimedia" % device.uid, "GrabMultimedia", False, widget_tree)
        
        self.component = widget_tree.get_object("DriverComponent")
        
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
                logger.info("Failed ungrab. %s" % str(e))
            logger.info("Closing %d" % dev.fileno())
            try :
                self.fds[dev.fileno()].close()
            except Exception as e:
                logger.info("Failed close. %s" % str(e))
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
                    if dev:
                        dev.read()
                except OSError as e:
                    # Ignore this error if deactivated
                    if self._run:
                        raise e
        logger.info("Thread left")
        
            
'''
Abstract input device
'''
class AbstractInputDevice(SimpleDevice):
    def __init__(self, callback, key_map, *args, **kwargs):
        SimpleDevice.__init__(self, *args, **kwargs)
        self.callback = callback
        self.key_map = key_map

    def _event(self, event_code, state):
        if event_code in self.key_map:
            key = self.key_map[event_code]
            self.callback([key], state)
        else:
            logger.warning("Unmapped key for event: %s" % event_code)
        
'''
SimpleDevice implementation for handling multi-media keys. 
'''
class MultiMediaDevice(AbstractInputDevice):
    def __init__(self, callback, *args, **kwargs):
        AbstractInputDevice.__init__(self, callback, g930_key_map, *args, **kwargs)
        
    def receive(self, event):
        print "%s" % str(event)
        if event.etype == S.EV_KEY:
            state = g15driver.KEY_STATE_DOWN if event.evalue == 1 else g15driver.KEY_STATE_UP
            if event.evalue != 2:
                self._event(event.ecode, state)
        elif event.etype == 0:
            return
        else:
            logger.warning("Unhandled event: %s" % str(event))

class Driver(g15driver.AbstractDriver):

    def __init__(self, device, on_close=None):
        g15driver.AbstractDriver.__init__(self, "g930")
        self.notify_handles = []
        self.on_close = on_close
        self.key_thread = None
        self.device = device
        self.connected = False
        self.conf_client = gconf.client_get_default()
        self._init_device()
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/%s/grab_multimedia" % self.device.uid, self._config_changed, None))
    
    def get_antialias(self):  
        return cairo.ANTIALIAS_NONE
        
    def on_disconnect(self):
        if not self.is_connected():
            raise Exception("Not connected")
        self._stop_receiving_keys()
        if self.on_close != None:
            g15util.schedule("Close", 0, self.on_close, self)
        
    def is_connected(self):
        return self.connected
    
    def get_model_names(self):
        return [ g15driver.MODEL_G930, g15driver.MODEL_G35 ]
            
    def get_name(self):
        return "Gnome15 G930/G35 Driver"
    
    def get_model_name(self):
        return self.device.model_id if self.device != None else None
    
    def simulate_key(self, widget, key, state):
        if self.callback != None:
            keys = []
            keys.append(key)
            self.callback(keys, state)
    
    def get_action_keys(self):
        return self.device.action_keys
        
    def get_key_layout(self):
        if self.grab_multimedia:
            l = list(self.device.key_layout)
            l.append([])
            l.append([ g15driver.G_KEY_VOL_UP, g15driver.G_KEY_VOL_DOWN, g15driver.G_KEY_MUTE ])
            return l
        else:
            return self.device.key_layout
        
    def connect(self):
        if self.is_connected():
            raise Exception("Already connected")
        self.notify_handles = []
        self._init_driver()
        if not self.device:
            raise usb.USBError("No supported logitech headphones found on USB bus")
        if self.device == None:
            raise usb.USBError("WARNING: Found no " + self.model + " Logitech headphone, Giving up")
        
    def _load_configuration(self):
        self.grab_multimedia = self.conf_client.get_bool("/apps/gnome15/%s/grab_multimedia" % self.device.uid)
            
    def _config_changed(self, client, connection_id, entry, args):
        self._reload_and_reconnect()
        
    def get_size(self):
        return self.device.lcd_size
        
    def get_bpp(self):
        return self.device.bpp
    
    def get_controls(self):
        return []
    
    def paint(self, img):  
        pass
                    
    def on_update_control(self, control):
        pass
    
    def grab_keyboard(self, callback):
        if self.key_thread != None:
            raise Exception("Keyboard already grabbed")
        
        self.key_thread = KeyboardReceiveThread(self.device)
        for devpath in self.mm_devices:
            logger.info("Adding input multi-media device %s" % devpath)
            self.key_thread.devices.append(MultiMediaDevice(callback, devpath, devpath))
            
        self.key_thread.start()
        
    '''
    Private
    '''
        
    def _reload_and_reconnect(self):
        self._load_configuration()
        if self.is_connected():
            self.disconnect()
            
    def _stop_receiving_keys(self):
        if self.key_thread != None:
            self.key_thread.deactivate()
            self.key_thread = None
            
    def _init_device(self):
        self._load_configuration()
        self.device_name = None
        
    def _init_driver(self):
        self._init_device()
        self.mm_devices = []
        dir_path = "/dev/input/by-id"
        for p in os.listdir(dir_path):
            # TODO - not sure about the G35 - feedback needed
            if re.search(r"usb-Logitech_Logitech_G930_Headset-event-if.*", p) or re.search(r"usb-Logitech_Logitech_G35_Headset-event-if.*", p):
                logger.info("Input multi-media device %s matches" % p)
                self.mm_devices.append(dir_path + "/" + p)
                
    def __del__(self):
        for h in self.notify_handles:
            self.conf_client.notify_remove(h)