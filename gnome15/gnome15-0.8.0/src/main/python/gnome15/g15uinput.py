#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) Brett Smith <tanktarta@blueyonder.co.uk>                      |
#        |                                                                             |
#        | This program is free software; you can redistribute it and/or               |
#        | modify it under the terms of the GNU General Public License                 |
#        | as published by the Free Software Foundation; either version 2              |
#        | of the License, or (at your option) any later version.                      |
#        |                                                                             |
#        | This program is distributed in the hope that it will be useful,             |
#        | but WITHOUT ANY WARRANTY; without even the implied warranty of              |
#        | MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               |
#        | GNU General Public License for more details.                                |
#        |                                                                             |
#        | You should have received a copy of the GNU General Public License           |
#        | along with this program; if not, write to the Free Software                 |
#        | Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA. |
#        +-----------------------------------------------------------------------------+

"""
Manages the use of uinput to inject input events (key presses, mouse movement,
joystick events) into the kernel.
"""
        
import logging
import uinput
import os
from threading import RLock
from gnome15 import g15globals
logger = logging.getLogger("uinput")

MOUSE = "mouse"
JOYSTICK = "joystick"
DIGITAL_JOYSTICK = "digital-joystick"
KEYBOARD = "keyboard"
DEVICE_TYPES = [ MOUSE, KEYBOARD, JOYSTICK, DIGITAL_JOYSTICK ]

registered_parameters = { MOUSE: {}, 
                   JOYSTICK:  {
                    uinput.ABS_X: (0, 255, 0, 4),
                    uinput.ABS_Y: (0, 255, 0, 4),
                             }, 
                   DIGITAL_JOYSTICK:  {
                    uinput.ABS_X: (0, 255, 0, 15),
                    uinput.ABS_Y: (0, 255, 0, 15),
                             }, 
                   KEYBOARD: {} }
uinput_devices = {}
locks = {}
for t in DEVICE_TYPES:
    locks[t] = RLock()

"""
These are the very unofficial vendor / produce codes used for the virtual
devices 
"""
GNOME15_USB_VENDOR_ID = 0xdd55
GNOME15_MOUSE_PRODUCT_ID = 0x0001
GNOME15_JOYSTICK_PRODUCT_ID = 0x0002
GNOME15_KEYBOARD_PRODUCT_ID = 0x0003
GNOME15_DIGITAL_JOYSTICK_PRODUCT_ID = 0x0004
    
    
def open_devices():
    """
    Initialize, opening all devices
    """
    __check_devices()
    
def close_devices():
    """
    Clean up, closing all the devices
    """
    for device_type in DEVICE_TYPES:
        if device_type in uinput_devices:
            logger.debug("Closing UINPUT device %s" % device_type)
            del uinput_devices[device_type]
    
def syn(target):
    """
    Emit the syn.
    
    Keyword arguments:
    target         --    target device type (MOUSE, KEYBOARD or JOYSTICK).
    """
    uinput_devices[target].syn()
    
def emit(target, code, value, syn=True, event_type = None):
    """
    Emit an input event, optionally emit a SYN as well
    
    Keyword arguments:
    target         --    The target device type (MOUSE, KEYBOARD or JOYSTICK)
                         type code.
    code           --    uinput code
    value          --    uinput value
    syn            --    emit SYN (defaults to True)
    ev_type        --    if not supplied, will be default for target type
    """
    ev_type = event_type
    if ev_type is None:
        if target == MOUSE and code in [ uinput.REL_X, uinput.REL_Y ]:
            if logger.level == logging.DEBUG:
                logger.debug("UINPUT mouse event at %s, code = %d, val = %d, syn = %s" % ( target, code, value, str(syn) ) )
            ev_type = uinput.EV_REL
        elif ( target == JOYSTICK or target == DIGITAL_JOYSTICK ) and code in [ uinput.ABS_X, uinput.ABS_Y ]:
            if logger.level == logging.DEBUG:
                logger.debug("UINPUT joystick event at %s, code = %d, val = %d, syn = %s" % ( target, code, value, str(syn) ) )
            ev_type = uinput.EV_ABS
        else: 
            ev_type = uinput.EV_KEY
            if logger.level == logging.DEBUG:
                logger.debug("UINPUT uinput keyboard event at %s, code = %d, val = %d, syn = %s" % ( target, code, value, str(syn) ) )
    
    locks[target].acquire()
    try:
        uinput_devices[target].emit(ev_type, code, value, syn)
    finally:
        locks[target].release()
    
def __get_keys(prefix, exclude = None):
    l = []
    caps = uinput.capabilities.CAPABILITIES
    for k in sorted(caps.iterkeys()):
        if k.startswith(prefix) and ( exclude == None or not k.startswith(exclude) ):
            l.append(caps[k])
    return l

def get_keys(device_type):
    if device_type == MOUSE:
        return __get_keys("BTN_", "BTN_TOOL_")
    elif device_type == JOYSTICK:
        return __get_keys("BTN_")
    else:
        return __get_keys("KEY_")

def get_buttons(device_type):
    fname = os.path.join(g15globals.ukeys_dir, "%s.keys" % device_type)
    f = open(fname, "r")
    caps = uinput.capabilities.CAPABILITIES
    b = []
    for line in f.readlines():
        line = line.strip()
        if not line == "" and not line.startswith("#"):
            if line in caps:
                b.append((line, caps[line]))
            else:
                logger.warning("Invalid key name '%s' in %s" % (line, fname))
    return b
    
def __check_devices():
    for device_type in DEVICE_TYPES:
        if not device_type in uinput_devices:
            logger.debug("Opening UINPUT device for %s" % device_type)
            abs_parms = { }       
            keys = []
            for b, v in get_buttons(device_type):
                keys.append(uinput.capabilities.CAPABILITIES[b])
            if device_type == MOUSE:
                virtual_product_id = GNOME15_MOUSE_PRODUCT_ID
                caps = {
                    uinput.EV_REL: [uinput.REL_X, uinput.REL_Y],
                    uinput.EV_KEY: keys,
                }
            elif device_type == JOYSTICK:
                virtual_product_id = GNOME15_JOYSTICK_PRODUCT_ID
                caps = {
                    uinput.EV_ABS: [uinput.ABS_X, uinput.ABS_Y],
                    uinput.EV_KEY: keys,
                }
                abs_parms = registered_parameters[device_type]
            elif device_type == DIGITAL_JOYSTICK:
                virtual_product_id = GNOME15_JOYSTICK_PRODUCT_ID
                caps = {
                    uinput.EV_ABS: [uinput.ABS_X, uinput.ABS_Y],
                    uinput.EV_KEY: keys,
                }
                abs_parms = registered_parameters[device_type]
            else:
                virtual_product_id = GNOME15_KEYBOARD_PRODUCT_ID
                caps = {
                    uinput.EV_KEY: keys,
                }
            uinput_device = uinput.Device(name="gnome15-%s" % device_type,
                                          capabilities = caps,
                                          abs_parameters = abs_parms,
                                          vendor = GNOME15_USB_VENDOR_ID,
                                          product = virtual_product_id)                
            uinput_devices[device_type] = uinput_device
            uinput_device.emit(0, 0, 0, True)