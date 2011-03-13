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
import g15_globals as pglobals
import gtk.gdk
import gobject
import os
import cairo
import pangocairo
import pango
import math
import Image
import rsvg
import urllib
import base64
import sys
import traceback

# Logging
import logging
logger = logging.getLogger("util")

from cStringIO import StringIO
import jobqueue
from threading import Thread

''' 
Default scheduler
'''
scheduler = jobqueue.JobScheduler()

'''
Look for icons locally as well if running from source
'''
gtk_icon_theme = gtk.icon_theme_get_default()
if pglobals.dev:
    gtk_icon_theme.prepend_search_path(pglobals.icons_dir)
    
'''
Executing stuff
'''

def run_script(script, args = None, background = True):
    a = ""
    if args:
        for arg in args:
            a += "\"%s\"" % arg
    p = os.path.realpath(os.path.join(pglobals.scripts_dir,script))
    logger.info("Running '%s'" % p)
    os.system("python \"%s\" %s %s" % ( p, a, " &" if background else "" ))


'''
GConf stuff
'''
        
def configure_colorchooser_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, default_alpha = None):
    widget = widget_tree.get_object(widget_id)
    if widget == None:
        raise Exception("No widget with id %s." % widget_id)
    val = gconf_client.get_string(gconf_key)
    if val == None or val == "":
        col  = to_color(default_value)
    else:   
        col = to_color(to_rgb(val))
    if default_alpha != None:
        alpha = gconf_client.get_int(gconf_key + "_opacity")
        widget.set_use_alpha(True)
        widget.set_alpha(alpha << 8)
    else:
        widget.set_use_alpha(False)
    widget.set_color(col)
    widget.connect("color-set", color_changed, gconf_client, gconf_key)
    
def to_cairo_rgba(gconf_client, key, default):
    str_val = gconf_client.get_string(key)
    if str_val == None or str_val == "":
        val = default
    else:
        v = to_rgb(str_val)
        alpha = gconf_client.get_int(key + "_opacity")
        val = ( v[0], v[1],v[2], alpha)
    return (float(val[0]) / 255.0, float(val[1]) / 255.0, float(val[2]) / 255.0, float(val[3]) / 255.0)
    
def color_changed(widget, gconf_client, key):
    val = widget.get_color()
    gconf_client.set_string(key, "%d,%d,%d" % ( val.red >> 8, val.green >> 8, val.blue >> 8 ))
    if widget.get_use_alpha():
        gconf_client.set_int(key + "_opacity", widget.get_alpha() >> 8)
        
def rgb_to_string(rgb):
    if rgb == None:
        return None
    else:
        return "%d,%d,%d" % rgb
    
def color_to_rgb(color):         
    i = ( color.red >> 8, color.green >> 8, color.blue >> 8 )
    return ( i[0],i[1],i[2] )
        
def to_rgb(string_rgb, default = None):
    if string_rgb == None or string_rgb == "":
        return default
    rgb = string_rgb.split(",")
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        
def to_color(rgb):
    return gtk.gdk.Color(rgb[0] <<8, rgb[1] <<8,rgb[2] <<8)
    
def spinner_changed(widget, gconf_client, key, model, decimal = False):
    if decimal:
        gconf_client.set_float(key, widget.get_value())
    else:
        gconf_client.set_int(key, widget.get_value())
        
def configure_spinner_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, decimal = False):
    widget = widget_tree.get_object(widget_id)
    if widget == None:
        raise Exception("No widget with id %s." % widget_id)
    model = widget.get_adjustment()
    entry = gconf_client.get(gconf_key)
    val = default_value
    if entry != None:
        if decimal:
            val = entry.get_float()
        else:
            val = entry.get_int()
    model.set_value(val)
    widget.connect("value-changed", spinner_changed, gconf_client, gconf_key, model)

def configure_combo_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree):
    widget = widget_tree.get_object(widget_id)
    if widget == None:
        raise Exception("No widget with id %s." % widget_id)
    model = widget.get_model()
    widget.connect("changed", combo_box_changed, gconf_client, gconf_key, model)
    val = gconf_client.get_string(gconf_key)
    if val == None or val == "":
        val = default_value
    idx = 0
    for row in model:
        if row[0] == val:
            widget.set_active(idx)
        idx += 1
    
def combo_box_changed(widget, gconf_client, key, model):
    gconf_client.set_string(key, model[widget.get_active()][0])
    
def boolean_conf_value_change(client, connection_id, entry, args):
    widget, key = args
    widget.set_active( entry.get_value().get_bool())
        
