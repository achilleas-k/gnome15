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


'''
THIS HAS TURNED INTO A DUMPING GROUND AND NEEDS REFACTORING
'''

import g15_driver as g15driver
import gtk.gdk
import gobject
import array
import cairo
import struct
import math
import Image
import rsvg
from threading import Timer
import xdg.IconTheme as icons
import xdg.Config as config
from cStringIO import StringIO
from jobqueue import JobQueue


'''
Task scheduler. Tasks may be added to the queue to execute
after a specified interval. The timer is done by the gobject
event loop, which then executes the job on a different thread
'''
scheduled_tasks = JobQueue(name="ScheduledTasks")
class GTimer:    
    def __init__(self, interval, function, *args):
        self.source = gobject.timeout_add(int(interval * 1000), self.exec_item, function, *args)
        
    def exec_item(self, function, *args):
        scheduled_tasks.run(function, *args)
        
    def cancel(self, *args):
        gobject.source_remove(self.source)        

def schedule(name, interval, function, *args):
    timer = GTimer(interval, function, *args)
    return timer

'''
General utilities
'''
def value_or_empty(d, key):
    return value_or_default(d, key, [])

def value_or_blank(d, key):
    return value_or_default(d, key, "")

def value_or_default(d, key, default_value):
    try :
        return d[key]
    except KeyError:
        return default_value

''' 
Date / time utilities
''' 
def total_seconds(time_delta):
    return (time_delta.microseconds + (time_delta.seconds + time_delta.days * 24.0 * 3600.0) * 10.0**6.0) / 10.0**6.0

'''
Various conversions
'''
def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def degrees_to_radians(degrees):
    return degrees * (math.pi / 180.0)

'''
Cairo utilities
'''
    
def rotate(context, degrees):
    context.rotate(degrees_to_radians(degrees));
    
def rotate_around_center(context, width, height, degrees):    
    context.translate (height * 0.5, width * 0.5);
    context.rotate(degrees * (math.pi / 180));
    context.translate(-width * 0.5, -height * 0.5);

def flip_horizontal(context, width, height):    
    flip_hv_centered_on(context, -1, 1, width / 2, height / 2)

def flip_vertical(context, width, height):
    # TODO - Should work according to http://cairographics.org/matrix_transform/, but doesn't
    flip_hv_centered_on(context, -1, 1, width / 2, height / 2)
    
def flip_hv_centered_on(context, fx, fy, cx, cy):    
    mtrx = cairo.Matrix(fx,0,0,fy,cx*(1-fx),cy*(fy-1))
    context.transform(mtrx)

def load_surface_from_file(filename, size = None):
    if filename.endswith(".svg"):
        svg = rsvg.Handle(filename)
        svg_size = svg.get_dimension_data()[2:4]
        if size == None:
            size = svg_size
        surface = cairo.ImageSurface(0, int(size[0]), int(size[1]))
        context = cairo.Context(surface)
        if size != svg_size:
            scale = get_scale(size, svg_size)
            context.scale(scale, scale)
        svg.render_cairo(context)
        return surface, context
    else:
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        x = pixbuf.get_width()
        y = pixbuf.get_height()
        scale = get_scale(size, (x, y))        
        surface = cairo.ImageSurface(0, int(x * scale), int(y * scale))
        context = cairo.Context(surface)
        gdk_context = gtk.gdk.CairoContext(context)
        if size != None:
            gdk_context.scale(scale, scale)
        gdk_context.set_source_pixbuf(pixbuf,0,0)
        gdk_context.paint()
        gdk_context.scale(1 / scale, 1 / scale)
        return surface, context
    
'''
Icon utilities
'''

def get_icon_path(gconf_client, icon, size = None):
    icon_theme = gconf_client.get_string("/desktop/gnome/interface/icon_theme")
    if size == None:
        size = 128
    i_size = size
    if not isinstance(size, int):
        i_size = max(size[0], size[1])
    real_icon_file = icons.getIconPath(icon, theme=icon_theme, size = i_size)
    if real_icon_file != None:
        return real_icon_file


def get_icon(gconf_client, icon, size = None):
    real_icon_file = get_icon_path(gconf_client, icon, size)
    if real_icon_file != None:
        if real_icon_file.endswith(".svg"):
            pixbuf = gtk.gdk.pixbuf_new_from_file(real_icon_file)            
            scale = get_scale(size, (pixbuf.get_width(), pixbuf.get_height()))
            if scale != 1.0:
                pixbuf = pixbuf.scale_simple(pixbuf.get_width() * scale, pixbuf.get_height() * scale, gtk.gdk.INTERP_BILINEAR)
            img = Image.fromstring("RGBA", (pixbuf.get_width(), pixbuf.get_height()), pixbuf.get_pixels())
        else:           
            img = Image.open(real_icon_file)            
            scale = get_scale(size, img.size)
            if scale != 1.0:
                img = img.resize((img.size[0] * scale, img.size[1] * scale),Image.BILINEAR)
                
        return img
    
'''
Various maths
'''
        
