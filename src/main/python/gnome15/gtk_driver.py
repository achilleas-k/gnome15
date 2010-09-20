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


import g15_driver as g15driver
import gtk
import gtk.gdk
import g15_globals as pglobals
import gobject

import Image
import StringIO

def image2pixbuf(im):  
    file1 = StringIO.StringIO()  
    im.save(file1, "ppm")  
    contents = file1.getvalue()  
    file1.close()  
    loader = gtk.gdk.PixbufLoader("pnm")  
    loader.write(contents, len(contents))  
    pixbuf = loader.get_pixbuf()  
    loader.close()  
    return pixbuf  

G15_V1_MODE=0
G15_V2_MODE=1
G19_MODE=2
G13_MODE=3

class GtkDriver():
    
    def __init__(self):
        self.lights = 0
        self.keyboard_backlight = 0
        self.lcd_backlight = 0
        self.contrast = 0
        self.mode = G19_MODE
        self.callback = None
        
        self.image = gtk.Image()
        vbox = gtk.VBox ()            
        vbox.add(self.image)
        
        # G buttons
        g = 1
        for row in self.get_gkey_layout():
            hbox = gtk.HBox()
            for i in range(0, row):
                g_button = gtk.Button("G%d" % g)
                g_button.connect("pressed", self.g_key, g - 1, g15driver.KEY_STATE_DOWN)
                g_button.connect("released", self.g_key, g - 1, g15driver.KEY_STATE_UP)
                g += 1
                hbox.add(g_button)
            vbox.add(hbox)
        
        # L buttons
        hbox = gtk.HBox()
        for i in range(1, 6):
            l_button = gtk.Button("L%d" % i)
            l_button.connect("pressed", self.g_key, 21 + i, g15driver.KEY_STATE_DOWN)
            l_button.connect("released", self.g_key, 21 + i, g15driver.KEY_STATE_UP)
            hbox.add(l_button)         
        vbox.add(hbox)
        
        # M buttons
        hbox = gtk.HBox()
        for i in range(1, 4):
            m_button = gtk.Button("M%d" % i)
            m_button.connect("pressed", self.g_key, 17 + i, g15driver.KEY_STATE_DOWN)
            m_button.connect("released", self.g_key, 17 + i, g15driver.KEY_STATE_UP)
            hbox.add(m_button)
        mr_button = gtk.Button("MR")
        mr_button.connect("pressed", self.g_key, 21, g15driver.KEY_STATE_DOWN)
        mr_button.connect("released", self.g_key,  21, g15driver.KEY_STATE_UP)
        hbox.add(mr_button)            
        vbox.add(hbox)
        
        # Light
        hbox = gtk.HBox()
        light_button = gtk.Button("Light")
        light_button.connect("pressed", self.g_key, 27, g15driver.KEY_STATE_DOWN)
        light_button.connect("released", self.g_key,  27, g15driver.KEY_STATE_UP)
        hbox.add(light_button)            
        vbox.add(hbox)
        
        self.main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.main_window.set_title("Gnome15") 
        self.main_window.set_icon_from_file(pglobals.image_dir + "/g15key.png")
        self.main_window.add(vbox)
    
    def g_key(self, widget, key, val):
        print "Key",str(widget),str(1 << key),str(val)
        if self.callback != None:
            self.callback(1 << key, val)
        
    def get_gkey_layout(self):
        if self.mode == G15_V1_MODE:
            return (3, 3, 3, 3, 3, 3)
        elif self.mode == G15_V2_MODE:
            return (1, 1, 1, 1, 1, 1)
        elif self.mode == G13_MODE:
            return (7,7,5,3)
        else:
            return (2, 2, 2, 2, 2, 2)
        
    def get_zoom(self):
        if self.mode == G15_V1_MODE:
            return 3
        elif self.mode == G15_V2_MODE:
            return 3
        elif self.mode == G13_MODE:
            return 3
        else:
            return 2
        
    def connect(self):
        self.main_window.show_all()
    
    def get_name(self):
        return "Gtk"
        
    def get_size(self):
        if self.mode == G15_V1_MODE or self.mode == G15_V2_MODE or self.mode == G13_MODE:
            return (160, 43)
        else:
            return (320, 240)
        
    def get_bpp(self):
        if self.mode == G15_V1_MODE or self.mode == G15_V2_MODE or self.mode == G13_MODE:
            return 1
        else:
            return 16
    
    def get_keyboard_backlight_colours(self):
        if self.mode == G15_V1_MODE or self.mode == G15_V2_MODE:
            return 3
        else:
            return 16777215
    
    def get_gkeys(self):
        if self.mode == G15_V1_MODE:
            return 18
        elif self.mode == G15_V2_MODE:
            return 6
        elif self.mode == G13_MODE:
            return 22
        else:
            return 12
    
    def paint(self, image):
        image = image.resize((image.size[0] * self.get_zoom(), image.size[1] * self.get_zoom()), Image.NEAREST)
        self.pixbuf = image2pixbuf(image)
        gobject.timeout_add(0,self.draw_image, self)
        
    def draw_image(self, event):
        self.image.set_from_pixbuf(self.pixbuf)
    
    def switch_priorities(self):
        raise NotImplementedError( "Not implemented" )
        
    def is_foreground(self):
        raise NotImplementedError( "Not implemented" )
    
    def never_user_selected(self):
        raise NotImplementedError( "Not implemented" )
    
    def is_user_selected(self):
        raise NotImplementedError( "Not implemented" )
    
    def set_lcd_backlight(self, level):
        self.lcd_backlight = level
       
    def set_contrast(self, level):
        self.contrast = level
    
    def set_keyboard_backlight(self, level):
        if self.get_keyboard_backlight_colours() == 3:
            pass
        else:
            hex_col = "#" + hex(level)[2:].zfill(6)
            self.keyboard_backlight = level
            map = self.main_window.get_colormap()
            colour = map.alloc_color(hex_col)
            style = self.main_window.get_style().copy()
            style.bg[gtk.STATE_NORMAL] = colour
            self.main_window.set_style(style)

    
    def set_mkey_lights(self, lights):
        self.lights = lights
    
    def grab_keyboard(self, callback):
        self.callback = callback;
    
