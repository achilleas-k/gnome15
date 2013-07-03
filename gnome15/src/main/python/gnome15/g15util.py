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
This file only exists to keep compatibility with 3rd party plugins.
It has been splitted into several files
'''

import util.g15cairo as g15cairo
import util.g15convert as g15convert
import util.g15gconf as g15gconf
import util.g15icontools as g15icontools
import util.g15markup as g15markup
import util.g115os as g15os
import util.g15pythonlang as g15pythonlang
import util.g15scheduler as g15scheduler
import util.g15svg as g15svg
import util.g15uigconf as g15uigconf
import g15notify
import g15driver


def execute_for_output(cmd):
    return g15os.get_command_output(cmd)

def run_script(script, args = None, background = True):
    return g15os.run_script(script, args, background)

def attr_exists(obj, attr_name):
    return g15pythonlang.attr_exists(obj, attr_name)

def call_if_exists(obj, function_name, *args):
    g15pythonlang.call_if_exists(obj, function_name, args)

def configure_colorchooser_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, default_alpha = None):
    g15uigconf.configure_colorchooser_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, default_alpha)

def to_cairo_rgba(gconf_client, key, default):
    return g15gconf.get_cairo_rgba_or_default(gconf_client, key, default)

def color_changed(widget, gconf_client, key):
    g15uigconf.color_changed(widget, gconf_client, key)

def rgb_to_string(rgb):
    return g15convert.rgb_to_string(rgb)

def get_alt_color(color):
    return g15convert.get_alt_color(color)

def color_to_rgb(color):
    return g15convert.color_to_rgb(color)

def to_rgb(string_rgb, default = None):
    return g15convert.to_rgb(string_rgb, default)

def to_pixel(rgb):
    return g15convert.to_pixel(rgb)

def to_color(rgb):
    return g15convert.to_color(rgb)

def spinner_changed(widget, gconf_client, key, model, decimal = False):
    g15uigconf.spinner_changed(widget, gconf_client, key, model, decimal)

def configure_spinner_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, decimal = False):
    g15uigconf.configure_spinner_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, decimal)

def configure_combo_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree):
    g15uigconf.configure_combo_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree)

def combo_box_changed(widget, gconf_client, key, model, default_value):
    g15uigconf.combo_box_changed(widget, gconf_client, key, model, default_value)

def boolean_conf_value_change(client, connection_id, entry, args):
    g15uigconf.boolean_conf_value_change(client, connection_id, entry, args)

def text_conf_value_change(client, connection_id, entry, args):
    g15uigconf.text_conf_value_change(client, connection_id, entry, args)

def radio_conf_value_change(client, connection_id, entry, args):
    g15uigconf.radio_conf_value_change(client, connection_id, entry, args)

def configure_checkbox_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, watch_changes = False):
    return g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, watch_changes)

def configure_text_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, watch_changes = False):
    return g15uigconf.configure_text_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree, watch_changes)

def configure_radio_from_gconf(gconf_client, gconf_key, widget_ids , gconf_values, default_value, widget_tree, watch_changes = False):
    return g15uigconf.configure_radio_from_gconf(gconf_client, gconf_key, widget_ids , gconf_values, default_value, widget_tree, watch_changes)

def configure_adjustment_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree):
    g15uigconf.configure_adjustment_from_gconf(gconf_client, gconf_key, widget_id, default_value, widget_tree)

def adjustment_changed(adjustment, key, gconf_client, integer = True):
    g15uigconf.adjustment_changed(adjustment, key, gconf_client, integer)

def checkbox_changed(widget, key, gconf_client):
    g15uigconf.checkbox_changed(widget, key, gconf_client)

def text_changed(widget, key, gconf_client):
    g15uigconf.text_changed(widget, key, gconf_client)

def radio_changed(widget, key, gconf_client, gconf_value):
    g15uigconf.radio_changed(widget, key, gconf_client, gconf_value)

def get_float_or_default(gconf_client, key, default = None):
    return g15gconf.get_float_or_default(gconf_client, key, default)

def get_string_or_default(gconf_client, key, default = None):
    return g15gconf.get_string_or_default(gconf_client, key, default)

def get_bool_or_default(gconf_client, key, default = None):
    return g15gconf.get_bool_or_default(gconf_client, key, default)

def get_int_or_default(gconf_client, key, default = None):
    return g15gconf.get_int_or_default(gconf_client, key, default)

def get_rgb_or_default(gconf_client, key, default = None):
    return g15gconf.get_rgb_or_default(gconf_client, key, default)

def is_gobject_thread():
    return g15pythonlang.is_gobject_thread()

def set_gobject_thread():
    g15pythonlang.set_gobject_thread()

def get_lsb_release():
    return g15os.get_lsb_release()

def get_lsb_distributor():
    return g15os.get_lsb_distributor()

def append_if_exists( el, key, val, formatter = "%s"):
    return g15pythonlang.append_if_exists( el, key, val, formatter)

def get_command_output( cmd):
    return g15os.get_command_output( cmd)

def module_exists(module_name):
    return g15pythonlang.module_exists(module_name)

def value_or_empty(d, key):
    return g15pythonlang.value_or_empty(d, key)

def value_or_blank(d, key):
    return g15pythonlang.value_or_blank(d, key)

def value_or_default(d, key, default_value):
    return g15pythonlang.value_or_default(d, key, default_value)

def find(f, seq):
    return g15pythonlang.find(f, seq)

def mkdir_p(path):
    g15os.mkdir_p(path)

def notify(summary, body = "", icon = "dialog-info", actions = [], hints = {}, timeout  = 0):
    return g15notify.notify(summary, body, icon, actions, hints, timeout, 0)

def strip_tags(html):
    return g15markup.strip_tags(html)

def total_seconds(time_delta):
    return g15pythonlang.total_seconds(time_delta)

def rgb_to_uint16(r, g, b):
    return g15convert.rgb_to_uint16(r, g, b)

def rgb_to_hex(rgb):
    return g15convert.rgb_to_hex(rgb)

def degrees_to_radians(degrees):
    return g15convert.degrees_to_radians(degrees)

def rotate(context, degrees):
    g15cairo.rotate(context, degrees)

def rotate_around_center(context, width, height, degrees):
    g15cairo.rotate_around_center(context, width, height, degrees)

def flip_horizontal(context, width, height):
    g15cairo.flip_horizontal(context, width, height)

def flip_vertical(context, width, height):
    g15cairo.flip_vertical(context, width, height)

def flip_hv_centered_on(context, fx, fy, cx, cy):
    g15cairo.flip_hv_centered_on(context, fx, fy, cx, cy)

def get_cache_filename(filename, size = None):
    return g15cairo.get_cache_filename(filename, size)

def get_image_cache_file(filename, size = None):
    return g15cairo.get_image_cache_file(filename, size)

def is_url(path):
    return g15cairo.is_url(path)

def load_surface_from_file(filename, size = None):
    return g15cairo.load_surface_from_file(filename, size)

def load_svg_as_surface(filename, size):
    return g15cairo.load_svg_as_surface(filename, size)

def image_to_surface(image, type = "ppm"):
    return g15cairo.image_to_surface(image, type)

def pixbuf_to_surface(pixbuf, size = None):
    return g15cairo.pixbuf_to_surface(pixbuf, size)

def local_icon_or_default(icon_name, size = 128):
    return g15icontools.local_icon_or_default(icon_name, size)

def get_embedded_image_url(path):
    return g15icontools.get_embedded_image_url(path)

def get_icon_path(icon = None, size = 128, warning = True, include_missing = True):
    return g15icontools.get_icon_path(icon, size, warning, include_missing)

def get_app_icon(gconf_client, icon, size = 128):
    return g15icontools.get_app_icon(gconf_client, icon, size)

def get_icon(gconf_client, icon, size = None):
    return g15icontools.get_icon(gconf_client, icon, size)

def paint_thumbnail_image(allocated_size, image, canvas):
    return g15cairo.paint_thumbnail_image(allocated_size, image, canvas)

def get_scale(target, actual):
    return g15cairo.get_scale(target, actual)

def approx_px_to_pt(px):
    return g15cairo.approx_px_to_pt(px)

def rotate_element(element, degrees):
    g15svg.rotate_element(element, degrees)

def split_args(args):
    return g15pythonlang.split_args(args)

def get_transforms(element, position_only = False):
    return g15svg.get_transforms(element, position_only)

def get_location(element):
    return g15svg.get_location(element)

def get_actual_bounds(element, relative_to = None):
    return g15svg.get_actual_bounds(element, relative_to)

def get_bounds(element):
    return g15svg.get_bounds(element)

def image_to_pixbuf(im, type = "ppm"):
    return g15cairo.image_to_pixbuf(im, type)

def surface_to_pixbuf(surface):
    return g15cairo.surface_to_pixbuf(surface)

def get_key_names(keys):
    return g15driver.get_key_names(keys)

def html_escape(text):
    return g15markup.html_escape(text)

def parse_as_properties(properties_string):
    return g15pythonlang.parse_as_properties(properties_string)

def to_int_or_none(s):
    return g15pythonlang.to_int_or_none(s)

def to_float_or_none(s):
    return g15pythonlang.to_float_or_none(s)
