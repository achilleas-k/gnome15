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
    return default if val == None or val == "" else _to_rgb(val)

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
        v = _to_rgb(str_val)
        alpha = gconf_client.get_int(key + "_opacity")
        val = ( v[0], v[1],v[2], alpha)
    return (float(val[0]) / 255.0, float(val[1]) / 255.0, float(val[2]) / 255.0, float(val[3]) / 255.0)

def _to_rgb(string_rgb, default = None):
    #This method should be in g15convert. The thing is that
    #g15convert depends on gtk and on Fedora it raises an error when launching
    #g15-system-service.
    #(See https://projects.russo79.com/issues/173)
    if string_rgb == None or string_rgb == "":
        return default
    rgb = string_rgb.split(",")
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
