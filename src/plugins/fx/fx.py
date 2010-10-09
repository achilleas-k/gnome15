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
import gnome15.g15_driver as g15driver
import datetime
from threading import Timer
import Image
import gtk
import os
import sys
import time
import cairo
import random


# Plugin details - All of these must be provided
id="fx"
name="Special Effect"
description="This plugin introduces special effects when switching between screens. " \
  + "Currently 2 main types of effect are provided, a sliding effect (in both directions) " \
  + "and a fading effect. On a monochrome LCD such as the G15's, the fade appears as more " \
  + "of a 'disolve' effect." \
  
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True

def create(gconf_key, gconf_client, screen):
    return G15Fx(gconf_key, gconf_client, screen)

def show_preferences(parent, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "fx.glade"))
    
    dialog = widget_tree.get_object("FxDialog")
    dialog.set_transient_for(parent)
    
    transition_effect_combo = widget_tree.get_object("TransitionCombo")
    transition_effect_model = widget_tree.get_object("TransitionModel")
    transition_effect_combo.connect("changed", effect_changed, gconf_client, gconf_key + "/transition_effect", transition_effect_model)
    effect = gconf_client.get_string(gconf_key + "/transition_effect")
    if effect == "":
        effect = "random"
    idx = 0
    for row in transition_effect_model:
        if row[0] == effect:
            transition_effect_combo.set_active(idx)
        idx += 1
    
    configure_checkbox(widget_tree, "Invert", "/invert", gconf_client, gconf_key)
    
    dialog.run()
    dialog.hide()
        
def configure_checkbox(widget_tree, glade_id, key, gconf_client, gconf_key):
    widget = widget_tree.get_object(glade_id)
    widget.set_active(gconf_client.get_bool(gconf_key + key))
    widget.connect("toggled", changed, gconf_key + key, gconf_client)
    
def effect_changed(widget, gconf_client, key, model):
    gconf_client.set_string(key, model[widget.get_active()][0])
    
def changed(widget, key, gconf_client):
    gconf_client.set_bool(key, widget.get_active())
    
    
effects = [ "vertical-scroll", "horizontal-scroll", "fade" ]

class G15Fx():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        self.chained_painter = self.screen.set_painter(self.paint)
        self.chained_transition =self.screen.set_transition(self.transition)
        self.notify_handler = self.gconf_client.notify_add(self.gconf_key, self.config_changed); 
    
    def deactivate(self):
        self.gconf_client.notify_remove(self.notify_handler); 
        self.screen.set_painter(self.chained_painter)
        self.screen.set_transition(self.chained_transition)
        
    def destroy(self):
        pass
    
    ''' Callbacks
    '''
        
    def config_changed(self, client, connection_id, entry, args):
        self.screen.redraw()
        
    def paint(self, image):        
        invert = self.gconf_client.get_bool(self.gconf_key + "/invert")
        if invert:         
            data = image.get_data()
            idx = 0
            for idx in range(0, len(data), 4):
                data[idx] = chr(255 - ord(data[idx]))
                data[idx + 1] = chr(255 - ord(data[idx + 1]))
                data[idx + 2] = chr(255 - ord(data[idx + 2]))
        
        if self.chained_painter != None:
            self.chained_painter.paint(image)
        else:        
            self.screen.driver.paint(image)
    
    
    def transition(self, old_surface, new_surface, old_page, new_page, direction="up"):
        # Determine effect to use
        effect = self.gconf_client.get_string(self.gconf_key + "/transition_effect")
        if effect == "":
            effect = "random"
        if effect == "random":
            effect = effects[int(random.random() * len(effects))]    
        
        
        # Don't transition for high priority screens
        if new_page == None or old_page == None or new_page.priority == g15screen.PRI_HIGH:
            return
        
        width = self.screen.width
        height = self.screen.height
        
        # NOTE. This is a quick way of making the animation quicker on a G19. The G19 requires
        # a lot more data, plus there is further latency with the daemon. 
        
        factor = self.screen.driver.get_bpp()
        
        # Create a working surface
        
        
        img_surface = cairo.ImageSurface (g15driver.CAIRO_IMAGE_FORMAT, self.screen.width, self.screen.height)
        img_context = cairo.Context(img_surface)
        if effect == "vertical-scroll":
            # Vertical scroll
            step = 1 * factor      
            if direction == "down":                
                for i in range(0, self.screen.height, step):
                    img_context.save()
                    img_context.translate(0, -i)                
                    img_context.set_source_surface(old_surface)
                    img_context.paint()
                    img_context.translate(0, self.screen.height)
                    img_context.set_source_surface(new_surface)
                    img_context.paint()
                    img_context.restore()
                    self.paint(img_surface)
            else:                
                for i in range(0, self.screen.height, step):
                    img_context.save() 
                    img_context.translate(0, -(self.screen.height - i))                
                    img_context.set_source_surface(new_surface)
                    img_context.paint()
                    img_context.translate(0, self.screen.height)
                    img_context.set_source_surface(old_surface)
                    img_context.paint()
                    img_context.restore()
                    self.paint(img_surface)
                
        elif effect == "horizontal-scroll":    
            # Horizontal scroll
            step = ( width / height ) * factor
            if direction == "down":                
                for i in range(0, self.screen.width, step):
                    img_context.save()
                    img_context.translate(-i, 0)                
                    img_context.set_source_surface(old_surface)
                    img_context.paint()
                    img_context.translate(self.screen.width, 0)
                    img_context.set_source_surface(new_surface)
                    img_context.paint()
                    img_context.restore()
                    self.paint(img_surface)
            else:                
                for i in range(0, self.screen.width, step):
                    img_context.save() 
                    img_context.translate(-(self.screen.width - i), 0)                
                    img_context.set_source_surface(new_surface)
                    img_context.paint()
                    img_context.translate(self.screen.width, 0)
                    img_context.set_source_surface(old_surface)
                    img_context.paint()
                    img_context.restore()
                    self.paint(img_surface)
        elif effect == "fade":
            step = factor      
            for i in range(0, 256, step):                
                img_context.set_source_surface(new_surface)
                img_context.paint_with_alpha(float(i) / 256.0)                
                img_context.set_source_surface(old_surface)
                img_context.paint_with_alpha(1.0 - ( float(i) / 256.0 ) )
                self.paint(img_surface)
            
        if self.chained_transition != None:
            self.chained_transition(old_canvas, new_canvas, old_page, new_page, direction)