def get_scale(target, actual):
    scale = 1.0
    if target != None:
        if isinstance(target, int):
            sx = float(target) / actual[0]
            sy = float(target) / actual[1]
        else:
            sx = float(target[0]) / actual[0]
            sy = float(target[1]) / actual[1]
        scale = max(sx, sy)
    return scale

'''
SVG utilties
'''

def rotate_element(element, degrees):
    transforms = get_transforms(element)
    if len(transforms) > 0:
        t = transforms[0]
        for i in range(1, len(transforms)):
            t = t.multiply(transforms[i])
    else: 
        t = cairo.Matrix()
        
    t.rotate(degrees_to_radians(degrees))
    ts = "m" + str(t)[7:]
    element.set("transform", ts)

def get_transforms(element, position_only = False):    
    transform_val = element.get("transform")
    list = []
    if transform_val != None:
        start = 0
        while True:
            start_args = transform_val.find("(", start)
            if start_args == -1:
                break
            name = transform_val[:start_args].lstrip()
            end_args = transform_val.find(")", start_args)
            if end_args == -1:
                break
            args = transform_val[start_args + 1:end_args].split(",")
            if name == "translate":
                list.append(cairo.Matrix(1.0, 0.0, 0.0, 1.0, float(args[0]), float(args[1])))
            elif name == "matrix":
                if position_only:
                    list.append(cairo.Matrix(float(args[0]), float(args[1]), float(args[2]), float(args[3]),float(args[4]),float(args[5])))
                else:
                    list.append(cairo.Matrix(1, 0, 0, 1, float(args[4]),float(args[5])))
            else:
                print "Unspported transform %s" % name
            start = end_args + 1
                
    return list

def get_location(element):        
    list = []
    while element != None:
        x = element.get("x")        
        y = element.get("y")
        if x != None and y != None:
            list.append((float(x), float(y)))
        transform_val = element.get("transform")
        if transform_val != None:
            start = 0
            while True:
                start_args = transform_val.find("(", start)
                if start_args == -1:
                    break
                name = transform_val[:start_args].lstrip()
                end_args = transform_val.find(")", start_args)
                if end_args == -1:
                    print "Unexpected end of transform arguments"
                    break
                args = transform_val[start_args + 1:end_args].split(",")
                if name == "translate":
                    list.append((float(args[0]), float(args[1])))
                elif name == "matrix":
                    list.append((float(args[4]),float(args[5])))
                else:
                    print "Unspported transform %s" % name
                start = end_args + 1
        element = element.getparent()
    list.reverse()
    x = 0
    y = 0
    for i in list:
        x += i[0]
        y += i[1]  
    return (x, y)

def get_actual_bounds(element):
    id = element.get("id")
    transforms = []
    bounds = get_bounds(element)
    while element != None:
        transforms += get_transforms(element, position_only=True)
        element = element.getparent()
    transforms.reverse()
    if len(transforms) > 0:
        t = transforms[0]
        for i in range(1, len(transforms)):
            t = t.multiply(transforms[i])
    else:
        t = cairo.Matrix()
    t.translate(bounds[0],bounds[1])
    args = str(t)[13:-1].split(", ")
    b = (float(args[4]),float(args[5]),bounds[2],bounds[3])
    return b

def get_bounds(element):
    x = 0.0
    y = 0.0
    w = 0.0
    h = 0.0
    v = element.get("x")
    if v != None:
        x = float(v)
    v = element.get("y")
    if v != None:
        y = float(v)
    v = element.get("width")
    if v != None:
        w = float(v)
    v = element.get("height")
    if v != None:
        h = float(v)
    return (x, y, w, h)

'''
Convert a PIL image to a GDK pixbuf  
'''
def image_to_pixbuf(im):  
    file1 = StringIO()  
    im.save(file1, "ppm")  
    contents = file1.getvalue()  
    file1.close()  
    loader = gtk.gdk.PixbufLoader("pnm")  
    loader.write(contents, len(contents))  
    pixbuf = loader.get_pixbuf()  
    loader.close()  
    return pixbuf

'''
Convert a PIL image to a Cairo surface 
'''
def image_to_surface(img):
#    sio = StringIO()
#    
#    # PIL is RGBa. Cairo uses aRGB native endian
#    for i in img.getdata():
#        sio.write("%c%c%c%c" % ( i[2],i[1],i[0],i[3]) )
#    imgd = sio.getvalue()

#    imgd = img.tostring("raw","ARGB",0,1)
#    arr = array.array('B',imgd)
#    img_surface = cairo.ImageSurface.create_for_data(arr, g15driver.CAIRO_IMAGE_FORMAT, img.size[0], img.size[1])
#    return img_surface
    arr = array.array('B',img.tostring())
    img_surface = cairo.ImageSurface.create_for_data(arr, cairo.FORMAT_ARGB32, img.size[0], img.size[1])

    
#    timer = Timer(interval, function, args, kwargs)
#    timer.name = name
#    timer.setDaemon(True)
#    timer.start()
#    return timer

"""
Get the string name of the key given it's code
"""
def get_key_names(keys):
    key_names = []
    for key in keys:
        key_names.append((key[:1].upper() + key[1:]).replace('-',' '))
    return key_names