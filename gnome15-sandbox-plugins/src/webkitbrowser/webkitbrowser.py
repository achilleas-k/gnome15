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
import gnome15.g15screen as g15screen
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15gtk  as g15gtk
import os
import gtk
import gobject
import webkit

# Plugin details - All of these must be provided
id="webkitbrowser"
name="Webkit Browser"
description="Webkit based browser." 
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
supported_models = [ g15driver.MODEL_G19 ]

def create(gconf_key, gconf_client, screen):
    return G15WebkitBrowser(gconf_client, gconf_key, screen)

class G15WebkitBrowser():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        if self.screen.driver.get_model_name() != g15driver.MODEL_G19:
            raise Exception("Webkit plugin only works on G19")
        self._reload_theme()
        self.page = self.screen.new_page(self.paint, id=id, priority = g15screen.PRI_LOW)
        self.page.set_title(name)
        gobject.idle_add(self._create_offscreen_window)
    
    def deactivate(self):
        if self.page != None:
            self.screen.del_page(self.page)
            self.page = None
        
    def destroy(self):
        pass
        
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP: 
            if g15driver.G_KEY_UP in keys:
                gobject.idle_add(self._scroll_up) 
            elif g15driver.G_KEY_DOWN in keys:
                gobject.idle_add(self._scroll_down)
    
    def paint(self, canvas):
        print "Painting"
        properties = {
                      "url" : "www.somewhere.com",
                      "icon" : g15util.get_icon_path("system-config-display")
                      }
        self.theme.draw(canvas, properties)
        
    '''
    Private
    '''
    def _scroll_up(self):
        print "Scroll up"
        adj = self.scroller.get_vadjustment()
        adj.set_value(adj.get_value() - adj.get_page_increment())
        print "Val is now", adj.get_value(), "page increment", adj.get_page_increment(), "upper", adj.get_upper()
        self.screen.redraw(self.page)
    
    def _scroll_down(self):
        print "Scroll down"
        adj = self.scroller.get_vadjustment()
        adj.set_value(adj.get_value() + adj.get_page_increment())
        print "Val is now", adj.get_value(), "page increment", adj.get_page_increment(), "upper", adj.get_upper()
        self.screen.redraw(self.page)
    
    def _reload_theme(self):
        self.offscreen_window = None      
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        
    def _create_offscreen_window(self):
        vbox = gtk.VBox()
        view = webkit.WebView()
        view.open("http://www.youtube.com")
        self.scroller = gtk.ScrolledWindow()
        self.scroller.add(view)
        
        self.offscreen_window = self.theme.add_window("offscreenWindow", self.page)
        self.offscreen_window.content.add(self.scroller)
        self.offscreen_window.show_all()
        self.screen.redraw(self.page)