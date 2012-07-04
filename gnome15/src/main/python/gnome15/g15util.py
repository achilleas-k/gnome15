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
from gnome15 import g15globals


'''
THIS HAS TURNED INTO A DUMPING GROUND AND NEEDS REFACTORING
'''

import g15globals as pglobals
import gtk.gdk
import os
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
import jobqueue

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
    
def execute_for_output(cmd):
    pipe = os.popen('{ ' + cmd + '; } 2>/dev/null', 'r')
    text = pipe.read()
    sts = pipe.close()
    if sts is None: sts = 0
    if text[-1:] == '\n': text = text[:-1]
    return sts, text

def run_script(script, args = None, background = True):
    a = ""
    if args:
        for arg in args:
            a += "\"%s\"" % arg
    p = os.path.realpath(os.path.join(pglobals.scripts_dir,script))
    logger.info("Running '%s'" % p)
    return os.system("python \"%s\" %s %s" % ( p, a, " &" if background else "" ))

def attr_exists(obj, attr_name):
    """
    Get if an attribute exists on an object
    
    Keyword arguments:
    obj            -- object
    attr_name      -- attribute name
    """    
    return getattr(obj, attr_name, None) is not None

def call_if_exists(obj, function_name, *args):
    """
    Call a function on an object if it exists, ignoring any errors if it doesn't
    """
    func = getattr(obj, function_name, None)
    if callable(func):
        func(*args)


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
    
def spinner_changed(widget, gconf_client, key, model, decimal = False):
    if decimal:
        gconf_client.set_float(key, widget.get_value())
    else:
        gconf_client.set_int(key, int(widget.get_value()))
        
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
    widget.connect("changed", combo_box_changed, gconf_client, gconf_key, model, default_value)
    
    if isinstance(default_value, int):
        e = gconf_client.get(gconf_key)
        if e:
            val = e.get_int()
        else:
            val = default_value
    else:
        val = gconf_client.get_string(gconf_key)
        if val == None or val == "":
            val = default_value
    idx = 0
    for row in model:
        if isinstance(default_value, int):
            row_val = int(row[0])
        else:
            row_val = str(row[0])
        if row_val == val:
            widget.set_active(idx)
        idx += 1
    
def combo_box_changed(widget, gconf_client, key, model, default_value):
    if isinstance(default_value, int):
        gconf_client.set_int(key, int(model[widget.get_active()][0]))
    else:
        gconf_client.set_string(key, model[widget.get_active()][0])
    
def boolean_conf_value_change(client, connection_id, entry, args):
    widget, key = args
    widget.set_active( entry.get_value().get_bool())
    
def radio_conf_value_change(client, connection_id, entry, args):
    widget, key, gconf_value = args
    str_value = entry.get_value().get_string()
    widget.set_active(str_value == gconf_value)
        
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
        
def configure_radio_from_gconf(gconf_client, gconf_key, widget_ids , gconf_values, default_value, widget_tree, watch_changes = False):
    entry = gconf_client.get(gconf_key)
    handles = []
    sel_entry = entry.get_string() if entry else None
    for i in range(0, len(widget_ids)):
        gconf_value = gconf_values[i]
        active = ( entry != None and gconf_value == sel_entry ) or ( entry == None and default_value == gconf_value )
        widget_tree.get_object(widget_ids[i]).set_active(active)
        
    for i in range(0, len(widget_ids)):
        widget = widget_tree.get_object(widget_ids[i])
        widget.connect("toggled", radio_changed, gconf_key, gconf_client, gconf_values[i])
        if watch_changes:
            handles.append(gconf_client.notify_add(gconf_key, radio_conf_value_change,( widget, gconf_key, gconf_values[i] )))
    return handles
        
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
    
def radio_changed(widget, key, gconf_client, gconf_value):
    gconf_client.set_string(key, gconf_value)
    
