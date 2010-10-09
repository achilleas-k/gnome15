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
import datetime
from threading import Timer
import cairo
import gtk
import os
import sys
import time
import Image

# Plugin details - All of these must be provided
id="background"
name="Wallpaper"
description="Use an image for the LCD background"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True

def create(gconf_key, gconf_client, screen):
    return G15Background(gconf_key, gconf_client, screen)

def show_preferences(parent, gconf_client, gconf_key):
    G15BackgroundPreferences(parent, gconf_client, gconf_key)
    
class G15BackgroundPreferences():
    
    def __init__(self, parent, gconf_client, gconf_key):
        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "background.glade"))
        
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        
        # Widgets
        dialog = self.widget_tree.get_object("BackgroundDialog")
        dialog.set_transient_for(parent)
        
        # The file chooser
        self.chooser = gtk.FileChooserDialog("Open..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        self.chooser.set_default_response(gtk.RESPONSE_OK)
        
        filter = gtk.FileFilter()
        filter.set_name("Images")
        filter.add_mime_type("image/png")
        filter.add_mime_type("image/jpeg")
        filter.add_mime_type("image/gif")
        filter.add_pattern("*.png")
        filter.add_pattern("*.jpg")
        filter.add_pattern("*.jpeg")
        filter.add_pattern("*.gif")
        self.chooser.add_filter(filter)
        
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        self.chooser.add_filter(filter)
        
        self.chooser_button = self.widget_tree.get_object("FileChooserButton")        
        self.chooser_button.dialog = self.chooser        
        self.chooser_button.connect("file-set", self.file_set)
        self.widget_tree.connect_signals(self)
        bg_img = gconf_client.get_string(gconf_key + "/path")
        if bg_img == None:
            bg_img = ""
        self.chooser_button.set_filename(bg_img)
        
        dialog.run()
        dialog.hide()
        
    def file_set(self, widget):
        self.gconf_client.set_string(self.gconf_key + "/path", widget.get_filename())
        
class G15Background():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.this_image = None
        self.background_image = None
        self.target_surface = None
        self.target_context = None
        self.was_cairo = False
    
    def activate(self):
        self.chained_painter = self.screen.set_background_painter(self.paint)
        self.notify_handler = self.gconf_client.notify_add(self.gconf_key + "/path", self.config_changed);
        self.screen.redraw()
    
    def deactivate(self):
        self.screen.set_background_painter(self.chained_painter)
        self.gconf_client.notify_remove(self.notify_handler);
        self.screen.redraw()
        
    def config_changed(self, client, connection_id, entry, args):
        self.screen.redraw()
        
    def destroy(self):
        pass
        
    def paint(self, canvas):
        bg_img = self.gconf_client.get_string(self.gconf_key + "/path")
        screen_size = self.screen.size
        if bg_img == None:
            bg_img = os.path.join(os.path.dirname(__file__), "background-%dx%d.png" % ( screen_size[0], screen_size[1] ) )

        if bg_img != self.this_image or ( self.was_cairo and not isinstance(canvas, cairo.Context) ) or ( not self.was_cairo and isinstance(canvas, cairo.Context)):
            self.this_image = bg_img
            if isinstance(canvas, cairo.Context):
                self.was_cairo = True
                if os.path.exists(bg_img):
                    # Load the background
                    self.background_image, self.bg_context = g15util.load_surface_from_file(bg_img, screen_size)
                else:
                    self.background_image = None
            else:
                self.was_cairo = False    
                if os.path.exists(bg_img):
                    self.background_image = Image.open(bg_img).convert("RGBA")
                    if self.background_image.size[0] != screen_size[0] or self.background_image.size[1] != screen_size[1]:
                        # TODO resize maintaining aspect            
                        self.background_image = self.background_image.resize((screen_size[0], screen_size[1]), Image.BILINEAR)
                    bg = self.background_image
                else:
                    self.background_image = None
         
        if self.background_image != None:
            if isinstance(canvas, cairo.Context):
                
                canvas.set_source_surface(self.background_image, 0.0, 0.0)
                canvas.paint()
            else:
                canvas.draw_image(self.background_image, (0, 0))
         
        if self.chained_painter != None:
            self.chained_painter(canvas)