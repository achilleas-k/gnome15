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
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import time
import dbus
import os
import xdg.Config as config
import gtk
import Image
import gobject
import gnome15.dbusmenu as dbusmenu
from threading import Timer
from dbus.exceptions import DBusException

import logging
logger = logging.getLogger("indicator-me")

# Plugin details - All of these must be provided
id="indicator-me"
name="Indicator Me"
description="Indicator that shows user information and status."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110 ]

''' This simple plugin displays user information and status
'''

def create(gconf_key, gconf_client, screen):
    return G15IndicatorMe(gconf_client, screen)
        
            
STATUS_ICONS = { "user-available-panel" : "Available", 
                 "user-away-panel" : "Away", 
                 "user-busy-panel" : "Busy", 
                 "user-offline-panel" : "Offline", 
                 "user-invisible-panel" : "Invisible",
                 "user-indeterminate" : "Invisible" }
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


class IndicatorMeMenuEntry(dbusmenu.DBUSMenuEntry):
    def __init__(self, id, properties, menu):
        dbusmenu.DBUSMenuEntry.__init__(self, id, properties, menu)
        
    def set_properties(self, properties):
        print "props: %s" % str(properties)
        dbusmenu.DBUSMenuEntry.set_properties(self, properties)        
        if self.type == TYPE_INDICATOR_ITEM and INDICATOR_LABEL in self.properties:
            self.label = self.properties[INDICATOR_LABEL]
        if self.type == TYPE_INDICATOR_ITEM:
            self.icon = self.properties[INDICATOR_ICON] if INDICATOR_ICON in self.properties else None
        
    def get_alt_label(self):
        return self.properties[RIGHT_SIDE_TEXT] if RIGHT_SIDE_TEXT in self.properties else None
        
    def is_app_running(self):
        return APP_RUNNING in self.properties and self.properties[APP_RUNNING]

class IndicatorMeMenu(dbusmenu.DBUSMenu):
    
    def __init__(self, session_bus, on_change = None):
        try:
            dbusmenu.DBUSMenu.__init__(self, session_bus, "org.ayatana.indicator.me", "/org/ayatana/indicator/me/menu", "org.ayatana.dbusmenu", on_change, False)
        except dbus.DBusException as dbe:
            dbusmenu.DBUSMenu.__init__(self, session_bus, "com.canonical.indicator.me", "/com/canonical/indicator/me/menu", "com.canonical.dbusmenu", on_change, True)

    def create_entry(self, id, properties):
        return IndicatorMeMenuEntry(id, properties, self)
            
