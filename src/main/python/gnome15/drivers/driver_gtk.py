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

import gtk
import gtk.gdk
import gobject
import cairo

import driver_g15 as g15
import driver_g19 as g19

import Image
import ImageMath
import StringIO
import array


class Driver(g15driver.AbstractDriver):

    
    def __init__(self, on_close = None):
        self.lights = 0
        self.callback = None
        self.on_close = None
        self.conf_client = gconf.client_get_default()        
        self.mode = self.conf_client.get_string("/apps/gnome15/gtk_mode")
        if self.mode == None or self.mode == "":
            self.mode = g15driver.MODEL_G19
        print "GTK driver mode " + self.mode
        
        if self.mode == g15driver.MODEL_G15_V1 or self.mode == g15driver.MODEL_G15_V2 or self.mode == g15driver.MODEL_G13:
            self.controls = g15.controls
            if self.mode == g15driver.MODEL_G15_V1:
                self.key_layout = g15.g15v1_key_layout
            elif self.mode == g15driver.MODEL_G15_V1:
                self.key_layout = g15.g15v1_key_layout
            elif self.mode == g15driver.MODEL_G13:
                self.key_layout = g15.g13_key_layout
        else:            
            self.controls = g19.controls
            self.key_layout = g19.key_layout
        
        self.area = gtk.Image()
        
        zoomed_size = self.get_zoomed_size()
         
        self.area.set_size_request(zoomed_size[0], zoomed_size[1])        
        self.area.show()

        vbox = gtk.VBox ()            
        vbox.add(self.area)
        
        
        for row in self.get_key_layout():
            hbox = gtk.HBox()
            for key in row:
                g_button = gtk.Button(" ".join(g15util.get_key_names(list(key))))
                g_button.connect("pressed", self.simulate_key, key, g15driver.KEY_STATE_DOWN)
                g_button.connect("released", self.simulate_key, key, g15driver.KEY_STATE_UP)
                hbox.add(g_button)
            vbox.add(hbox)
        
        self.main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.main_window.set_title("Gnome15") 
        self.main_window.set_icon_from_file(pglobals.image_dir + "/g15key.png")
        self.main_window.add(vbox)
        self.main_window.connect("delete-event", self.window_closed)
        
    def get_antialias(self):        
        if self.mode == g15driver.MODEL_G15_V1 or self.mode == g15driver.MODEL_G15_V2 or self.mode == g15driver.MODEL_G13: 
            return cairo.ANTIALIAS_NONE
        else:
            return cairo.ANTIALIAS_DEFAULT
        
    def disconnect(self):
        self.main_window.hide()
        
    def is_connected(self):
        return self.main_window.get_visible()
        
    def window_closed(window, evt):
        if self.on_close != None:
            self.on_close()
    
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
        self.main_window.show_all()
    
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
        zoom = self.get_zoom()
             
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
            
            invert_control = self.get_control("invert-lcd")
            if invert_control.value == 1:            
                pil_img = pil_img.point(lambda i: 1^i)
                
            
            
            pil_img = pil_img.convert("RGB")
            gobject.timeout_add(0, self.draw_pixbuf, pil_img)           
        else:
            gobject.timeout_add(0, self.draw_surface, image)
            
    def process_svg(self, document):  
        if self.get_bpp() == 1:
            g15.fix_sans_style(document.getroot())
        
    def draw_surface(self, image):
        # Finally paint the Cairo surface on the GTK widget
        zoom = self.get_zoom()
        context = self.area.window.cairo_create()        
        context.set_antialias(self.get_antialias())
        context.scale(zoom, zoom)
        context.set_source_surface(image)
        context.paint()
            
    def draw_pixbuf(self, image):
        size = self.get_size()
        width = size[0]
        height = size[1]
        zoom = self.get_zoom()
        pixbuf = g15util.image_to_pixbuf(image)
        pixbuf = pixbuf.scale_simple(zoom * width, zoom * height, 0)
        self.area.set_from_pixbuf(pixbuf)
        
    def update_control(self, control):
        if not self.mode == g15driver.MODEL_G19:
            pass
        else:
            pass
#            hex_col = "#" + hex(control.value)[2:].zfill(6)
#            map = self.main_window.get_colormap()
#            colour = map.alloc_color(hex_col)
#            style = self.main_window.get_style().copy()
#            style.bg[gtk.STATE_NORMAL] = colour
#            self.main_window.set_style(style)

    
    def set_mkey_lights(self, lights):
        self.lights = lights
    
    def grab_keyboard(self, callback):
        self.callback = callback;
    
