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
#
# Based on bits of pywapi :-
#
#Copyright (c) 2009 Eugene Kaznacheev <qetzal@gmail.com>

#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:

#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("weather-yahoo", modfile = __file__).ugettext

import gnome15.g15accounts as g15accounts
import gnome15.g15globals as g15globals
import gnome15.g15util as g15util
import weather
import gtk
import os
import datetime
import urllib2, re
import json
from xml.dom import minidom
from urllib import quote
import time

#select * from xml where url="http://weather.yahooapis.com/forecastrss?w=26350898"

YAHOO_WEATHER_URL    = 'http://xml.weather.yahoo.com/forecastrss?w=%s&u=%s&d=5'
YAHOO_WEATHER_URL_JSON    = 'http://query.yahooapis.com/v1/public/yql?q=select%20item%20from%20weather.forecast%20where%20location%3D%2248907%22&format=json'
YAHOO_WEATHER_NS     = 'http://xml.weather.yahoo.com/ns/rss/1.0'

# Logging
import logging
logger = logging.getLogger("weather-yahoo")
 
"""
Plugin definition
"""
backend_name="Yahoo"
id="weather-yahoo"
name=_("Weather (Yahoo support)")
description=_("Adds Yahoo as a source of weather data.")
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
    return YahooWeatherOptions(gconf_client, gconf_key)

def create_backend(gconf_client, gconf_key):
    return YahooWeatherBackend(gconf_client, gconf_key)

"""
Utilities for parsing
"""

def xml_get_ns_yahoo_tag(dom, ns, tag, attrs):
    """
    Parses the necessary tag and returns the dictionary with values
    
    Parameters:
    dom - DOM
    ns - namespace
    tag - necessary tag
    attrs - tuple of attributes

    Returns: a dictionary of elements 
    """
    element = dom.getElementsByTagNameNS(ns, tag)[0]
    return xml_get_attrs(element,attrs)


def xml_get_attrs(xml_element, attrs):
    """
    Returns the list of necessary attributes
    
    Parameters: 
    element: xml element
    attrs: tuple of attributes

    Return: a dictionary of elements
    """
    
    result = {}
    for attr in attrs:
        result[attr] = xml_element.getAttribute(attr)   
    return result


class YahooWeatherOptions(weather.WeatherOptions):
    def __init__(self, gconf_client, gconf_key):
        weather.WeatherOptions.__init__(self)
                
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "weather-yahoo.glade"))
        self.component = self.widget_tree.get_object("OptionPanel")
        
        g15util.configure_text_from_gconf(gconf_client, "%s/location_id" % gconf_key, "LocationID", "", self.widget_tree)

class YahooWeatherData(weather.WeatherData):
    
    def __init__(self, station_id):
        weather.WeatherData.__init__(self, station_id)
        
