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
 
import gnome15.g15_theme as g15theme
import gnome15.g15_screen as g15screen
import gnome15.g15_driver as g15driver
import gnome15.g15_util as g15util
import gnome15.g15_gtk  as g15gtk
import os
import gtk
import gobject

# Plugin details - All of these must be provided
id="backlight"
name="Backlight"
description="Set the keyboard backlight color using the LCD screen and menu keys. " + \
            "This plugin demonstrates the use of ordinary GTK widgets on the LCD." 
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False

def create(gconf_key, gconf_client, screen):
    return G15Backlight(gconf_client, gconf_key, screen)

class G15Backlight():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        if self.screen.driver.get_model_name() != g15driver.MODEL_G19:
            raise Exception("Backlight plugin only works on G19")
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
        if not post and state == g15driver.KEY_STATE_UP and g15driver.G_KEY_BACK in keys:
            self.screen.set_priority(self.page, g15screen.PRI_LOW)
        elif self.offscreen_window != None:
            self.offscreen_window.handle_key(keys, state, post)
    
    def paint(self, canvas):
        print "Painting"
        
        backlight_control = self.screen.driver.get_control_for_hint(g15driver.HINT_DIMMABLE)
        color = backlight_control.value
        properties = {
                      "title" : "Set Backlight",
                      "icon" : g15util.get_icon_path(self.gconf_client, "system-config-display"),
                      "r" : color[0],
                      "g" : color[1],
                      "b" : color[2]
                      }
        self.theme.draw(canvas, properties)
        
    '''
    Private
    '''
    
    def _reload_theme(self):
        self.offscreen_window = None      
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        
    def _value_changed(self, widget, octet):
        backlight_control = self.screen.driver.get_control_for_hint(g15driver.HINT_DIMMABLE)
        color = list(backlight_control.value)
        color[octet] = int(widget.get_value())
        self.gconf_client.set_string("/apps/gnome15/" + backlight_control.id, "%d,%d,%d" % ( color[0],color[1],color[2]))
        print "New color is",color
        
    def _create_offscreen_window(self):
        
        backlight_control = self.screen.driver.get_control_for_hint(g15driver.HINT_DIMMABLE)
        color = backlight_control.value
        
        vbox = gtk.VBox()
        adjustment = gtk.Adjustment(color[0], 0, 255, 1, 10, 10)
        red = gtk.HScale(adjustment)
        red.set_draw_value(False)
        adjustment.connect("value-changed", self._value_changed, 0)
        
        vbox.add(red)
        red.grab_focus()
        adjustment = gtk.Adjustment(color[1], 0, 255, 1, 10, 10)
        green = gtk.HScale(adjustment)
        green.set_draw_value(False)
        adjustment.connect("value-changed", self._value_changed, 1)
        green.set_range(0, 255)
        green.set_increments(1, 10)
        vbox.add(green)
        adjustment = gtk.Adjustment(color[2], 0, 255, 1, 10, 10)
        blue = gtk.HScale(adjustment)
        blue.set_draw_value(False)
        adjustment.connect("value-changed", self._value_changed, 2)
        blue.set_range(0, 255)
        blue.set_increments(1, 10)
        vbox.add(blue)
        
        self.offscreen_window = self.theme.add_window("offscreenWindow", self.page)
        self.offscreen_window.content.add(vbox)
        self.offscreen_window.show_all()
        self.screen.redraw(self.page)