def configure_checkbox_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, watch_changes = False):
    widget = widget_tree.get_object(widget_id)
    entry = gconf_client.get(gconf_key)
    if entry != None:
        widget.set_active(entry.get_bool())
    else:
        widget.set_active(default_value)
    widget.connect("toggled", checkbox_changed, gconf_key, gconf_client)
    if watch_changes:
        return gconf_client.notify_add(gconf_key, boolean_conf_value_change,( widget, gconf_key ));
        
def configure_adjustment_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree):
    adj = widget_tree.get_object(widget_id)
    entry = gconf_client.get(gconf_key)
    if entry != None:
        if isinstance(default_value, int):
            adj.set_value(entry.get_int())
        else:
            adj.set_value(entry.get_float())
    else:
        adj.set_value(default_value)
    adj.connect("value-changed", adjustment_changed, gconf_key, gconf_client, isinstance(default_value, int))
    
def adjustment_changed(adjustment, key, gconf_client, integer = True):
    if integer:
        gconf_client.set_int(key, int(adjustment.get_value()))
    else:
        gconf_client.set_float(key, adjustment.get_value())
    
def checkbox_changed(widget, key, gconf_client):
    gconf_client.set_bool(key, widget.get_active())
    
'''
Task scheduler. Tasks may be added to the queue to execute
after a specified interval. The timer is done by the gobject
event loop, which then executes the job on a different thread
'''

def clear_jobs(queue_name = None):
    scheduler.clear_jobs(queue_name)

def execute(queue_name, job_name, function, *args):
    scheduler.execute(queue_name, job_name, function, *args)

def schedule(job_name, interval, function, *args):
    return scheduler.schedule(job_name, interval, function, *args)

def queue(queue_name, job_name, interval, function, *args):    
    return scheduler.queue(queue_name, job_name, interval, function, *args)

def stop_all_schedulers():
    scheduler.stop_all()

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
    if filename == None:
        logger.warning("Empty filename requested")
        return None
    if "://" in filename:
        try:
            file = urllib.urlopen(filename)
            data = file.read()
            type = file.info().gettype()
            if filename.endswith(".svg"):
                svg = rsvg.Handle()
                svg.write(data)
                svg_size = svg.get_dimension_data()[2:4]
                if size == None:
                    size = svg_size
                surface = cairo.ImageSurface(0, int(size[0]), int(size[1]))
                context = cairo.Context(surface)
                if size != svg_size:
                    scale = get_scale(size, svg_size)
                    context.scale(scale, scale)
                svg.render_cairo(context)
                return surface
            else:
                pbl = gtk.gdk.pixbuf_loader_new_with_mime_type(type)
                pbl.write(data)
                pixbuf = pbl.get_pixbuf()
                pbl.close()
                return pixbuf_to_surface(pixbuf, size)
        except IOError as e:
            logger.warning("({})".format(e))
            return None
    else:
#        if filename.endswith(".svg"):
#            svg = rsvg.Handle(filename)
#            svg_size = svg.get_dimension_data()[2:4]
#            if size == None:
#                size = svg_size
#            surface = cairo.ImageSurface(0, int(size[0]), int(size[1]))
#            context = cairo.Context(surface)
#            if size != svg_size:
#                scale = get_scale(size, svg_size)
#                context.scale(scale, scale)
#            svg.render_cairo(context)
#            return surface, context
#        else:
#            return pixbuf_to_surface(gtk.gdk.pixbuf_new_from_file(filename), size)
        return pixbuf_to_surface(gtk.gdk.pixbuf_new_from_file(filename), size)
        
def pixbuf_to_surface(pixbuf, size = None):
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
    return surface
    
'''
Icon utilities
'''

def local_icon_or_default(icon_name, size = 128):
    return get_icon_path(icon_name, size)

def get_embedded_image_url(path):
    
    file_str = StringIO()
    img_data = StringIO()
    file_str.write("data:")
    
    if isinstance(path, cairo.Surface):
        # Cairo canvas
        file_str.write("image/png")
        path.write_to_png(img_data)
    else:
        if not "://" in path:
            # File
            surface = load_surface_from_file(path)
            file_str.write("image/png")
            surface.write_to_png(img_data)
        else:
            # URL        
            pagehandler = urllib.urlopen(path)
            file_str.write(pagehandler.info().gettype())
            while 1:
                data = pagehandler.read(512)
                if not data:
                    break
                img_data.write(data)
    
    file_str.write(";base64,")
    file_str.write(base64.b64encode(img_data.getvalue()))
    return file_str.getvalue()

