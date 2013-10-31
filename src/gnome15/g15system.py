#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2011 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 
import gobject
import g15globals
import signal
import dbus.service
import os.path
import g15devices
import g15driver
import util.g15scheduler as g15scheduler

# Logging
import logging
logger = logging.getLogger(__name__)
    
NAME = "Gnome15"
VERSION = g15globals.version
BUS_NAME="org.gnome15.SystemService"
OBJECT_PATH="/org/gnome15/SystemService"
IF_NAME="org.gnome15.SystemService"

"""
Maps model id's to driver names
"""
driver_names = {
                g15driver.MODEL_G15_V1: "g15",
                g15driver.MODEL_G15_V2: "g15",
                g15driver.MODEL_G19: "g19",
                g15driver.MODEL_G110: "g110",
                g15driver.MODEL_G13: "g13",
                }

class SystemService(dbus.service.Object):
    
    def __init__(self, bus, controller):
        bus_name = dbus.service.BusName(BUS_NAME, bus=bus, replace_existing=False, allow_replacement=False, do_not_queue=True)
        dbus.service.Object.__init__(self, None, OBJECT_PATH, bus_name)
        self._controller = controller
        
    """
    DBUS API
    """
    
    @dbus.service.method(IF_NAME)
    def Stop(self):
        self._controller.stop()
        
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetInformation(self):
        return ( "%s System Service" % g15globals.name, "Gnome15 Project", g15globals.version, "1.0" )
    
    @dbus.service.method(IF_NAME, in_signature='ssn')
    def SetLight(self, device, light, value):
        self._controller.devices[device].leds[light].set_led_value(value);
        
    @dbus.service.method(IF_NAME, in_signature='sb')
    def SetKeymapSwitching(self, device, enabled):        
        self._controller.devices[device].set_keymap_switching(enabled)
        
    @dbus.service.method(IF_NAME, in_signature='s', out_signature='b')
    def GetKeymapSwitching(self, device):        
        self._controller.devices[device].get_keymap_switching()
        
    @dbus.service.method(IF_NAME, in_signature='sn')
    def SetKeymapIndex(self, device, index):        
        self._controller.devices[device].set_keymap_index(index)
        
    @dbus.service.method(IF_NAME, in_signature='s', out_signature='n')
    def GetKeymapIndex(self, device):        
        return self._controller.devices[device].get_keymap_index()
        
    @dbus.service.method(IF_NAME, in_signature='sa{tt}')
    def SetKeymap(self, device, keymap):        
        self._controller.devices[device].set_keymap(keymap)
        
    @dbus.service.method(IF_NAME, in_signature='s', out_signature='a{tt}')
    def GetKeymap(self, device):        
        return self._controller.devices[device].get_keymap()
        
    @dbus.service.method(IF_NAME, in_signature='ss', out_signature='n')
    def GetLight(self, device, light):        
        return self._controller.devices[device].leds[light].get_value()
        
    @dbus.service.method(IF_NAME, out_signature='as')
    def GetDevices(self):        
        c = []
        for l in self._controller.devices:
            c.append(l)
        return c
        
    @dbus.service.method(IF_NAME, in_signature='s', out_signature='as')
    def GetLights(self, device):        
        return self._controller.devices[device].leds.keys()
        
    @dbus.service.method(IF_NAME, in_signature='ss', out_signature='n')
    def GetMaxLight(self, device, light):
        return self._controller.devices[device].leds[light].get_max()
    
    
def get_int_value(filename):
    return int(get_value(filename))
        
def get_value(filename):
    fd = open(filename, "r")
    try :
        return fd.read()
    finally :
        fd.close()
        
def set_value(filename, value):
    g15scheduler.execute("System", "setValue", _do_set_value, filename, value);
        
def _do_set_value(filename, value):
    logger.debug("Writing %s to %s" % (filename, value))
    fd = open(filename, "w")
    try :
        fd.write("%s\n" % str(value))
    finally :
        fd.close()            
    
