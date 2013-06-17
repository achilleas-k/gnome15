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

import g15convert

def get_float_or_default(gconf_client, key, default = None):
    """
    Tries to read a float value from GConf and return a default value it
    doesn't exist.

    Keyword arguments:
    gconf_client : GConf client instance that will read the value
    key          : full path of the key to be read
    default      : value to return if key was not found
    """
    float_val = gconf_client.get(key)
    return default if float_val == None else float_val.get_float()

def get_string_or_default(gconf_client, key, default = None):
    """
    Tries to read a string value from GConf and return a default value it
    doesn't exist.

    Keyword arguments:
    gconf_client : GConf client instance that will read the value
    key          : full path of the key to be read
    default      : value to return if key was not found
    """
    str_val = gconf_client.get(key)
    return default if str_val == None else str_val.get_string()

def get_bool_or_default(gconf_client, key, default = None):
    """
    Tries to read a boolean value from GConf and return a default value it
    doesn't exist.

    Keyword arguments:
    gconf_client : GConf client instance that will read the value
    key          : full path of the key to be read
    default      : value to return if key was not found
    """
    bool_val = gconf_client.get(key)
    return default if bool_val == None else bool_val.get_bool()

def get_int_or_default(gconf_client, key, default = None):
    """
    Tries to read a integer value from GConf and return a default value it
    doesn't exist.

    Keyword arguments:
    gconf_client : GConf client instance that will read the value
    key          : full path of the key to be read
    default      : value to return if key was not found
    """
    int_val = gconf_client.get(key)
    return default if int_val == None else int_val.get_int()

def get_rgb_or_default(gconf_client, key, default = None):
    """
    Tries to read a "rgb" value from GConf and return a default value it
    doesn't exist.
    A "rgb" value is in fact a comma separated string with the Red, Green and
    Blue components encoded from 0 to 255.

    Keyword arguments:
    gconf_client : GConf client instance that will read the value
    key          : full path of the key to be read
    default      : value to return if key was not found
    """
    val = gconf_client.get_string(key)
    return default if val == None or val == "" else g15convert.to_rgb(val)

def get_cairo_rgba_or_default(gconf_client, key, default):
    """
    Tries to read a "rgba" value from GConf and return a default value if
    it doesn't exist.
    A "rgba" value is encoded as two key on gconf. The first one is similar to
    the rgb value described in get_rgb_or_default. The second one is stored in
    <key>_opacity and it represents the alpha value.
    The returned value is encoded in a float tuple with each component ranging
    from 0.0 to 1.

    Keyword arguments:
    gconf_client : GConf client instance that will read the value
    key          : full path of the key to be read
    default      : value to return if key was not found
    """
    str_val = gconf_client.get_string(key)
    if str_val == None or str_val == "":
        val = default
    else:
        v = g15convert.to_rgb(str_val)
        alpha = gconf_client.get_int(key + "_opacity")
        val = ( v[0], v[1],v[2], alpha)
    return (float(val[0]) / 255.0, float(val[1]) / 255.0, float(val[2]) / 255.0, float(val[3]) / 255.0)
