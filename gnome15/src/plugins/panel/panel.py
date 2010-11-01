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
import gnome15.g15_driver as g15driver
import gnome15.g15_util as g15util
import os
import gtk

# Plugin details - All of these must be provided
id="panel"
name="Panel"
description="Adds a small area at the bottom of the screen for other plugins to add permanent components to. " \
        + "This plugin only works on the G19. "
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True
        
def create(gconf_key, gconf_client, screen):
    return G15Panel(gconf_key, gconf_client, screen)

def show_preferences(parent, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "panel.glade"))
    dialog = widget_tree.get_object("PanelDialog")
    dialog.set_transient_for(parent)
    g15util.configure_adjustment_from_gconf(gconf_client, gconf_key + "/size", "SizeAdjustment", 24, widget_tree)
    g15util.configure_combo_from_gconf(gconf_client, gconf_key + "/position", "PositionCombo", "bottom", widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/stretch", "Stretch", False, widget_tree)
    g15util.configure_colorchooser_from_gconf(gconf_client, gconf_key + "/color", "Color", ( 128, 128, 128 ), widget_tree, default_alpha = 128)
    dialog.run()
    dialog.hide()

class G15Panel():    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.active = False
    
    def activate(self):    
        if self.screen.driver.get_bpp() == 1:
            raise Exception("Panel not supported on low-res LCD")
        self.notify_handle = self.gconf_client.notify_add(self.gconf_key, self._config_changed);
        self._set_available_screen_size()
        self.active = True
        self.chained_painter = self.screen.set_foreground_painter(self.paint)
        self.screen.redraw()
            
    def is_active(self):
        return self.active
    
    def deactivate(self):
        self.gconf_client.notify_remove(self.notify_handle);
        self.active = False
        self.screen.set_foreground_painter(self.chained_painter)
        self.screen.set_available_size((0, 0, self.screen.width, self.screen.height))
        self.screen.redraw()
        
    def destroy(self):
        pass
    
    def get_enabled(self, panel_applet):
        # TODO - allow disabling of panel applets in panel preferences
        return True
    
    def _config_changed(self, client, connection_id, entry, args):
        self._set_available_screen_size()
        self.screen.redraw()
        
    def _set_available_screen_size(self):
        x = 0
        y = 0
        pos = self._get_panel_position()
        panel_height = self._get_panel_size()
        stretch = self.gconf_client.get_bool(self.gconf_key + "/stretch")
        
        if pos == "bottom" or pos == "top":
            scale = float( self.screen.height - panel_height ) / float(self.screen.height)
            if not stretch:
                x = ( float(self.screen.width) - float(self.screen.width * scale ) ) / 2.0
            if pos == "top":
                y = panel_height
            self.screen.set_available_size((x, y, self.screen.width, self.screen.height - panel_height))
        
        if pos == "left" or pos == "right":
            scale = float( self.screen.width - panel_height ) / float(self.screen.width)
            if not stretch:
                y = ( float(self.screen.height) - float(self.screen.height * scale ) ) / 2.0
            if pos == "left":
                x = panel_height
            self.screen.set_available_size((x, y, self.screen.width - panel_height, self.screen.height))
    
    def _get_panel_size(self):
        panel_size = self.gconf_client.get_int(self.gconf_key + "/size")
        if panel_size == 0:
            panel_size = 24
        return panel_size
    
    def _get_panel_position(self):
        panel_pos = self.gconf_client.get_string(self.gconf_key + "/position")
        if panel_pos == None or panel_pos == "":
            panel_pos = "bottom"
        return panel_pos
        
    def paint(self, canvas):
        panel_height = self._get_panel_size()
        position = self._get_panel_position()
            
        canvas.save()        
        
#        if position == "bottom":
#            canvas.translate(0, self.screen.height - panel_height)
#        elif position == "right":
#            canvas.translate(self.screen.width - panel_height, 0)
        
        # Paint panel background
            
        gap = panel_height / 10.0                
        widget_size = panel_height - ( gap * 2 )
        canvas.set_source_rgba(*g15util.to_cairo_rgba(self.gconf_client, self.gconf_key + "/color", ( 128, 128, 128, 128 )) )
        if position == "top" or position == "bottom":            
            if position == "bottom":
                canvas.translate(0, self.screen.height - panel_height)            
            canvas.rectangle(0, 0, self.screen.width, panel_height)
            canvas.fill()            
            for page in self.screen.pages:
                if page != self.screen.get_visible_page() and page.panel_painter != None:
                    canvas.translate(gap, gap)
                    canvas.save()         
                    canvas.set_source_rgb(*self.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 )))
                    taken_up = page.panel_painter(canvas, widget_size, True)
                    canvas.restore()        
                    if taken_up != None:
                        canvas.translate(taken_up, 0)
                        canvas.translate(0, -gap)
                    else:
                        canvas.translate(-gap, -gap)
        else:
            if position == "right":
                canvas.translate(self.screen.width - panel_height, 0)
            canvas.rectangle(0, 0, panel_height, self.screen.height)
            canvas.fill()
            for page in self.screen.pages:
                if page != self.screen.get_visible_page() and page.panel_painter != None:
                    canvas.translate(gap, gap)
                    canvas.save()         
                    canvas.set_source_rgb(*self.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 )))
                    taken_up = page.panel_painter(canvas, widget_size, False)
                    canvas.restore()        
                    if taken_up != None:
                        canvas.translate(0, taken_up)
                        canvas.translate(-gap, 0)
                    else:
                        canvas.translate(-gap, -gap)
                
            
        canvas.restore()        
        
        if self.chained_painter != None:
            self.chained_painter(canvas)   