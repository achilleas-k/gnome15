#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2012 Brett Smith <tanktarta@blueyonder.co.uk>
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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("weather-noaa", modfile = __file__).ugettext

import gnome15.g15accounts as g15accounts
import gnome15.g15globals as g15globals
import gnome15.util.g15uigconf as g15uigconf
import gnome15.util.g15pythonlang as g15pythonlang
import gnome15.util.g15gconf as g15gconf
import weather
import gtk
import os
import pywapi
import email.utils
import time
import datetime

# Logging
import logging
logger = logging.getLogger("weather-noaa")
 
"""
Plugin definition
"""
backend_name="NOAA"
id="weather-noaa"
name=_("Weather (NOAA support)")
description=_("Adds the National Oceanic and Atmospheric Administration as a source of weather data.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=False
passive=True
needs_network=True
global_plugin=True
requires="weather"
unsupported_models=weather.unsupported_models

"""
Weather Back-end module functions
"""
def create_options(gconf_client, gconf_key):
    return NOAAWeatherOptions(gconf_client, gconf_key)

def create_backend(gconf_client, gconf_key):
    return NOAAWeatherBackend(gconf_client, gconf_key)

class NOAAWeatherOptions(weather.WeatherOptions):
    def __init__(self, gconf_client, gconf_key):
        weather.WeatherOptions.__init__(self)
                
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "weather-noaa.glade"))
        self.component = self.widget_tree.get_object("OptionPanel")
        
        g15uigconf.configure_text_from_gconf(gconf_client, "%s/station_id" % gconf_key, "StationID", "KPEO", self.widget_tree)

class NOAAWeatherData(weather.WeatherData):
    
    def __init__(self, station_id):
        weather.WeatherData.__init__(self, station_id)
        
