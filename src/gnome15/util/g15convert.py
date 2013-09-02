#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2010 Brett Smith <tanktarta@blueyonder.co.uk>
#  Copyright (C) 2013 Nuno Araujo <nuno.araujo@russo79.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
    # Currently this method is implemented in g15gconf so that it avoids
    # a dependency on g15convert.
    # g15convert depends on gtk, and when initializing the gtk module a
    # DISPLAY needs to be available.
    # Unfortunately, for running g15-system-service, there is no DISPLAY
    # set in it's environment, so it would make it throw an error.
    # See https://projects.russo79.com/issues/173
    import g15gconf
    return g15gconf._to_rgb(string_rgb, default)

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
    # Currently this method is implemented in g15driver so that it avoids
    # a dependency on g15convert.
    # g15convert depends on gtk, and when initializing the gtk module a
    # DISPLAY needs to be available.
    # Unfortunately, for running g15-system-service, there is no DISPLAY
    # set in it's environment, so it would make it throw an error.
    # See https://projects.russo79.com/issues/173
    import g15driver
    return g15driver.rgb_to_hex(rgb)

def degrees_to_radians(degrees):
    return degrees * (math.pi / 180.0)

