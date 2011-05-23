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
 
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import gnome15.g15_driver as g15driver
import gnome15.g15_screen as g15screen
import gnome15.g15_globals as g15globals
import os
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
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_Z10 ]
reserved_keys = [ g15driver.G_KEY_MENU, g15driver.G_KEY_L2 ]

def create(gconf_key, gconf_client, screen):
    return G15Menu(gconf_client, gconf_key, screen)

class MenuItem():
    
    def __init__(self, page):
        self.page = page
        self.thumbnail = None
        
class G15ScreensMenu(g15theme.Menu):
    def __init__(self, screen):
        g15theme.Menu.__init__(self, "menu", screen)
        
    def render_item(self, item, selected, canvas, properties, attributes, group = False):        
        item_properties = {}
        if selected == item:
            item_properties["item_selected"] = True
        item_properties["item_name"] = item.page.title 
        item_properties["item_alt"] = ""
        item_properties["item_type"] = ""
        item_properties["item_icon"] = item.thumbnail
        self.entry_theme.draw(canvas, item_properties)
        return self.entry_theme.bounds[3]

class G15Menu():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        self._reload_theme()
        self.timer = None
        self.page = None
        self.screen.redraw(self.page)
    
    def deactivate(self):
        if self.page != None:
            self._hide_menu()
        
    def destroy(self):
        pass
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_DOWN:

            if self.page == None:            
                if g15driver.G_KEY_MENU in keys or g15driver.G_KEY_L2 in keys:
                    self._show_menu()
                    return True
            else:                            
                if self.screen.get_visible_page() == self.page:                    
                    if g15driver.G_KEY_MENU in keys or g15driver.G_KEY_L2 in keys:
                        self._hide_menu()
                        self.screen.service.resched_cycle()
                        return True
                    elif self.menu.handle_key(keys, state, post):
                        return True           
                    elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                        self.screen.raise_page(self.menu.selected.page)
                        self.screen.service.resched_cycle()
                        self._hide_menu()
                        return True                
                
        return False
    
    def paint(self, canvas):
        self.theme.draw(canvas, 
                        properties = {
                                      "title" : g15globals.name,
                                      "icon" : g15util.get_icon_path("gnome-main-menu")
                                      }, 
                        attributes = {
                                      "items" : self.menu.items,
                                      "selected" : self.menu.selected
                                      })
        
    '''
    screen listener callbacks
    '''
    def new_page(self, page):
        self._reload_menu()
        
    def page_changed(self, page):
        pass
        
    def title_changed(self, page, title):
        self._reload_menu()
    
    def del_page(self, page):
        self._reload_menu()
        
    '''
    Private
    '''
    def _reload_menu(self):
        self.menu.items = []
        for page in self.screen.pages:
            if page != self.page and page.priority > g15screen.PRI_INVISIBLE:
                self.menu.items.append(MenuItem(page))
        self.menu.selected = self.menu.items[0]
               
        for item in self.menu.items:
            if item.page.thumbnail_painter != None:
                img = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.screen.height, self.screen.height)
                thumb_canvas = cairo.Context(img)
                try :
                    if item.page.thumbnail_painter(thumb_canvas, self.screen.height, True):
                        img_data = StringIO()
                        img.write_to_png(img_data)
                        item.thumbnail = base64.b64encode(img_data.getvalue())                    
                        
                except :
                    logger.warning("Problem with painting thumbnail in %s" % item.page.id)                   
                    traceback.print_exc(file=sys.stderr) 
                    
        self.screen.redraw(self.page)
        
    def _reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), self.screen, "menu-screen")
        self.menu = G15ScreensMenu(self.screen)
        self.menu.on_move = self._on_move
        self.menu.on_selected = self._on_selected
        self.theme.add_component(self.menu)
        self.theme.add_component(g15theme.Scrollbar("viewScrollbar", self.menu.get_scroll_values))
        
    def _on_selected(self):
        self.screen.redraw(self.page)
        
    def _on_move(self):
        pass
        
    def _show_menu(self):        
        self.page = self.screen.new_page(self.paint, id="Menu", priority = g15screen.PRI_EXCLUSIVE)
        self._reload_menu()            
        self.screen.add_screen_change_listener(self)
    
    def _hide_menu(self):     
        self.screen.remove_screen_change_listener(self)
        self.screen.del_page(self.page)
        self.page = None