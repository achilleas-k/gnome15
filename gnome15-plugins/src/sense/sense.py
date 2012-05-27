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
import dbus
import sensors
import gtk
import gconf
import gobject

import subprocess

# Logging
import logging
logger = logging.getLogger()

id = "sense"
name = _("Sensors")
description = _("Display information from various sensors. The plugin \
supports Temperatures, Fans and Voltages from various sources. \
\n\n\
Sources include libsensors, nvidiactl and UDisks.\
\n\n\
NOTE: UDisk may cause a delay in starting up Gnome15. This bug is\
being investigated.")        
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = _("Copyright (C)2010 Brett Smith")
site = "http://www.gnome15.org"
has_preferences = True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous sensor"), 
         g15driver.NEXT_SELECTION : _("Next sensor"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page")
         }
 
UDISKS_DEVICE_NAME = "org.freedesktop.UDisks.Device"
UDISKS_BUS_NAME= "org.freedesktop.UDisks"

'''
Sensor types
'''
VOLTAGE = 0
TEMPERATURE = 2
FAN = 1
UNKNOWN_1 = 3
INTRUSION = 17

TYPE_NAMES = { VOLTAGE: "Voltage", FAN: "Fan", TEMPERATURE : "Temp" }
VARIANT_NAMES = { VOLTAGE : "volt", TEMPERATURE : None, FAN : "fan", UNKNOWN_1 : "volt", INTRUSION: "intrusion" } 

''' 
This plugin displays sensor information
'''

def create(gconf_key, gconf_client, screen):
    return G15Sensors(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    G15SensorsPreferences(parent, driver, gconf_client, gconf_key)
    
def get_sensor_sources():
    sensor_sources = []
    for c in [ LibsensorsSource(), NvidiaSource(), UDisksSource() ]:
        logger.info("Testing if '%s' is a valid sensor source" % c.name)
        if c.is_valid():
            logger.info("Adding '%s' as a sensor source" % c.name)
            sensor_sources.append(c)
        else:
            c.stop()
    return sensor_sources

class G15SensorsPreferences():
    
    def __init__(self, parent, driver, gconf_client, gconf_key):
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "sense.glade"))
        
        # Feeds
        self.sensor_model = widget_tree.get_object("SensorModel")
        self.reload_model()
        self.sensor_list = widget_tree.get_object("SensorList")
        self.enabled_renderer = widget_tree.get_object("EnabledRenderer")
        self.label_renderer = widget_tree.get_object("LabelRenderer")
        
        # Lines
        self.interval_adjustment = widget_tree.get_object("IntervalAdjustment")
        self.interval_adjustment.set_value(g15util.get_float_or_default(self._gconf_client, "%s/interval" % self._gconf_key, 10))
        
        # Connect to events
        self.interval_adjustment.connect("value-changed", self.interval_changed)
        self.label_renderer.connect("edited", self.label_edited)
        self.enabled_renderer.connect("toggled", self.sensor_toggled)
        
        # Show dialog
        self.dialog = widget_tree.get_object("SenseDialog")
        self.dialog.set_transient_for(parent)
        
        self.dialog.run()
        self.dialog.hide()
        
    def interval_changed(self, widget):
        self._gconf_client.set_float(self._gconf_key + "/interval", int(widget.get_value()))
        
    def label_edited(self, widget, row_index, value):
        row_index = int(row_index)
        if value != "":
            if self.sensor_model[row_index][2] != value:
                self.sensor_model.set_value(self.sensor_model.get_iter(row_index), 2, value)
                sensor_name = self.sensor_model[row_index][0]
                self._gconf_client.set_string("%s/sensors/%s/label" % (self._gconf_key, gconf.escape_key(sensor_name, len(sensor_name))), value)
            
    def sensor_toggled(self, widget, row_index):
        row_index = int(row_index)
        now_active = not widget.get_active()
        self.sensor_model.set_value(self.sensor_model.get_iter(row_index), 1, now_active)
        sensor_name = self.sensor_model[row_index][0]
        self._gconf_client.set_bool("%s/sensors/%s/enabled" % (self._gconf_key, gconf.escape_key(sensor_name, len(sensor_name))), now_active)
        
    def reload_model(self):
        self.sensor_model.clear() 
        ss = get_sensor_sources()
        for source in ss:
            sa  = source.get_sensors()
            for sensor in sa:
                sense_key = "%s/sensors/%s" % (self._gconf_key, gconf.escape_key(sensor.name, len(sensor.name)))
                if sensor.sense_type in TYPE_NAMES:
                    self.sensor_model.append([ sensor.name, g15util.get_bool_or_default(self._gconf_client, "%s/enabled" % (sense_key), True), 
                                              g15util.get_string_or_default(self._gconf_client, "%s/label" % (sense_key), sensor.name), TYPE_NAMES[sensor.sense_type] ])
            source.stop()
            

