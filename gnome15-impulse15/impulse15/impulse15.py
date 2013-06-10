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
import gnome15.g15scheduler as g15scheduler
import gnome15.g15driver as g15driver
import gnome15.g15theme as g15theme
import gobject
import gtk
import os
import sys
import datetime

# Logging
import logging
logger = logging.getLogger("impulse15")

id="impulse15"
name="Impulse15"
description="Spectrum analyser. Based on the Impulse screenlet and desktop widget"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith, Ian Halpern"
site="https://launchpad.net/impulse.bzr"
unsupported_models = [ g15driver.MODEL_G930, g15driver.MODEL_G35 ]
has_preferences=True

def get_source_index(source_name):
    status, output = g15util.get_command_output("pacmd list-sources")
    if status == 0 and len(output) > 0:
        i = 0
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("index: "):
                i = int(line[7:])
            elif line.startswith("name: <%s" % source_name):
                return i
    logger.warn("Audio source %s not found, default to first source" % source_name)
    return 0

def create(gconf_key, gconf_client, screen):
    return G15Impulse(gconf_key, gconf_client, screen) 

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "impulse15.glade"))
    
    dialog = widget_tree.get_object("ImpulseDialog")
    dialog.set_transient_for(parent)
    
    # Set up the audio source model  
    audio_source_model = widget_tree.get_object("AudioSourceModel")
    status, output = g15util.get_command_output("pacmd list-sources")
    source_name = "0"
    if status == 0 and len(output) > 0:
        i = 0
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("index: "):
                i = int(line[7:])
                source_name = str(i)
            elif line.startswith("name: "):
                source_name = line[7:-1]
            elif line.startswith("device.description = "):
                audio_source_model.append((source_name, line[22:-1]))
    else:
        for i in range(0, 9):
            audio_source_model.append((str(i), "Source %d" % i))

    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/disco", "Disco", False, widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, gconf_key + "/animate_mkeys", "AnimateMKeys", False, widget_tree)
    g15util.configure_combo_from_gconf(gconf_client, gconf_key + "/mode", "ModeCombo", "spectrum", widget_tree)
    g15util.configure_combo_from_gconf(gconf_client, gconf_key + "/paint", "PaintCombo", "screen", widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/bars", "BarsSpinner", 16, widget_tree)
    g15util.configure_combo_from_gconf(gconf_client, gconf_key + "/audio_source_name", "AudioSource", source_name, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/bar_width", "BarWidthSpinner", 16, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/spacing", "SpacingSpinner", 0, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/rows", "RowsSpinner", 16, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/bar_height", "BarHeightSpinner", 2, widget_tree)
    g15util.configure_colorchooser_from_gconf(gconf_client, gconf_key + "/col1", "Color1", ( 255, 0, 0 ), widget_tree, default_alpha = 255)
    g15util.configure_colorchooser_from_gconf(gconf_client, gconf_key + "/col2", "Color2", ( 0, 0, 255 ), widget_tree, default_alpha = 255)
    g15util.configure_adjustment_from_gconf(gconf_client, gconf_key + "/frame_rate", "FrameRateAdjustment", 10.0, widget_tree)
    g15util.configure_adjustment_from_gconf(gconf_client, gconf_key + "/gain", "GainAdjustment", 1.0, widget_tree)
    
    if driver.get_bpp() == 0:
        widget_tree.get_object("LCDTable").set_visible(False)

    
    dialog.run()
    dialog.hide() 

class G15ImpulsePainter(g15screen.Painter):
    
    def __init__(self, plugin):
        g15screen.Painter.__init__(self, g15screen.BACKGROUND_PAINTER, -5000)
        self.theme_module = None
        self.backlight_acquisition = None
        self.mkey_acquisition = None        
        self.mode = "default"
        self.plugin = plugin
        self.last_sound = datetime.datetime.now()
        
    def do_lights(self, audio_sample_array = None):     
        if not audio_sample_array:
            audio_sample_array = self._get_sample()
        
        if self.backlight_acquisition is not None:
            self.backlight_acquisition.set_value(self._col_avg(audio_sample_array))
        tot_avg = self._tot_avg(audio_sample_array)
        if self.mkey_acquisition is not None:
            self._set_mkey_lights(tot_avg)
        return tot_avg
    
    def is_idle(self):
        return datetime.datetime.now() > ( self.last_sound + datetime.timedelta(0, 5.0) )
            
    def paint(self, canvas):
        if not self.theme_module: 
            return
        audio_sample_array = self._get_sample()
        tot_avg = self.do_lights(audio_sample_array)
        if tot_avg > 0:
            self.last_sound = datetime.datetime.now()
        
        canvas.save()
        self.theme_module.on_draw( audio_sample_array, canvas, self.plugin )
        canvas.restore()
        
    """
    Private
    """
    
    def _get_sample(self):
        fft = False
        if hasattr( self.theme_module, "fft" ) and self.theme_module.fft:
            fft = True

        audio_sample_array = impulse.getSnapshot( fft )
        if self.plugin.gain != 1:
            arr = []
            for a in audio_sample_array:
                arr.append(a * self.plugin.gain)
            audio_sample_array = arr
        
        return audio_sample_array
    
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
            
    def _release_mkey_acquisition(self):      
        if self.mkey_acquisition:          
            self.plugin.screen.driver.release_control(self.mkey_acquisition)
            self.mkey_acquisition = None
        
    def _release_backlight_acquisition(self):          
        if self.backlight_acquisition is not None:      
            self.plugin.screen.driver.release_control(self.backlight_acquisition)
            self.backlight_acquisition = None

class G15Impulse():    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.hidden = False
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.active = False
        self.last_paint = None
        self.audio_source_index = 0
        self.config_change_timer = None

        import impulse
        sys.modules[ __name__ ].impulse = impulse
        sys.path.append(os.path.join(os.path.dirname(__file__), "themes"))

    def set_audio_source( self, *args, **kwargs ):
        impulse.setSourceIndex( self.audio_source_index )
        
    def activate(self):
        self.painter = G15ImpulsePainter(self)
        self.width = self.screen.driver.get_size()[0]
        self.height = self.screen.driver.get_size()[1]
        self.active = True
        self.page = None
        self.visible = False
        self.timer = None
        self._load_config() 
        self.notify_handle = self.gconf_client.notify_add(self.gconf_key, self._config_changed)
        self.redraw()
    
    def deactivate(self): 
        self.painter._release_backlight_acquisition()
        self.painter._release_mkey_acquisition()
        self.active = False
        self.refresh_interval = 1.0 / 25.0
        self.gconf_client.notify_remove(self.notify_handle);
        self.hide_page()
        self._clear_painter()
    
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
        g15scheduler.clear_jobs("impulseQueue")
        
    def destroy(self):
        pass
    
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
    
    def redraw(self):        
        if self.screen.driver.get_bpp() == 0:
            self.painter.do_lights()
        else:
            if self.paint_mode == "screen" and self.visible:
                self.screen.redraw(self.page, queue = False)
            elif self.paint_mode != "screen": 
                self.screen.redraw(redraw_content = False, queue = False)
        self._schedule_redraw()
        
    """
    Private
    """
        
    def _schedule_redraw(self):
        if self.active:
            next_tick = self.refresh_interval
            if self.painter.is_idle():
                next_tick = 1.0
            self.timer = g15scheduler.queue("impulseQueue", "ImpulseRedraw", next_tick, self.redraw)
        
    def _config_changed(self, client, connection_id, entry, args):
        if self.config_change_timer is not None:
            self.config_change_timer.cancel()
        self.config_change_timer = g15scheduler.schedule("ConfigReload", 1, self._do_config_changed)
        
    def _do_config_changed(self):
        self.stop_redraw()
        self._load_config()        
        self.redraw()
        self.config_change_timer = None
            
    def _on_load_theme (self):
        if not self.painter.theme_module or self.mode != self.painter.theme_module.__name__:
            self.painter.theme_module = __import__( self.mode )
            self.painter.theme_module.load_theme(self)
            
    def _activate_painter(self):
        if not self.painter in self.screen.painters:
            self.screen.painters.append(self.painter)
            
    def _clear_painter(self):
        if self.painter in self.screen.painters:
            self.screen.painters.remove(self.painter)
    
    def _load_config(self):
        logger.info("Reloading configuration")
        self.audio_source_index = get_source_index(self.gconf_client.get_string(self.gconf_key + "/audio_source_name"))
        gobject.idle_add(self.set_audio_source)
        self.mode = self.gconf_client.get_string(self.gconf_key + "/mode")
        self.disco = g15util.get_bool_or_default(self.gconf_client, self.gconf_key + "/disco", False)
        self.refresh_interval = 1.0 / g15util.get_float_or_default(self.gconf_client, self.gconf_key + "/frame_rate", 25.0)
        self.gain = g15util.get_float_or_default(self.gconf_client, self.gconf_key + "/gain", 1.0)
        logger.info("Refresh interval is %f" % self.refresh_interval)
        self.animate_mkeys = g15util.get_bool_or_default(self.gconf_client, self.gconf_key + "/animate_mkeys", False)
        if self.mode == None or self.mode == "" or self.mode == "spectrum" or self.mode == "scope":
            self.mode = "default"
        self.paint_mode = self.gconf_client.get_string(self.gconf_key + "/paint")
        if self.paint_mode == None or self.mode == "":
            self.paint_mode = "screen"
        self._on_load_theme()
            
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
        if paint != self.last_paint and self.screen.driver.get_bpp() != 0: 
            self.last_paint = paint
            self._clear_painter()
            if paint == "screen":
                if self.page == None:
                    self.page = g15theme.G15Page(id, self.screen, title = name, painter = self.painter.paint, on_shown = self.on_shown, on_hidden = self.on_hidden, originating_plugin = self)
                    self.screen.add_page(self.page)
                else:
                    self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
            elif paint == "foreground":
                self.painter.place = g15screen.FOREGROUND_PAINTER
                self._activate_painter()
                self.hide_page() 
            elif paint == "background":    
                self.painter.place = g15screen.BACKGROUND_PAINTER
                self._activate_painter()
                self.hide_page()            
                
        # Acquire the backlight control if appropriate
        control = self.screen.driver.get_control_for_hint(g15driver.HINT_DIMMABLE)
        if control:
            if self.disco and self.painter.backlight_acquisition is None:
                self.painter.backlight_acquisition = self.screen.driver.acquire_control(control)
            elif not self.disco and self.painter.backlight_acquisition is not None:
                self.painter._release_backlight_acquisition()
                
        # Acquire the M-Key lights control if appropriate
        if self.animate_mkeys and self.painter.mkey_acquisition is None:
            self.painter.mkey_acquisition = self.screen.driver.acquire_control_with_hint(g15driver.HINT_MKEYS)
        elif not self.animate_mkeys and self.painter.mkey_acquisition is not None:
            self.painter._release_mkey_acquisition()