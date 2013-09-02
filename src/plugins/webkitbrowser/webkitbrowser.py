#!/usr/bin/env python
 
#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2011 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 
import gnome15.g15driver as g15driver
import gnome15.g15gtk  as g15gtk
import gnome15.g15plugin  as g15plugin
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

class G15WebkitBrowser(g15plugin.G15PagePlugin):
    
    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15PagePlugin.__init__(self, gconf_client, gconf_key, screen, \
            [ "browser", "gnome-web-browser", "web-browser", "www-browser", \
             "redhat-web-browser", "internet-web-browser" ], id, name)
        self.add_page_on_activate = False
    
    def populate_page(self):
        g15plugin.G15PagePlugin.populate_page(self)
        self.window = g15gtk.G15OffscreenWindow("offscreenWindow")
        self.page.add_child(self.window)
        gobject.idle_add(self._create_browser)

    def activate(self):
        g15plugin.G15PagePlugin.activate(self)
        self.screen.key_handler.action_listeners.append(self) 
    
    def deactivate(self):
        g15plugin.G15PagePlugin.deactivate(self)
        self.screen.key_handler.action_listeners.remove(self)
        
    def action_performed(self, binding):
        if self.page is not None and self.page.is_visible(): 
            if binding.action == g15driver.PREVIOUS_PAGE:
                gobject.idle_add(self._scroll_up)
                return True
            elif binding.action == g15driver.NEXT_PAGE:
                gobject.idle_add(self._scroll_down)
                return True
        
    '''
    Private
    '''
    
    def get_theme_properties(self):
        return dict(g15plugin.G15PagePlugin.get_theme_properties(self).items() + {
            "url" : "www.somewhere.com"
        }.items())
        
    def _scroll_up(self):
        adj = self.scroller.get_vadjustment()
        adj.set_value(adj.get_value() - adj.get_page_increment())
        self.screen.redraw(self.page)
    
    def _scroll_down(self):
        adj = self.scroller.get_vadjustment()
        adj.set_value(adj.get_value() + adj.get_page_increment())
        self.screen.redraw(self.page)
    
    def _create_browser(self):
        view = webkit.WebView()
        self.scroller = gtk.ScrolledWindow()
        self.scroller.add(view)    
        view.open("http://www.youtube.com")
        self.window.set_content(self.scroller)
        self.screen.add_page(self.page)
        self.screen.redraw(self.page)