class Sensor():
    
    def __init__(self, sense_type, name, value, critical = None):
        self.sense_type = sense_type
        self.name = name
        self.value = value
        self.critical = critical
        
    def get_default_crit(self):
        # Meaningless really, but more sensible than a single value
        
        if self.sense_type == FAN:
            return 7000
        elif self.sense_type == VOLTAGE:
            return 12
        else:
            return 100
        
        
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
                    sensor = Sensor(TEMPERATURE, sensor_name, 0.0)
                    device_file = str(udisk_properties.Get(UDISKS_DEVICE_NAME, "DeviceFile"))
                    if int(udisk_properties.Get(UDISKS_DEVICE_NAME, "DriveAtaSmartTimeCollected")) > 0:
                        # Only get the temperature if SMART data is collected to avoide spinning up disk
                        smart_blob = udisk_properties.Get(UDISKS_DEVICE_NAME, "DriveAtaSmartBlob", byte_arrays=True)
                        smart_blob_str = str(smart_blob)
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
        sensor_names = []
        for chip in sensors.iter_detected_chips():
            logger.debug("Found chip %s, adapter %s" % ( chip, chip.adapter_name))
            for feature in chip:
                sensor_name = feature.label
                
                # Prevent name conflicts across chips
                if not sensor_name in sensor_names:
                    sensor_names.append(sensor_name)
                else:
                    o = sensor_name
                    idx = 1
                    while sensor_name in sensor_names:
                        idx += 1
                        sensor_name = "%s-%d" % (o, idx) 
                    sensor_names.append(sensor_name)
                
                logger.debug("'  %s: %.2f" % (sensor_name, feature.get_value()))
                sensor = Sensor(feature.type, sensor_name, float(feature.get_value()))
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
        return [Sensor(TEMPERATURE, "GPUCoreTemp", int(self.getstatusoutput("nvidia-settings -q GPUCoreTemp -t")[1]))]
    
    def getstatusoutput(self, cmd):
        pipe = os.popen('{ ' + cmd + '; } 2>/dev/null', 'r')
        text = pipe.read()
        sts = pipe.close()
        if sts is None: sts = 0
        if text[-1:] == '\n': text = text[:-1]
        return sts, text

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
    
    def __init__(self,  item_id, sensor, sensor_label):
        g15theme.MenuItem.__init__(self, item_id)
        self.sensor = sensor
        self.sensor_label = sensor_label
        
    def get_theme_properties(self):        
        properties = g15theme.MenuItem.get_theme_properties(self)
        properties["item_name"] = self.sensor_label
        properties["item_alt"] = self._format_value(self.sensor.value)
        properties["item_alt2"] = self._format_value(self.sensor.critical) if self.sensor.critical is not None else ""
        max_val = self.sensor.critical if self.sensor.critical is not None else self.sensor.get_default_crit()
        properties["temp_percent"] = ( self.sensor.value / max_val ) * 100.0
        return properties
    
    def _format_value(self, val):
        return "%.2f" % val if val < 1000 else "%4d" % int(val)
     
class G15Sensors(g15plugin.G15RefreshingPlugin):
    
    def __init__(self, gconf_key, gconf_client, screen):
        g15plugin.G15RefreshingPlugin.__init__(self, gconf_client, gconf_key, screen, [ "system" ], id, name, 5.0)
        
    def activate(self):
        gobject.idle_add(self._do_activate)
        
    def _do_activate(self):
        self.sensor_sources = get_sensor_sources()
        self.sensor_dict = {}        
        g15plugin.G15RefreshingPlugin.activate(self)        
        self._sensors_changed_handle = self.gconf_client.notify_add(self.gconf_key + "/sensors", self._sensors_changed)
    
    def populate_page(self):
        g15plugin.G15RefreshingPlugin.populate_page(self)
        
        enabled_sensors = []
        for c in self.sensor_sources:
            for s in c.get_sensors():                
                sense_key = "%s/sensors/%s" % (self.gconf_key, gconf.escape_key(s.name, len(s.name)))
                if g15util.get_bool_or_default(self.gconf_client, "%s/enabled" % (sense_key), True):
                    enabled_sensors.append(s)
                    
        self.menu = g15theme.Menu("menu")
              
        # If there are no sensors enabled, display the 'none' variant
        # which shows a message
        if len(enabled_sensors) == 0: 
            self.page.theme.set_variant("none")
        else:      
            self.page.theme.set_variant(None)
            def menu_selected():
                self.page.theme.set_variant(VARIANT_NAMES[self.menu.selected.sensor.sense_type])
                self.refresh()
                self.page.redraw()
                
            self.menu.on_selected = menu_selected
            self.page.add_child(self.menu)
            self.page.theme.svg_processor = self._process_svg        
            self.page.add_child(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
            i = 0
            for s in enabled_sensors:                
                if s.sense_type in TYPE_NAMES:
                    sense_key = "%s/sensors/%s" % (self.gconf_key, gconf.escape_key(s.name, len(s.name)))
                    sense_label = g15util.get_string_or_default(self.gconf_client, "%s/label" % (sense_key), s.name) 
                    menu_item = SensorMenuItem("menuitem-%d" % i, s, sense_label)
                    self.sensor_dict[s.name] = menu_item
                    self.menu.add_child(menu_item)
                    
                    # If this is the first child, change the theme variant
                    if self.menu.get_child_count() == 1: 
                        self.page.theme.set_variant(VARIANT_NAMES[menu_item.sensor.sense_type])
                    
                    i += 1
            
    
    def deactivate(self):
        for c in self.sensor_sources:
            c.stop()
        g15plugin.G15RefreshingPlugin.deactivate(self)
        self.gconf_client.notify_remove(self._sensors_changed_handle)
        
    def refresh(self):
        self._get_stats()
        self._build_properties()
    
    def get_next_tick(self):
        return g15util.get_float_or_default(self.gconf_client, "%s/interval" % self.gconf_key, 5.0)
    
    ''' Private
    '''
    
    def _sensors_changed(self, client, connection_id, entry, args):        
        self.page.remove_all_children()
        self.populate_page()
        self.refresh()
        
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
                if s.name in self.sensor_dict:
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
            if self.menu.selected.sensor.sense_type == FAN:        
                properties["rpm"] = "%4d" % float(self.menu.selected.sensor.value)
            elif self.menu.selected.sensor.sense_type == VOLTAGE:        
                properties["voltage"] = "%.2f" % float(self.menu.selected.sensor.value)
            else:        
                properties["temp_c"] = "%.2f C" % float(self.menu.selected.sensor.value)
        self.page.theme_properties = properties