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
 
import gnome15.g15screen as g15screen
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
from threading import Timer
import gtk
import dbus
import logging
import os.path
logger = logging.getLogger("screensaver")

# Plugin details - All of these must be provided
id="screensaver"
name="Screensaver"
description="Dim the keyboard and display a message (on models with an LCD screen) when the desktop screen saver activates."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=True


''' 
This plugin displays a high priority screen when the screensaver activates
'''

def create(gconf_key, gconf_client, screen):
    return G15ScreenSaver(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "screensaver.glade"))
    
    dialog = widget_tree.get_object("ScreenSaverDialog")
    dialog.set_transient_for(parent)
    
    dim_keyboard = widget_tree.get_object("DimKeyboardCheckbox")
    dim_keyboard.set_active(gconf_client.get_bool(gconf_key + "/dim_keyboard"))
    dim_h = dim_keyboard.connect("toggled", changed, gconf_key + "/dim_keyboard", gconf_client)
    
    if driver.get_bpp() == 0:
        widget_tree.get_object("MessageFrame").hide()
        
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
        self._screen = screen
        self._session_bus = None
        self._in_screensaver = False
        self._page = None
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self.dimmed = False

    def activate(self):      
        self._controls = []
        self._control_values  = []
        for control in self._screen.driver.get_controls():
            if control.hint & g15driver.HINT_DIMMABLE != 0 or  control.hint & g15driver.HINT_SHADEABLE != 0:
                self._controls.append(control)
        self._dbus_name = "org.gnome.ScreenSaver"
        self._dbus_interface = "org.gnome.ScreenSaver"
                
        if self._session_bus == None:
            
            try:
                self._session_bus = dbus.SessionBus()
            except Exception as e:
                self._session_bus = None
                logger.error("Error. %s retrying in 10 seconds" % str(e) ) 
                Timer(10, self.activate, ()).start()
                return
            
        
            try :
                screen_saver = dbus.Interface(self._session_bus.get_object(self._dbus_name, '/'), self._dbus_interface)
            except Exception as e:
                self._dbus_name = "org.kde.screensaver"
                self._dbus_interface = "org.freedesktop.ScreenSaver"
                screen_saver = dbus.Interface(self._session_bus.get_object(self._dbus_name, '/ScreenSaver'), self._dbus_interface)
                
            self._session_bus.add_signal_receiver(self._screensaver_changed_handler, dbus_interface = self._dbus_interface, signal_name = "ActiveChanged")
            
        self._in_screensaver = screen_saver.GetActive()
        self._activated = True
        self._check_page()
    
    def deactivate(self):
        if self._in_screensaver:
            if self._gconf_client.get_bool(self._gconf_key + "/dim_keyboard"):
                self._light_keyboard()
        self._remove_page()
        self._activated = False
        
    def destroy(self):
        if self._session_bus:
            self._session_bus.remove_signal_receiver(self._screensaver_changed_handler, dbus_interface = self._dbus_interface, signal_name = "ActiveChanged")
        
    def handle_key(self, keys, state, post):
        # Sinks all keyboard events when the page is active
        return self._page is not None
        
    ''' Functions specific to plugin
    ''' 
    
    def _remove_page(self):
        if self._page != None:
            self._screen.del_page(self._page)
            self._page = None
            
    def _check_page(self):
        if self._in_screensaver:
            if self._screen.driver.get_bpp() != 0 and self._page == None:
                self._reload_theme()
                self._page = g15theme.G15Page(id, self._screen, priority = g15screen.PRI_EXCLUSIVE, \
                                              title = name, theme = self._theme,
                                              theme_properties_callback = self._get_theme_properties)
                self._page.key_handlers.append(self)
                self._screen.add_page(self._page)
                self._screen.redraw(self._page)
            if not self.dimmed and self._gconf_client.get_bool(self._gconf_key + "/dim_keyboard"):
                self._dim_keyboard()
        else:
            if self._screen.driver.get_bpp() != 0:
                self._remove_page()
            if self.dimmed and self._gconf_client.get_bool(self._gconf_key + "/dim_keyboard"):
                self._light_keyboard()
        
    def _screensaver_changed_handler(self, value):
        if self._activated:
            self._in_screensaver = bool(value)
            self._check_page()
        
    def _dim_keyboard(self):
        self._control_values  = []
        for c in self._controls:
            self._control_values .append(c.value)
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
            self._screen.driver.update_control(c)
        self.dimmed = True
    
    def _light_keyboard(self):
        i = 0
        for c in self._controls:
            c.value = self._control_values [i]
            i += 1
            self._screen.driver.update_control(c)
        self.dimmed = False
            
    def _reload_theme(self):        
        text = self._gconf_client.get_string(self._gconf_key + "/message_text")
        variant = ""
        if text == None or text == "":
            variant = "nobody"
        self._theme = g15theme.G15Theme(self, variant)
        
    def _get_theme_properties(self):
        
        properties = {}
        properties["title"] = "Workstation Locked"
        properties["body"] = self._gconf_client.get_string(self._gconf_key + "/message_text")
        properties["icon"] = g15util.get_icon_path("sleep", self._screen.height)
        
        return properties
