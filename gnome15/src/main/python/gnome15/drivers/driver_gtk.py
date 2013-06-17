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

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("gnome15-drivers").ugettext

import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15ui_gconf as g15ui_gconf
import gnome15.g15cairo as g15cairo
import gnome15.g15icontools as g15icontools
import gnome15.g15globals as g15globals

import gconf

import os
import gtk.gdk
import gobject
import cairo

import Image
import ImageMath
import logging
logger = logging.getLogger("driver") 

# Driver information (used by driver selection UI)
id="gtk"
name=_("GTK Virtual Keyboard Driver")
description=_("A special development driver that emulates all supported, " + \
            "models as a window on your desktop. This allows " + \
            "you to develop plugins without having access to a real Logitech hardward ")
has_preferences=True

# Controls

g19_mkeys_control = g15driver.Control("mkeys", _("Memory Bank Keys"), 0, 0, 15, hint=g15driver.HINT_MKEYS)
g19_keyboard_backlight_control = g15driver.Control("backlight_colour", _("Keyboard Backlight Colour"), (0, 255, 0), hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
g19_lcd_brightness_control = g15driver.Control("lcd_brightness", _("LCD Brightness"), 100, 0, 100, hint = g15driver.HINT_SHADEABLE)
g19_foreground_control = g15driver.Control("foreground", _("Default LCD Foreground"), (255, 255, 255), hint = g15driver.HINT_FOREGROUND | g15driver.HINT_VIRTUAL)
g19_background_control = g15driver.Control("background", _("Default LCD Background"), (0, 0, 0), hint = g15driver.HINT_BACKGROUND | g15driver.HINT_VIRTUAL)
g19_highlight_control = g15driver.Control("highlight", _("Default Highlight Color"), (255, 0, 0), hint=g15driver.HINT_HIGHLIGHT | g15driver.HINT_VIRTUAL)

g15_mkeys_control = g15driver.Control("mkeys", _("Memory Bank Keys"), 1, 0, 15, hint=g15driver.HINT_MKEYS)
g15_backlight_control = g15driver.Control("keyboard_backlight", _("Keyboard Backlight Level"), 2, 0, 2, hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)
g15_invert_control = g15driver.Control("invert_lcd", _("Invert LCD"), 0, 0, 1, hint = g15driver.HINT_SWITCH )

g110_keyboard_backlight_control = g15driver.Control("backlight_colour", _("Keyboard Backlight Colour"), (255, 0, 0), hint = g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE | g15driver.HINT_RED_BLUE_LED)

controls = { 
  g15driver.MODEL_G11 : [ g15_mkeys_control, g15_backlight_control ], 
  g15driver.MODEL_G19 : [ g19_mkeys_control, g19_keyboard_backlight_control, g19_lcd_brightness_control, g19_foreground_control, g19_background_control, g19_highlight_control ], 
  g15driver.MODEL_G15_V1 : [ g15_mkeys_control, g15_backlight_control, g15_invert_control ], 
  g15driver.MODEL_G15_V2 : [ g15_mkeys_control, g15_backlight_control, g15_invert_control ],
  g15driver.MODEL_G13 : [ g15_mkeys_control, g15_backlight_control, g15_invert_control ],
  g15driver.MODEL_G510 : [ g15_mkeys_control, g19_keyboard_backlight_control, g15_invert_control ],
  g15driver.MODEL_Z10 : [ g15_backlight_control, g15_invert_control ],
  g15driver.MODEL_GAMEPANEL : [ g15_backlight_control, g15_invert_control ],
  g15driver.MODEL_G110 : [ g19_mkeys_control, g110_keyboard_backlight_control ],
  g15driver.MODEL_MX5500 : [ g15_invert_control ],
  g15driver.MODEL_G930 : [ ],
  g15driver.MODEL_G35 : [ ],
            }  

def show_preferences(device, parent, gconf_client):
    if device.model_id != 'virtual':
        return None
    g15locale.get_translation("driver_gtk")
    widget_tree = gtk.Builder()
    widget_tree.set_translation_domain("driver_gtk")
    widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "driver_gtk.glade")) 
    mode_model = widget_tree.get_object("ModeModel")
    mode_model.clear()
    for mode in g15driver.MODELS:
        mode_model.append([mode])    
    g15ui_gconf.configure_combo_from_gconf(gconf_client, "/apps/gnome15/%s/gtk_mode" % device.uid, "ModeCombo", g15driver.MODEL_G19, widget_tree)
    return widget_tree.get_object("DriverComponent")

