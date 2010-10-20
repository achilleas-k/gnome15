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
 
import sys
import pygtk
pygtk.require('2.0')
import gtk
import g15_service as g15service
import g15_util as g15util
import appindicator
import cairo
import gconf

class G15Indicator():
    
    def __init__(self,  parent_window=None):
        
#        gconf_client = gconf.client_get_default()
        
        ind = appindicator.Indicator("example-simple-client",
                               g15util.local_icon_or_default("logitech-g-keyboard-panel"),
                               appindicator.CATEGORY_HARDWARE)
        ind.set_status (appindicator.STATUS_ACTIVE)
        
        self.ind = ind
        self.page_items = {}        
        self.ind.set_attention_icon(g15util.local_icon_or_default("logitech-g-keyboard-error-panel"))
        self.service = g15service.G15Service(self, parent_window)
                
        # Indicator menu
        self.menu = gtk.Menu()
        
        item = gtk.MenuItem("Properties")
        item.connect("activate", self.service.properties)
        self.menu.append(item)
        
        item = gtk.MenuItem("Macros")
        item.connect("activate", self.service.macros)
        self.menu.append(item)
        
        item = gtk.MenuItem("About")
        item.connect("activate", self.service.about_info)
        self.menu.append(item)
        
        self.menu.append(gtk.MenuItem())
        
        self.menu.show_all()
        self.ind.set_menu(self.menu)
        
        self.service.start()
        self.service.screen.add_screen_change_listener(self)
        
    def show_page(self,event, page):        
        self.service.screen.raise_page(page)  
        self.service.screen.applet.resched_cycle() 
        
    def new_page(self, page):
#        item = gtk.ImageMenuItem(page.id)
        item = gtk.MenuItem(page.title)
        self.page_items[page.id] = item
        item.connect("activate", self.show_page, page)
        
#        if page.thumbnail_painter != None:
#            img = cairo.ImageSurface(cairo.FORMAT_ARGB32, 32, 32)
#            thumb_canvas = cairo.Context(img)
#            if page.thumbnail_painter(thumb_canvas, 32, 32):
#                img_widget = gtk.Image()
#                img_widget.set_from_pixbuf(g15util.surface_to_pixbuf(img))
#                img_widget.show()
                
        item.show_all()
                
        self.menu.append(item)
        
    def title_changed(self, page, title):
        item = self.page_items[page.id]
        item.set_label(title)
    
    def del_page(self, page):
        item = self.page_items[page.id]
        self.menu.remove(item)
        item.destroy()
        del self.page_items[page.id]
        self.menu.show_all()
        
    def scroll (self, indicator_object, delta, direction):
        print delta,direction
        
    def clear_attention(self):
        self.ind.set_status (appindicator.STATUS_ACTIVE)
        
    def attention(self, message = None):
        self.ind.set_status (appindicator.STATUS_ATTENTION)

    def quit(self):                
        gtk.main_quit()