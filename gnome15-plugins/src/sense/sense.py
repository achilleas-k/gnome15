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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("sensors", modfile = __file__).ugettext

import gnome15.g15driver as g15driver
import gnome15.g15plugin as g15plugin
import gnome15.g15theme as g15theme
import gnome15.g15util as g15util
import os.path
import commands
import dbus
import sensors

from ctypes import byref, c_int

import subprocess

# Logging
import logging
logger = logging.getLogger()

id = "sense"
name = _("Temperature Sensors")
description = _("Display information from various temperature sensors.")        
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = _("Copyright (C)2010 Brett Smith")
site = "http://www.gnome15.org"
has_preferences = False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous sensor"), 
         g15driver.NEXT_SELECTION : _("Next sensor"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page")
         }
 
UDISKS_DEVICE_NAME = "org.freedesktop.UDisks.Device"
UDISKS_BUS_NAME= "org.freedesktop.UDisks"

''' 
This plugin displays sensor information
'''

def create(gconf_key, gconf_client, screen):
    return G15Sensors(gconf_key, gconf_client, screen)

class Sensor():
    
    def __init__(self, name, value, critical = None):
        self.name = name
        self.value = value
        self.critical = critical
        
class UDisksSource():
    
    def __init__(self):
        self.name = "UDisks"
        self.udisks = None
        self.system_bus = None
        self.sensors = {}
        
    def get_sensors(self):
        self._check_dbus_connection()
        return self.sensors.values()
    
    def is_valid(self):
        self._check_dbus_connection()
        return self.udisks is not None
    
    def stop(self):
        pass
    
    def _check_dbus_connection(self):
        if self.udisks == None:
            self.system_bus = dbus.SystemBus()
            udisks_object = self.system_bus.get_object(UDISKS_BUS_NAME, '/org/freedesktop/UDisks')     
            self.udisks = dbus.Interface(udisks_object, UDISKS_BUS_NAME)
            self.sensors = {}
            for device in self.udisks.EnumerateDevices():
                udisk_object = self.system_bus.get_object(UDISKS_BUS_NAME, device)
                udisk_properties = dbus.Interface(udisk_object, 'org.freedesktop.DBus.Properties')
                
                if udisk_properties.Get(UDISKS_DEVICE_NAME, "DriveAtaSmartIsAvailable"):
                    sensor_name = udisk_properties.Get(UDISKS_DEVICE_NAME, "DriveModel")
                    if sensor_name in self.sensors:
                        # TODO get something else unique?
                        n = udisk_properties.Get(UDISKS_DEVICE_NAME, "DeviceFile")
                        if n: 
                            sensor_name += " (%s)" % n 
                        else:
                            n = udisk_properties.Get(UDISKS_DEVICE_NAME, "DriveSerial")
                            if n: 
                                sensor_name += " (%s)" % n
                    sensor = Sensor(sensor_name, 0.0)
                    device_file = str(udisk_properties.Get(UDISKS_DEVICE_NAME, "DeviceFile"))
                    if int(udisk_properties.Get(UDISKS_DEVICE_NAME, "DriveAtaSmartTimeCollected")) > 0:
                        # Only get the temperature if SMART data is collected to avoide spinning up disk
                        smart_blob = udisk_properties.Get(UDISKS_DEVICE_NAME, "DriveAtaSmartBlob")
                        smart_blob_str = ""
                        for c in smart_blob:
                            smart_blob_str += str(c)
                            
                        process = subprocess.Popen(['skdump', '--temperature', '--load=-'], shell = False, stdout = subprocess.PIPE, stdin = subprocess.PIPE)
                        process.stdin.write(smart_blob_str)
                        process.stdin.flush()
                        process.stdin.close()                            
                        result  = process.stdout.readline()
                        process.wait()
                        kelvin = int(result) 
                        kelvin /= 1000;
                        temp_c = kelvin - 273.15
                        sensor.value = temp_c
                        
                    self.sensors[sensor.name] = sensor
                
                

class LibsensorsSource():
    def __init__(self):
        self.name = "Libsensors"
        self.started = False
    
    def get_sensors(self):
        sensor_objects = []
        
        for chip in sensors.iter_detected_chips():
            logger.debug("Found chip %s, adapter %s" % ( chip, chip.adapter_name))
            for feature in chip:
                logger.debug("'  %s: %.2f" % (feature.label, feature.get_value()))
                sensor = Sensor(feature.label, float(feature.get_value()))
                sensor_objects.append(sensor)
                
                for subfeature in feature:
                    name = subfeature.name                    
                    if name.endswith("_crit"):
                        sensor.critical = float(subfeature.get_value())
                    elif name.endswith("_input"):
                        sensor.value = float(subfeature.get_value())
        return sensor_objects
    
    def is_valid(self):     
        if not self.started:   
            sensors.init()
            self.started = True
        return self.started
    
    def stop(self):
        if self.started:
            sensors.cleanup()

