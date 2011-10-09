# coding=UTF-8
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
_ = g15locale.get_translation("weather", modfile = __file__).ugettext

import gnome15.g15screen as g15screen
import gnome15.g15theme as g15theme
import gnome15.g15util as g15util
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15text as g15text
import datetime
from threading import Timer
import gtk
import os
import pywapi
import pango
import logging
logger = logging.getLogger("weather")


# Plugin details - All of these must be provided
id="weather"
name=_("Weather")
description=_("Displays the current weather at a location. It currently uses the unofficial Google Weather API as a source \
of weather information. A word of warning. The plugin tries to use images from your current theme. If the theme does \
not have icons, it will fall back to using images hosted on Google. This may be slow, and cause Gnome15 to temporarily hang.\
when displaying this plugin.")  
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=True
default_enabled=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]

DEFAULT_LOCATION="london,england"

''' 
This simple plugin displays the current weather at a location
'''

CELSIUS=0
FARANHEIT=1
KELVIN=2

def create(gconf_key, gconf_client, screen):
    return G15Weather(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "weather.glade"))
    
    dialog = widget_tree.get_object("WeatherDialog")
    dialog.set_transient_for(parent)
    
    location = widget_tree.get_object("Location")
    location.set_text(get_location(gconf_client, gconf_key))
    location.connect("changed", changed, location, gconf_key + "/location", gconf_client)
    
    
    update = widget_tree.get_object("UpdateAdjustment")
    update.set_value(gconf_client.get_int(gconf_key + "/update"))
    update.connect("value-changed", value_changed, location, gconf_key + "/update", gconf_client)
    
    unit = widget_tree.get_object("UnitCombo")
    unit.set_active(gconf_client.get_int(gconf_key + "/units"))
    unit.connect("changed", unit_changed, location, gconf_key + "/units", gconf_client)
    
    dialog.run()
    dialog.hide()
    
def changed(widget, location, gconf_key, gconf_client):
    gconf_client.set_string(gconf_key, widget.get_text())
    
def unit_changed(widget, location, gconf_key, gconf_client):
    gconf_client.set_int(gconf_key, widget.get_active())
    
def value_changed(widget, location, gconf_key, gconf_client):
    gconf_client.set_int(gconf_key, int(widget.get_value()))
            
def get_location(gconf_client, gconf_key):
    loc = gconf_client.get_string(gconf_key + "/location")
    if loc == None:
        return DEFAULT_LOCATION
    return loc