def get_icon_path(icon = None, size = 128):
    o_icon = icon
    if isinstance(icon, list):
        for i in icon:
            p = get_icon_path(i, size)
            if p != None:
                return p
    else:
        icon = gtk_icon_theme.lookup_icon(icon, size, 0)
        if icon != None:
            if icon.get_filename() == None:
                logger.warning("Found icon %s (%d), but no filename was available" % ( o_icon, size ))
            return icon.get_filename()
        else:
            if os.path.isfile(o_icon):
                return o_icon
            else:
                logger.warning("Icon %s (%d) not found" % ( o_icon, size ))
    
def get_app_icon(gconf_client, icon, size = 128):
    icon_path = get_icon_path(icon, size)
    if icon_path == None:
        icon_path = gtk.gdk.pixbuf_new_from_file(os.path.join(pglobals.icons_dir, icon + '.svg'))
    return icon_path

def get_icon(gconf_client, icon, size = None):
    real_icon_file = get_icon_path(icon, size)
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
Thumbnails
'''
def paint_thumbnail_image(allocated_size, image, canvas):
    s = float(allocated_size) / image.get_height()
    canvas.scale(s, s)
    canvas.set_source_surface(image)
    canvas.paint()
    canvas.scale(1 / s, 1 / s)
    return image.get_width() * s
    
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
Pango
'''
             
def create_pango_context(canvas, screen, text, wrap = None, align = None, width = None, spacing = None, font_desc = None, font_absolute_size = None):
    pango_context = pangocairo.CairoContext(canvas)
    
    # Font options, set anti-alias
    pango_context.set_antialias(screen.driver.get_antialias()) 
    fo = cairo.FontOptions()
    fo.set_antialias(screen.driver.get_antialias())
    if screen.driver.get_antialias() == cairo.ANTIALIAS_NONE:
        fo.set_hint_style(cairo.HINT_STYLE_NONE)
        fo.set_hint_metrics(cairo.HINT_METRICS_OFF)                
    layout = pango_context.create_layout()            
    pangocairo.context_set_font_options(layout.get_context(), fo)
    
    # Font
    font_desc = pango.FontDescription("Sans 10" if font_desc == None else font_desc)
    if font_absolute_size != None:
        font_desc.set_absolute_size(font_absolute_size)
    layout.set_font_description(font_desc)
    
    # Layout
    if align != None:
        layout.set_alignment(align)
    if spacing != None:
        layout.set_spacing(spacing)
    if width != None:
        layout.set_width(width)
    if wrap != None:
        layout.set_wrap(wrap)      
    layout.set_text(text)
    canvas.set_source_rgb(*screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 )))
    return pango_context, layout

def get_extents(layout):
    text_extents = layout.get_extents()[1]
    return text_extents[0] / pango.SCALE, text_extents[1] / pango.SCALE, text_extents[2] / pango.SCALE, text_extents[3] / pango.SCALE 

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
                logger.warning("Unspported transform %s" % name)
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
                    logger.warning("Unexpected end of transform arguments")
                    break
                args = transform_val[start_args + 1:end_args].split(",")
                if name == "translate":
                    list.append((float(args[0]), float(args[1])))
                elif name == "matrix":
                    list.append((float(args[4]),float(args[5])))
                else:
                    logger.warning("WARNING: Unsupported transform %s" % name)
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
def image_to_pixbuf(im, type = "ppm"):  
    p_type = type
    if type == "ppm":
        p_type = "pnm"
    file1 = StringIO()  
    im.save(file1, type)  
    contents = file1.getvalue()  
    file1.close()  
    loader = gtk.gdk.PixbufLoader(p_type)  
    loader.write(contents, len(contents))  
    pixbuf = loader.get_pixbuf()  
    loader.close()  
    return pixbuf

def surface_to_pixbuf(surface):  
    file1 = StringIO()
    surface.write_to_png(file1) 
    contents = file1.getvalue()  
    file1.close()  
    loader = gtk.gdk.PixbufLoader("png")  
    loader.write(contents, len(contents))  
    pixbuf = loader.get_pixbuf()  
    loader.close()  
    return pixbuf

def Xsurface_to_pixbuf(surface):
    return gtk.gdk.pixbuf_new_from_data(surface.get_data(), gtk.gdk.COLORSPACE_RGB, True, 8, surface.get_width(), surface.get_height(), surface.get_width() * 4)

"""
Get the string name of the key given it's code
"""
def get_key_names(keys):
    key_names = []
    for key in keys:
        key_names.append((key[:1].upper() + key[1:].lower()).replace('-',' '))
    return key_names