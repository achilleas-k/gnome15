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

