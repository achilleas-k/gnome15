############################################################################
##
## Copyright (C), all rights reserved:
##      2010 Brett Smith <tanktarta@blueyonder.co.uk>
##      2013 Nuno Araujo <nuno.araujo@russo79.com>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License version 2
##
## Gnome15 - Suite of GNOME applications that work with the logitech G15
##           keyboard
##
############################################################################

'''
Various conversions
'''

import gtk.gdk
import math

def rgb_to_string(rgb):
    if rgb == None:
        return None
    else:
        return "%d,%d,%d" % rgb

def get_alt_color(color):
    if color[0] == color[1] == color[2]:
        return (1.0-color[0], 1.0-color[1], 1.0-color[2], color[3])
    else:
        return (color[1],color[2],color[0],color[3])

def color_to_rgb(color):
    i = ( color.red >> 8, color.green >> 8, color.blue >> 8 )
    return ( i[0],i[1],i[2] )

def to_rgb(string_rgb, default = None):
    if string_rgb == None or string_rgb == "":
        return default
    rgb = string_rgb.split(",")
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]))

def to_pixel(rgb):
    return ( rgb[0] << 24 ) + ( rgb[1] << 16 ) + ( rgb[2] < 8 ) + 0

def to_color(rgb):
    return gtk.gdk.Color(rgb[0] <<8, rgb[1] <<8,rgb[2] <<8)

def rgb_to_uint16(r, g, b):
    rBits = r * 32 / 255
    gBits = g * 64 / 255
    bBits = b * 32 / 255

    rBits = rBits if rBits <= 31 else 31
    gBits = gBits if gBits <= 63 else 63
    bBits = bBits if bBits <= 31 else 31

    valueH = (rBits << 3) | (gBits >> 3)
    valueL = (gBits << 5) | bBits

    return chr(valueL & 0xff) + chr(valueH & 0xff)

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def degrees_to_radians(degrees):
    return degrees * (math.pi / 180.0)

