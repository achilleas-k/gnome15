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

"""
Bitmask values for setting the M key LED lights. See set_mkey_lights()
"""
MKEY_LIGHT_1 = 1<<0
MKEY_LIGHT_2 = 1<<1
MKEY_LIGHT_3 = 1<<2
MKEY_LIGHT_MR = 1<<3

"""
Constants for key codes
"""
KEY_STATE_UP = 0
KEY_STATE_DOWN = 1

"""
G keys

G15v1 - G1-G18
G15v1 - G1-G18
G13 - G1-22
G19 - G1-G12
"""
G_KEY_G1  = "g1"
G_KEY_G2  = "g2"
G_KEY_G3  = "g3"
G_KEY_G4  = "g4"
G_KEY_G5  = "g5"
G_KEY_G6  = "g6"
G_KEY_G7  = "g7"
G_KEY_G8  = "g8"
G_KEY_G9  = "g9"
G_KEY_G10 = "g10"
G_KEY_G11 = "g11"
G_KEY_G12 = "g12"
G_KEY_G13 = "g13"
G_KEY_G14 = "g14"
G_KEY_G15 = "g15"
G_KEY_G16 = "g16"
G_KEY_G17 = "g17"
G_KEY_G18 = "g18"
G_KEY_G19 = "g19"
G_KEY_G20 = "g20"
G_KEY_G21 = "g21"
G_KEY_G22 = "g22"


"""
Display keys
"""
G_KEY_BACK = "back"
G_KEY_DOWN = "down"
G_KEY_LEFT = "left"
G_KEY_MENU = "menu"
G_KEY_OK = "ok"
G_KEY_RIGHT = "right"
G_KEY_SETTINGS = "settings"
G_KEY_UP = "up"

"""
M keys. On all models
"""
G_KEY_M1  = "m1"
G_KEY_M2  = "m2"
G_KEY_M3  = "m3"
G_KEY_MR  = "mr"

"""
L-Keys. On g15v1, v2, g13 and g19. NOT on g110 
"""
G_KEY_L1  = "l1"
G_KEY_L2  = "l2"
G_KEY_L3  = "l3"
G_KEY_L4  = "l4"
G_KEY_L5  = "l5"

"""
Light key. On all models
"""
G_KEY_LIGHT = "light"

"""
Multimedia keys
"""
G_KEY_WINKEY_SWITCH = "win"
G_KEY_NEXT = "next"
G_KEY_PREV = "prev"
G_KEY_STOP = "stop"
G_KEY_PLAY = "play"
G_KEY_MUTE = "mute"
G_KEY_VOL_UP = "vol-up"
G_KEY_VOL_DOWN = "vol-down"

"""
G110 only
"""
G_KEY_MIC_MUTE = "mic-mute"
G_KEY_HEADPHONES_MUTE = "headphones-mute"

"""
Models
"""
MODEL_G15_V1 = "g15v1"
MODEL_G15_V2 = "g15v2"
MODEL_G13 = "g13"
MODEL_G19 = "g19"
MODEL_G510 = "g510"
MODEL_G510_AUDIO = "g510audio"
MODEL_G110 = "g110"
MODEL_Z10 = "z10"

MODELS = [ MODEL_G15_V1, MODEL_G15_V2, MODEL_G13, MODEL_G19, MODEL_G510, MODEL_G510_AUDIO, MODEL_G110, MODEL_Z10 ]

HINT_DIMMABLE = 1 << 0
HINT_SHADEABLE = 1 << 1
HINT_FOREGROUND = 1 << 2
HINT_BACKGROUND = 1 << 3
HINT_SWITCH = 1 << 4

# 16bit 565
CAIRO_IMAGE_FORMAT=4

import g15util as g15util

seq_no = 0

class Control():
    
    def __init__(self, id, name, value = 0.0, lower = 0.0, upper = 255.0, hint = 0):
        self.id = id
        self.hint = hint
        self.name = name
        self.lower = lower
        self.upper = upper
        self.value = value
        