class NvidiaSource():
    def __init__(self):
        self.name = "NVidia"
        
    def get_sensors(self):
        return [Sensor("GPUCoreTemp", int(commands.getoutput("nvidia-settings -q GPUCoreTemp -t")))]
    
    def is_valid(self):
        if not os.path.exists("/dev/nvidiactl"):
            return False
        if not os.access("/dev/nvidiactl", os.R_OK):
            logger.warning("/dev/nvidiactl exists, but it is not readable by the current user, skipping sensor source.")
            return False
        return True
    
    def stop(self):
        pass

class SensorMenuItem(g15theme.MenuItem):
    
    def __init__(self,  item_id, sensor):
        g15theme.MenuItem.__init__(self, item_id)
        self.sensor = sensor
        
    def get_theme_properties(self):        
        properties = g15theme.MenuItem.get_theme_properties(self)
        properties["item_name"] = self.sensor.name
        properties["item_alt"] = "%.2f" % self.sensor.value
        properties["item_alt2"] = "%.2f" % self.sensor.critical if self.sensor.critical is not None else ""
        max = self.sensor.critical if self.sensor.critical is not None else 100.0
        properties["temp_percent"] = ( self.sensor.value / max ) * 100.0
        return properties
     
    
class G15Sensors(g15plugin.G15RefreshingPlugin):
    
    def __init__(self, gconf_key, gconf_client, screen):
        g15plugin.G15RefreshingPlugin.__init__(self, gconf_client, gconf_key, screen, [ "system" ], id, name, 5.0)
        
    def activate(self):
        self.sensor_sources = []
        self.sensor_dict = {}
        for c in [ LibsensorsSource(), NvidiaSource(), UDisksSource() ]:
            logger.info("Testing if '%s' is a valid sensor source" % c.name)
            if c.is_valid():
                logger.info("Adding '%s' as a sensor source" % c.name)
                self.sensor_sources.append(c)
            else:
                c.stop()        
        g15plugin.G15RefreshingPlugin.activate(self)
        
    def populate_page(self):
        g15plugin.G15RefreshingPlugin.populate_page(self)
        self.menu = g15theme.Menu("menu")
        def menu_selected():
            self.page.mark_dirty()
            self.page.redraw()
        self.menu.on_selected = menu_selected
        self.page.add_child(self.menu)
        self.page.theme.svg_processor = self._process_svg        
        self.page.add_child(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
        i = 0
        for c in self.sensor_sources:
            for s in c.get_sensors():
                menu_item = SensorMenuItem("menuitem-%d" % i, s)
                self.sensor_dict[s.name] = menu_item
                self.menu.add_child(menu_item)
                i += 1
    
    def deactivate(self):
        for c in self.sensor_sources:
            c.stop()
        g15plugin.G15RefreshingPlugin.deactivate(self)
        
    def refresh(self):
        self._get_stats()
        self._build_properties()
    
    ''' Private
    '''
        
    def _process_svg(self, document, properties, attributes):
        root = document.getroot()
        if self.menu.selected is not None:
            needle = self.page.theme.get_element("needle")
            needle_center = self.page.theme.get_element("needle_center")
            val = float(self.menu.selected.sensor.value)
            
            """
            The title contains the bounds for the gauge, in the format
            lower_val,upper_val,middle_val,lower_deg,upper_deg
            """
            gauge_data = needle_center.get("title").split(",")
            lower_val = float(gauge_data[0])
            upper_val = float(gauge_data[1])
            middle_val = float(gauge_data[2])
            lower_deg = float(gauge_data[3])
            upper_deg = float(gauge_data[4])
            
            # Clamp the value
            val = min(upper_val, max(lower_val, val))
            
            # Ratio of gauge bounds to rotate by 
            ratio = val / ( upper_val - lower_val )
            
            """
            Work out total number of degrees in the bounds
            """
            total_deg = upper_deg + ( 360 - lower_deg )
            
            
            # Work out total number of degress to rotate
            rot_degrees = total_deg * ratio
            
            # 
            degr = lower_deg
            degr += rot_degrees
            
            
            """
            This is a bit weak. It doesn't take transformations into account,
            so care is needed in the SVG.            
            """
            center_bounds = g15util.get_bounds(needle_center)
            needle.set("transform", "rotate(%f,%f,%f)" % (degr, center_bounds[0], center_bounds[1]) )
        
    def _get_stats(self):
        for c in self.sensor_sources:
            for s in c.get_sensors(): 
                self.sensor_dict[s.name].sensor = s
                if s.critical is not None:
                    logger.debug("Sensor %s on %s is %f (critical %f)" % ( s.name, c.name, s.value, s.critical ))
                else:
                    logger.debug("Sensor %s on %s is %f" % ( s.name, c.name, s.value ))
                    
    def _build_properties(self): 
        self.page.mark_dirty()
        properties = {}
        if self.menu.selected is not None:
            properties["sensor"] = self.menu.selected.sensor.name        
            properties["temp_c"] = "%.2f C" % float(self.menu.selected.sensor.value)
        self.page.theme_properties = properties