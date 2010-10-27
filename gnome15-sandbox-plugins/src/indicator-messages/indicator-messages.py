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
import gnome15.g15_driver as g15driver
import time
import dbus
import os
import xdg.IconTheme as icons
import xdg.Config as config
import gtk
import Image
import indicator_messages_menu as messagesmenu

from lxml import etree

# Plugin details - All of these must be provided
id="indicator-messages"
name="Indicator Messages"
description="Indicator that shows waiting messages."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False

def create(gconf_key, gconf_client, screen):
    return G15IndicatorMessages(gconf_client, screen)


class G15IndicatorMessages():
    
    def __init__(self, gconf_client, screen):
        self.screen = screen;
        self.hide_timer = None
        self.session_bus = None
        self.gconf_client = gconf_client
        self.session_bus = dbus.SessionBus()

    def activate(self):
        self._reload_theme()
        self.selected = None
        self.messages_menu = messagesmenu.IndicatorMessagesMenu(self.session_bus)        
        self._load_items()
        self.page = self.screen.new_page(self._paint, priority=g15screen.PRI_NORMAL, id="Indicator Messages", panel_painter = self._paint_thumbnail)
        self.messages_menu.on_change = self._menu_changed
        self.session_bus.add_signal_receiver(self._icon_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "IconChanged")
        self.session_bus.add_signal_receiver(self._attention_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "AttentionChanged")   
    
    def deactivate(self):
        self.screen.del_page(self.page)
        self.session_bus.remove_signal_receiver(self._icon_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "IconChanged")
        self.session_bus.remove_signal_receiver(self._attention_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "AttentionChanged")      
        
    def destroy(self):
        pass
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP:
            if self.screen.get_visible_page() == self.page:
                # TODO this is the 3rd use of menus in gnome15 - need to create a re-usable component for them (see menu and rss)
                if g15driver.G_KEY_UP in keys or g15driver.G_KEY_L3 in keys:                    
                    i = 1 if self.selected == None else self.items.index(self.selected)
                    i -= 1
                    if i < 0:
                        i = len(self.items) - 1
                    self.selected = self.items[i]
                    self.screen.applet.resched_cycle()
                    self.screen.redraw(self.page)
                    return True
                elif g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:                    
                    i = -1 if self.selected == None else self.items.index(self.selected)
                    i += 1
                    if i >= len(self.items):
                        i = 0
                    self.selected = self.items[i]
                    self.screen.applet.resched_cycle()
                    self.screen.redraw(self.page)
                    return True           
                elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                    print "Selected ",self.selected.page.id
                    self.screen.raise_page(self.selected.page)
                    self.screen.applet.resched_cycle()
                    self._hide_menu()
                    return True                
                
        return False
        
    '''
    Messages Service callbacks
    '''
    def _icon_changed(self, new_icon):
        print "Icon changed"
        
    def _attention_changed(self, new_icon):
        print "Attention changed"
       
        
    '''
    Private
    ''' 
    def _menu_changed(self):
        self._load_items()
        self.screen.redraw(self.page)
        
    def _load_items(self):
        self.items = []
        for item in self.messages_menu.root_item.flatten():
            if item.is_visible():
                self.items.append(item)
        
    def _popup(self):    
        self.screen.set_priority(self.screen.get_page("Indicator Messages"), g15screen.PRI_HIGH, revert_after = 3.0)
        self.screen.redraw(page)
    
    def _reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        pass

    def _paint(self, canvas):  
        self.theme.draw(canvas, 
                        properties = {
                                      "title" : "Messages",
                                      "icon" : g15util.get_icon_path(self.gconf_client, "indicator-messages")
                                      }, 
                        attributes = {
                                      "items" : self.items,
                                      "selected" : self.selected
                                      })
        