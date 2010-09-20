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

G15_KEY_G1  = 1<<0
G15_KEY_G2  = 1<<1
G15_KEY_G3  = 1<<2
G15_KEY_G4  = 1<<3
G15_KEY_G5  = 1<<4
G15_KEY_G6  = 1<<5
G15_KEY_G7  = 1<<6
G15_KEY_G8  = 1<<7
G15_KEY_G9  = 1<<8
G15_KEY_G10 = 1<<9
G15_KEY_G11 = 1<<10
G15_KEY_G12 = 1<<11
G15_KEY_G13 = 1<<12
G15_KEY_G14 = 1<<13
G15_KEY_G15 = 1<<14
G15_KEY_G16 = 1<<15
G15_KEY_G17 = 1<<16
G15_KEY_G18 = 1<<17

G15_KEY_M1  = 1<<18
G15_KEY_M2  = 1<<19
G15_KEY_M3  = 1<<20
G15_KEY_MR  = 1<<21

G15_KEY_L1  = 1<<22
G15_KEY_L2  = 1<<23
G15_KEY_L3  = 1<<24
G15_KEY_L4  = 1<<25
G15_KEY_L5  = 1<<26

G15_KEY_LIGHT = 1<<27

class AbstractDriver(object):
    
    """
    Start the driver
    """
    def connect(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get the name of the driver
    """
    def get_name(self):
        raise NotImplementedError( "Not implemented" )
        
    """
    Get the size of the screen. Returns a tuple of (width, height)
    """
    def get_size(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get the grid dimensions of the g-key layout. This is currently only a hint for the Gtk driver
    """
    def get_gkey_layout(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get the bits per pixel. 1 would be monochrome
    """
    def get_bpp(self):
        raise NotImplementedError( "Not implemented")
    
    """
    Get the number of colours available for keyboard backlight (or brightness as it is on the G15)
    """
    def get_keyboard_backlight_colours(self):
        raise NotImplementedError( "Not implemented")
    
    """
    How many G keys are there
    """
    def get_gkeys(self):
        raise NotImplementedError( "Not implemented")
    
    """
    Repaint the screen. 
    """
    def paint(self, image):
        raise NotImplementedError( "Not implemented" )
    
    """
    Set whether Gnome15 is the currently active underlying driver screen
    (if it supports it). The default g15daemon does support this, but gnome15
    itself only ever requires one screen.
    """
    def switch_priorities(self):
        raise NotImplementedError( "Not implemented" )
        
    """
    Get whether Gnome15 is the currently active underlying driver screen
    (if it supports it). The default g15daemon does support this, but gnome15
    itself only ever requires one screen. 
    """
    def is_foreground(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Never let the user select the gnome15 screen. This only really applies to
    the g15daemon driver implementation which has this concept. See
    also is_foreground(), switch_priorities() and never_user_selected()
    """
    def never_user_selected(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Get whether Gnome15 was 'user selected'. This only really applies to
    the g15daemon driver implementation which has this concept. See
    also is_foreground(), switch_priorities() and never_user_selected()
    """
    def is_user_selected(self):
        raise NotImplementedError( "Not implemented" )
    
    """
    Set the LCD backlight level. This may be any integer from 0 to 2.
    """
    def set_lcd_backlight(self, level):
        raise NotImplementedError( "Not implemented" )
       
    """
    Set the LCD contrast level. This may be any integer from 0 to 2.
    """     
    def set_contrast(self, level):
        raise NotImplementedError( "Not implemented" )
    
    """
    Set the keyboard backlight level. This may be any integer from 0 to 2, a 24 bit integer
    or a tuple of RGB depending on what the device supports
    """     
    def set_keyboard_backlight(self, level):
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
    arguments, the first being the key code (see the constants G15_KEY_xx)
    and the second being the key state (KEY_STATE_DOWN or KEY_STATE_UP). 
    """    
    def grab_keyboard(self, callback):
        raise NotImplementedError( "Not implemented" )
    