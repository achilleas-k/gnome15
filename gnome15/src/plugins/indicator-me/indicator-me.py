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
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import time
import dbus
import os
import xdg.IconTheme as icons
import xdg.Config as config
import gtk
import Image
from threading import Timer

# Plugin details - All of these must be provided
id="indicator-me"
name="Indicator Me"
description="Indicator that shows user information and status."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False

''' This simple plugin displays user information and status
'''

def create(gconf_key, gconf_client, screen):
    return G15IndicatorMe(gconf_client, screen)
            
class G15IndicatorMe():
    
    def __init__(self, gconf_client, screen):
        self.screen = screen;
        self.hide_timer = None
        self.session_bus = None
        self.gconf_client = gconf_client
        self.session_bus = dbus.SessionBus()

    def activate(self):
        self.me_service = self.session_bus.get_object('org.ayatana.indicator.me', '/org/ayatana/indicator/me/service')
        self.session_bus.add_signal_receiver(self._status_icon_changed, dbus_interface = "org.ayatana.indicator.me.service", signal_name = "StatusIconsChanged")
        self.session_bus.add_signal_receiver(self._user_changed, dbus_interface = "org.ayatana.indicator.me.service", signal_name = "UserChanged")
        self._reload_theme()
        self._get_details()     
        self.page = self.screen.new_page(self._paint, priority=g15screen.PRI_INVISIBLE, id="Indicator Me", panel_painter = self._paint_thumbnail)   
    
    def deactivate(self):
        self.session_bus.remove_signal_receiver(self._status_icon_changed, dbus_interface = "org.ayatana.indicator.me.service", signal_name = "StatusIconsChanged")
        self.session_bus.remove_signal_receiver(self._user_changed, dbus_interface = "org.ayatana.indicator.me.service", signal_name = "UserChanged")      
        
    def destroy(self):
        pass
        
    '''
    Private
    '''
    
    def _status_icon_changed(self, new_icon):
        self._popup()
        
    def _user_changed(self, new_icon):
        self._popup()
        
    def _popup(self):    
        page = self.screen.get_page("Indicator Me")
        self._get_details()
        self.screen.set_priority(page, g15screen.PRI_HIGH, revert_after = 3.0)
        self.screen.redraw(page)
        
    def _get_details(self):
        self.icon = self.me_service.StatusIcons()
        self.icon_image = g15util.load_surface_from_file(g15util.get_icon_path(self.icon))
        self.username = self.me_service.PrettyUserName()
        
    def _reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None:
            if self.icon_image != None:
                return g15util.paint_thumbnail_image(allocated_size, self.icon_image, canvas)

    def _paint(self, canvas):     
        properties = { "icon" : g15util.get_icon_path(self.icon, self.screen.width) }
        properties["text"] = "Unknown"
        if self.icon == "user-available-panel":
            properties["text"] = "Available"
        elif self.icon == "user-away-panel":
            properties["text"] = "Away"
        elif self.icon == "user-busy-panel":
            properties["text"] = "Busy"
        elif self.icon == "user-offline-panel":
            properties["text"] = "Offline"
        elif self.icon == "user-invisible-panel":
            properties["text"] = "Invisible"
            
        self.theme.draw(canvas, properties)