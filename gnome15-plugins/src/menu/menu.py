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
 
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15screen as g15screen
import gnome15.g15plugin as g15plugin
import sys
import cairo
import traceback
import base64
from cStringIO import StringIO
import logging
logger = logging.getLogger("menu")

# Plugin details - All of these must be provided
id="menu"
name="Menu"
description="Allows selections of any currently active screen " + \
            "through a menu on the LCD. It is activated by the " + \
            "<b>Menu</b> key on the G19, or L2 on other models. " + \
            "Once activated, use the D-pad on the G19 " + \
            "or L3-L5 on the the G15 to navigate and select."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_Z10, g15driver.MODEL_G11 ]
reserved_keys = [ g15driver.G_KEY_MENU, g15driver.G_KEY_L2 ]

def create(gconf_key, gconf_client, screen):
    return G15Menu(gconf_client, gconf_key, screen)

class MenuItem(g15theme.MenuItem):
    
    
    def __init__(self, item_page, plugin, id):
        g15theme.MenuItem.__init__(self, id)
        self._item_page = item_page
        self.thumbnail = None
        self.plugin = plugin
        
    def activate(self):
        self.theme.screen.raise_page(self.plugin.menu.selected._item_page)
        self.theme.screen.resched_cycle()
        self.plugin.hide_menu()
        
    def get_theme_properties(self):        
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self._item_page.title 
        item_properties["item_alt"] = ""
        item_properties["item_type"] = ""
        item_properties["item_icon"] = self.thumbnail
        return item_properties

class G15Menu(g15plugin.G15MenuPlugin):
    
    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, [ "gnome-main-menu" ], id, name)
    
    def activate(self):
        self.page = None   
        self.delete_timer = None     
        self.reload_theme()
        self.listener = MenuScreenChangeListener(self)
        self.screen.add_screen_change_listener(self.listener)
        self.screen.action_listeners.append(self)
        
    def deactivate(self): 
        g15plugin.G15MenuPlugin.deactivate(self)
        self.screen.action_listeners.remove(self)
        self.screen.remove_screen_change_listener(self.listener)
        
    def action_performed(self, binding):
        if self.page is not None:
            self._reset_delete_timer()
        if binding.action == g15driver.MENU:
            if self.page is not None:
                self.hide_menu()
            else:
                self.show_menu()
                self.page.set_priority(g15screen.PRI_HIGH)
                
    def hide_menu(self):
        g15plugin.G15MenuPlugin.hide_menu(self)   
                
    def show_menu(self):
        g15plugin.G15MenuPlugin.show_menu(self)
        self._reset_delete_timer()   
        
    def load_menu_items(self):
        self.menu.remove_all_children()
        i = 0
        for page in self.screen.pages:
            if page != self.page and page.priority > g15screen.PRI_INVISIBLE:
                self.menu.add_child(MenuItem(page, self, "menuitem-%d" % i))
                i += 1
        items = self.menu.get_children()
        if len(items) > 0:
            self.menu.selected = items[0]
        else:
            self.menu.selected = None
               
        for item in items:
            if item._item_page.thumbnail_painter != None:
                img = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.screen.height, self.screen.height)
                thumb_canvas = cairo.Context(img)
                try :
                    if item._item_page.thumbnail_painter(thumb_canvas, self.screen.height, True):
                        img_data = StringIO()
                        img.write_to_png(img_data)
                        item.thumbnail = base64.b64encode(img_data.getvalue())                    
                        
                except :
                    logger.warning("Problem with painting thumbnail in %s" % item._item_page.id)                   
                    traceback.print_exc(file=sys.stderr)
        
    '''
    Private
    '''
    def _reset_delete_timer(self):
        if self.delete_timer:
            self.delete_timer.cancel()        
        self.delete_timer = self.screen.delete_after(10.0, self.page)
                    
    def _reload_menu(self):
        self.load_menu_items()
        self.screen.redraw(self.page)
        
class MenuScreenChangeListener(g15screen.ScreenChangeAdapter):
    def __init__(self, plugin):
        self.plugin = plugin
        
    def new_page(self, page):
        if self.plugin.page != None:
            self.plugin._reload_menu()
        
    def title_changed(self, page, title):
        if self.plugin.page != None:
            self.plugin._reload_menu()
    
    def del_page(self, page):
        if self.plugin.page != None:
            self.plugin._reload_menu()