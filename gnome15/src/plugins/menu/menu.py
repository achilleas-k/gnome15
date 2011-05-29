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
 
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15screen as g15screen
import gnome15.g15globals as g15globals
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

class MenuItem(g15theme.MenuItem):
    
    def __init__(self, item_page):
        g15theme.MenuItem.__init__(self, "menuitem")
        self._item_page = item_page
        self.thumbnail = None
        
    def draw(self, selected, canvas, menu_properties, menu_attributes):        
        item_properties = {}
        if selected == self:
            item_properties["item_selected"] = True
        item_properties["item_name"] = self._item_page.title 
        item_properties["item_alt"] = ""
        item_properties["item_type"] = ""
        item_properties["item_icon"] = self.thumbnail
        self.theme.draw(canvas, item_properties)
        return self.theme.bounds[3]

class G15Menu():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
    
    def activate(self):
        self._reload_theme()
        self._page = None
        self._screen.redraw(self._page)
    
    def deactivate(self):
        if self._page != None:
            self._hide_menu()
        
    def destroy(self):
        pass
                    
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_DOWN:

            if self._page == None:            
                if g15driver.G_KEY_MENU in keys or g15driver.G_KEY_L2 in keys:
                    self._show_menu()
                    return True
            else:                            
                if self._screen.get_visible_page() == self._page:                    
                    if g15driver.G_KEY_MENU in keys or g15driver.G_KEY_L2 in keys:
                        self._hide_menu()
                        self._screen.service.resched_cycle()
                        return True
                    elif self._menu.handle_key(keys, state, post):
                        return True           
                    elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                        self._screen.raise_page(self._menu.selected._item_page)
                        self._screen.service.resched_cycle()
                        self._hide_menu()
                        return True                
                
        return False
    
    def paint(self, canvas):
        self._theme.draw(canvas, 
                        properties = {
                                      "title" : g15globals.name,
                                      "icon" : g15util.get_icon_path("gnome-main-menu")
                                      }, 
                        attributes = {
                                      "items" : self._menu.get_items(),
                                      "selected" : self._menu.selected
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
        self._menu.clear_items()
        for page in self._screen.pages:
            if page != self._page and page.priority > g15screen.PRI_INVISIBLE:
                self._menu.add_item(MenuItem(page))
        items = self._menu.get_items()
        if len(items) > 0:
            self._menu.selected = items[0]
        else:
            self._menu.selected = None
               
        for item in items:
            if item._item_page.thumbnail_painter != None:
                img = cairo.ImageSurface(cairo.FORMAT_ARGB32, self._screen.height, self._screen.height)
                thumb_canvas = cairo.Context(img)
                try :
                    if item._item_page.thumbnail_painter(thumb_canvas, self._screen.height, True):
                        img_data = StringIO()
                        img.write_to_png(img_data)
                        item.thumbnail = base64.b64encode(img_data.getvalue())                    
                        
                except :
                    logger.warning("Problem with painting thumbnail in %s" % item._item_page.id)                   
                    traceback.print_exc(file=sys.stderr) 
                    
        self._screen.redraw(self._page)
        
    def _reload_theme(self):        
        self._theme = g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), self._screen, "menu-screen")
        self._menu = g15theme.Menu("menu", self._screen)
        self._menu.on_move = self._on_move
        self._menu.on_selected = self._on_selected
        self._theme.add_component(self._menu)
        self._theme.add_component(g15theme.Scrollbar("viewScrollbar", self._menu.get_scroll_values))
        
    def _on_selected(self):
        self._screen.redraw(self._page)
        
    def _on_move(self):
        pass
        
    def _show_menu(self):        
        self._page = self._screen.new_page(self.paint, id="Menu", priority = g15screen.PRI_EXCLUSIVE)
        self._reload_menu()            
        self._screen.add_screen_change_listener(self)
    
    def _hide_menu(self):     
        self._screen.remove_screen_change_listener(self)
        self._screen.del_page(self._page)
        self._page = None