class KeyboardDevice():
    def __init__(self, device, device_path, index):
        self.leds = {}
        self.device = device
        self.device_path = device_path
        self.minor = get_int_value(os.path.join(device_path, "minor"))  
        self.uid = "%s_%d" % ( device.model_id, index )      
        leds_path = os.path.join(device_path, "leds")
        for d in os.listdir(leds_path):
            f = os.path.join(leds_path, d)
            keyboard_device, color, control = d.split(":")
            keyboard_device, index = keyboard_device.split("_")
            light_key = "%s:%s" % ( color, control )
            self.leds[light_key] = LED(light_key, self, f)
            
    def set_keymap_switching(self, enabled):
        logger.info("Setting keymap switching on %s to '%s'" % (self.device.uid, str(enabled)))
        set_value(os.path.join(self.device_path, "keymap_switching"), 1 if enabled else 0)
        
    def get_keymap_switching(self):
        return get_int_value(os.path.join(self.device_path, "keymap_switching")) == 1 
            
    def set_keymap_index(self, index):
        logger.info("Setting keymap index on %s to '%d'" % (self.device.uid, index))
        set_value(os.path.join(self.device_path, "keymap_index"), index)
        
    def get_keymap_index(self):
        return get_int_value(os.path.join(self.device_path, "keymap_index")) 
            
    def set_keymap(self, keymap):
        s = ""
        for k in keymap:
            s += "%04x %04x\n" % ( k, keymap[k])
        logger.info("Setting keymap on %s to '%s'" % (self.device.uid, str(keymap)))
        set_value(os.path.join(self.device_path, "keymap"), s)
        
    def get_keymap(self):
        val = get_value(os.path.join(self.device_path, "keymap"))
        while val.endswith(chr(0)):
            val = val[:-1]
        keymap = {}
        for line in val.splitlines():
            args = line.split(" ")
            keycode = int(args[0], 16)
            scancode = int(args[1], 16)
            keymap[keycode] = scancode
        return keymap
        
class LED():
    """
    Represents a single LED, the keyboard it is linked to,
    and the /sys filename for the LED
    """
    def __init__(self, light_key, keyboard_device, filename):
        self.light_key = light_key
        self.keyboard_device = keyboard_device
        self.filename = filename
        
    def set_led_value(self, val):
        """
        Set the current brightness of the LED
        
        Keyword arguments:
        val            --
        """
        if val < 0 or val > self.get_max():
            raise Exception("LED value out of range")
        set_value(os.path.join(self.filename, "brightness"), val)
        
    def get_value(self):
        return get_int_value(os.path.join(self.filename, "brightness"))
        
    def get_max(self):
        return get_int_value(os.path.join(self.filename, "max_brightness"))
            
DEVICES_PATH="/sys/bus/hid/devices"
            
class G15SystemServiceController():
    
    def __init__(self, bus, no_trap=False):
        self._page_sequence_number = 1
        self._bus = bus
        self.devices = {}
        logger.debug("Exposing service")
        
        if not no_trap:
            signal.signal(signal.SIGINT, self.sigint_handler)
            signal.signal(signal.SIGTERM, self.sigterm_handler)
            
        self._loop = gobject.MainLoop()
        gobject.idle_add(self._start_service)
        
    def stop(self):
        self._loop.quit()
        
    def start_loop(self):
        logger.info("Starting GLib loop")
        self._loop.run()
        logger.debug("Exited GLib loop")
        
    def sigint_handler(self, signum, frame):
        logger.info("Got SIGINT signal, shutting down")
        self.shutdown()
    
    def sigterm_handler(self, signum, frame):
        logger.info("Got SIGTERM signal, shutting down")
        self.shutdown()
        
    def shutdown(self):
        logger.info("Shutting down")
        self._loop.quit()
        
    """
    Private
    """
    def _start_service(self):
        self._scan_devices()
        SystemService(self._bus, self)
        
    def _scan_devices(self):
        self.devices = {}
        indices = {}
        if os.path.exists(DEVICES_PATH):
            for device in os.listdir(DEVICES_PATH):
                # Only want devices with leds
                device_path = os.path.join(DEVICES_PATH, device)
                leds_path = os.path.join(device_path, "leds")
                if os.path.exists(leds_path):
                    # Extract the USB ID
                    a = device.split(":")
                    usb_id = ( int("0x%s" % a[1], 16), int("0x%s" % a[2].split(".")[0], 16) )
                    logger.info("Testing if device %04x:%04x is supported by Gnome15" % (usb_id[0], usb_id[1]))
                    
                    # Look for a matching Gnome15 device
                    for device in g15devices.find_all_devices():
                        if device.controls_usb_id == usb_id:
                            # Found a device we want
                            logger.info("Found device %s " % str(device))
                            
                            # Work out UID
                            # TODO this is not quite right - if there is more than one device of same type, indexs might not match                            
                            index = 0 if not device.model_id in indices else indices[device.model_id] 
                            keyboard_device = KeyboardDevice(device, device_path, index)
                            self.devices[device.uid] = keyboard_device
                            indices[device.model_id] = index + 1
                 
        else:
            logger.info("No devices found at %s" % DEVICES_PATH)
            
