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
import gnome15.g15_draw as g15draw
import datetime
from threading import Timer
import gtk
import os
import sys
import time

# Plugin details - All of these must be provided
id="fx"
name="Special Effect"
description="Screen transitions and stuff"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://localhost"
has_preferences=True

def create(gconf_key, gconf_client, screen):
    return G15Fx(gconf_key, gconf_client, screen)

class G15Fx():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        self.chained_painter = self.screen.set_painter(self.paint)
        self.chained_transition =self.screen.set_transition(self.transition)
    
    def deactivate(self):
        self.screen.set_painter(self.chained_painter)
        self.screen.set_transition(self.chained_transition)
        
    def destroy(self):
        pass
    
    def show_preferences(self, parent):
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "fx.glade"))
        
        dialog = widget_tree.get_object("FxDialog")
        dialog.set_transient_for(parent)
        
        self.configure_checkbox(widget_tree, "ScrollVertically", "/vertical_scroll")
        self.configure_checkbox(widget_tree, "Invert", "/invert")
        
        dialog.run()
        dialog.hide()
        
    '''
    '''
    def configure_checkbox(self, widget_tree, glade_id, key):
        widget = widget_tree.get_object(glade_id)
        widget.set_active(self.gconf_client.get_bool(self.gconf_key + key))
        widget.connect("toggled", self.changed, self.gconf_key + key)
    
    ''' Callbacks
    '''
    def changed(self, widget, key):
        self.gconf_client.set_bool(key, widget.get_active())
        self.screen.draw_current_canvas()
        
    def paint(self, image):
        invert = self.gconf_client.get_bool(self.gconf_key + "/invert")
        if invert:    
            image = image.point(lambda i: 255^i)
        
        if self.chained_painter != None:
            self.chained_painter.paint(image)
        else:        
            self.screen.driver.paint(image)
    
    def transition(self, old_page, new_page, direction="up"):
        
        vertical = self.gconf_client.get_bool(self.gconf_key + "/vertical_scroll")
        
        if new_page.priority == g15screen.PRI_HIGH or old_page == None or new_page == None:
            return
        
        old_canvas = old_page.canvas
        new_canvas = new_page.canvas
        
        width = self.screen.driver.get_size()[0]
        height = self.screen.driver.get_size()[1]
        
        if vertical:
            step = 1
            
            if direction == "up":
                for i in range(0, height, step):
                    working_img = old_canvas.img.copy()
                    new_img = new_canvas.img.copy()
                    im = old_canvas.img.crop((0, i + step, width, height))
                    working_img.paste(im, (0, 0))
                    im = new_img.crop((0, 0, width, i + step))
                    working_img.paste(im, (0, height - i - step))
                    self.paint(working_img)
            else:
                for i in range(0, height, step):
                    working_img = old_canvas.img.copy()
                    new_img = new_canvas.img.copy()
                    im = old_canvas.img.crop((0, 0, width, height - i - step))
                    working_img.paste(im, (0, i + step))
                    im = new_img.crop((0, height - i - step, width, height))
                    working_img.paste(im, (0, 0))
                    self.paint(working_img)
                
        else:
            step = width / height
            
            
            if direction == "up":
                for i in range(0, width, step):
                
                    working_img = old_canvas.img.copy()
                    new_img = new_canvas.img.copy()
                    
                    # Shift the original 1 pixel to the left
                    im = old_canvas.img.crop((i + step, 0, width, height))
                    
                    working_img.paste(im, (0, 0))
                
                    # Paste the new canvas            
                    im = new_img.crop((0, 0, i + step, height))
                    working_img.paste(im, (width - i - step, 0))
                    
                    # Now draw it
                    self.paint(working_img)
            else:
                for i in range(0, width, step):
                
                    working_img = old_canvas.img.copy()
                    new_img = new_canvas.img.copy()
                    
                    # Shift the original 1 pixel to the right
                    im = old_canvas.img.crop((0, 0, width - i - step, height))                    
                    working_img.paste(im, (i + step, 0))
                
                    # Paste the new canvas            
                    im = new_img.crop((width - i - step, 0, width, height))
                    working_img.paste(im, (0, 0))
                    
                    # Now draw it
                    self.paint(working_img)
    
        if self.chained_transition != None:
            self.chained_transition(old_page, new_page, direction)
