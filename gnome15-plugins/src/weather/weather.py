# coding=UTF-8
#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) 2010-2012 Brett Smith <tanktarta@blueyonder.co.uk>            |
#        | Copyright (c) Nuno Araujo <nuno.araujo@russo79.com>                         |
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
_ = g15locale.get_translation("weather", modfile = __file__).ugettext

import gnome15.g15screen as g15screen
import gnome15.g15util as g15util
import gnome15.g15scheduler as g15scheduler
import gnome15.g15ui_gconf as g15ui_gconf
import gnome15.g15python_helpers as g15python_helpers
import gnome15.g15gconf as g15gconf
import gnome15.g15cairo as g15cairo
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15text as g15text
import gnome15.g15plugin as g15plugin
import gtk
import os
import pango
import logging
import time
import traceback
import sys
logger = logging.getLogger("weather")


# Plugin details - All of these must be provided
id="weather"
name=_("Weather")
description=_("Displays the current weather at a location. It can currently use NOAA and Yahoo as sources \
of weather information.")  
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=True
default_enabled=True
needs_network=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

DEFAULT_LOCATION="london,england"

''' 
This simple plugin displays the current weather at a location
'''

CELSIUS=0
FARANHEIT=1
KELVIN=2

DEFAULT_UPDATE_INTERVAL = 60 # minutes

def create(gconf_key, gconf_client, screen):
    return G15Weather(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    G15WeatherPreferences(parent, gconf_client, gconf_key)

def get_location(gconf_client, gconf_key):
    loc = gconf_client.get_string(gconf_key + "/location")
    if loc == None:
        return DEFAULT_LOCATION
    return loc

def get_backend(account_type):
    """
    Get the backend plugin module, given the account_type
    
    Keyword arguments:
    account_type          -- account type
    """
    import gnome15.g15pluginmanager as g15pluginmanager
    return g15pluginmanager.get_module_for_id("weather-%s" % account_type)

def get_available_backends():
    """
    Get the "account type" names that are available by listing all of the
    backend plugins that are installed 
    """
    l = []
    import gnome15.g15pluginmanager as g15pluginmanager
    for p in g15pluginmanager.imported_plugins:
        if p.id.startswith("weather-"):
            l.append(p.id[8:])
    return l

def c_to_f(c):
    return c * 9/5.0 + 32

def c_to_k(c):
    return c + 273.15

def mph_to_kph(mph):
    return mph * 1.609344

def kph_to_mph(mph):
    return mph * 0.621371192
 
class G15WeatherPreferences():
    '''
    Configuration UI
    '''    
    
    def __init__(self, parent, gconf_client, gconf_key):
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._visible_options = None
        
        self._widget_tree = gtk.Builder()
        self._widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "weather.glade"))
        
        dialog = self._widget_tree.get_object("WeatherDialog")
        dialog.set_transient_for(parent)
        
        self._source = self._widget_tree.get_object("Source")
        self._source.connect("changed", self._load_options_for_source)
        
        self._sources_model = self._widget_tree.get_object("SourcesModel")
        for b in get_available_backends():
            l = [b, get_backend(b).backend_name ]
            self._sources_model.append(l)
        g15ui_gconf.configure_combo_from_gconf(gconf_client, "%s/source" % gconf_key, "Source", self._sources_model[0][0] if len(self._sources_model) > 0 else None, self._widget_tree)
        self._load_options_for_source()
        
        update = self._widget_tree.get_object("UpdateAdjustment")
        update.set_value(g15gconf.get_int_or_default(gconf_client, gconf_key + "/update", DEFAULT_UPDATE_INTERVAL))
        update.connect("value-changed", self._value_changed, update, gconf_key + "/update")
        
        unit = self._widget_tree.get_object("UnitCombo")
        unit.set_active(gconf_client.get_int(gconf_key + "/units"))
        unit.connect("changed", self._unit_changed, unit, gconf_key + "/units")
        
        g15ui_gconf.configure_checkbox_from_gconf(gconf_client, "%s/use_theme_icons" % gconf_key, "UseThemeIcons", True, self._widget_tree)
        g15ui_gconf.configure_checkbox_from_gconf(gconf_client, "%s/twenty_four_hour_times" % gconf_key, "TwentyFourHourTimes", True, self._widget_tree)
        
        dialog.run()
        dialog.hide()
        
    def _create_options_for_source(self, source):
        backend = get_backend(source)
        if backend is None:
            logger.warning("No backend for weather source %s" % source)
            return None
        return backend.create_options(self._gconf_client, "%s/%s" % ( self._gconf_key, source ) )
            
    def _get_selected_source(self):
        active = self._source.get_active()
        return None if active == -1 else self._sources_model[active][0]
        
    def _load_options_for_source(self, widget = None):
        source = self._get_selected_source()
        if source:
            options = self._create_options_for_source(source)
        else:
            options = None
        if self._visible_options != None:
            self._visible_options.component.destroy()
        self._visible_options = options
        place_holder = self._widget_tree.get_object("PlaceHolder")
        for c in place_holder.get_children():
            place_holder.remove(c) 
        if self._visible_options is not None:                   
            self._visible_options.component.reparent(place_holder)
        else:                   
            l = gtk.Label("No options found for this source\n")
            l.xalign = 0.5
            l.show()
            place_holder.add(l)
        
    def _changed(self, widget, location, gconf_key):
        self._gconf_client.set_string(gconf_key, widget.get_text())
        
    def _unit_changed(self, widget, location, gconf_key):
        self._gconf_client.set_int(gconf_key, widget.get_active())
        
    def _value_changed(self, widget, location, gconf_key):
        self._gconf_client.set_int(gconf_key, int(widget.get_value()))
        

