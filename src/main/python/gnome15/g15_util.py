#!/usr/bin/env python
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

import g15_driver as g15driver


"""
Get the string name of the key given it's code
"""
def get_key_names(key):
    keys = []
    if key & g15driver.G15_KEY_G1 != 0:
        keys.append("G1")
    if key & g15driver.G15_KEY_G2 != 0:
        keys.append("G2")
    if key & g15driver.G15_KEY_G3 != 0:
        keys.append("G3")
    if key & g15driver.G15_KEY_G4 != 0:
        keys.append("G4")
    if key & g15driver.G15_KEY_G5 != 0:
        keys.append("G5")
    if key & g15driver.G15_KEY_G6 != 0:
        keys.append("G6")
    if key & g15driver.G15_KEY_G7 != 0:
        keys.append("G7")
    if key & g15driver.G15_KEY_G8 != 0:
        keys.append("G8")
    if key & g15driver.G15_KEY_G9 != 0:
        keys.append("G9")
    if key & g15driver.G15_KEY_G10 != 0:
        keys.append("G10")
    if key & g15driver.G15_KEY_G11 != 0:
        keys.append("G11")
    if key & g15driver.G15_KEY_G12 != 0:
        keys.append("G12")
    if key & g15driver.G15_KEY_G13 != 0:
        keys.append("G13")
    if key & g15driver.G15_KEY_G14 != 0:
        keys.append("G14")
    if key & g15driver.G15_KEY_G15 != 0:
        keys.append("G15")
    if key & g15driver.G15_KEY_G16 != 0:
        keys.append("G16")
    if key & g15driver.G15_KEY_G17 != 0:
        keys.append("G17")
    if key & g15driver.G15_KEY_G18 != 0:
        keys.append("G18")
    if key & g15driver.G15_KEY_L1 != 0:
        keys.append("L1")
    if key & g15driver.G15_KEY_L2 != 0:
        keys.append("L2")
    if key & g15driver.G15_KEY_L3 != 0:
        keys.append("L3")
    if key & g15driver.G15_KEY_L4 != 0:
        keys.append("L4")
    if key & g15driver.G15_KEY_L5 != 0:
        keys.append("L5")
    if key & g15driver.G15_KEY_M1 != 0:
        keys.append("M1")
    if key & g15driver.G15_KEY_M2 != 0:
        keys.append("M2")
    if key & g15driver.G15_KEY_M3 != 0:
        keys.append("M3")
    if key & g15driver.G15_KEY_MR != 0:
        keys.append("MR")
    if key & g15driver.G15_KEY_LIGHT != 0:
        keys.append("Light")

    return keys
