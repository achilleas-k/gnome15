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
 
import gnome15.g15screen as g15screen  
import gnome15.g15util as g15util  
import gnome15.g15driver as g15driver
import gnome15.g15theme as g15theme
import gtk
import os
import sys

id="impulse15"
name="Impulse15"
description="Spectrum analyser. Based on the Impulse screenlet and desktop widget"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith, Ian Halpern"
site="https://launchpad.net/impulse.bzr"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]


def create(gconf_key, gconf_client, screen):
    return G15Impulse(gconf_key, gconf_client, screen) 

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "impulse15.glade"))
    
    dialog = widget_tree.get_object("ImpulseDialog")
    dialog.set_transient_for(parent)

    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/disco", "Disco", False, widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/animate_mkeys", "AnimateMKeys", False, widget_tree)
    g15util.configure_combo_from_gconf(gconf_client, gconf_key + "/mode", "ModeCombo", "spectrum", widget_tree)
    g15util.configure_combo_from_gconf(gconf_client, gconf_key + "/paint", "PaintCombo", "screen", widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/bars", "BarsSpinner", 16, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/audio_source", "AudioSourceSpinner", 0, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/bar_width", "BarWidthSpinner", 16, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/spacing", "SpacingSpinner", 0, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/rows", "RowsSpinner", 16, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/bar_height", "BarHeightSpinner", 2, widget_tree)
    g15util.configure_colorchooser_from_gconf(gconf_client, gconf_key + "/col1", "Color1", ( 255, 0, 0 ), widget_tree, default_alpha = 255)
    g15util.configure_colorchooser_from_gconf(gconf_client, gconf_key + "/col2", "Color2", ( 0, 0, 255 ), widget_tree, default_alpha = 255)
    g15util.configure_adjustment_from_gconf(gconf_client, gconf_key + "/frame_rate", "FrameRateAdjustment", 25.0, widget_tree)
    
    dialog.run()
    dialog.hide() 