'''
gconf utilities
'''
def get_float_or_default(gconf_client, key, default = None):
    float_val = gconf_client.get(key)
    return default if float_val == None else float_val.get_float()

def get_string_or_default(gconf_client, key, default = None):
    str_val = gconf_client.get(key)
    return default if str_val == None else str_val.get_string()

def get_bool_or_default(gconf_client, key, default = None):
    bool_val = gconf_client.get(key)
    return default if bool_val == None else bool_val.get_bool()

def get_int_or_default(gconf_client, key, default = None):
    int_val = gconf_client.get(key)
    return default if int_val == None else int_val.get_int()

def get_rgb_or_default(gconf_client, key, default = None):
    val = gconf_client.get_string(key)
    return default if val == None or val == "" else to_rgb(val)
    
'''
Task scheduler. Tasks may be added to the queue to execute
after a specified interval. The timer is done by the gobject
event loop, which then executes the job on a different thread
'''

def clear_jobs(queue_name = None):
    scheduler.clear_jobs(queue_name)

def execute(queue_name, job_name, function, *args):
    return scheduler.execute(queue_name, job_name, function, *args)

def schedule(job_name, interval, function, *args):
    return scheduler.schedule(job_name, interval, function, *args)

def stop_queue(queue_name):
    scheduler.stop_queue(queue_name)

def queue(queue_name, job_name, interval, function, *args):    
    return scheduler.queue(queue_name, job_name, interval, function, *args)

def stop_all_schedulers():
    scheduler.stop_all()
    
'''
GObject. Allows us to test if we are on the gobject loop
'''    
def is_gobject_thread():
    return threading.currentThread() == gobject_thread[0]

def set_gobject_thread():
    gobject_thread[0] = threading.currentThread()
    
'''
Distribution / version
'''
def get_lsb_release():
    ret, r = get_command_output('lsb_release -rs')
    return float(r) if ret == 0 else 0

def get_lsb_distributor():
    ret, r = get_command_output('lsb_release -is')
    return r if ret == 0 else "Unknown"

'''
General utilities
'''
    
def get_command_output( cmd):
    pipe = os.popen('{ ' + cmd + '; } 2>/dev/null', 'r')
    text = pipe.read()
    sts = pipe.close()
    if sts is None: sts = 0
    if text[-1:] == '\n': text = text[:-1]
    return sts, text
    
def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True
    
def value_or_empty(d, key):
    return value_or_default(d, key, [])

def value_or_blank(d, key):
    return value_or_default(d, key, "")

def value_or_default(d, key, default_value):
    try :
        return d[key]
    except KeyError:
        return default_value

def find(f, seq):
    """Return first item in sequence where f(item) == True."""
    for item in seq:
        if f(item): 
            return item

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        import errno
        if exc.errno == errno.EEXIST:
            pass
        else: raise

        
'''
Notification
'''
def notify(summary, body = "", icon = "dialog-info", actions = [], hints = {}, timeout  = 0):    
    session_bus = dbus.SessionBus()
    notification = dbus.Interface(session_bus.get_object("org.freedesktop.Notifications", '/org/freedesktop/Notifications'), "org.freedesktop.Notifications")
    def reph(return_args):
        pass
    def errh(exception):
        logger.error("Failed notification message. %s" % str(exception))
        
#    @dbus.service.method(IF_NAME, in_signature='susssasa{sv}i', out_signature='u')
#    def Notify(self, app_name, id, icon, summary, body, actions, hints, timeout):
    icon = icon if icon is not None else ""
    return notification.Notify(g15globals.name, 0, icon , summary, body, actions, hints, timeout, error_handler = errh, reply_handler = reph)
    
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
    
def get_cache_filename(filename, size = None):    
    cache_file = base64.urlsafe_b64encode("%s-%s" % ( filename, str(size if size is not None else "0,0") ) )
    cache_dir = os.path.expanduser("~/.cache/gnome15")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return "%s/%s.img" % ( cache_dir, cache_file )
    
