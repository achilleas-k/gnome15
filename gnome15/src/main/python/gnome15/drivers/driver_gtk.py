#!/usr/bin/env python
############################################################################
##
## Copyright (C), all rights reserved:
##      2010 Brett Smith <tanktarta@blueyonder.co.uk>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License version 2
##
## Gnome15 - Suite of GNOME applications that work with the logitech G15
##           keyboard
##
############################################################################


import gnome15.g15_driver as g15driver
import gnome15.g15_util as g15util
import gnome15.g15_globals as pglobals

import gconf

import os
import gtk
import gobject
import cairo

import Image
import ImageMath

# Driver information (used by driver selection UI)
id="gtk"
name="GTK"
description="A special development driver that emulates the G19, " + \
            "G15v1, G15v2 and G13 as a window on your desktop. This allows " + \
            "you to develop plugins without having access to a real Logitech " + \
            "G keyboard"
has_preferences=True

# Key layouts
g15v1_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3 ],
                  [ g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6 ],
                  [ g15driver.G_KEY_G7, g15driver.G_KEY_G8, g15driver.G_KEY_G9 ],
                  [ g15driver.G_KEY_G10, g15driver.G_KEY_G11, g15driver.G_KEY_G12 ],
                  [ g15driver.G_KEY_G13, g15driver.G_KEY_G14, g15driver.G_KEY_G15 ],
                  [ g15driver.G_KEY_G16, g15driver.G_KEY_G17, g15driver.G_KEY_G18 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4,  g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]

g15v2_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3 ],
                  [ g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4,  g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]          

g13_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3, g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6, g15driver.G_KEY_G7 ],
                  [ g15driver.G_KEY_G8, g15driver.G_KEY_G9, g15driver.G_KEY_G10, g15driver.G_KEY_G11, g15driver.G_KEY_G12, g15driver.G_KEY_G13, g15driver.G_KEY_G14 ],
                  [ g15driver.G_KEY_G15, g15driver.G_KEY_G16, g15driver.G_KEY_G17, g15driver.G_KEY_G18, g15driver.G_KEY_G19 ],
                  [ g15driver.G_KEY_G20, g15driver.G_KEY_G21, g15driver.G_KEY_G22 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4,  g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]
g19_key_layout = [
              [ g15driver.G_KEY_G1, g15driver.G_KEY_G7 ],
              [ g15driver.G_KEY_G2, g15driver.G_KEY_G8 ],
              [ g15driver.G_KEY_G3, g15driver.G_KEY_G9 ],
              [ g15driver.G_KEY_G4, g15driver.G_KEY_G10 ],
              [ g15driver.G_KEY_G5, g15driver.G_KEY_G11 ],
              [ g15driver.G_KEY_G6, g15driver.G_KEY_G12 ],
              [ g15driver.G_KEY_G6, g15driver.G_KEY_G12 ],
              [ g15driver.G_KEY_UP ],
              [ g15driver.G_KEY_LEFT, g15driver.G_KEY_OK, g15driver.G_KEY_RIGHT ],
              [ g15driver.G_KEY_DOWN ],
              [ g15driver.G_KEY_MENU, g15driver.G_KEY_BACK, g15driver.G_KEY_SETTINGS ],
              [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ],
              ]

# Controls

