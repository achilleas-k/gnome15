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
SVG utilities
'''

import cairo
import g15python_helpers

# Logging
import logging
logger = logging.getLogger("svg")


def rotate_element(element, degrees):
    transforms = get_transforms(element)
    if len(transforms) > 0:
        t = transforms[0]
        for i in range(1, len(transforms)):
            t = t.multiply(transforms[i])
    else:
        t = cairo.Matrix()

    t.rotate(g15util.degrees_to_radians(degrees))
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
                args = g15python_helpers.split_args(transform_val[start_args + 1:end_args])
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

