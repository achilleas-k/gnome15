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
import gnome15.g15cairo as g15cairo
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15screen as g15screen
import gnome15.g15globals as g15globals
import subprocess
import time
import os
import sys
import gtk
import gconf
import cairo
import traceback
import webkit
import gobject

# Plugin details - All of these must be provided
id="browser"
name="Browser"
description="Adds an HTML browser using pywebkitgtk"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False

def create(gconf_key, gconf_client, screen):
    return G15Browser(gconf_client, gconf_key, screen)


class BrowserPage(webkit.WebView):

    def __init__(self):
        webkit.WebView.__init__(self)
        settings = self.get_settings()
#        settings.set_property("enable-developer-extras", True)

        # scale other content besides from text as well
        self.set_full_content_zoom(True)
        
    def queue_draw(self):
        print "Queue draw"
        webkit.WebView.queue_draw()
        
class BrowserWindow(gtk.OffscreenWindow):
    
    def __init__(self, plugin):
        self.plugin = plugin
        self.screen = self.plugin.screen
        self.image = None
        gtk.OffscreenWindow.__init__(self)
#        self.set_visible_window(False)
        
        self.browser = BrowserPage()
        
        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.props.hscrollbar_policy = gtk.POLICY_AUTOMATIC
        self.scrolled_window.props.vscrollbar_policy = gtk.POLICY_AUTOMATIC
        self.scrolled_window.add(self.browser)
        self.scrolled_window.show_all()
        
        self.vbox = gtk.VBox(spacing=1)
        self.vbox.pack_start(self.scrolled_window)

        self.add(self.vbox)
        self.set_double_buffered(True)
#        self.set_size_request(self.screen.width, self.screen.height)
        self.set_default_size(self.screen.width, self.screen.height)
        self.vbox.show_all()
        self.connect("expose_event", self.expose)
        self.browser.connect("expose_event", self.expose)
        self.browser.connect('resource-request-starting', self.resource_cb)
        self.browser.load_uri("http://www.youtube.com/")
        
#        self.set_opacity(0.0)
#        self.connect('map', self.map)
#        self.set_app_paintable(True)
        self.show_all()
#        self.window.set_composited(True)

    def load_status(self, view, frame, resource, request, response):
        print "Load status",request.get_uri()

    def resource_cb(self, view, frame, resource, request, response):
        print "Request",request.get_uri()

    def map(self, widget, event):
        print "**Map**"

    def expose(self, widget, event):
        print "**Expose**"
        gobject.idle_add(self._do_redraw)
        return False
        
    def _do_redraw(self):
        if self.browser.window != None:
            print "Getting pixbuf"
            pixbuf = gtk.gdk.Pixbuf( gtk.gdk.COLORSPACE_RGB, False, 8, self.screen.width, self.screen.height)
            print "Getting from drawable"
            pixbuf.get_from_drawable(self.vbox.window, self.vbox.get_colormap(), 0, 0, 0, 0, self.screen.width, self.screen.height)
            print "Creating surface"
            self.plugin.pixbuf = pixbuf
        
        self.plugin.screen.redraw(self.plugin.page)
    
class G15Browser():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.pixbuf = None
    
    def activate(self):
        self.page = self.screen.new_page(self.paint, id="Browser", priority = g15screen.PRI_NORMAL)
        self.screen.redraw(self.page)
        gobject.idle_add(self.start_browser)
        
    def start_browser(self):
        self.browser = BrowserWindow(self)
    
    def deactivate(self):
        self.screen.del_page(self.page)
        
    def destroy(self):
        pass
    
    def paint(self, canvas):
        print "Painting"
        pixbuf = self.pixbuf
        if pixbuf != None:
            image = g15cairo.pixbuf_to_surface(pixbuf)
            canvas.set_source_surface(image)
            canvas.paint()