class G15Impulse():    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.active = False
        self.last_paint = None
        self.audio_source_index = 0

        import impulse
        sys.modules[ __name__ ].impulse = impulse
        sys.path.append(os.path.join(os.path.dirname(__file__), "themes"))

    def set_audio_source( self, *args, **kwargs ):
        impulse.setSourceIndex( self.audio_source_index )
        
    def activate(self):
        self.width = self.screen.driver.get_size()[0]
        self.height = self.screen.driver.get_size()[1]
        self.mode = "default"
        self.theme_module = None
        self.active = True
        self.page = None
        self.background_painter_set = False
        self.foreground_painter_set = False
        self.chained_background_painter = None
        self.chained_foreground_painter = None
        self.backlight_acquisition = None
        self.mkey_acquisition = None
        self.visible = False
        self.timer = None
        self._load_config() 
        self.notify_handle = self.gconf_client.notify_add(self.gconf_key, self._config_changed)
        self.redraw()
    
    def deactivate(self): 
        self._release_backlight_acquisition()
        self._release_mkey_acquisition()
        self.active = False
        self.refresh_interval = 1.0 / 25.0
        self.gconf_client.notify_remove(self.notify_handle);
        self.hide_page()
        self._clear_background_painter()
        self._clear_foreground_painter()
    
    def hide_page(self):   
        self.stop_redraw()  
        if self.page != None:
            self.screen.del_page(self.page)
            self.page = None
        
    def on_shown(self):
        self.visible = True 
        self._schedule_redraw()     
        
    def on_hidden(self):
        self.visible = False
        self.stop_redraw()
        
    def stop_redraw(self):  
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
        
    def destroy(self):
        pass
    

    def on_load_theme (self):
        if not self.theme_module or self.mode != self.theme_module.__name__:
            self.theme_module = __import__( self.mode )
            self.theme_module.load_theme( self )
    
    def paint(self, canvas):
        if not self.theme_module: 
            return

        fft = False
        if hasattr( self.theme_module, "fft" ) and self.theme_module.fft:
            fft = True

        audio_sample_array = impulse.getSnapshot( fft )
        
        if self.backlight_acquisition is not None:
            self.backlight_acquisition.set_value(self._col_avg(audio_sample_array))
        
        if self.mkey_acquisition is not None:
            self._set_mkey_lights(self._tot_avg(audio_sample_array))
        
        canvas.save()
        self.theme_module.on_draw( audio_sample_array, canvas, self )
        canvas.restore()
        
    """
    Private
    """
    
    def _col_avg(self, list):
        cols = []
        each = len(list) / 3
        z = 0
        for j in range(0, 3):
            t = 0
            for x in range(0, each):
                t += min(255, list[z] * 340)
                z += 1
            cols.append(int(t / each))
        return ( cols[0], cols[1], cols[2] )
    
    def _tot_avg(self, list):
        sz = len(list)
        z = 0
        t = 0
        for x in range(0, sz):
            t += min(255, list[z] * 340)
            z += 1
        return t / sz
                  
    def _set_mkey_lights(self, val):
        if val > 200:
            self.mkey_acquisition.set_value(g15driver.MKEY_LIGHT_MR | g15driver.MKEY_LIGHT_1 | g15driver.MKEY_LIGHT_2 | g15driver.MKEY_LIGHT_3)        
        elif val > 100:
            self.mkey_acquisition.set_value(g15driver.MKEY_LIGHT_1 | g15driver.MKEY_LIGHT_2 | g15driver.MKEY_LIGHT_3)        
        elif val > 50:
            self.mkey_acquisition.set_value(g15driver.MKEY_LIGHT_1 | g15driver.MKEY_LIGHT_2)        
        elif val > 25:
            self.mkey_acquisition.set_value(g15driver.MKEY_LIGHT_1)        
        else:
            self.mkey_acquisition.set_value(0)
        
    def _schedule_redraw(self):
        if self.active:
            self.timer = g15util.schedule("ImpulseRedraw", self.refresh_interval, self.redraw)
            
    def _release_mkey_acquisition(self):                
        self.screen.driver.release_mkey_lights(self.mkey_acquisition)
        self.mkey_acquisition = None
        
    def _release_backlight_acquisition(self):          
        if self.backlight_acquisition is not None:      
            self.screen.driver.release_control(self.backlight_acquisition)
            self.backlight_acquisition = None
        
    def _config_changed(self, client, connection_id, entry, args):
        self.stop_redraw()
        self._load_config()        
        self.redraw()
            
    def _paint_background(self, canvas):
        if self.chained_background_painter != None:
            self.chained_background_painter(canvas)
        self.paint(canvas)
    
    def _paint_foreground(self, canvas):
        if self.chained_foreground_painter != None:
            self.chained_foreground_painter(canvas)
        self.paint(canvas)
            
    def _clear_background_painter(self):
        if self.background_painter_set:
            self.screen.set_background_painter(self.chained_background_painter)
            self.chained_background_painter = None
            self.background_painter_set = False
            
    def _clear_foreground_painter(self):
        if self.foreground_painter_set:
            self.screen.set_foreground_painter(self.chained_foreground_painter)
            self.chained_foreground_painter = None
            self.foreground_painter_set = False
    
    def redraw(self):        
        if self.paint_mode == "screen" and self.visible:
            self.screen.redraw(self.page)
            self._schedule_redraw()
        elif self.paint_mode != "screen": 
            self.screen.redraw(redraw_content = False)
            self._schedule_redraw()
    
    def _load_config(self):
        self.audio_source_index = self.gconf_client.get_int(self.gconf_key + "/audio_source")
        self.set_audio_source()
        self.mode = self.gconf_client.get_string(self.gconf_key + "/mode")
        self.disco = g15util.get_bool_or_default(self.gconf_client, self.gconf_key + "/disco", False)
        self.refresh_interval = 1.0 / g15util.get_float_or_default(self.gconf_client, self.gconf_key + "/frame_rate", 25.0)
        self.animate_mkeys = g15util.get_bool_or_default(self.gconf_client, self.gconf_key + "/animate_mkeys", False)
        if self.mode == None or self.mode == "" or self.mode == "spectrum" or self.mode == "scope":
            self.mode = "default"
        self.paint_mode = self.gconf_client.get_string(self.gconf_key + "/paint")
        if self.paint_mode == None or self.mode == "":
            self.paint_mode = "screen"
        self.on_load_theme()
            
        self.bars = self.gconf_client.get_int(self.gconf_key + "/bars")
        if self.bars == 0:
            self.bars = 16
        self.bar_width = self.gconf_client.get_int(self.gconf_key + "/bar_width")
        if self.bar_width == 0:
            self.bar_width = 16
        self.bar_height = self.gconf_client.get_int(self.gconf_key + "/bar_height")
        if self.bar_height == 0:
            self.bar_height = 2
        self.rows = self.gconf_client.get_int(self.gconf_key + "/rows")
        if self.rows == 0:
            self.rows = 16
        self.spacing = self.gconf_client.get_int(self.gconf_key + "/spacing")
        self.col1 = g15util.to_cairo_rgba(self.gconf_client, self.gconf_key + "/col1", ( 255, 0, 0, 255 )) 
        self.col2 = g15util.to_cairo_rgba(self.gconf_client, self.gconf_key + "/col2", ( 0, 0, 255, 255 ))
            
        self.peak_heights = [ 0 for i in range( self.bars ) ]

        paint = self.gconf_client.get_string(self.gconf_key + "/paint")
        if paint != self.last_paint:
            self.last_paint = paint
            if paint == "screen":
                self._clear_background_painter()
                self._clear_foreground_painter()
                if self.page == None:
                    self.page = g15theme.G15Page(id, self.screen, title = name, painter = self.paint, on_shown = self.on_shown, on_hidden = self.on_hidden)
                    self.screen.add_page(self.page)
                else:
                    self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
            elif paint == "foreground":
                self._clear_background_painter()
                self.chained_foreground_painter = self.screen.set_foreground_painter(self._paint_foreground)
                self.foreground_painter_set = True
                self.hide_page()
            elif paint == "background":
                self._clear_foreground_painter()
                self.chained_background_painter = self.screen.set_background_painter(self._paint_background)
                self.background_painter_set = True
                self.hide_page()
                
        # Acquire the backlight control if appropriate
        control = self.screen.driver.get_control_for_hint(g15driver.HINT_DIMMABLE)
        if control:
            if self.disco and self.backlight_acquisition is None:
                self.backlight_acquisition = self.screen.driver.acquire_control(control)
            elif not self.disco and self.backlight_acquisition is not None:
                self._release_backlight_acquisition()
                
        # Acquire the M-Key lights control if appropriate
        if self.animate_mkeys and self.mkey_acquisition is None:
            self.mkey_acquisition = self.screen.driver.acquire_mkey_lights()
        elif not self.animate_mkeys and self.mkey_acquisition is not None:
            self._release_mkey_acquisition()