class Driver(g15driver.AbstractDriver):

    def __init__(self, device, on_close = None):
        g15driver.AbstractDriver.__init__(self, "gtk")
        self.lights = 0
        self.main_window = None
        self.connected = False
        self.bpp = device.bpp
        self.lcd_size = device.lcd_size
        self.callback = None
        self.action_keys = None
        self.device = device
        self.area = None
        self.image = None
        self.buttons = {}
        self.event_box = None
        self.on_close = on_close
        self.conf_client = gconf.client_get_default()
        self.notify_handle = self.conf_client.notify_add("/apps/gnome15/%s/gtk_mode" % self.device.uid, self.config_changed)
        self._init_driver()
        
    def get_antialias(self):        
        if self.mode == g15driver.MODEL_G19:
            return cairo.ANTIALIAS_DEFAULT
        else: 
            return cairo.ANTIALIAS_NONE
        
    def config_changed(self, client, connection_id, entry, args):
        self._init_driver()
        if self.on_driver_options_change:
            self.on_driver_options_change()
        
    def is_connected(self):
        return self.connected
    
    def get_model_names(self):
        return [ 'virtual' ]
            
    def get_name(self):
        return _("GTK Keyboard Emulator Driver")
    
    def get_model_name(self):
        return self.mode
    
    def get_action_keys(self):
        return self.action_keys
        
    def get_key_layout(self):
        return self.key_layout
        
    def get_zoomed_size(self):
        zoom = self.get_zoom()
        return ( self.lcd_size[0] * zoom, self.lcd_size[1] * zoom )
        
    def get_zoom(self):
        if self.bpp == 16:
            return 1
        else:
            return 3
    
    def get_size(self):
        return self.lcd_size
        
    def get_bpp(self):
        return self.bpp
    
    def get_controls(self):
        return self.controls
    
    def paint(self, image):   
        
        if self.bpp != 0:
            width = self.lcd_size[0]
            height = self.lcd_size[1]
                 
            if self.bpp == 1:
                # Paint to 565 image provided into an ARGB image surface for PIL's benefit. PIL doesn't support 565?
                argb_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
                argb_context = cairo.Context(argb_surface)
                argb_context.set_source_surface(image)
                argb_context.paint()
                
                # Now convert the ARGB to a PIL image so it can be converted to a 1 bit monochrome image, with all
                # colours dithered. It would be nice if Cairo could do this :( Any suggestions? 
                pil_img = Image.frombuffer("RGBA", self.lcd_size, argb_surface.get_data(), "raw", "RGBA", 0, 1)
                pil_img = ImageMath.eval("convert(pil_img,'1')",pil_img=pil_img)
                pil_img = ImageMath.eval("convert(pil_img,'P')",pil_img=pil_img)
                pil_img = pil_img.point(lambda i: i >= 250,'1')
                
                invert_control = self.get_control("invert_lcd")
                if invert_control and invert_control.value == 1:            
                    pil_img = pil_img.point(lambda i: 1^i)
                    
                # Create drawable message
                pil_img = pil_img.convert("RGB")
                self.image = pil_img           
            else:
                # Take a copy of the image to prevent flickering
                argb_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
                argb_context = cairo.Context(argb_surface)
                argb_context.set_source_surface(image)
                argb_context.paint()
                self.image = argb_surface
            gobject.timeout_add(0, self.redraw)
            
    def process_svg(self, document):  
        if self.bpp == 1:
            for element in document.getroot().iter():
                style = element.get("style")
                if style != None:
                    element.set("style", style.replace("font-family:Sans","font-family:%s" % g15globals.fixed_size_font_name))
                    
    def redraw(self):
        if self.image != None and self.main_window is not None:
            if isinstance(self.image, cairo.Surface):
                self._draw_surface()
            else:
                self._draw_pixbuf()
            self.area.queue_draw()
        
    def on_update_control(self, control):
        gobject.idle_add(self._do_update_control, control)
    
    def grab_keyboard(self, callback):
        self.callback = callback;
        
    '''
    Private
    '''
    def _on_connect(self):
        self._init_driver()
        logger.info("Starting GTK driver")
        gobject.idle_add(self._init_ui)
        
    def _on_disconnect(self):
        logger.info("Disconnecting GTK driver")
        if not self.is_connected():
            raise Exception("Not connected")
        self.connected = False
        if self.on_close != None:
            self.on_close(self, retry=False)
        gobject.idle_add(self._close_window)
        
    def _simulate_key(self, widget, key, state):
        if self.callback != None:
            keys = []
            keys.append(key)
            self.callback(keys, state)
        
    def _do_update_control(self, control):
        if self.connected:   
            if control == self.get_control_for_hint(g15driver.HINT_MKEYS):
                self._do_set_mkey_lights()
            elif control == self.get_control_for_hint(g15driver.HINT_DIMMABLE):
                if isinstance(control.value, int):
                    v = ( 65535 / control.upper ) * control.value
                    self.event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(v, v, v))
                else:
                    self.event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(control.value[0] << 8, control.value[1] << 8, control.value[2] << 8))
        
    def _window_closed(self, window, evt):
        if self.main_window != None:
            self.conf_client.set_bool("/apps/gnome15/%s/enabled" % self.device.uid, False)

    def _do_set_mkey_lights(self):
        c = self.get_control_for_hint(g15driver.HINT_MKEYS)
        if c is not None and c.value is not None:
            if g15driver.G_KEY_M1 in self.buttons:
                self._modify_button(g15driver.G_KEY_M1, c.value, g15driver.MKEY_LIGHT_1)
            if g15driver.G_KEY_M2 in self.buttons:
                self._modify_button(g15driver.G_KEY_M2, c.value, g15driver.MKEY_LIGHT_2)
            if g15driver.G_KEY_M3 in self.buttons:
                self._modify_button(g15driver.G_KEY_M3, c.value, g15driver.MKEY_LIGHT_3)
            if g15driver.G_KEY_MR in self.buttons:
                self._modify_button(g15driver.G_KEY_MR, c.value, g15driver.MKEY_LIGHT_MR)
        
    def _modify_button(self, id, lights, mask):
        on = lights & mask != 0
        c = self.buttons[id]
        key_text = " ".join(g15util.get_key_names(list(id)))
        c.set_label("*%s" % key_text if on else "%s" % key_text)
        
    def _close_window(self):
        if self.main_window != None:
            w = self.main_window
            self.main_window = None
            w.hide()
            w.destroy()
        self.area = None
        
    def _mode_changed(self, client, connection_id, entry, args):
        if self.is_connected():
            gobject.idle_add(self.disconnect)
        else:
            logger.warning("Mode change would cause disconnect when already connected. %s" % str(entry) )
            
    def _draw_surface(self):
        # Finally paint the Cairo surface on the GTK widget
        zoom = self.get_zoom()
        width = self.lcd_size[0]
        height = self.lcd_size[1]
        if self.area != None and self.area.window != None:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, zoom * width, zoom * height)
            context = cairo.Context(surface)        
            context.set_antialias(self.get_antialias())
            context.scale(zoom, zoom)
            context.set_source_surface(self.image)
            context.paint()
            self.area.set_surface(surface)
            
    def _draw_pixbuf(self):
        width = self.lcd_size[0]
        height = self.lcd_size[1]
        zoom = self.get_zoom()
        pixbuf = g15cairo.image_to_pixbuf(self.image)
        pixbuf = pixbuf.scale_simple(zoom * width, zoom * height, 0)
        if self.area != None:
            self.area.set_pixbuf(pixbuf)
        
    def _init_driver(self):      
        logger.info("Initialising GTK driver")
        if self.device.model_id == 'virtual':
            self.mode = self.conf_client.get_string("/apps/gnome15/%s/gtk_mode" % self.device.uid)
        else:
            self.mode = self.device.model_id
        if self.mode == None or self.mode == "":
            self.mode = g15driver.MODEL_G19
        logger.info("Mode is now %s" % self.mode)
        self.controls = controls[self.mode]
        import gnome15.g15devices as g15devices
        device_info = g15devices.get_device_info(self.mode)
        self.bpp = device_info.bpp
        self.action_keys = device_info.action_keys
        self.lcd_size = device_info.lcd_size
        self.key_layout = device_info.key_layout
        logger.info("Initialised GTK driver")
        
    def _init_ui(self):
        logger.info("Initialising GTK UI")
        self.area = VirtualLCD(self)
        #self.area.connect("expose_event", self._expose)
        self.hboxes = []
        self.buttons = {}
        zoomed_size = self.get_zoomed_size()
        self.area.set_size_request(zoomed_size[0], zoomed_size[1])        
        self.vbox = gtk.VBox ()            
        self.vbox.add(self.area)
        rows = gtk.VBox()
        for row in self.get_key_layout():
            hbox = gtk.HBox()
            for key in row:
                key_text = " ".join(g15util.get_key_names(list(key)))
                g_button = gtk.Button(key_text)
                g_button.connect("pressed", self._simulate_key, key, g15driver.KEY_STATE_DOWN)
                g_button.connect("released", self._simulate_key, key, g15driver.KEY_STATE_UP)
                hbox.add(g_button)
                self.buttons[key] = g_button
            rows.add(hbox)
            
        self.event_box = gtk.EventBox()
        self.event_box.add(rows)
        self.vbox.add(self.event_box)
        
        self.main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.main_window.set_title("Gnome15") 
        self.main_window.set_icon_from_file(g15icontools.get_app_icon(self.conf_client, "gnome15"))
        self.main_window.add(self.vbox)
        self.main_window.connect("delete-event", self._window_closed)
        
        control = self.get_control_for_hint(g15driver.HINT_DIMMABLE) 
        if control:       
            if isinstance(control.value, int):
                v = ( 65535 / control.upper ) * control.value
                self.event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(v, v, v))
            else:
                self.event_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(control.value[0] << 8, control.value[1] << 8, control.value[2] << 8))
        
        self.main_window.show_all()
        logger.info("Initialised GTK UI")
        self.connected = True
        logger.info("Connected")
        
    def __del__(self):
        self.conf_client.notify_remove(self.notify_handle)
        
class VirtualLCD(gtk.DrawingArea):

    def __init__(self, driver):        
        self.__gobject_init__()
        self.driver = driver
        self.set_double_buffered(True)
        super(VirtualLCD, self).__init__()
        self.connect("expose-event", self._expose)
        self.buffer = None

    def _expose(self, widget, event):
        if not self.driver.is_connected():
            return
        cr = widget.window.cairo_create()
        cr.rectangle(event.area.x, event.area.y,
                     event.area.width, event.area.height)
        cr.clip()
            
        # Paint
        if self.buffer:
            cr.set_source_surface(self.buffer)
        cr.paint()
        
    def set_pixbuf(self, pixbuf):
        self.buffer = g15cairo.pixbuf_to_surface(pixbuf)
        
    def set_surface(self, surface):
        self.buffer = surface
#        self.window.begin_paint_rect((0, 0, zoom * width, zoom * height))
#        context = self.window.cairo_create()
#        context.set_source_surface(surface)
#        context.paint()
#        self.window.end_paint()
    
gobject.type_register(VirtualLCD)
    
