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

import re
import threading

'''
Helper methods "extending" the python syntax
'''

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

def module_exists(module_name):
    """
    Get if a module exists

    Keyword arguments:
    module_name: the name of the module to check
    """
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True

def value_or_empty(d, key):
    """
    Returns the value corresponding to a given key in a dictionnary.
    If no value is found, then an empty array is returned.

    Keyword arguments:
    d:   The dictionnary where to search for the value
    key: The key to use for the lookup
    """
    return value_or_default(d, key, [])

def value_or_blank(d, key):
    """
    Returns the value corresponding to a given key in a dictionnary.
    If no value is found, then an empty string is returned.

    Keyword arguments:
    d:   The dictionnary where to search for the value
    key: The key to use for the lookup
    """
    return value_or_default(d, key, "")

def value_or_default(d, key, default_value):
    """
    Returns the value corresponding to a given key in a dictionnary.
    If no value is found, then a default value is returned.

    Keyword arguments:
    d:             The dictionnary where to search for the value
    key:           The key to use for the lookup
    default_value: The default value to return if no value is found
    """
    try :
        return d[key]
    except KeyError:
        return default_value

def to_int_or_none(s):
    """
    Converts a string to a int or returns None if there was an error converting
    """
    try:
        return int(s)
    except (ValueError, TypeError):
        return None

def to_float_or_none(s):
    """
    Converts a string to a float or returns None if there was an error converting
    """
    try:
        return float(s)
    except (ValueError, TypeError):
        return None

def find(f, seq):
    """Return first item in sequence where f(item) == True."""
    for item in seq:
        if f(item):
            return item

def append_if_exists(el, key, val, formatter = "%s"):
    """
    Appends a value from a dictionnary to a string applying a formatter.
    The value is only appended if it exists in the dictionnary and it's value is not None

    Keyword arguments:
    el:        The dictionnary where to search for the value
    key:       The key to search of the dictionnary
    val:       The string to which the found value will be appended
    formatter: A format string to apply when appending the found value

    Returns:  A new string with the found value appended to (prefixed by a comma)
    """
    if key in el and el[key] is not None and len(str(el[key])) > 0:
        if len(val) > 0:
            val += ","
        val += formatter % el[key]
    return val

def parse_as_properties(properties_string):
    """
    Create a dictionnary [key,value] from a string containing a set of
    name=value pairs separated by '\n'

    Keyword elements:
    properties_string: string containing a set of name=value fields
    """
    d = {}
    for l in properties_string.split("\n"):
        a = l.split("=")
        if len(a) > 1:
            d[a[0]] = a[1]
    return d

def split_args(args):
    return re.findall(r'\w+', args)

'''
Date / time utilities
'''
def total_seconds(time_delta):
    """
    Calculate the total of seconds ellapsed in a timedelta value

    Keyword arguments:
    time_delta: The timedelta value for which the number of seconds should be
    calculated.
    """
    return (time_delta.microseconds + (time_delta.seconds + time_delta.days * 24.0 * 3600.0) * 10.0**6.0) / 10.0**6.0

'''
GObject thread. Hosting applications may set this so that is_gobject_thread()
function works
'''
gobject_thread = [ None ]

def is_gobject_thread():
    return threading.currentThread() == gobject_thread[0]

def set_gobject_thread():
    gobject_thread[0] = threading.currentThread()

