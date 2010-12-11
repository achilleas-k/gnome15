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
 
import gnome15.g15_screen as g15screen
import gnome15.g15_driver as g15driver
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
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
description="Dim the keyboard and display a message when the screen saver activates."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True


''' 
This plugin displays a high priority screen when the screensaver activates
'''

def create(gconf_key, gconf_client, screen):
    return G15ScreenSaver(gconf_key, gconf_client, screen)

def show_preferences(parent, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "screensaver.glade"))
    
    dialog = widget_tree.get_object("ScreenSaverDialog")
    dialog.set_transient_for(parent)
    
    dim_keyboard = widget_tree.get_object("DimKeyboardCheckbox")
    dim_keyboard.set_active(gconf_client.get_bool(gconf_key + "/dim_keyboard"))
    dim_h = dim_keyboard.connect("toggled", changed, gconf_key + "/dim_keyboard", gconf_client)
    
    message_text = widget_tree.get_object("MessageTextView")
    text_buffer = widget_tree.get_object("TextBuffer")
    text = gconf_client.get_string(gconf_key + "/message_text")
    if text == None:
        text = ""
    text_buffer.set_text(text)
    text_h = text_buffer.connect("changed", changed, gconf_key + "/message_text", gconf_client)
    
    dialog.run()
    dialog.hide()
    dim_keyboard.disconnect(dim_h)
    text_buffer.disconnect(text_h)
    
def changed(widget, key, gconf_client):
    if key.endswith("/dim_keyboard"):
        gconf_client.set_bool(key, widget.get_active())
    else:
        bounds = widget.get_bounds()
        gconf_client.set_string(key, widget.get_text(bounds[0],bounds[1]))
        pass
            
class G15ScreenSaver():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.session_bus = None
        self.in_screensaver = False
        self.page = None
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key  
    

    def activate(self):      
        self.controls = []
        self.control_values = []
        for control in self.screen.driver.get_controls():
            if control.hint & g15driver.HINT_DIMMABLE != 0 or  control.hint & g15driver.HINT_SHADEABLE != 0:
                self.controls.append(control)
                
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
        self.remove_page()
        self.activated = False
        
    def destroy(self):
        self.session_bus.remove_signal_receiver(self.screensaver_changed_handler, dbus_interface = "org.gnome.ScreenSaver", signal_name = "ActiveChanged")
        
    ''' Functions specific to plugin
    ''' 
    
    def remove_page(self):
        if self.page != None:
            self.screen.del_page(self.page)
            self.page = None
        
    def screensaver_changed_handler(self, value):
        if self.activated:
            self.in_screensaver = bool(value)
            if self.in_screensaver:
                self.page = self.screen.get_page("Screensaver")
                if self.page == None:
                    self.reload_theme()
                    self.page = self.screen.new_page(self.paint, g15screen.PRI_EXCLUSIVE, id="Screensaver")
                    self.screen.redraw(self.page)
                if self.gconf_client.get_bool(self.gconf_key + "/dim_keyboard"):
                    self.dim_keyboard()
            else:
                self.remove_page()
                if self.gconf_client.get_bool(self.gconf_key + "/dim_keyboard"):
                    self.light_keyboard()
        
    def dim_keyboard(self):
        self.control_values = []
        for c in self.controls:
            self.control_values.append(c.value)
            if c.hint & g15driver.HINT_DIMMABLE != 0:
                if isinstance(c.value,int):
                    c.value = 0
                else:
                    c.value = (0, 0, 0)
            else:
                if isinstance(c.value,int):
                    c.value = int(c.value * 0.1)
                else:
                    c.value = (c.value[0] * 0.1,c.value[1] * 0.1,c.value[2] * 0.1)
            self.screen.driver.update_control(c)
    
    def light_keyboard(self):
        i = 0
        for c in self.controls:
            c.value = self.control_values[i]
            i += 1
            self.screen.driver.update_control(c)
            
    def reload_theme(self):        
        text = self.gconf_client.get_string(self.gconf_key + "/message_text")
        variant = ""
        if text == None or text == "":
            variant = "nomessage"
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen, variant)
        
    def paint(self, canvas):
        
        properties = {}
        properties["title"] = "Workstation Locked"
        properties["message"] = self.gconf_client.get_string(self.gconf_key + "/message_text")
        properties["icon"] = g15util.get_icon_path("sleep", self.screen.height)
        
        self.theme.draw(canvas, properties)
