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
 
import gobject
import g15globals
import signal
import dbus.service
import os.path
import g15devices
import g15driver

# Logging
import logging
logger = logging.getLogger("systemservice")
    
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
        self._controller.leds[device][light].set_value(value)
        
    @dbus.service.method(IF_NAME, in_signature='ss', out_signature='n')
    def GetLight(self, device, light):        
        return self._controller.leds[device][light].get_value()
        
    @dbus.service.method(IF_NAME, out_signature='as')
    def GetDevices(self):        
        c = []
        for l in self._controller.leds:
            c.append(l)
        return c
        
    @dbus.service.method(IF_NAME, in_signature='s', out_signature='as')
    def GetLights(self, device):        
        return self._controller.leds[device].keys()
        
    @dbus.service.method(IF_NAME, in_signature='ss', out_signature='n')
    def GetMaxLight(self, device, light):
        return self._controller.leds[device][light].get_max()
    
        
class LED():
    """
    Represents a single LED, the keyboard it is linked to,
    and the /sys filename for the LED
    """
    def __init__(self, light_key, keyboard_device, filename):
        self.light_key = light_key
        self.keyboard_device = keyboard_device
        self.filename = filename
        
    def set_value(self, val):
        """
        Set the current brightness of the LED
        
        Keyword arguments:
        val            --
        """
        if val < 0 or val > self.get_max():
            raise Exception("LED value out of range")
        file = open(os.path.join(self.filename, "brightness"), "w")
        try :
            file.write("%d\n" % val)
        finally :
            file.close()            
        
    def get_value(self):
        """
        Get the current brightness of the LED    
        """
        file = open(os.path.join(self.filename, "brightness"), "r")
        try :
            return int(file.readline())
        finally :
            file.close()
        
    def get_max(self):
        """
        Get the maximum brightness of the LED    
        """
        file = open(os.path.join(self.filename, "max_brightness"), "r")
        try :
            return int(file.readline())
        finally :
            file.close()
            
class G15SystemServiceController():
    
    def __init__(self, bus, led_path = "/sys/class/leds", no_trap=False):
        self._page_sequence_number = 1
        self._bus = bus
        self._led_path = led_path
        self._leds = {}
        logger.debug("Exposing service")
        
        if not no_trap:
            signal.signal(signal.SIGINT, self.sigint_handler)
            signal.signal(signal.SIGTERM, self.sigterm_handler)
            
        self._loop = gobject.MainLoop()
        gobject.idle_add(self._start_service)
        
    def stop(self):
        self._loop.stop()
        
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
        self._scan_leds()
        SystemService(self._bus, self)
        
    def _scan_leds(self):
        self.leds = {}
        if os.path.exists(self._led_path):
            for device in g15devices.find_all_devices():
                if device.model_id in driver_names:
                    driver_name = driver_names[device.model_id]
                    led_prefix = "%s_" % driver_name
                    for dir in os.listdir(self._led_path):
                        if dir.startswith(led_prefix):
                            keyboard_device, color, control = dir.split(":")
                            keyboard_device, index = keyboard_device.split("_")
                            leds = self.leds[device.uid] if device.uid in self.leds else {}
                            light_key = "%s:%s" % ( color, control )
                            leds[light_key] = LED(light_key, device, os.path.join(self._led_path, dir))
                            self.leds[device.uid] = leds
                 
        else:
            logger.info("No LED files found at %s" % self._led_path)
            
        logger.info(">>%s" % str(self.leds))