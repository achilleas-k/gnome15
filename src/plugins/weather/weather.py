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
 
import gnome15.g15_daemon as g15daemon
import gnome15.g15_draw as g15draw
import gnome15.g15_screen as g15screen
import datetime
from threading import Timer
import gtk
import os
import sys
import pywapi
import urllib2
import Image
import gconf


# Plugin details - All of these must be provided
id="weather"
name="Weather"
description="Displays the current weather at a location.\nUses Google Weather API"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=True

DEFAULT_LOCATION="london,england"

''' 
This simple plugin displays the current weather at a location
'''

def create(gconf_key, gconf_client, screen):
    return G15Weather(gconf_key, gconf_client, screen)

class G15Weather():
    
    ''' Lifecycle functions. You must provide activate and deactivate,
        the constructor and destroy function are optional
    '''
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.gconf_client.add_dir(self.gconf_key, gconf.CLIENT_PRELOAD_NONE)
        self.canvas = None
        self.hidden = True
    
    def activate(self):
        self.get_weather()
        self.canvas = self.screen.new_canvas(on_shown=self.on_shown,on_hidden=self.on_hidden, id="Weather")
        self.screen.draw_current_canvas()        
        self.timer = Timer(3600, self.refresh, ())
        self.timer.name = "WeatherRefreshTimer"
        self.timer.setDaemon(True)
        self.timer.start()
        self.gconf_client.notify_add(self.gconf_key, self.loc_changed);
        
    def loc_changed(self, client, connection_id, entry, args):
        self.screen.set_priority(self.canvas, g15screen.PRI_HIGH, revert_after = 3.0)
        self.refresh()
    
    def deactivate(self):
        if self.timer != None:
            self.timer.cancel()
        self.screen.del_canvas(self.canvas)
        self.canvas = None
        
    def destroy(self):
        pass
        
    ''' Functions specific to plugin
    ''' 

    def show_preferences(self, parent):
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "weather.glade"))
        
        dialog = widget_tree.get_object("WeatherDialog")
        dialog.set_transient_for(parent)
        
        location = widget_tree.get_object("Location")
        location.set_text(self.get_location())
        location_h = location.connect("changed", self.changed, location, self.gconf_key + "/location")
        
        dialog.run()
        dialog.hide()
        location.disconnect(location_h)
        
    def changed(self, widget, location, gconf_key):
        self.gconf_client.set_string(gconf_key, widget.get_text())
                
    def get_location(self):
        loc = self.gconf_client.get_string(self.gconf_key + "/location")
        if loc == None:
            return DEFAULT_LOCATION
        return loc
        
    def on_shown(self):
        self.hidden = False
        self.draw_weather()
        
    def on_hidden(self):
        self.hidden = True
    
    def refresh(self):
        if self.canvas != None:
            self.get_weather()
            self.draw_weather()
    
    def get_weather(self):
        try :
            self.weather = pywapi.get_weather_from_google(self.get_location(),  hl = ''  )
        except Exception as e:
            print e
            self.weather = None
            print "Failed to get weather"
            
    def draw_weather(self):
        if not self.hidden:
            self.canvas.clear()
            
            if self.weather == None:            
                self.canvas.set_font_size(g15draw.FONT_SMALL)
                self.canvas.draw_text("Failed to get weather for :-", (g15draw.CENTER, g15draw.CENTER))
                self.canvas.draw_text(self.get_location(), (g15draw.CENTER, g15draw.BOTTOM))
            else:
                current = self.weather['current_conditions']
                
                if len(current) == 0:
                    self.canvas.set_font_size(g15draw.FONT_SMALL)
                    self.canvas.draw_text("No information for location :-", (g15draw.CENTER, g15draw.CENTER))
                    self.canvas.draw_text(self.get_location(), (g15draw.CENTER, g15draw.BOTTOM))
                else:                                
                    # Get the image
                    #
                    opener = urllib2.build_opener()
                    weather_icon_page = opener.open("http://www.google.com" + current['icon'])
                    weather_icon = weather_icon_page.read()
                    temp_name = "/tmp/" + os.path.basename(current['icon'])
                    fout = open(temp_name, "wb")
                    fout.write(weather_icon)
                    fout.close()
                    image = self.canvas.process_image_from_file(temp_name, (32, 32))
                    image = image.convert("RGBA")
                    self.canvas.draw_image(image, (0, 4))
                    
                    # Text
    
                    y = 4
                    for forecast in self.weather['forecasts']:
                        self.canvas.set_font_size(g15draw.FONT_TINY)
                        self.canvas.draw_text(forecast['day_of_week'][:1] + " " + forecast['condition'] + " " +  forecast['high'] + "F", (self.screen.driver.get_size()[0] / 3, y))
                        y+= 8
                        
                    self.canvas.set_font_size(g15draw.FONT_SMALL)
                    self.canvas.draw_text(current['temp_c'] + "C" + " " + current['temp_f'] + "F", (g15draw.LEFT, g15draw.TOP), emboss="White")
                    self.canvas.draw_text(current['condition'], (g15draw.LEFT, g15draw.BOTTOM), emboss="White")
                    
                    
            self.screen.draw(self.canvas)
                