class NOAAWeatherBackend(weather.WeatherBackend):
    
    def __init__(self, gconf_client, gconf_key):
        weather.WeatherBackend.__init__(self, gconf_client, gconf_key)
    
    def get_weather_data(self):
        station_id = g15gconf.get_string_or_default(self.gconf_client, "%s/station_id" % self.gconf_key, "KPEO")
        p = pywapi.get_weather_from_noaa(station_id)
        
        tm = email.utils.parsedate_tz(p["observation_time_rfc822"])[:9]
        data = {
            "location" : p["location"],
            "datetime" : datetime.datetime.fromtimestamp(time.mktime(tm)),
            "current_conditions" : {
                "wind_speed" : g15pythonlang.to_int_or_none(weather.mph_to_kph(float(p["wind_mph"]))) if "wind_mph" in p else None,
                "wind_direction" : g15pythonlang.to_int_or_none(p["wind_degrees"]) if "wind_degrees" in p else None,
                "pressure" : p["pressure_mb"] if "pressure_mb" in p else None,
                "humidity" : p["relative_humidity"] if "relative_humidity" in p else None,
                "condition" : p["weather"] if "weather" in p else None,
                "temp_c" : p["temp_c"] if "temp_c" in p else None,
                "icon" : self._get_icon(p["icon_url_name"]) if "icon_url_name" in p else None,
                "fallback_icon" : "http://w1.weather.gov/images/fcicons/%s" % ( "%s.jpg" % os.path.splitext(p["icon_url_name"])[0] ) if "icon_url_name" in p else None
            }
        }
                
        return data
    
    def _get_icon(self, icon):
        night = False
        icon_name = icon
        if icon.startswith("n"):
            icon_name = icon_name[1:]
            night = True
        elif icon.startswith("hi_n"):
            icon_name = "hi_" + icon_name[3:]
            night = True
            
        name, extension = os.path.splitext(icon_name)
        theme_icon = None
        if name in [ "bkn" ]:
            # Mostly Cloudy | Mostly Cloudy with Haze | Mostly Cloudy and Breezy
            theme_icon = "weather-overcast"
        elif name in [ "skc" ]:
            # Fair | Clear | Fair with Haze | Clear with Haze | Fair and Breezy | Clear and Breezy
            theme_icon = "weather-clear"
        elif name in [ "few" ]:
            # A Few Clouds | A Few Clouds with Haze | A Few Clouds and Breezy
            theme_icon = "weather-few-clouds"
        elif name in [ "sct" ]:
            # Partly Cloudy | Partly Cloudy with Haze | Partly Cloudy and Breezy
            theme_icon = "weather-clouds"
        elif name in [ "ovc" ]:
            # Overcast | Overcast with Haze | Overcast and Breezy
            theme_icon = "weather-overcast"
        elif name in [ "fg" ]:
            # Fog/Mist | Fog | Freezing Fog | Shallow Fog | Partial Fog | Patches of Fog | Fog in Vicinity | Freezing Fog in Vicinity | Shallow Fog in Vicinity | Partial Fog in Vicinity | Patches of Fog in Vicinity | Showers in Vicinity Fog | Light Freezing Fog | Heavy Freezing Fog
            theme_icon = "weather-fog"
        elif name in [ "shra", "hi_shwrs", "ra1", "ra" ]:
            # Rain Showers | Light Rain Showers | Light Rain and Breezy | Heavy Rain Showers | Rain Showers in Vicinity | Light Showers Rain | Heavy Showers Rain | Showers Rain | Showers Rain in Vicinity | Rain Showers Fog/Mist | Light Rain Showers Fog/Mist | Heavy Rain Showers Fog/Mist | Rain Showers in Vicinity Fog/Mist | Light Showers Rain Fog/Mist | Heavy Showers Rain Fog/Mist | Showers Rain Fog/Mist | Showers Rain in Vicinity Fog/Mist
            theme_icon = "weather-showers"
        elif name in [ "tsra" ]:
            # Rain Showers | Light Rain Showers | Light Rain and Breezy | Heavy Rain Showers | Rain Showers in Vicinity | Light Showers Rain | Heavy Showers Rain | Showers Rain | Showers Rain in Vicinity | Rain Showers Fog/Mist | Light Rain Showers Fog/Mist | Heavy Rain Showers Fog/Mist | Rain Showers in Vicinity Fog/Mist | Light Showers Rain Fog/Mist | Heavy Showers Rain Fog/Mist | Showers Rain Fog/Mist | Showers Rain in Vicinity Fog/Mist
            theme_icon = "weather-storm"
        elif name in [ "sn" ]:
            # Snow | Light Snow | Heavy Snow | Snow Showers | Light Snow Showers | Heavy Snow Showers | Showers Snow | Light Showers Snow | Heavy Showers Snow | Snow Fog/Mist | Light Snow Fog/Mist | Heavy Snow Fog/Mist | Snow Showers Fog/Mist | Light Snow Showers Fog/Mist | Heavy Snow Showers Fog/Mist | Showers Snow Fog/Mist | Light Showers Snow Fog/Mist | Heavy Showers Snow Fog/Mist | Snow Fog | Light Snow Fog | Heavy Snow Fog | Snow Showers Fog | Light Snow Showers Fog | Heavy Snow Showers Fog | Showers Snow Fog | Light Showers Snow Fog | Heavy Showers Snow Fog | Showers in Vicinity Snow | Snow Showers in Vicinity | Snow Showers in Vicinity Fog/Mist | Snow Showers in Vicinity Fog | Low Drifting Snow | Blowing Snow | Snow Low Drifting Snow | Snow Blowing Snow | Light Snow Low Drifting Snow | Light Snow Blowing Snow | Light Snow Blowing Snow Fog/Mist | Heavy Snow Low Drifting Snow | Heavy Snow Blowing Snow | Thunderstorm Snow | Light Thunderstorm Snow | Heavy Thunderstorm Snow | Snow Grains | Light Snow Grains | Heavy Snow Grains | Heavy Blowing Snow | Blowing Snow in Vicinity
            theme_icon = "weather-snow"
        elif name in [ "svrtsra" ]:
            # Funnel Cloud | Funnel Cloud in Vicinity | Tornado/Water Spout
            theme_icon = "weather-severe-alert"
            
        if theme_icon is not None and night:
            theme_icon = "%s-night" % theme_icon
            
        if theme_icon is None:
            # Fallback to using actual image
            theme_icon = "http://w1.weather.gov/images/fcicons/%s.jpg" % name
            
        return theme_icon
        
