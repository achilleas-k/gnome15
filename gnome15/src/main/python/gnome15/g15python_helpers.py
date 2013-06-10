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