class AbstractDriver(object):
    
    def __init__(self, id):
        self.id = id
        global seq_no
        seq_no += 1
        self.seq = seq_no
        self.control_update_listeners = []
    
    """
    Start the driver
    """
    def connect(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Stop the driver
    """
    def disconnect(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get if driver is connected
    """
    def is_connected(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get the name of the driver
    """
    def get_name(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get a list of the model names this driver supports
    """
    def get_model_names(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get the model name that this driver is connected to
    """
    def get_model_name(self):
        raise NotImplementedError( "Not implemented" )
        
    """
    Get the size of the screen. Returns a tuple of (width, height)
    """
    def get_size(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get the grid the extra keys available on this keyboard. This is currently only a hint for the Gtk driver
    """
    def get_key_layout(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get the bits per pixel. 1 would be monochrome
    """
    def get_bpp(self):
        raise NotImplementedError( "Not implemented")
    
    """
    Get the all of the controls available. This would include things such as LCD contrast, LCD brightness,
    keyboard colour, keyboard backlight etc
    """
    def get_controls(self):
        raise NotImplementedError( "Not implemented")
    
    """
    Repaint the screen. 
    """
    def paint(self, image):
        raise NotImplementedError( "Not implemented" )
    
    """
    Synchronize a control with the keyboard. For example, if the control was for the
    keyboard colour, the keyboard colour would actually change when this function
    is invoked
    
    Subclasses should not override this function, instead they should implement
    on_update_control()
    """
    def update_control(self, control):
        for l in self.control_update_listeners:
            l.control_updated(control)
        self.on_update_control(control)
    
    def on_update_control(self, control):
        raise NotImplementedError( "Not implemented" )
                
        
    """
    Set the M key LCD lights. The value is a bitmask made up of MKEY_LIGHT1,
    MKEY_LIGHT2, MKEY_LIGHT3 and MKEY_LIGHT_MR      
    """    
    def set_mkey_lights(self, lights):
        raise NotImplementedError( "Not implemented" )
    
    """
    Start receiving events when the additional keys (G keys, L keys and M keys)
    are pressed and released. The provided callback will be invoked with two
    arguments, the first being the key code (see the constants G_KEY_xx)
    and the second being the key state (KEY_STATE_DOWN or KEY_STATE_UP). 
    """    
    def grab_keyboard(self, callback):
        raise NotImplementedError( "Not implemented" )
    
    """
    Give the driver a chance to alter a theme's SVG. This has been introduced to work
    around a problem of Inkscape (the recommended 'IDE' for designing themes),
    does not saving bitmap font names
    """
    def process_svg(self, document):
        raise NotImplementedError( "Not implemented" )
        
    '''
    Utilities
    '''
    def get_control(self, id):
        controls = self.get_controls()
        if controls:
            for control in self.get_controls():
                if id == control.id:
                    return control
            
    def get_control_for_hint(self, hint):
        controls = self.get_controls()
        if controls:
            for control in self.get_controls():
                if ( hint & control.hint ) == hint:
                    return control
        
    def set_controls_from_configuration(self, conf_client):
        controls = self.get_controls()
        if controls:
            for control in controls:
                self.set_control_from_configuration(control, conf_client)
            
    def set_control_from_configuration(self, control, conf_client):
        entry = conf_client.get("/apps/gnome15/" + control.id)
        if entry != None:
            if isinstance(control.value, int):
                control.value = entry.get_int()
            else:
                rgb = entry.get_string().split(",")
                control.value = (int(rgb[0]),int(rgb[1]),int(rgb[2]))
    
    def get_color_as_ratios(self, hint, default):
        fg_control = self.get_control_for_hint(hint)
        fg_rgb = default
        if fg_control != None:
            fg_rgb = fg_control.value
        return ( float(fg_rgb[0]) / 255.0,float(fg_rgb[1]) / 255.0,float(fg_rgb[2]) / 255.0 )
    
    def get_color_as_hexrgb(self, hint, default):
        fg_control = self.get_control_for_hint(hint)
        fg_rgb = default
        if fg_control != None:
            fg_rgb = fg_control.value
        return g15util.rgb_to_hex(fg_rgb)
    
    def get_color(self, hint, default):
        fg_control = self.get_control_for_hint(hint)
        fg_rgb = default
        if fg_control != None:
            fg_rgb = fg_control.value
        return fg_rgb
    