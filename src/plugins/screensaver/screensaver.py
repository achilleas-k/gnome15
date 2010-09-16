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
 
import gnome15.g15_draw as g15draw
import gnome15.g15_screen as g15screen
import datetime
from threading import Timer
import gtk
import os
import sys
import dbus
import os

# Plugin details - All of these must be provided
id="screensaver"
name="Screensaver"
description="Dim the keyboard and display\na message when the screen saver\nactivates"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=True


''' 
This plugin displays a high priority screen when the screensaver activates
'''

def create(gconf_key, gconf_client, screen):
    return G15ScreenSaver(gconf_key, gconf_client, screen)
            
class G15ScreenSaver():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.session_bus = None
        self.in_screensaver = False
        self.canvas = None
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def show_preferences(self, parent):
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "screensaver.glade"))
        
        dialog = widget_tree.get_object("ScreenSaverDialog")
        dialog.set_transient_for(parent)
        
        dim_keyboard = widget_tree.get_object("DimKeyboardCheckbox")
        dim_keyboard.set_active(self.gconf_client.get_bool(self.gconf_key + "/dim_keyboard"))
        dim_h = dim_keyboard.connect("toggled", self.changed, self.gconf_key + "/dim_keyboard")
        
        message_text = widget_tree.get_object("MessageTextView")
        text_buffer = widget_tree.get_object("TextBuffer")
        text = self.gconf_client.get_string(self.gconf_key + "/message_text")
        if text == None:
            text = ""
        text_buffer.set_text(text)
        text_h = text_buffer.connect("changed", self.changed, self.gconf_key + "/message_text")
        
        dialog.run()
        dialog.hide()
        dim_keyboard.disconnect(dim_h)
        text_buffer.disconnect(text_h)
        
    def changed(self, widget, key):
        if key.endswith("/dim_keyboard"):
            self.gconf_client.set_bool(key, widget.get_active())
        else:
            bounds = widget.get_bounds()
            self.gconf_client.set_string(key, widget.get_text(bounds[0],bounds[1]))
            pass

    def activate(self):
        if self.session_bus == None:
            try:
                self.session_bus = dbus.SessionBus()
                self.session_bus.add_signal_receiver(self.screensaver_changed_handler, dbus_interface = "org.gnome.ScreenSaver", signal_name = "ActiveChanged")
            except Exception as e:
                self.session_bus = None
                print "Error. " + str(e) + ", retrying in 10 seconds"
                Timer(10, self.activate, ()).start()
                return
        
        self.activated = True
    
    def deactivate(self):
        self.remove_canvas()
        self.activated = False
        
    def destroy(self):
        self.session_bus.remove_signal_receiver(self.screensaver_changed_handler, dbus_interface = "org.gnome.ScreenSaver", signal_name = "ActiveChanged")
        
        
    ''' Functions specific to plugin
    ''' 
    
    def remove_canvas(self):
        if self.canvas != None:
            self.screen.del_canvas(self.canvas)
            self.canvas = None
        
    def screensaver_changed_handler(self, value):
        if self.activated:
            self.in_screensaver = bool(value)
            if self.in_screensaver:
                if self.canvas == None:
                    self.canvas = self.screen.new_canvas(g15screen.PRI_HIGH, id="Screensaver")
                    self.screen.draw_current_canvas()
                if self.gconf_client.get_bool(self.gconf_key + "/dim_keyboard"):
                    self.screen.driver.set_keyboard_backlight(0)
                self.draw()
            else:
                self.remove_canvas()
                if self.gconf_client.get_bool(self.gconf_key + "/dim_keyboard"):
                    self.screen.driver.set_keyboard_backlight(self.gconf_client.get_int("/apps/gnome15/keyboard_backlight"))
        
    def draw(self):
        self.canvas.clear()    
        text = self.gconf_client.get_string(self.gconf_key + "/message_text")
        if text == None:
            text = ""
        split = text.split("\n")
        y = 0                        
        if len(split) == 0:
            # Draw nothing
            pass
        elif len(split) == 1:
            self.canvas.set_font_size(g15draw.FONT_MEDIUM)
            self.canvas.draw_text(split[0], (g15draw.CENTER, g15draw.CENTER), emboss="White")
            y = g15draw.CENTER 
        elif len(split) == 2:
            self.canvas.set_font_size(g15draw.FONT_MEDIUM)
            self.canvas.draw_text(split[0], (g15draw.CENTER, g15draw.TOP), emboss="White")
            self.canvas.draw_text(split[1], (g15draw.CENTER, g15draw.BOTTOM), emboss="White")
        else:
            self.canvas.set_font_size(g15draw.FONT_SMALL)
            self.canvas.draw_text(split[0], (g15draw.CENTER, g15draw.TOP), emboss="White")
            self.canvas.draw_text(split[1], (g15draw.CENTER, g15draw.CENTER), emboss="White")
            self.canvas.draw_text(split[2], (g15draw.CENTER, g15draw.BOTTOM), emboss="White")
            
        self.screen.draw(self.canvas)