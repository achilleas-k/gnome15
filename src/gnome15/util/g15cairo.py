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
Cairo utilities
Has functions to transform, load and convert cairo surfaces
'''

import gtk.gdk
import os, os.path
import cairo
import math
import rsvg
import urllib
import base64
import xdg.Mime as mime
import g15convert
import g15os
import gnome15.g15globals

# Logging
import logging
logger = logging.getLogger(__name__)

from cStringIO import StringIO

def rotate(context, degrees):
    context.rotate(g15convert.degrees_to_radians(degrees));
    
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
    
def get_cache_filename(filename, size = None):    
    cache_file = base64.urlsafe_b64encode("%s-%s" % ( filename, str(size if size is not None else "0,0") ) )
    g15os.mkdir_p(g15globals.user_cache_dir)
    return os.path.join(g15globals.user_cache_dir, "%s.img" % cache_file)
    
def get_image_cache_file(filename, size = None):
    full_cache_path = get_cache_filename(filename, size)
    if os.path.exists(full_cache_path):
        return full_cache_path
    
def is_url(path):
    # TODO try harder
    return "://" in path
    
def load_surface_from_file(filename, size = None):
    type = None
    if filename == None:
        logger.warning("Empty filename requested")
        return None
        
    if filename.startswith("http:") or filename.startswith("https:"):
        full_cache_path = get_image_cache_file(filename, size)
        if full_cache_path:
            meta_fileobj = open(full_cache_path + "m", "r")
            type = meta_fileobj.readline()
            meta_fileobj.close()
            if type == "image/svg+xml" or filename.lower().endswith(".svg"):
                return load_svg_as_surface(filename, size)
            else:
                return pixbuf_to_surface(gtk.gdk.pixbuf_new_from_file(full_cache_path), size)
                
    if is_url(filename):
        type = None
        try:
            file = urllib.urlopen(filename)
            data = file.read()
            type = file.info().gettype()
            
            if filename.startswith("file://"):
                type = str(mime.get_type(filename))
            
            if filename.startswith("http:") or filename.startswith("https:"):
                full_cache_path = get_cache_filename(filename, size)
                cache_fileobj = open(full_cache_path, "w")
                cache_fileobj.write(data)
                cache_fileobj.close()
                meta_fileobj = open(full_cache_path + "m", "w")
                meta_fileobj.write(type + "\n")
                meta_fileobj.close()
            
            if type == "image/svg+xml" or filename.lower().endswith(".svg"):
                svg = rsvg.Handle()
                try:
                    if not svg.write(data):
                        raise Exception("Failed to load SVG")
                    svg_size = svg.get_dimension_data()[2:4]
                    if size == None:
                        size = svg_size
                    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(size[0]) if not isinstance(size, int) else size, int(size[1]) if not isinstance(size, int) else size)
                    context = cairo.Context(surface)
                    if size != svg_size:
                        scale = get_scale(size, svg_size)
                        context.scale(scale, scale)
                    svg.render_cairo(context)
                    surface.flush()
                    return surface
                finally:
                    svg.close()
            else:                
                if type == "text/plain":
                    if filename.startswith("file://"):
                        pixbuf = gtk.gdk.pixbuf_new_from_file(filename[7:])
                        return pixbuf_to_surface(pixbuf, size)
                    raise Exception("Could not determine type")
                else:
                    pbl = gtk.gdk.pixbuf_loader_new_with_mime_type(type)
                    pbl.write(data)
                    pixbuf = pbl.get_pixbuf()
                    pbl.close()
                    return pixbuf_to_surface(pixbuf, size)
            return None
        except Exception as e:
            logger.warning("Failed to get image %s (%s).", filename, type, exc_info = e)
            return None
    else:
        if os.path.exists(filename):
            try:
                if filename.lower().endswith(".svg"):
                    if os.path.islink(filename):
                        filename = os.path.realpath(filename)
                    return load_svg_as_surface(filename, size)
                else:
                    return pixbuf_to_surface(gtk.gdk.pixbuf_new_from_file(filename), size)
            
            except Exception as e:
                logger.warning("Failed to get image %s (%s).", filename, type, exc_info = e)
                return None
            
def load_svg_as_surface(filename, size):
    svg = rsvg.Handle(filename)
    try:
        svg_size = svg.get_dimension_data()[2:4]
        if size == None:
            size = svg_size
        sx = int(size) if isinstance(size, int) or isinstance(size, float) else int(size[0])
        sy = int(size) if isinstance(size, int) or isinstance(size, float) else int(size[1])
        surface = cairo.ImageSurface(0, sx, sy)
        context = cairo.Context(surface)
        if size != svg_size:
            scale = get_scale(size, svg_size)
            context.scale(scale, scale)
        svg.render_cairo(context)
        return surface
    finally:
        svg.close()
    
def image_to_surface(image, type = "ppm"):
    # TODO make better
    return pixbuf_to_surface(image_to_pixbuf(image, type))
        
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
Convert a PIL image to a GDK pixbuf  
'''
def image_to_pixbuf(im, type = "ppm"):  
    p_type = type
    if type == "ppm":
        p_type = "pnm"
    file1 = StringIO()  
    try:
        im.save(file1, type)  
        contents = file1.getvalue()  
    finally:
        file1.close()  
    loader = gtk.gdk.PixbufLoader(p_type)  
    loader.write(contents, len(contents))  
    pixbuf = loader.get_pixbuf()  
    loader.close()  
    return pixbuf

def surface_to_pixbuf(surface):  
    try:
        file1 = StringIO()
        surface.write_to_png(file1) 
        contents = file1.getvalue() 
    finally:
        file1.close()   
    loader = gtk.gdk.PixbufLoader("png")  
    loader.write(contents, len(contents))  
    pixbuf = loader.get_pixbuf()  
    loader.close()  
    return pixbuf

def paint_thumbnail_image(allocated_size, image, canvas):
    s = float(allocated_size) / image.get_height()
    canvas.save()
    canvas.scale(s, s)
    canvas.set_source_surface(image)
    canvas.paint()
    canvas.scale(1 / s, 1 / s)
    canvas.restore()
    return image.get_width() * s

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

def approx_px_to_pt(px):
    px = round(px)
    if px in px_to_pt:
        return px_to_pt[px]
    else:
        return int(px * 72.0 / 96)