g19_keyboard_backlight_control = g15driver.Control("backlight_colour", "Keyboard Backlight Colour", (0, 0, 0), hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
g19_lcd_brightness_control = g15driver.Control("lcd_brightness", "LCD Brightness", 100, 0, 100, hint = g15driver.HINT_SHADEABLE)
g19_foreground_control = g15driver.Control("foreground", "Default LCD Foreground", (255, 255, 255), hint = g15driver.HINT_FOREGROUND)
g19_background_control = g15driver.Control("background", "Default LCD Background", (0, 0, 0), hint = g15driver.HINT_BACKGROUND)
g19_controls = [ g19_keyboard_backlight_control, g19_lcd_brightness_control, g19_foreground_control, g19_background_control]

g15_backlight_control = g15driver.Control("keyboard_backlight", "Keyboard Backlight Level", 0, 0, 2, hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
g15_invert_control = g15driver.Control("invert_lcd", "Invert LCD", 0, 0, 1, hint = g15driver.HINT_SWITCH )
g15_controls = [ g15_backlight_control, g15_invert_control ]  

def show_preferences(parent, gconf_client):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(pglobals.glade_dir, "driver_gtk.glade"))    
    dialog = widget_tree.get_object("DriverDialog")
    dialog.set_transient_for(parent)
    g15util.configure_combo_from_gconf(gconf_client,"/apps/gnome15/gtk_mode", "ModeCombo", g15driver.MODEL_G15_V1, widget_tree)
    dialog.run()
    dialog.hide()

class Driver(g15driver.AbstractDriver):

    def __init__(self, on_close = None):
        g15driver.AbstractDriver.__init__(self, "gtk")
        self.lights = 0
        self.main_window = None
        self.callback = None
        self.area = None
        self.image = None
        self.event_box = None
        self.on_close = on_close
        self.conf_client = gconf.client_get_default()
        self._init_driver()
        
    def get_antialias(self):        
        if self.mode == g15driver.MODEL_G15_V1 or self.mode == g15driver.MODEL_G15_V2 or self.mode == g15driver.MODEL_G13: 
            return cairo.ANTIALIAS_NONE
        else:
            return cairo.ANTIALIAS_DEFAULT
        
    def disconnect(self):
        if not self.is_connected():
            raise Exception("Not connected")
        self.conf_client.notify_remove(self.notify_h)
        gobject.idle_add(self._do_disconnect)
        if self.on_close != None:
            g15util.schedule("Close", 0, self.on_close)
        
    def is_connected(self):
        return self.main_window != None and self.main_window.get_visible()
        
    def window_closed(self, window, evt):
        if self.on_close != None:
            self.on_close(retry=False)
    
    def get_model_names(self):
        return [ g15driver.MODEL_G15_V1, g15driver.MODEL_G15_V2, g15driver.MODEL_G13, g15driver.MODEL_G19 ]
    
    def get_model_name(self):
        return self.mode
    
    def simulate_key(self, widget, key, state):
        if self.callback != None:
            keys = []
            keys.append(key)
            self.callback(keys, state)
        
    def get_key_layout(self):
        return self.key_layout
        
    def get_zoomed_size(self):
        size = self.get_size()
        zoom = self.get_zoom()
        return ( size[0] * zoom, size[1] * zoom )
        
    def get_zoom(self):
        if self.mode == g15driver.MODEL_G19:
            return 1
        else:
            return 3
        
    def connect(self):
        if self.is_connected():
            raise Exception("Already connected")      
        self.notify_h = self.conf_client.notify_add("/apps/gnome15/gtk_mode", self._mode_changed);
        gobject.idle_add(self._do_connect)
    
    def get_name(self):
        return "Gtk"
        
    def get_size(self):
        if self.mode == g15driver.MODEL_G15_V1 or self.mode == g15driver.MODEL_G15_V2 or self.mode == g15driver.MODEL_G13:
            return (160, 43)
        else:
            return (320, 240)
        
    def get_bpp(self):
        if self.mode == g15driver.MODEL_G15_V1 or self.mode == g15driver.MODEL_G15_V2 or self.mode == g15driver.MODEL_G13:
            return 1
        else:
            return 16
    
    def get_controls(self):
        return self.controls
    
    def paint(self, image):   
        
        size = self.get_size()
        width = size[0]
        height = size[1]
             
        if self.get_bpp() == 1:
            # Paint to 565 image provided into an ARGB image surface for PIL's benefit. PIL doesn't support 565?
            argb_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            argb_context = cairo.Context(argb_surface)
            argb_context.set_source_surface(image)
            argb_context.paint()
            
            # Now convert the ARGB to a PIL image so it can be converted to a 1 bit monochrome image, with all
            # colours dithered. It would be nice if Cairo could do this :( Any suggestions? 
            pil_img = Image.frombuffer("RGBA", size, argb_surface.get_data(), "raw", "RGBA", 0, 1)
            pil_img = ImageMath.eval("convert(pil_img,'1')",pil_img=pil_img)
            pil_img = ImageMath.eval("convert(pil_img,'P')",pil_img=pil_img)
            pil_img = pil_img.point(lambda i: i >= 250,'1')
            
            invert_control = self.get_control("invert_lcd")
            if invert_control.value == 1:            
                pil_img = pil_img.point(lambda i: 1^i)
            
            pil_img = pil_img.convert("RGB")
            self.image = pil_img           
        else:
            self.image = image
        gobject.timeout_add(0, self.redraw)
            
    def process_svg(self, document):  
        if self.get_bpp() == 1:
            for element in document.getroot().iter():
                style = element.get("style")
                if style != None:
                    element.set("style", style.replace("font-family:Sans","font-family:Fixed"))
                    
    def redraw(self):
        if self.image != None:
            if isinstance(self.image, cairo.Surface):
                self._draw_surface()
            else:
                self._draw_pixbuf()
        
    def update_control(self, control):  
        if self.event_box != None: 
            if control == self.get_control_for_hint(g15driver.HINT_DIMMABLE):
                if isinstance(control.value, int):
                    v = ( 65535 / control.upper ) * control.value
                    self.event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(v, v, v))
                else:
                    self.event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(control.value[0] << 8, control.value[1] << 8, control.value[2] << 8))
    
    def set_mkey_lights(self, lights):
        self.lights = lights
    
    def grab_keyboard(self, callback):
        self.callback = callback;
        
    '''
    Private
    '''
        
    def _mode_changed(self, client, connection_id, entry, args):
        if self.is_connected():
            gobject.idle_add(self.disconnect)
        else:
            print "WARNING: Mode change would cause disconnect when already connected.", entry
        
    def _draw_surface(self):
        # Finally paint the Cairo surface on the GTK widget
        zoom = self.get_zoom()
        if self.area != None and self.area.window != None:
            context = self.area.window.cairo_create()        
            context.set_antialias(self.get_antialias())
            context.scale(zoom, zoom)
            context.set_source_surface(self.image)
            context.paint()
            
    def _draw_pixbuf(self):
        size = self.get_size()
        width = size[0]
        height = size[1]
        zoom = self.get_zoom()
        pixbuf = g15util.image_to_pixbuf(self.image)
        pixbuf = pixbuf.scale_simple(zoom * width, zoom * height, 0)
        if self.area != None:
            self.area.set_from_pixbuf(pixbuf)
        
    def _do_connect(self):
        self._init_driver()
        self._init_ui()
        control = self.get_control_for_hint(g15driver.HINT_DIMMABLE)        
        if isinstance(control.value, int):
            v = ( 65535 / control.upper ) * control.value
            self.event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(v, v, v))
        else:
            self.event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(control.value[0] << 8, control.value[1] << 8, control.value[2] << 8))
            
            
    def _init_driver(self):          
        self.mode = self.conf_client.get_string("/apps/gnome15/gtk_mode")
        if self.mode == None or self.mode == "":
            self.mode = g15driver.MODEL_G19
        
        if self.mode == g15driver.MODEL_G15_V1 or self.mode == g15driver.MODEL_G15_V2 or self.mode == g15driver.MODEL_G13:
            self.controls = g15_controls
            if self.mode == g15driver.MODEL_G15_V1:
                self.key_layout = g15v1_key_layout
            elif self.mode == g15driver.MODEL_G15_V2:
                self.key_layout = g15v2_key_layout
            elif self.mode == g15driver.MODEL_G13:
                self.key_layout = g13_key_layout
        else:            
            self.controls = g19_controls
            self.key_layout = g19_key_layout
        
    def _init_ui(self):
        self.area = gtk.Image()
        self.area.set_double_buffered(True)
        self.hboxes = []
        
        zoomed_size = self.get_zoomed_size()
         
        self.area.set_size_request(zoomed_size[0], zoomed_size[1])        
        self.area.show()

        self.vbox = gtk.VBox ()            
        self.vbox.add(self.area)
        
        rows = gtk.VBox()
        for row in self.get_key_layout():
            hbox = gtk.HBox()
            for key in row:
                g_button = gtk.Button(" ".join(g15util.get_key_names(list(key))))
                g_button.connect("pressed", self.simulate_key, key, g15driver.KEY_STATE_DOWN)
                g_button.connect("released", self.simulate_key, key, g15driver.KEY_STATE_UP)
                hbox.add(g_button)
            rows.add(hbox)
            
        self.event_box = gtk.EventBox()
        self.event_box.add(rows)

        self.vbox.add(self.event_box)
        
        self.main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.main_window.set_title("Gnome15") 
        self.main_window.set_icon_from_file(g15util.get_app_icon(self.conf_client, "gnome15"))
        self.main_window.add(self.vbox)
        self.main_window.connect("delete-event", self.window_closed)
        
        self.main_window.show_all()
    
    def _do_disconnect(self):
        if self.main_window != None:
            self.main_window.hide()
            self.main_window.destroy()
            self.main_window = None
        self.area = None