class YahooWeatherBackend(weather.WeatherBackend):
    
    def __init__(self, gconf_client, gconf_key):
        weather.WeatherBackend.__init__(self, gconf_client, gconf_key)
        
    def get_weather_data(self):
        return self._do_get_weather_data_xml()
    
    def _do_get_weather_data_json(self):
        location_id = quote(location_id)
        if units == 'metric':
            unit = 'c'
        else:
            unit = 'f'
        url = YAHOO_WEATHER_URL_JSON % (location_id, unit)
        handler = urllib2.urlopen(url)
        jobj = json.load(handler)    
        handler.close()
        
    def _do_get_weather_data_xml(self):
        location_id = g15util.get_string_or_default(self.gconf_client, "%s/location_id" % self.gconf_key, "KPEO")
        p = self._get_weather_from_yahoo(location_id)
        if p is None:
            return None
        
        # Get location
        location_el = p["location"]
        location = g15util.append_if_exists(location_el, "city", "")
        location = g15util.append_if_exists(location_el, "region", location)
        location = g15util.append_if_exists(location_el, "country", location)
        
        # Get current condition
        condition_el = p["condition"]
        wind_el = p["wind"] if "wind" in p else None
        
        # Observed date
        try:
            observed_datetime = datetime.datetime.strptime(condition_el["date"], "%a, %d %b %Y %H:%M %p %Z")
        except ValueError as v: 
            import email.utils
            dxt = email.utils.parsedate_tz(condition_el["date"])
            class TZ(datetime.tzinfo):
                def dst(self, dt):
                    return datetime.timedelta(0)
                
                def tzname(self, dt):
                    return dxt[9]
                
                def utcoffset(self, dt): return datetime.timedelta(seconds=dxt[9])
            observed_datetime = datetime.datetime(*dxt[:7],  tzinfo=TZ())
        
        # Forecasts (we only get 2 from yahoo)
        forecasts_el = p["forecasts"]
        forecasts = []
        today_low = None
        today_high = None
        for f in forecasts_el:        
            condition_code = int(f["code"])
            high = float(f["high"])
            low = float(f["low"])
            if today_low is None:
                today_low = low
                today_high = high
            forecasts.append({
                "condition" : f["text"],                
                "high" : high,              
                "low" : low,            
                "day_of_week" : f["day"],
                "icon" : self._translate_icon(condition_code),
                "fallback_icon" : "http://l.yimg.com/a/i/us/we/52/%s.gif" % condition_code
                              })
            
        # Sunset and sunrise
        sunset = None
        sunrise = None
        if "astronomy" in p:
            astronomy = p["astronomy"]
            if "sunset" in astronomy:
                sunset = g15locale.parse_US_time(astronomy["sunset"])
            if "sunrise" in astronomy:
                sunrise = g15locale.parse_US_time(astronomy["sunrise"])
                
        # Pressure, Visibility and Humidity
        pressure = None
        if "atmosphere" in p:
            atmosphere = p["atmosphere"]
            if "pressure" in atmosphere:
                pressure = float(atmosphere["pressure"])
            if "visibility" in atmosphere:
                visibility = float(atmosphere["visibility"])
            if "humidity" in atmosphere:
                humidity = float(atmosphere["humidity"])
        
        # Build data structure        
        condition_code = int(condition_el["code"])
        data = {
            "location" : location,
            "forecasts" : forecasts,
            "datetime": observed_datetime,
            "current_conditions" : {
                "wind_chill": wind_el["chill"] if wind_el is not None and "chill" in wind_el else None,
                "wind_direction": wind_el["direction"] if wind_el is not None and "direction" in wind_el else None,
                "wind_speed": wind_el["speed"] if wind_el is not None and "speed" in wind_el else None,
                "condition" : condition_el["text"],
                "sunset" : sunset,
                "sunrise" : sunrise,
                "pressure" : pressure,
                "visibility" : visibility,
                "humidity" : humidity,
                "low" : today_low,
                "high" : today_high,
                "temp_c" : float(condition_el["temp"]),
                "icon" : self._translate_icon(condition_code),
                "fallback_icon" : "http://l.yimg.com/a/i/us/we/52/%s.gif" % condition_code
            }
        }
                
        return data
    
    def _translate_icon(self, code):
        
        theme_icon = None
        if code in [ 0, 1, 2, 3, 4 ]:
            theme_icon = "weather-severe-alert"
        elif code in [ 8, 9, 10, 11, 12, 35 ]:
            theme_icon = "weather-showers"
        elif code in [ 5, 6, 7, 13, 14, 15, 16, 41, 42, 43, 46 ]:
            theme_icon = "weather-snow"
        elif code in [ 20 ]:
            theme_icon = "weather-fog"
        elif code in [ 37, 38, 39, 45, 47 ]:
            theme_icon = "weather-storm"
        elif code in [ 40 ]:
            theme_icon = "weather-showers-scattered"
        elif code in [ 31 ]:
            theme_icon = "weather-clear-night"
        elif code in [ 30,44 ]:
            theme_icon = "weather-few-clouds"
        elif code in [ 29 ]:
            theme_icon = "weather-few-clouds-night"
        elif code in [ 28, 26 ]:
            theme_icon = "weather-overcast"
        elif code in [ 27 ]:
            theme_icon = "weather-overcast-night"
        elif code in [ 34, 21 ]:
            theme_icon = "weather-clouds"
        elif code in [ 33 ]:
            theme_icon = "weather-clouds-night"
        elif code in [ 32, 36 ]:
            theme_icon = "weather-clear"
            
            
        if theme_icon is None:
            # Fallback to using image extracted from data
            theme_icon = "http://l.yimg.com/a/i/us/we/52/%s.gif" % code
        
        """
        The following will always use yahoo images
        
  <code number="17" description="hail"/>
  <code number="18" description="sleet"/>
  <code number="19" description="dust"/>
  <code number="22" description="smoky"/>
  <code number="23" description="blustery"/>
  <code number="24" description="windy"/>
  <code number="25" description="cold"/>
  <code number="3200" description="not available"/>
        """
        
        return theme_icon
    
    
    def _get_weather_from_yahoo(self, location_id, units = 'metric'):
        """
        Fetches weather report from Yahoo!
    
        Parameters 
        location_id: A five digit US zip code or location ID. To find your location ID, 
        browse or search for your city from the Weather home page(http://weather.yahoo.com/)
        The weather ID is in the URL for the forecast page for that city. You can also get the location ID by entering your zip code on the home page. For example, if you search for Los Angeles on the Weather home page, the forecast page for that city is http://weather.yahoo.com/forecast/USCA0638.html. The location ID is USCA0638.
    
        units: type of units. 'metric' for metric and '' for  non-metric
        Note that choosing metric units changes all the weather units to metric, for example, wind speed will be reported as kilometers per hour and barometric pressure as millibars.
     
        Returns:
        weather_data: a dictionary of weather data that exists in XML feed. See  http://developer.yahoo.com/weather/#channel
        """
        location_id = quote(location_id)
        if units == 'metric':
            unit = 'c'
        else:
            unit = 'f'
        url = YAHOO_WEATHER_URL % (location_id, unit)
        handler = urllib2.urlopen(url)
        dom = minidom.parse(handler)    
        handler.close()
            
        weather_data = {}
        weather_data['title'] = dom.getElementsByTagName('title')[0].firstChild.data
        linkel = dom.getElementsByTagName('link')
        
        if len(linkel) < 1:
            return None
        
        weather_data['link'] = linkel[0].firstChild.data
    
        ns_data_structure = { 
            'location': ('city', 'region', 'country'),
            'units': ('temperature', 'distance', 'pressure', 'speed'),
            'wind': ('chill', 'direction', 'speed'),
            'atmosphere': ('humidity', 'visibility', 'pressure', 'rising'),
            'astronomy': ('sunrise', 'sunset'),
            'condition': ('text', 'code', 'temp', 'date', 'day')
        }       
        
        for (tag, attrs) in ns_data_structure.iteritems():
            weather_data[tag] = xml_get_ns_yahoo_tag(dom, YAHOO_WEATHER_NS, tag, attrs)
    
        weather_data['geo'] = {}
        weather_data['geo']['lat'] = dom.getElementsByTagName('geo:lat')[0].firstChild.data
        weather_data['geo']['long'] = dom.getElementsByTagName('geo:long')[0].firstChild.data
    
        weather_data['condition']['title'] = dom.getElementsByTagName('item')[0].getElementsByTagName('title')[0].firstChild.data
        weather_data['html_description'] = dom.getElementsByTagName('item')[0].getElementsByTagName('description')[0].firstChild.data
        
        forecasts = []
        for forecast in dom.getElementsByTagNameNS(YAHOO_WEATHER_NS, 'forecast'):
            forecasts.append(xml_get_attrs(forecast,('date', 'low', 'high', 'text', 'code', 'day')))
        weather_data['forecasts'] = forecasts
        
        dom.unlink()
    
        return weather_data
            
        