class G15IndicatorMe():
    
    def __init__(self, gconf_client, screen):
        self._screen = screen;
        self._hide_timer = None
        self._session_bus = None
        self._me_service = None
        self._gconf_client = gconf_client
        self._session_bus = dbus.SessionBus()
        self._menu = None

    def activate(self):
        self._icon = "user-offline-panel"
        self._natty = False
        self._menu_page = None
        try :
            me_object = self._session_bus.get_object('com.canonical.indicator.me', '/com/canonical/indicator/me/service')
            self._me_service = dbus.Interface(me_object, 'com.canonical.indicator.me.service')
            self._natty = True
        except DBusException as dbe:
            me_object = self._session_bus.get_object('org.ayatana.indicator.me', '/org/ayatana/indicator/me/service')
            self._me_service = dbus.Interface(me_object, 'org.ayatana.indicator.me.service')
            
        self._me_menu = IndicatorMeMenu(self._session_bus)
        
        self._status_changed_handle = self._me_service.connect_to_signal("StatusIconsChanged", self._status_icon_changed)
        self._user_changed_handle = self._me_service.connect_to_signal("UserChanged", self._user_changed)

        self._reload_theme()
        self._get_details()
        self._create_pages()
    
    def deactivate(self):
        self._session_bus.remove_signal_receiver(self._status_changed_handle)
        self._session_bus.remove_signal_receiver(self._user_changed_handle)
        if self._menu_page != None and self._screen.pages.contains(self._menu_page):
            self._screen.del_page(self._menu_page)
        if self._popup_page != None and self._screen.pages.contains(self._popup_page):
            self._screen.del_page(self._popup_page)
        
    def destroy(self):
        pass
    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_DOWN:              
            if self._screen.get_visible_page() == self._menu_page:    
                if self._menu.handle_key(keys, state, post):
                    return True           
                elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                    self._menu.selected.dbus_menu_entry.activate()
                    self._screen.service.resched_cycle()
                    return True
                
        return False
        
    '''
    Private
    '''     
    def _create_pages(self):  
        self._menu_page = self._screen.new_page(self._paint_menu, id=name, priority = g15screen.PRI_NORMAL, on_shown = self._on_menu_page_show)
        self._menu_page.set_title(self._get_status_text())
        self._screen.redraw(self._menu_page)
        self._popup_page = self._screen.new_page(self._paint_popup, priority=g15screen.PRI_INVISIBLE, id="Indicator Me", panel_painter = self._paint_popup_thumbnail)
        
    def _on_menu_page_show(self):
        for item in self._menu.get_items():
            if isinstance(item, g15theme.DBusMenuItem) and self._icon == item.dbus_menu_entry.get_icon_name():
                self._menu.selected = item
                self._screen.redraw(self._menu_page)
    
    def _status_icon_changed(self, new_icon):
        self._popup()
        
    def _user_changed(self, new_icon):
        self._popup()
            
    def _menu_changed(self, menu = None, property = None, value = None):
        self._get_details()
        self._menu.menu_changed(menu, property, value)
        
    def _popup(self):    
        print "Popup!"
        self._get_details()
        self._screen.set_priority(self._popup_page, g15screen.PRI_HIGH, revert_after = 3.0)
        self._screen.redraw(self._popup_page)
        
    def _get_details(self):
        self._icon = self._me_service.StatusIcons()
        self._icon_image = g15util.load_surface_from_file(g15util.get_icon_path(self._icon))
        self._username = self._me_service.PrettyUserName()
        if self._menu_page != None:
            self._menu_page.set_title(self._get_status_text())
            
    def _get_status_text(self):
        return "Status - %s" % STATUS_ICONS[self._icon]
        
    def _reload_theme(self):       
        
        # Create the menu
        self._menu = g15theme.DBusMenu(self._screen, self._me_menu)
        self._menu.on_selected = self._redraw_menu
        self._me_menu.on_change = self._menu_changed
        
        # Setup the theme
        self._menu_theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self._screen, "menu-screen") 
        self._popup_theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self._screen)
        self._menu_theme.add_component(self._menu)
        self._menu_theme.add_component(g15theme.Scrollbar("viewScrollbar", self._menu.get_scroll_values))
        
    def _redraw_menu(self):
        self._screen.redraw(self._menu_page)
    
    def _paint_popup_thumbnail(self, canvas, allocated_size, horizontal):
        if self._popup_page != None:
            if self._icon_image != None and self._screen.driver.get_bpp() != 1:
                return g15util.paint_thumbnail_image(allocated_size, self._icon_image, canvas)
            
    def _paint_menu(self, canvas):
        props = { "icon" :  g15util.get_icon_path(self._icon),
                 "title" : "Status",
                 "status": STATUS_ICONS[self._icon] }
        
        # Draw the page
        self._menu_theme.draw(canvas, props, 
                        attributes = {
                                      "items" : self._menu.get_items(),
                                      "selected" : self._menu.selected
                                      })

    def _paint_popup(self, canvas):     
        properties = { "icon" : g15util.get_icon_path(self._icon, self._screen.width) }
        properties["text"] = "Unknown"
        if self._icon in STATUS_ICONS:
            properties["text"] = STATUS_ICONS[self._icon]
        else:
            logger.warning("Unknown status icon %s" % self._icon)
        self._popup_theme.draw(canvas, properties)