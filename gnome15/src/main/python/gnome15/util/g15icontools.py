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
Icon utilities
'''

from gnome15 import g15globals
import g15cairo
import gtk.gdk
import os
import cairo
from PIL import Image
import urllib
import base64

# Logging
import logging
logger = logging.getLogger("icon")

from cStringIO import StringIO

'''
Look for icons locally as well if running from source
'''
gtk_icon_theme = gtk.icon_theme_get_default()
if g15globals.dev:
    gtk_icon_theme.prepend_search_path(g15globals.icons_dir)

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
        icon_path = os.path.join(g15globals.icons_dir,"hicolor", "scalable", "apps", "%s.svg" % icon)
    return icon_path

def get_icon(gconf_client, icon, size = None):
    real_icon_file = get_icon_path(icon, size)
    if real_icon_file != None:
        if real_icon_file.endswith(".svg"):
            pixbuf = gtk.gdk.pixbuf_new_from_file(real_icon_file)
            scale = g15cairo.get_scale(size, (pixbuf.get_width(), pixbuf.get_height()))
            if scale != 1.0:
                pixbuf = pixbuf.scale_simple(pixbuf.get_width() * scale, pixbuf.get_height() * scale, gtk.gdk.INTERP_BILINEAR)
            img = Image.fromstring("RGBA", (pixbuf.get_width(), pixbuf.get_height()), pixbuf.get_pixels())
        else:
            img = Image.open(real_icon_file)
            scale = g15cairo.get_scale(size, img.size)
            if scale != 1.0:
                img = img.resize((img.size[0] * scale, img.size[1] * scale),Image.BILINEAR)

        return img

