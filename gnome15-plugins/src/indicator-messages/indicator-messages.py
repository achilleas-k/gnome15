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
 
import gnome15.g15globals as g15globals
import gnome15.g15screen as g15screen
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gobject
import time
import dbus
import os
import gtk
import Image
import gnome15.dbusmenu as dbusmenu

from lxml import etree

# Plugin details - All of these must be provided
id="indicator-messages"
name="Indicator Messages"
description="Indicator that shows waiting messages."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]

def create(gconf_key, gconf_client, screen):
    return G15IndicatorMessages(gconf_client, screen)

'''
Indicator Messages  DBUSMenu property names
'''

APP_RUNNING = "app-running"
INDICATOR_LABEL = "indicator-label"
INDICATOR_ICON = "indicator-icon"
RIGHT_SIDE_TEXT = "right-side-text"

'''
Indicator Messages DBUSMenu types
'''
TYPE_APPLICATION_ITEM = "application-item"
TYPE_INDICATOR_ITEM = "indicator-item"


class IndicatorMessagesMenuEntry(dbusmenu.DBUSMenuEntry):
    def __init__(self, id, properties, menu):
        dbusmenu.DBUSMenuEntry.__init__(self, id, properties, menu)
        
    def set_properties(self, properties):
        dbusmenu.DBUSMenuEntry.set_properties(self, properties)        
        if self.type == TYPE_INDICATOR_ITEM and INDICATOR_LABEL in self.properties:
            self.label = self.properties[INDICATOR_LABEL]
        if self.type == TYPE_INDICATOR_ITEM:
            self.icon = self.properties[INDICATOR_ICON] if INDICATOR_ICON in self.properties else None
        
    def get_alt_label(self):
        return self.properties[RIGHT_SIDE_TEXT] if RIGHT_SIDE_TEXT in self.properties else None
        
    def is_app_running(self):
        return APP_RUNNING in self.properties and self.properties[APP_RUNNING]

class IndicatorMessagesMenu(dbusmenu.DBUSMenu):
    
    
    def __init__(self, session_bus, on_change = None):
        try:
            dbusmenu.DBUSMenu.__init__(self, session_bus, "org.ayatana.indicator.messages", "/org/ayatana/indicator/messages/menu", "org.ayatana.dbusmenu", on_change, False)
        except dbus.DBusException as dbe:
            dbusmenu.DBUSMenu.__init__(self, session_bus, "com.canonical.indicator.messages", "/com/canonical/indicator/messages/menu", "com.canonical.dbusmenu", on_change, True)

    def create_entry(self, id, properties):
        return IndicatorMessagesMenuEntry(id, properties, self)

class G15IndicatorMessages():
    
    def __init__(self, gconf_client, screen):
        self._screen = screen;
        self._hide_timer = None
        self._session_bus = None
        self._thumb_icon = None
        self._gconf_client = gconf_client
        self._session_bus = dbus.SessionBus()

    def activate(self):
        self._messages_menu = IndicatorMessagesMenu(self._session_bus)  
        self._reload_theme()
        self._raise_timer = None
        self._attention = False
        self._page = self._screen.new_page(self._paint, priority=g15screen.PRI_NORMAL, id="Indicator Messages", panel_painter = self._paint_panel, thumbnail_painter = self._paint_thumbnail)
        
        if self._messages_menu.natty:
            self._session_bus.add_signal_receiver(self._icon_changed, dbus_interface = "com.canonical.indicator.messages.service", signal_name = "IconChanged")
            self._session_bus.add_signal_receiver(self._attention_changed, dbus_interface = "com.canonical.indicator.messages.service", signal_name = "AttentionChanged")
        else:
            self._session_bus.add_signal_receiver(self._icon_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "IconChanged")
            self._session_bus.add_signal_receiver(self._attention_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "AttentionChanged")
            
        self._page.set_title(name)
        self._screen.redraw(self._page)
    
    def deactivate(self):
        self._screen.del_page(self._page)
        if self._messages_menu.natty:
            self._session_bus.remove_signal_receiver(self._icon_changed, dbus_interface = "com.canonical.indicator.messages.service", signal_name = "IconChanged")
            self._session_bus.remove_signal_receiver(self._attention_changed, dbus_interface = "com.canonical.indicator.messages.service", signal_name = "AttentionChanged")
        else:
            self._session_bus.remove_signal_receiver(self._icon_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "IconChanged")
            self._session_bus.remove_signal_receiver(self._attention_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "AttentionChanged")      
        
    def destroy(self):
        pass
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_DOWN:              
            if self._screen.get_visible_page() == self._page:    
                if self._menu.handle_key(keys, state, post):
                    return True           
                elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                    self._menu.selected.dbus_menu_entry.activate()
                    return True
                
        return False
        
    '''
    Messages Service callbacks
    '''
    def _icon_changed(self, new_icon):
        pass
        
    def _attention_changed(self, attention):
        self._attention = attention
        if self._attention == 1:
            if self._screen.driver.get_bpp() == 1:
                self._thumb_icon = g15util.load_surface_from_file(os.path.join(os.path.dirname(__file__), "mono-mail-new.gif"))
            else:
                self._thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path("indicator-messages-new")) 
            self._popup()
        else:
            if self._screen.driver.get_bpp() == 1:
                self._thumb_icon = g15util.load_surface_from_file(os.path.join(os.path.dirname(__file__), "mono-mail-new.gif"))
            else:
                self._thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path("indicator-messages"))
            self._screen.redraw()
            
    def _menu_changed(self, menu = None, property = None, value = None):
        self._menu.menu_changed(menu, property, value)
        self._popup()
        
    '''
    Private
    ''' 
        
    def _popup(self):    
        if not self._page.is_visible():
            self._raise_timer = self._screen.set_priority(self._screen.get_page("Indicator Messages"), g15screen.PRI_HIGH, revert_after = 4.0)
            self._screen.redraw(self._page)
        else:
            self._reset_raise()
    
    def _reset_raise(self):
        '''
        Reset the timer if the page is already visible because of a timer
        '''
        if self._screen.is_on_timer(self._page):
            self._raise_timer = self._screen.set_priority(self._screen.get_page("Indicator Messages"), g15screen.PRI_HIGH, revert_after = 4.0)
        self._screen.redraw(self._page)
    
    def _reload_theme(self):        
        self._theme = g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), self._screen, "menu-screen")
        self._menu = g15theme.DBusMenu(self._screen, self._messages_menu)
        self._messages_menu.on_change = self._menu_changed
        self._menu.on_selected = self._on_selected
        self._theme.add_component(self._menu)
        self._theme.add_component(g15theme.Scrollbar("viewScrollbar", self._menu.get_scroll_values))
        
    def _on_selected(self):
        self._screen.redraw(self._page)
        
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._page != None:
            if self._thumb_icon != None:
                return g15util.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)
    
    def _paint_panel(self, canvas, allocated_size, horizontal):
        if self._page != None:
            if self._thumb_icon != None and self._attention == 1:
                return g15util.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)

    def _paint(self, canvas):  
        self._theme.draw(canvas, 
                        properties = {
                                      "title" : "Messages",
                                      "icon" : g15util.get_icon_path("indicator-messages-new" if self._attention else "indicator-messages"),
                                      "attention": self._attention
                                      }, 
                        attributes = {
                                      "items" : self._menu.get_items(),
                                      "selected" : self._menu.selected
                                      })  