class G15Weather():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._page = None
        self._change_timer = None
        self._timer = None
        
    def activate(self):
        self._text = g15text.new_text(self._screen)
        self._page = g15theme.G15Page(id, self._screen, thumbnail_painter = self._paint_thumbnail,
                                        panel_painter = self._paint_thumbnail, \
                                        theme = g15theme.G15Theme(self))
        self._get_weather()
        self._screen.add_page(self._page)
        self._notify_handle = self._gconf_client.notify_add(self._gconf_key, self._loc_changed, None)
        self._screen.redraw(self._page)
        self._refresh_after_interval()
    
    def deactivate(self):
        self._gconf_client.notify_remove(self._notify_handle);
        self._cancel_timer()
        self._cancel_change_timer()
        self._screen.del_page(self._page)
        self._page = None
    
    def destroy(self):
        pass
        
    """
    Private
    """
        
    def _refresh(self):
        if self._page != None:
            self._get_weather()
            self._screen.set_priority(self._page, g15screen.PRI_HIGH, revert_after = 3.0)
        
    def _cancel_timer(self):
        if self._timer != None:
            self._timer.cancel()
            self._timer = None
    
    def _cancel_change_timer(self):
        if self._change_timer != None:
            self._change_timer.cancel()
            self._change_timer = None
        
    def _refresh_after_interval(self):
        self._cancel_timer()
        val = self._gconf_client.get_int(self._gconf_key + "/update")
        if val == 0:
            val = 3600
        self._timer = g15util.schedule("WeatherRefreshTimer", val * 60.0, self._refresh)
        
    def _loc_changed(self, client, connection_id, entry, args):
        # Only actually go and refresh after the value hasn't changed for a few seconds
        self._cancel_change_timer()            
        self._cancel_timer()
        self._change_timer = Timer(3.0, self._refresh, ())
        self._change_timer.name = "WeatherLocationChangeTimer"
        self._change_timer.setDaemon(True)
        self._change_timer.start()
        
        # And now start the main timer
        self._refresh_after_interval()
    
    def _get_weather(self):
        properties = {}
        attributes = {}
        try :
            loc = get_location(self._gconf_client, self._gconf_key)
            self._weather = pywapi.get_weather_from_google(loc,  hl = ''  )
            
            properties["location"] = loc
            current = self._weather['current_conditions']
            
            if len(current) == 0:
                properties["message"] = _("No weather data for location:-\n%s") % loc
            else:                                            
                properties["message"] = ""
                t_icon = self._translate_icon(current['icon'])
                if t_icon != None:
                    attributes["icon"] = g15util.load_surface_from_file(t_icon)
                    properties["icon"] = g15util.get_embedded_image_url(attributes["icon"])
                else:
                    logger.warning("No translated weather icon for %s" % current['icon'])
                mono_thumb = self._get_mono_thumb_icon(current['icon'])        
                if mono_thumb != None:
                    attributes["mono_thumb_icon"] = g15util.load_surface_from_file(os.path.join(os.path.join(os.path.dirname(__file__), "default"), mono_thumb))
                properties["condition"] = current['condition']
                
                properties["temp_c"] = "%3.1f°C" % float(current['temp_c'])
                properties["temp_f"] = "%3.1f°F" % float(current['temp_f'])
                properties["temp_k"] = "%3.1f°K" % ( float(current['temp_c']) + 273.15 )
                
                units = self._gconf_client.get_int(self._gconf_key + "/units")
                if units == CELSIUS:                 
                    properties["temp"] = properties["temp_c"]              
                    properties["temp_short"] = "%2.0f°" % float(current['temp_c'])
                elif units == FARANHEIT:                
                    properties["temp"] = properties["temp_f"]              
                    properties["temp_short"] = "%2.0f°" % float(current['temp_f'])
                else:                
                    properties["temp"] = properties["temp_k"]
                    properties["temp_short"] = "%2.0f°" % ( float(current['temp_c']) + 273.15 )
                    
                y = 1
                for forecast in self._weather['forecasts']:        
                    properties["condition" + str(y)] = forecast['condition']
                    lo_f = float(forecast['low'])
                    lo_c = ( ( lo_f - 32 ) / 9 ) * 5
                    lo_k = lo_c + 273.15
                    hi_f = float(forecast['high'])
                    hi_c = ( ( lo_f - 32 ) / 9 ) * 5
                    hi_k = lo_c + 273.15
                    
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
                    properties["icon" + str(y)] = self._translate_icon(forecast['icon'])
                    y += 1
            
            self._page.theme_properties = properties
            self._page.theme_attributes = attributes
        except Exception as e:
            print e
            self._weather = None
            if self._page:
                self._page.theme_properties = {}
                self._page.theme_attributes = {}
        
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
        
    def _translate_icon(self, icon):
        
        '''
        http://www.blindmotion.com/?p=73
        http://awapi.codeplex.com/Thread/View.aspx?ThreadId=54845
        
        The following are always retrieved from Google as there are no freedesktop equivalents 
        
        images/weather/icy.gif
        images/weather/dust.gif
        images/weather/smoke.gif
        images/weather/haze.gif
        '''
        
        
        theme_icon = None
        if icon == None or icon == "":
            return None
        else:
            base_icon= self._get_base_icon(icon)
            
            if base_icon in [ "chanceofrain", "scatteredshowers" ]:
                theme_icon = "weather-showers-scattered"
            elif base_icon in [ "sunny", "haze" ]: 
                theme_icon = "weather-clear"
            elif base_icon == "mostlysunny":
                theme_icon = "weather-few-clouds"
            elif base_icon == "partlycloudy":
                theme_icon = "weather-clouds"
            elif base_icon in [ "mostlycloudy", "cloudy" ]:
                theme_icon = "weather-overcast"
            elif base_icon == "rain":
                theme_icon = "weather-showers"
            elif base_icon in [ "mist", "fog" ]:
                theme_icon = "weather-fog"
            elif base_icon in [ "chanceofsnow", "sleet", "flurries"]:
                theme_icon = "weather-snow"
            elif base_icon in [ "storm", "chanceofstorm" ]:
                # TODO is this too extreme?
                theme_icon = "weather-severe-alert"
            elif base_icon in [ "thunderstorm", "chanceoftstorm" ]:
                # TODO is this right?
                theme_icon = "weather-storm"
            
        now = datetime.datetime.now()
        # TODO dusk / dawn based on locale / time of year - probably hard? 
        if theme_icon != None and ( now.hour > 18 or now.hour < 4):
            theme_icon = [ "%s-night" % theme_icon, theme_icon ]
            
        if theme_icon != None:
            icon_path = g15util.get_icon_path(theme_icon, warning = False)
            if icon_path == None and ( now.hour > 18 or now.hour < 4):
                # Try the day icons
                icon_path = g15util.get_icon_path(theme_icon[:len(theme_icon) - 6])
                
            if icon_path != None:
                return icon_path
             
        if icon.startswith("http"):
            logger.warning("Having to resort to using Google weather image %s. This may hang up the LCD for a bit" % icon)
            return icon
        else:
            logger.warning("Having to resort to using Google weather image http://www.google.com%s. This may hang up the LCD for a bit" % icon)
            return "http://www.google.com" + icon
        
    def _get_base_icon(self, icon):
        # Strips off URL path, image extension, size and weather prefix if present
        base_icon = os.path.splitext(os.path.basename(icon))[0].rsplit("-")[0]
        if base_icon.startswith("weather_"):
            base_icon = base_icon[8:]
        base_icon = base_icon.replace('_','')
        return base_icon
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        total_taken = 0 
        self._text.set_canvas(canvas)
        if self._screen.driver.get_bpp() == 1:
            if "mono_thumb_icon" in self._page.theme_attributes:
                size = g15util.paint_thumbnail_image(allocated_size, self._page.theme_attributes["mono_thumb_icon"], canvas)
                canvas.translate(size + 2, 0)
                total_taken += size + 2
            if "temp_short" in self._page.theme_properties:
                self._text.set_attributes(self._page.theme_properties["temp_short"], \
                                          font_desc = g15globals.fixed_size_font_name, \
                                          font_absolute_size =  6 * pango.SCALE / 2)
                x, y, width, height = self._text.measure()
                total_taken += width
                self._text.draw(x, y)
        else:
            rgb = self._screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 ))
            canvas.set_source_rgb(rgb[0],rgb[1],rgb[2])
            if "icon" in self._page.theme_attributes:
                size = g15util.paint_thumbnail_image(allocated_size, self._page.theme_attributes["icon"], canvas)
                total_taken += size
            if "temp" in self._page.theme_properties:
                if horizontal:
                    self._text.set_attributes(self._page.theme_properties["temp"], font_desc = "Sans", font_absolute_size =  allocated_size * pango.SCALE / 2)
                    x, y, width, height = self._text.measure()
                    self._text.draw(total_taken, (allocated_size / 2) - height / 2)
                    total_taken += width + 4
                else:  
                    self._text.set_attributes(self._page.theme_properties["temp"], font_desc = "Sans", font_absolute_size =  allocated_size * pango.SCALE / 4)
                    x, y, width, height = self._text.measure()
                    self._text.draw((allocated_size / 2) - width / 2, total_taken)
                    total_taken += height + 4     
        return total_taken
            
