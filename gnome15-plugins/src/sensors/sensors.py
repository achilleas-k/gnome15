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
 
import gnome15.g15driver as g15driver
import gnome15.g15plugin as g15plugin
import gnome15.g15theme as g15theme
import gnome15.g15util as g15util
import os.path
import commands
import dbus
import libsensors

from ctypes import *

# Logging
import logging
logger = logging.getLogger()

id = "sensors"
name = "Sensors"
description = "Display information from various sensors, such as temperature " + \
                "and fan speeds."        
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = "Copyright (C)2010 Brett Smith"
site = "http://www.gnome15.org"
has_preferences = False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : "Previous sensor", 
         g15driver.NEXT_SELECTION : "Next sensor",
         g15driver.NEXT_PAGE : "Next page",
         g15driver.PREVIOUS_PAGE : "Previous page"
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
            self.atasmart_dll = cdll.LoadLibrary("libatasmart.so.4")
            
            
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
                    if int(udisk_properties.Get(UDISKS_DEVICE_NAME, "DriveAtaSmartTimeCollected")) > 0:
                        # Only get the temperature if SMART data is collected to avoide spinning up disk
                        smart_blob = udisk_properties.Get(UDISKS_DEVICE_NAME, "DriveAtaSmartBlob")
                        
                        
                        
#                        smart_blob = g_value_get_boxed(&smart_blob_val);
#
#                  sk_disk_open(NULL, &sk_disk);
#                  sk_disk_set_blob (sk_disk, smart_blob->data, smart_blob->len);
#                  /* Note: A gdouble cannot be passed in through a cast as it is likely that the
#                   * temperature is placed in it purely through memory functions, hence a guint64
#                   * is passed and the number is then placed in a gdouble manually 
#                   */
#                  sk_disk_smart_get_temperature (sk_disk, &temperature_placer);
#                  temperature = temperature_placer;
#
#                  /* Temperature is in mK, so convert it to K first */
#                  temperature /= 1000;
#                  info->temp = temperature - 273.15;
#                  info->changed = FALSE;
#
#                  g_free (sk_disk);
#                  g_array_free(smart_blob, TRUE);
                    self.sensors[sensor.name] = sensor
                
                

class LibsensorsSource():
    def __init__(self):
        self.name = "Libsensors"
        self.started = False
    
    def get_sensors(self):
        sensors = []
        for chip_name in libsensors.get_detected_chips(None):
            s = str(chip_name)
            logger.debug("Found chip %s, adapter %s" % ( str(chip_name), libsensors.get_adapter_name(chip_name.bus)))
            for feature in libsensors.get_features(chip_name):
                label = libsensors.get_label(chip_name, feature)
                value = libsensors.get_value(chip_name, feature.number)
                logger.debug("   %s = %s" % (label, value) )
                sensor = Sensor(label, float(value))
                sensors.append(sensor)
                for subfeature in libsensors.get_all_subfeatures(chip_name, feature,):
                    value = libsensors.get_value(chip_name, subfeature.number)
                    if subfeature.name.endswith("_crit"):
                        sensor.critical = float(value)
                    elif subfeature.name.endswith("_input"):
                        sensor.value = float(value)
                    logger.debug("       %s = %s" % (subfeature.name, value) )
        return sensors
    
    def is_valid(self):     
        if not self.started:   
            libsensors.init()
            self.started = True
        return self.started
    
    def stop(self):
        if self.started:
            libsensors.cleanup()

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
            for element in root.xpath('//svg:rect[@class=\'needle\']',namespaces=self.page.theme.nsmap):
                g15util.rotate_element(element, self.menu.selected.sensor.value)
        
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