class WeatherOptions():
    
    def __init__(self):
        pass

class WeatherData():
    
    def __init__(self, location):
        self.location = location
    
class WeatherBackend():
    
    def __init__(self, gconf_client, gconf_key):
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def get_weather_data(self):
        raise Exception("Not implemented")

class G15Weather(g15plugin.G15RefreshingPlugin):
    
    def __init__(self, gconf_key, gconf_client, screen):
        g15plugin.G15RefreshingPlugin.__init__(self, gconf_client, gconf_key, screen, "weather-few-clouds", id, name)
        
    def activate(self):    
        self._page_properties = {}
        self._page_attributes = {}
        self._weather = None
        self._config_change_handle = None
        self._load_config()    
        self._text = g15text.new_text(self.screen)
        g15plugin.G15RefreshingPlugin.activate(self)
        self.watch(None, self._loc_changed)
        
    def deactivate(self):    
        self._page_properties = {}
        self._page_attributes = {}
        if self._config_change_handle is not None:
            self._config_change_handle.cancel()
        g15plugin.G15RefreshingPlugin.deactivate(self)
    
    def destroy(self):
        pass
    
    def refresh(self):        
        try :            
            backend_type = g15gconf.get_string_or_default(self.gconf_client, "%s/source" % self.gconf_key, None)
            if backend_type:
                backend = get_backend(backend_type).create_backend(self.gconf_client, "%s/%s" % (self.gconf_key, backend_type) )
                self._weather = backend.get_weather_data()
            else:
                self._weather = None
            self._page_properties, self._page_attributes = self._build_properties()
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            self._weather = None
            self._page_properties = {}
            self._page_attributes = {}
            self._page_properties['message'] = _("Error parsing weather data!")
    
    def get_theme_properties(self):
        return self._page_properties
    
    def get_theme_attributes(self):
        return self._page_properties
        
    """
    Private
    """
    
    def _load_config(self):        
        val = g15gconf.get_int_or_default(self.gconf_client, self.gconf_key + "/update", DEFAULT_UPDATE_INTERVAL)
        self.refresh_interval = val * 60.0
        
    def _loc_changed(self, client, connection_id, entry, args):
        if not entry.get_key().endswith("/theme") and not entry.get_key().endswith("/enabled"):
            if self._config_change_handle is not None:
                self._config_change_handle.cancel()
            self._config_change_handle = g15scheduler.schedule("ApplyConfig", 3.0, self._config_changed)
    
    def _config_changed(self):
        self.reload_theme()
        self._load_config()
        self._refresh()
        self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 6.0)
    
    def _get_icons(self, current):
        c_icon = current['icon'] if 'icon' in current else None
        f_icon = current['fallback_icon'] if 'fallback_icon' in current else None
        t_icon = self._translate_icon(c_icon, f_icon)
        return c_icon, f_icon, t_icon
        
    def _build_properties(self):
        properties = {}
        attributes = {}
        use_twenty_four_hour = g15gconf.get_bool_or_default(self.gconf_client, "%s/twenty_four_hour_times" % self.gconf_key, True)
        if self._weather is None:            
            properties["message"] = _("No weather source configuration")
        else: 
            current = self._weather['current_conditions']
            if len(current) == 0:
                properties["message"] = _("No weather data for location:-\n%s") % self._weather['location']
            else:
                properties["location"] = self._weather['location']
                dt = self._weather['datetime']
                if use_twenty_four_hour:
                    properties["time"] = g15locale.format_time_24hour(dt, self.gconf_client, False)
                else:          
                    properties["time"] = g15locale.format_time(dt, self.gconf_client, False)
                properties["date"] = g15locale.format_date(dt, self.gconf_client)
                properties["datetime"] = g15locale.format_date_time(dt, self.gconf_client, False)
                properties["message"] = ""
                c_icon, f_icon, t_icon = self._get_icons(current)
                if t_icon != None:
                    attributes["icon"] = g15cairo.load_surface_from_file(t_icon)
                    properties["icon"] = g15util.get_embedded_image_url(attributes["icon"]) 
                else:
                    logger.warning("No translated weather icon for %s" % c_icon)
                mono_thumb = self._get_mono_thumb_icon(c_icon)        
                if mono_thumb != None:
                    attributes["mono_thumb_icon"] = g15cairo.load_surface_from_file(os.path.join(os.path.join(os.path.dirname(__file__), "default"), mono_thumb))
                properties["condition"] = current['condition']
                
                temp_c = g15python_helpers.to_float_or_none(current['temp_c'])
                if temp_c is not None:
                    temp_f = c_to_f(temp_c)
                    temp_k = c_to_k(temp_c)
                low_c = g15python_helpers.to_float_or_none(current['low']) if 'low' in current else None
                if low_c is not None :
                    low_f = c_to_f(low_c)
                    low_k = c_to_k(low_c)
                high_c  = g15python_helpers.to_float_or_none(current['high']) if 'high' in current else None
                if high_c is not None :
                    high_f  = c_to_f(high_c)
                    high_k = c_to_k(high_c)
                
                properties["temp_c"] = "%3.1f°C" % temp_c if temp_c is not None else ""
                properties["hi_c"] = "%3.1f°C" % high_c if high_c is not None else ""
                properties["lo_c"] = "%3.1f°C" % low_c if low_c is not None else ""
                properties["temp_f"] = "%3.1f°F" % temp_f if temp_c is not None else ""
                properties["lo_f"] = "%3.1f°F" % low_f if low_c is not None else ""
                properties["high_f"] = "%3.1f°F" % high_f if high_c is not None else ""
                properties["temp_k"] = "%3.1f°K" % temp_k if temp_c is not None else ""
                properties["lo_k"] = "%3.1f°K" % low_k if low_c is not None else ""
                properties["high_k"] = "%3.1f°K" % high_k if high_c is not None else ""
                
                units = self.gconf_client.get_int(self.gconf_key + "/units")
                if units == CELSIUS:      
                    unit = "C"           
                    properties["temp"] = properties["temp_c"]
                    properties["temp_short"] = "%2.0f°" % temp_c if temp_c else ""
                    properties["hi"] = properties["hi_c"]
                    properties["hi_short"] = "%2.0f°" % high_c if high_c else ""                 
                    properties["lo"] = properties["lo_c"]
                    properties["lo_short"] = "%2.0f°" % low_c if low_c else ""
                elif units == FARANHEIT:      
                    unit = "F"                      
                    properties["lo"] = properties["lo_f"]              
                    properties["lo_short"] = "%2.0f°" % low_f if low_c is not None else ""
                    properties["hi"] = properties["high_f"]              
                    properties["hi_short"] = "%2.0f°" % high_f if high_c is not None else ""
                    properties["temp"] = properties["temp_f"]              
                    properties["temp_short"] = "%2.0f°" % temp_f if temp_c is not None else ""
                else:                         
                    unit = "K"          
                    properties["lo"] = properties["lo_k"]
                    properties["lo_short"] = "%2.0f°" % low_k if low_c is not None else ""      
                    properties["hi"] = properties["high_k"]
                    properties["hi_short"] = "%2.0f°" % high_k if high_c is not None else ""
                    properties["temp"] = properties["temp_k"]
                    properties["temp_short"] = "%2.0f°" % temp_k if temp_c is not None else ""
                    
                
                # Wind
                wind = g15python_helpers.append_if_exists(current, "wind_chill", "", "%sC")
                wind = g15python_helpers.append_if_exists(current, "wind_speed", wind, "%sKph")
                wind = g15python_helpers.append_if_exists(current, "wind_direction", wind, "%sdeg")
                properties["wind"] =  wind 
                
                # Visibility
                visibility = g15python_helpers.append_if_exists(current, "visibility", "", "%sM")
                properties["visibility"] =  visibility
                
                # Pressure
                pressure = g15python_helpers.append_if_exists(current, "pressure", "", "%smb")
                properties["pressure"] =  pressure
                
                # Humidity
                humidity = g15python_helpers.append_if_exists(current, "humidity", "", "%s%%")
                properties["humidity"] =  humidity
                
                # Sunrise                
                dt = current['sunrise'] if 'sunrise' in current else None
                if dt is None:
                    properties["sunrise_time"] = ""
                elif use_twenty_four_hour:
                    properties["sunrise_time"] = g15locale.format_time_24hour(dt, self.gconf_client, False)
                else:          
                    properties["sunrise_time"] = g15locale.format_time(dt, self.gconf_client, False)
                    
                # Sunset                
                dt = current['sunset'] if 'sunset' in current else None
                if dt is None:
                    properties["sunset_time"] = ""
                elif use_twenty_four_hour:
                    properties["sunset_time"] = g15locale.format_time_24hour(dt, self.gconf_client, False)
                else:          
                    properties["sunset_time"] = g15locale.format_time(dt, self.gconf_client, False)
                    
                # Blank all the forecasts by default
                for y in range(1, 10):
                    properties["condition" + str(y)] = ""
                    properties["hi" + str(y)] = ""
                    properties["lo" + str(y)] = ""
                    properties["day" + str(y)] = ""
                    properties["day_letter" + str(y)] = ""
                    properties["icon" + str(y)] = ""
                    
                # Forecasts
                y = 1
                if 'forecasts' in self._weather:
                    for forecast in self._weather['forecasts']:        
                        properties["condition" + str(y)] = forecast['condition']
                        
                        lo_c = g15python_helpers.to_float_or_none(forecast['low'])
                        if lo_c is not None:
                            lo_f = c_to_f(temp_c)
                            lo_k = c_to_k(temp_c)
                        hi_c = g15python_helpers.to_float_or_none(forecast['high'])
                        if hi_c is not None:
                            hi_f = c_to_f(hi_c)
                            hi_k = c_to_k(hi_c)
                        
                        if units == CELSIUS:                 
                            properties["hi" + str(y)] = "%3.0f°C" % hi_c
                            properties["lo" + str(y)] = "%3.0f°C" % lo_c
                        elif units == FARANHEIT:                         
                            properties["hi" + str(y)] = "%3.0f°F" % hi_f
                            properties["lo" + str(y)] = "%3.0f°F" % lo_f
                        else:                                  
                            properties["hi" + str(y)] = "%3.0f°K" % hi_k
                            properties["lo" + str(y)] = "%3.0f°K" % lo_k
        
                        properties["day" + str(y)] = forecast['day_of_week']
                        properties["day_letter" + str(y)] = forecast['day_of_week'][:1]
                        
                        c_icon, f_icon, t_icon = self._get_icons(forecast)
                        properties["icon" + str(y)] = g15util.get_embedded_image_url(g15cairo.load_surface_from_file(t_icon))
                        
                        y += 1
        
        return properties, attributes
        
    def _get_mono_thumb_icon(self, icon):
        if icon == None or icon == "":
            return None
        else :
            base_icon= self._get_base_icon(icon)
            
            if base_icon in [ "chanceofrain", "scatteredshowers" ]:
                return "weather-showers-scattered.gif"
            elif base_icon in [ "sunny", "haze" ]: 
                return "mono-sunny.gif"
            elif base_icon == "mostlysunny":
                return "mono-few-clouds.gif"
            elif base_icon == "partlycloudy":
                return "mono-clouds.gif"
            elif base_icon in [ "mostlycloudy", "cloudy" ]:
                return "mono-more-clouds.gif"
            elif base_icon == "rain":
                return "mono-rain.gif"
            elif base_icon in [ "mist", "fog" ]:
                return "mono-fog.gif"
            elif base_icon in [ "chanceofsnow", "snow", "sleet", "flurries" ]:
                return "mono-snow.gif"
            elif base_icon in [ "storm", "chanceofstorm" ]:
                return "mono-dark-clouds.gif"
            elif base_icon in [ "thunderstorm", "chanceoftstorm" ]:
                return "mono-thunder.gif"
        
    def _translate_icon(self, icon, fallback_icon):
        theme_icon = icon
        if theme_icon == None or theme_icon == "":
            return None
        else:
            if not g15gconf.get_bool_or_default(self.gconf_client, "%s/use_theme_icons" % self.gconf_key, True):
                return fallback_icon
            
        if theme_icon != None:
            icon_path = g15util.get_icon_path(theme_icon, warning = False, include_missing = False)
            if icon_path == None and theme_icon.endswith("-night"):
                icon_path = g15util.get_icon_path(theme_icon[:len(theme_icon) - 6], include_missing = False)
                
            if icon_path != None:
                return icon_path
             
        return g15util.get_icon_path(icon)
        
    def _get_base_icon(self, icon):
        # Strips off URL path, image extension, size and weather prefix if present
        base_icon = os.path.splitext(os.path.basename(icon))[0].rsplit("-")[0]
        if base_icon.startswith("weather_"):
            base_icon = base_icon[8:]
        base_icon = base_icon.replace('_','')
        return base_icon
    
    def _paint_panel(self, canvas, allocated_size, horizontal):
        return self._paint_thumbnail(canvas, allocated_size, horizontal)
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        total_taken = 0 
        self._text.set_canvas(canvas)
        if self.screen.driver.get_bpp() == 1:
            if "mono_thumb_icon" in self._page_attributes:
                size = g15util.paint_thumbnail_image(allocated_size, self._page_attributes["mono_thumb_icon"], canvas)
                canvas.translate(size + 2, 0)
                total_taken += size + 2
            if "temp_short" in self._page_properties:
                self._text.set_attributes(self._page_properties["temp_short"], \
                                          font_desc = g15globals.fixed_size_font_name, \
                                          font_absolute_size =  6 * pango.SCALE / 2)
                x, y, width, height = self._text.measure()
                total_taken += width
                self._text.draw(x, y)
        else:
            rgb = self.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 ))
            canvas.set_source_rgb(rgb[0],rgb[1],rgb[2])
            if "icon" in self._page_attributes:
                size = g15util.paint_thumbnail_image(allocated_size, self._page_attributes["icon"], canvas)
                total_taken += size
            if "temp" in self._page_properties:
                if horizontal:
                    self._text.set_attributes(self._page_properties["temp"], font_desc = "Sans", font_absolute_size =  allocated_size * pango.SCALE / 2)
                    x, y, width, height = self._text.measure()
                    self._text.draw(total_taken, (allocated_size / 2) - height / 2)
                    total_taken += width + 4
                else:  
                    self._text.set_attributes(self._page_properties["temp"], font_desc = "Sans", font_absolute_size =  allocated_size * pango.SCALE / 4)
                    x, y, width, height = self._text.measure()
                    self._text.draw((allocated_size / 2) - width / 2, total_taken)
                    total_taken += height + 4     
        return total_taken
            
