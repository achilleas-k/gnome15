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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("fx", modfile = __file__).ugettext

import gnome15.g15screen as g15screen 
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gtk
import os
import time
import cairo
import random


# Plugin details - All of these must be provided
id="fx"
name=_("Special Effect")
description=_("This plugin introduces special effects when switching between screens. \
Currently 3 main types of effect are provided, a sliding effect (in both directions) \
a fading effect and a zoom effect . On a monochrome LCD such as the G15's, the fade appears as more \
of a 'disolve' effect.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]

def create(gconf_key, gconf_client, screen):
    return G15Fx(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "fx.glade"))    
    dialog = widget_tree.get_object("FxDialog")
    dialog.set_transient_for(parent)    
    g15util.configure_combo_from_gconf(gconf_client, gconf_key + "/transition_effect", "TransitionCombo", "random", widget_tree)
    g15util.configure_adjustment_from_gconf(gconf_client, gconf_key + "/anim_speed", "AnimationSpeedAdjustment", 5.0, widget_tree)
    dialog.run()
    dialog.hide()
    
effects = [ "vertical-scroll", "horizontal-scroll", "fade", "zoom" ]

class G15Fx():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        self.chained_transition =self.screen.set_transition(self.transition)
        self.notify_handler = self.gconf_client.notify_add(self.gconf_key, self.config_changed)
    
    def deactivate(self):
        self.gconf_client.notify_remove(self.notify_handler)
        self.screen.set_transition(self.chained_transition)
        
    def destroy(self):
        pass
    
    ''' Callbacks
    '''
        
    def config_changed(self, client, connection_id, entry, args):
        self.screen.redraw()
    
    
    def transition(self, old_surface, new_surface, old_page, new_page, direction="up"):
        # Determine effect to use
        effect = self.gconf_client.get_string(self.gconf_key + "/transition_effect")
        if effect == "":
            effect = "random"
        if effect == "random":
            effect = effects[int(random.random() * len(effects))]
            
        # Animation speed
        speed_entry =  self.gconf_client.get(self.gconf_key + "/anim_speed")
        speed = 5.0 if speed_entry == None else speed_entry.get_float()
        
        # Don't transition for high priority screens
        if new_page == None or old_page == None or new_page.priority == g15screen.PRI_HIGH:
            return
        
        width = self.screen.width
        height = self.screen.height  
        
        # Create a working surface
        img_surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, self.screen.width, self.screen.height)
        img_context = cairo.Context(img_surface)
        if effect == "vertical-scroll":
            # Vertical scroll
            step = max( int(speed), 1 )      
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
                    self.screen.driver.paint(img_surface)
                    self.anim_delay(speed)
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
                    self.screen.driver.paint(img_surface)
                    self.anim_delay(speed)
                
        elif effect == "horizontal-scroll":    
            # Horizontal scroll
            step = max( ( width / height ) * speed, 1 )
            if direction == "down":                
                for i in range(0, self.screen.width, int(step)):
                    img_context.save()
                    img_context.translate(-i, 0)                
                    img_context.set_source_surface(old_surface)
                    img_context.paint()
                    img_context.translate(self.screen.width, 0)
                    img_context.set_source_surface(new_surface)
                    img_context.paint()
                    img_context.restore()
                    self.screen.driver.paint(img_surface)
                    self.anim_delay(speed)
            else:                
                for i in range(0, self.screen.width, int(step)):
                    img_context.save() 
                    img_context.translate(-(self.screen.width - i), 0)                
                    img_context.set_source_surface(new_surface)
                    img_context.paint()
                    img_context.translate(self.screen.width, 0)
                    img_context.set_source_surface(old_surface)
                    img_context.paint()
                    img_context.restore()
                    self.screen.driver.paint(img_surface)
                    self.anim_delay(speed)
        elif effect == "fade":
            step = max( int(speed), 1 )
            for i in range(0, 256, step):                
                img_context.set_source_surface(new_surface)
                img_context.paint_with_alpha(float(i) / 256.0)                
                img_context.set_source_surface(old_surface)
                img_context.paint_with_alpha(1.0 - ( float(i) / 256.0 ) )
                self.screen.driver.paint(img_surface)
                self.anim_delay(speed)
        elif effect == "zoom":
            step = max( int(speed), 1 )
            if direction == "down":               
                for i in range(1, self.screen.width, step):
                    img_context.save()                
                    img_context.set_source_surface(old_surface)
                    img_context.paint() 
                    scale = i / float(self.screen.width)
                    scaled_width = self.screen.width * scale
                    scaled_height = self.screen.height * scale
                    img_context.translate( ( self.screen.width - scaled_width) / 2, ( self.screen.height - scaled_height) / 2)  
                    img_context.scale(scale, scale)            
                    img_context.set_source_surface(new_surface)
                    img_context.paint()               
                    img_context.restore()             
                    self.screen.driver.paint(img_surface)
                    self.anim_delay(speed)
            else:                
                for i in range(self.screen.width, 0, step * -1):
                    img_context.save()             
                    img_context.set_source_surface(new_surface)
                    img_context.paint()               
                    scale = i / float(self.screen.width)
                    scaled_width = self.screen.width * scale
                    scaled_height = self.screen.height * scale
                    img_context.translate( ( self.screen.width - scaled_width) / 2, ( self.screen.height - scaled_height) / 2)  
                    img_context.scale(scale, scale)            
                    img_context.set_source_surface(old_surface)
                    img_context.paint()               
                    img_context.restore()  
                    self.screen.driver.paint(img_surface)
                    self.anim_delay(speed)
                
        if self.chained_transition != None:
            self.chained_transition(old_surface, new_surface, old_page, new_page, direction)

    def anim_delay(self, speed):
        if speed < 1.0:
            time.sleep( ( 1.0 - speed ) / 50.0 )