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
 
import gnome15.g15_globals as g15globals
import gnome15.g15_screen as g15screen
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import gnome15.g15_driver as g15driver
import gobject
import time
import dbus
import os
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

class G15DBusMenu(g15theme.Menu):
    def __init__(self):
        g15theme.Menu.__init__(self, "menu")
        
    def on_configure(self):
        g15theme.Menu.on_configure(self)
        self.child_entry_theme = g15theme.G15Theme(self.theme.dir, self.theme.screen, "menu-child-entry")
        self.separator_theme = g15theme.G15Theme(self.theme.dir, self.theme.screen, "menu-separator")
        
    def get_item_height(self, item, group = False):
        if item.get_type() == "separator":
            theme = self.separator_theme
        else:
            if group:
                theme = self.entry_theme
            else:
                theme = self.child_entry_theme
        return theme.bounds[3]
    
    def render_item(self, item, selected, canvas, properties, attributes, group = False):        
        item_properties = {}
        if selected == item:
            item_properties["item_selected"] = True
        item_properties["item_name"] = item.get_label() 
        item_properties["item_alt"] = item.get_right_side_text()
        item_properties["item_type"] = item.get_type()
        icon_name = item.get_icon_name()
        if icon_name != None:
            item_properties["item_icon"] = g15util.load_surface_from_file(g15util.get_icon_path(icon_name))
        else:
            item_properties["item_icon"] = item.get_icon()
            
        if item.get_type() == "separator":
            theme = self.separator_theme
        else:
            if group:
                theme = self.entry_theme
            else:
                theme = self.child_entry_theme
        theme.draw(canvas, item_properties)
        return theme.bounds[3]
        
class G15IndicatorMessages():
    
    def __init__(self, gconf_client, screen):
        self.screen = screen;
        self.hide_timer = None
        self.session_bus = None
        self.thumb_icon = None
        self.gconf_client = gconf_client
        self.session_bus = dbus.SessionBus()

    def activate(self):
        self._reload_theme()
        self.items = []
        self.attention = False
        self.selected = None
        self.messages_menu = messagesmenu.IndicatorMessagesMenu(self.session_bus)        
        self._load_items()
        self.page = self.screen.new_page(self._paint, priority=g15screen.PRI_NORMAL, id="Indicator Messages", panel_painter = self._paint_panel, thumbnail_painter = self._paint_thumbnail)
        self.messages_menu.on_change = self._menu_changed
        self.session_bus.add_signal_receiver(self._icon_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "IconChanged")
        self.session_bus.add_signal_receiver(self._attention_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "AttentionChanged")
        self.page.set_title(name)
    
    def deactivate(self):
        self.screen.del_page(self.page)
        self.session_bus.remove_signal_receiver(self._icon_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "IconChanged")
        self.session_bus.remove_signal_receiver(self._attention_changed, dbus_interface = "org.ayatana.indicator.messages.service", signal_name = "AttentionChanged")      
        
    def destroy(self):
        pass
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP:
            if self.screen.get_visible_page() == self.page:
                if g15driver.G_KEY_UP in keys or g15driver.G_KEY_L3 in keys:                    
                    i = 1 if self.selected == None or not self.selected in self.items else self.items.index(self.selected)
                    while True:
                        i -= 1
                        if i < 0:
                            i = 0
                            break
                        if self.items[i].get_type() != "separator":
                            break
                    self.selected = self.items[i] if i < len(self.items) else None
                    self.screen.applet.resched_cycle()
                    self.screen.redraw(self.page)
                    return True
                elif g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:                              
                    i = -1 if self.selected == None or not self.selected in self.items else self.items.index(self.selected)
                    while True:
                        i += 1
                        if i >= len(self.items):
                            i = len(self.items) - 1
                            break
                        if self.items[i].get_type() != "separator":
                            break
                    self.selected = self.items[i] if i < len(self.items) else None
                    self.screen.applet.resched_cycle()
                    self.screen.redraw(self.page)
                    return True           
                elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                    self.selected.activate()
                    self.screen.applet.resched_cycle()
                    return True                
                
        return False
        
    '''
    Messages Service callbacks
    '''
    def _icon_changed(self, new_icon):
        pass
        
    def _attention_changed(self, attention):
        self.attention = attention
        
        if self.attention == 1:
            if self.screen.driver.get_bpp() == 1:
                self.thumb_icon = g15util.load_surface_from_file(os.path.join(os.path.dirname(__file__), "mono-mail-new.gif"))
            else:
                self.thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path("indicator-messages-new"))
            self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 5.0)
        else:
            if self.screen.driver.get_bpp() == 1:
                self.thumb_icon = g15util.load_surface_from_file(os.path.join(os.path.dirname(__file__), "mono-mail-new.gif"))
            else:
                self.thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path("indicator-messages"))
            self.screen.redraw()
        
    '''
    Private
    ''' 
    def _menu_changed(self, menu = None, property = None, value = None):
        current_ids = []
        for item in self.items:
            current_ids.append(item.id)
            
        self._load_items()
        
        was_selected = self.selected
        
        # Scroll to item if it is newly visible
        if menu != None:
            if property != None and property == messagesmenu.VISIBLE and value and menu.get_type() != "separator":
                self.selected = menu
        else:
            # Layout change
            
            # See if the selected item is still there
            if self.selected != None:
                sel = self.selected
                self.selected = None
                for i in self.items:
                    if i.id == sel.id:
                        self.selected = i
            
            # See if there are new items, make them selected
            for item in self.items:
                if not item.id in current_ids:
                    self.selected = item
                    break
                
        # Fire DBUS event if 
                
        self.screen.redraw(self.page)
        
    def _load_items(self):
        self.items = []
        for item in self.messages_menu.root_item.children:
            if item.is_visible():
                self.items.append(item)
        
    def _popup(self):    
        self.screen.set_priority(self.screen.get_page("Indicator Messages"), g15screen.PRI_HIGH, revert_after = 3.0)
        self.screen.redraw(self.page)
    
    def _reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), self.screen, "menu-screen")
        self.menu = G15DBusMenu()
        self.theme.add_component(self.menu)
        self.theme.add_component(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self.page != None:
            if self.thumb_icon != None:
                return g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)
                return size
    
    def _paint_panel(self, canvas, allocated_size, horizontal):
        if self.page != None:
            if self.thumb_icon != None and self.attention == 1:
                return g15util.paint_thumbnail_image(allocated_size, self.thumb_icon, canvas)

    def _paint(self, canvas):  
        self.menu.items = self.items
        self.menu.selected = self.selected
        self.theme.draw(canvas, 
                        properties = {
                                      "title" : "Messages",
                                      "icon" : g15util.get_icon_path("indicator-messages-new" if self.attention else "indicator-messages"),
                                      "attention": self.attention
                                      }, 
                        attributes = {
                                      "items" : self.items,
                                      "selected" : self.selected
                                      })  
