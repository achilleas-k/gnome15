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
from gnome15 import g15globals


'''
THIS HAS TURNED INTO A DUMPING GROUND AND NEEDS REFACTORING
'''

import g15globals as pglobals
from gnome15 import g15os
import gtk.gdk
import os
import gobject
import re
import cairo
import math
import dbus
import Image
import rsvg
import urllib
import base64
import xdg.Mime as mime

# Logging
import logging
logger = logging.getLogger("util")

from cStringIO import StringIO

from HTMLParser import HTMLParser
import threading

'''
GObject thread. Hosting applications may set this so that is_gobject_thread()
function works
'''
gobject_thread = [ None ]

'''
Lookup tables
'''
pt_to_px = { 
            6.0: 8.0, 
            7.0: 9, 
            7.5: 10, 
            8.0: 11, 
            9.0: 12, 
            10.0: 13, 
            10.5: 14, 
            11.0: 15, 
            12.0: 16, 
            13.0: 17, 
            13.5: 18, 
            14.0: 19, 
            14.5: 20, 
            15.0: 21, 
            16.0: 22, 
            17.0: 23, 
            18.0: 24, 
            20.0: 26, 
            22.0: 29, 
            24.0: 32, 
            26.0: 35, 
            27.0: 36, 
            28.0: 37, 
            29.0: 38, 
            30.0: 40, 
            32.0: 42, 
            34.0: 45, 
            36.0: 48
            }
px_to_pt = {}
for pt in pt_to_px:
    px_to_pt[pt_to_px[pt]] = pt


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
    
'''
GObject. Allows us to test if we are on the gobject loop
'''    
def is_gobject_thread():
    return threading.currentThread() == gobject_thread[0]

def set_gobject_thread():
    gobject_thread[0] = threading.currentThread()
    
'''
Markup utilities
'''
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

''' 
Date / time utilities
''' 
def total_seconds(time_delta):
    return (time_delta.microseconds + (time_delta.seconds + time_delta.days * 24.0 * 3600.0) * 10.0**6.0) / 10.0**6.0

'''
Various conversions
'''
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

'''
Thumbnails
'''
def paint_thumbnail_image(allocated_size, image, canvas):
    s = float(allocated_size) / image.get_height()
    canvas.save()
    canvas.scale(s, s)
    canvas.set_source_surface(image)
    canvas.paint()
    canvas.scale(1 / s, 1 / s)
    canvas.restore()
    return image.get_width() * s
    
'''
Various maths
'''
        
def get_scale(target, actual):
    scale = 1.0
    if target != None:
        if isinstance(target, int) or isinstance(target, float):
            sx = float(target) / actual[0]
            sy = float(target) / actual[1]
        else:
            sx = float(target[0]) / actual[0]
            sy = float(target[1]) / actual[1]
        scale = max(sx, sy)
    return scale

def approx_px_to_pt(px):
    px = round(px)
    if px in px_to_pt:
        return px_to_pt[px]
    else:
        return int(px * 72.0 / 96)

def split_args(args):
    return re.findall(r'\w+', args)

"""
Get the string name of the key given it's code
"""
def get_key_names(keys):
    key_names = []
    for key in keys:
        key_names.append((key[:1].upper() + key[1:].lower()).replace('-',' '))
    return key_names

"""
HTML utilities
"""

html_escape_table = {
                     "&": "&amp;",
                     '"': "&quot;",
                     "'": "&apos;",
                     ">": "&gt;",
                     "<": "&lt;",
                     }

def html_escape(text):
    return "".join(html_escape_table.get(c,c) for c in text)

"""
Property type files
"""

def parse_as_properties(properties_string):
    d = {}
    for l in properties_string.split("\n"):
        a = l.split("=")
        if len(a) > 1:
            d[a[0]] = a[1]
    return d