def get_image_cache_file(filename, size = None):
    full_cache_path = get_cache_filename(filename, size)
    if os.path.exists(full_cache_path):
        return full_cache_path
    
def is_url(path):
    # TODO try harder
    return "://" in path
    
def load_surface_from_file(filename, size = None):
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
            logger.warning("Failed to get image %s (%s). %s" % (filename, type, e))
            return None
    else:
        if os.path.exists(filename):
            if filename.lower().endswith(".svg"):
                return load_svg_as_surface(filename, size)
            else:
                return pixbuf_to_surface(gtk.gdk.pixbuf_new_from_file(filename), size)
            
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
Icon utilities
'''

def local_icon_or_default(icon_name, size = 128):
    return get_icon_path(icon_name, size)

def get_embedded_image_url(path):
    
    file_str = StringIO()
    try:
        img_data = StringIO()
        try:
            file_str.write("data:")
            
            if isinstance(path, cairo.ImageSurface):
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
        finally:
            img_data.close()
    finally:
        file_str.close()

def get_icon_path(icon = None, size = 128, warning = True, include_missing = True):
    o_icon = icon
    if isinstance(icon, list):
        for i in icon:
            p = get_icon_path(i, size, warning = False, include_missing = False)
            if p != None:
                return p
        logger.warning("Icon %s (%d) not found" % ( str(icon), size ))
        if include_missing and not icon in [ "image-missing", "gtk-missing-image" ]:
            return get_icon_path(["image-missing", "gtk-missing-image"], size, warning)
    else:
        if icon != None:
            icon = gtk_icon_theme.lookup_icon(icon, size, 0)
        if icon != None:
            if icon.get_filename() == None and warning:
                logger.warning("Found icon %s (%d), but no filename was available" % ( o_icon, size ))
            fn = icon.get_filename()
            if os.path.isfile(fn):
                return fn
            elif include_missing and not icon in [ "image-missing", "gtk-missing-image" ]:
                if warning:
                    logger.warning("Icon %s (%d) not found, using missing image" % ( o_icon, size ))
                return get_icon_path(["image-missing", "gtk-missing-image"], size, warning)
        else:
            if os.path.isfile(o_icon):
                return o_icon
            else:
                if warning:
                    logger.warning("Icon %s (%d) not found" % ( o_icon, size ))
                if include_missing and not icon in [ "image-missing", "gtk-missing-image" ]:
                    return get_icon_path(["image-missing", "gtk-missing-image"], size, warning)
    
def get_app_icon(gconf_client, icon, size = 128):
    icon_path = get_icon_path(icon, size)
    if icon_path == None:
        icon_path = os.path.join(pglobals.icons_dir,"hicolor", "scalable", "apps", "%s.svg" % icon)
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
'''
SVG utilities
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
    
def split_args(args):
    return re.findall(r'\w+', args)

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
            elif name == "scale":
                list.append(cairo.Matrix(float(args[0]), 0.0, 0.0, float(args[1]), 0.0, 0.0))
            else:
                logger.warning("Unsupported transform %s" % name)
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
                args = split_args(transform_val[start_args + 1:end_args])
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

def get_actual_bounds(element, relative_to = None):
    id = element.get("id")
    
    bounds = get_bounds(element)
    transforms = []
    t = cairo.Matrix()
    t.translate(bounds[0],bounds[1])
    transforms.append(t)
    
    # If the element is a clip path and the associated clipped_node is provided, the work out the transforms from 
    # the parent of the clipped_node, not the clip itself
    if relative_to is not None:
        element = relative_to.getparent() 
    
    while element != None:
        transforms += get_transforms(element, position_only=True)
        element = element.getparent()
    transforms.reverse()
    if len(transforms) > 0:
        t = transforms[0]
        for i in range(1, len(transforms)):
            t = t.multiply(transforms[i])

    xx, yx, xy, yy, x0, y0 = t
    return x0, y0, bounds[2], bounds[3]

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