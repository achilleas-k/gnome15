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
 
'''
A top level GTK windows that draws on the LCD
'''
import gtk
import gobject
import cairo
import g15driver as g15driver
import g15util as g15util
import traceback
from threading import Lock
 
class G15Window(gtk.OffscreenWindow):
    
    def __init__(self, screen, page, area_x, area_y, area_width, area_height):
        gtk.OffscreenWindow.__init__(self)
        self.pixbuf = None
        self.screen = screen
        self.page = page  
        self.lock = None      
        self.area_x = int(area_x)
        self.area_y = int(area_y)
        self.area_width = int(area_width)
        self.area_height = int(area_height)
        self.surface = None
        self.redraw_surface()
        
        
        self.content = gtk.EventBox()
        self.set_app_paintable(True)
#        self.set_double_buffered(False)
#        self.content.set_double_buffered(False)
        self.content.set_app_paintable(True)        
        self.connect("screen-changed", self.screen_changed)
        self.content.connect("expose-event", self._transparent_expose)
        self.content.set_size_request(self.area_width, self.area_height)
        self.add(self.content)
        self.connect("damage_event", self._damage)
        self.connect("expose_event", self._expose)
        self.screen_changed(None, None)
        self.set_opacity(0.5)
        
    def handle_key(self, keys, state, post):
        gobject.idle_add(self._do_handle_key, keys, state, post)
        
    def _do_handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP:
            if g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L3 in keys:
                self.content.get_toplevel().child_focus(gtk.DIR_TAB_FORWARD)
                pass
            elif g15driver.G_KEY_UP in keys:
                self.content.get_toplevel().child_focus(gtk.DIR_TAB_BACKWARD)
            if g15driver.G_KEY_LEFT in keys or g15driver.G_KEY_RIGHT in keys or g15driver.G_KEY_L3 in keys:
                self._change_widget(keys)
                pass
                
    def _change_widget(self, keys):
        focussed = self.get_focus()
        if focussed != None:
            if isinstance(focussed, gtk.HScale):
                adj = focussed.get_adjustment()
                ps = adj.get_page_size()
                if ps == 0:
                    ps = 10
                if g15driver.G_KEY_LEFT in keys:
                    adj.set_value(adj.get_value() - ps)
                else:
                    adj.set_value(adj.get_value() + ps)
        
    def show_all(self):
        gtk.OffscreenWindow.show_all(self)
#        if self.content.window != None:
#            self.content.window.set_composited(True)
        self.content.window.set_composited(False)
#        self.set_opacity(0.5)

    def screen_changed(self, widget, old_screen=None):
        global supports_alpha
        
        # To check if the display supports alpha channels, get the colormap
        screen = self.get_screen()
        colormap = screen.get_rgba_colormap()
        if colormap == None:
            colormap = screen.get_rgb_colormap()
            supports_alpha = False
        else:
            supports_alpha = True
            
        # Now we have a colormap appropriate for the screen, use it
        self.set_colormap(colormap)
    
        return False
        
    def _transparent_expose(self, widget, event):
        cr = widget.window.cairo_create()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_surface(self.surface)
        cr.paint()
        return False
    
    def redraw_surface(self):
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.screen.width, self.screen.height) 
        ctx = cairo.Context(self.surface)
#        ctx.rectangle(self.area_x, self.area_y, self.area_width, self.area_height)
#        ctx.clip()
        scale = 1.0 / self.screen.get_desktop_scale()
        tx = ( ( float(self.screen.width) - ( float(self.screen.width) * scale) ) ) / 2.0        
        ctx.translate(-self.area_x, -self.area_y)
        ctx.scale(scale, scale)
        ctx.translate(tx ,0)
        ctx.set_source_surface(self.screen.surface)
        ctx.paint()
        
    def _expose(self, widget, event):
        
#        cr = widget.window.cairo_create()
#        cr.set_operator(cairo.OPERATOR_CLEAR)
#        region = gtk.gdk.region_rectangle(event.area)
#        cr.region(region)
#        cr.fill()
        self._do_capture
        return False
    
    def get_as_surface(self):
        self.redraw_surface()
        lock = Lock()
        self.lock = lock
        lock.acquire()
        self.queue_draw()
        lock.acquire()
        self.lock = None
        lock.release()
        return self.surface
    
    def get_as_pixbuf(self):
        self.redraw_surface()
        lock = Lock()
        self.lock = lock
        lock.acquire()
        self.queue_draw()
        lock.acquire()
        self.lock = None
        lock.release()
        return self.pixbuf
        
    def _damage(self, widget, event):
        self.redraw_surface()
        self._do_capture()
        return False
    
    def wait_for_capture(self):
        self.lock = Lock()
        
    def _do_capture(self):
        print "_do_capture()"
        pixbuf = gtk.gdk.Pixbuf( gtk.gdk.COLORSPACE_RGB, False, 8, self.area_width, self.area_height)
        print "created pixbuf"
        pixbuf.get_from_drawable(self.content.window, self.content.get_colormap(), 0, 0, 0, 0, self.area_width, self.area_height)
        print "built pixbuf"
        self.surface = g15util.pixbuf_to_surface(pixbuf)
        print "created surface"
        self.pixbuf = pixbuf
        if self.lock != None:
            self.lock.release()