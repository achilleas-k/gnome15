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
description="Indicator showing user information and status"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=False

''' This simple plugin displays user information and status
'''

def create(gconf_key, gconf_client, screen):
    return G15IndicatorMe(gconf_client, screen)
            
class G15IndicatorMe():
    
    def __init__(self, gconf_client, screen):
        self.screen = screen;
        self.timer = None
        self.session_bus = None
        self.canvas = None
        self.gconf_client = gconf_client
        self.session_bus = dbus.SessionBus()

    def activate(self):
        self.canvas= self.screen.new_canvas(id="Indicator Me")
        self.me_service = self.session_bus.get_object('org.ayatana.indicator.me', '/org/ayatana/indicator/me/service')
        self.session_bus.add_signal_receiver(self.status_icon_changed, dbus_interface = "org.ayatana.indicator.me.service", signal_name = "StatusIconsChanged")
        self.session_bus.add_signal_receiver(self.user_changed, dbus_interface = "org.ayatana.indicator.me.service", signal_name = "UserChanged")        
        self.redraw()
    
    def deactivate(self):
        self.screen.del_canvas(self.canvas)
        self.canvas = None
        self.session_bus.remove_signal_receiver(self.status_icon_changed, dbus_interface = "org.ayatana.indicator.me.service", signal_name = "StatusIconsChanged")
        self.session_bus.remove_signal_receiver(self.user_changed, dbus_interface = "org.ayatana.indicator.me.service", signal_name = "UserChanged")      
        
    def destroy(self):
        pass
        
    ''' Functions specific to plugin
    ''' 
    
    def status_icon_changed(self, new_icon):
        self.redraw()
        
    def user_changed(self, new_icon):
        self.redraw()
        
    def redraw(self):
        if self.timer != None:
            self.timer.cancel()        
        icon_theme = self.gconf_client.get_string("/desktop/gnome/interface/icon_theme")        
        self.canvas.clear()
        icon = self.me_service.StatusIcons()
        real_icon_file = icons.getIconPath(icon, theme=icon_theme, size = 32)
        if real_icon_file != None:
            if real_icon_file.endswith(".svg"):
                pixbuf = gtk.gdk.pixbuf_new_from_file(real_icon_file)
                image = Image.fromstring("RGBA", (pixbuf.get_width(), pixbuf.get_height()), pixbuf.get_pixels())  
                self.canvas.draw_image(image, (0, g15draw.CENTER), (40, 40), mask=True)
            else:              
                self.canvas.draw_image_from_file(real_icon_file, (0, g15draw.CENTER), (40, 40))
        text = "Unknown"
        if icon == "user-available-panel":
            text = "Available"
        elif icon == "user-away-panel":
            text = "Away"
        elif icon == "user-busy-panel":
            text = "Busy"
        elif icon == "user-offline-panel":
            text = "Offline"
        elif icon == "user-invisible-panel":
            text = "Invisible"
        self.canvas.set_font_size(g15draw.FONT_MEDIUM)
        self.canvas.draw_text(text, (48, 2), emboss="White")
        self.canvas.set_font_size(g15draw.FONT_SMALL)
        self.canvas.draw_text(self.me_service.PrettyUserName(), (48, 22), emboss="White")
        self.screen.set_priority(self.canvas, g15screen.PRI_HIGH)
        self.timer = Timer(3, self.lower, ())
        self.timer.name = "IndicatorHideTimer"
        self.timer.setDaemon(True)
        self.timer.start()
        
    def lower(self):
        self.screen.set_priority(self.canvas, g15screen.PRI_NORMAL)
        