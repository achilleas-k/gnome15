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

import logging
import uinput
logger = logging.getLogger("uinput")

"""
Manages the use of uinput to inject input events (key presses, mouse movement,
joystick events) into the kernel. 

Because we must register what keys we are going to send when opening the
device, we must close and re-open when the keys change. This is primarily to
support profile switching where different profiles may use different key
mappings.

"""

MOUSE = "mouse"
JOYSTICK = "joystick"
KEYBOARD = "keyboard"
DEVICE_TYPES = [ MOUSE, KEYBOARD, JOYSTICK ]

registered_keys = { MOUSE: {}, 
                   JOYSTICK: {}, 
                   KEYBOARD: {} }
uinput_devices = {}
    
class OpenDevice():
    def __init__(self, codes, uinput_device):
        self.codes = codes
        self.uinput_device = uinput_device
        self.code_tuple = tuple(codes)
                            
def deregister_codes(registration_id, device_types = None):
    """
    De-registered keys previously registered under the provided ID. If no
    such ID exists, no error will be raised.
    
    Keyword arguments:
    registration_id --    id to register
    device_types     --   optional type of device, or list of types, or None for all
    """
    
    if device_types is None:
        device_types = [ JOYSTICK, KEYBOARD, MOUSE ]
    if not isinstance(device_types, list):
        device_types = [ device_types ]
        
    for device_type in device_types:    
        if registration_id in registered_keys[device_type]:
            logger.info("De-registering UINPUT keys for %s under %s" % ( registration_id, device_type ) )
            del registered_keys[device_type][registration_id] 
            __check_devices()
            
def register_codes(registration_id, device_type, codes, parameters = None):
    """
    Register a list of keys that may be emitted. The registered list of keys
    may be de-registered using the same ID.
    
    Keyword arguments:
    registration_id --    id to register
    device_type     --    type of device
    codes           --    list of codes
    parameters      --    optional parameters
    """
    if registration_id in registered_keys[device_type]:
        raise Exception("UINPUT keys already registered for %s under %s" % ( registration_id, device_type ) )
    logger.info("Registering UINPUT keys for %s under %s" % ( registration_id, device_type ) )
    registered_keys[device_type][registration_id] = codes
    __check_devices()
    
def emit(target, code, value, syn=True):
    """
    Emit an input event, optionally emit a SYN as well
    
    Keyword arguments:
    target         --    target device type (MOUSE, KEYBOARD or JOYSTICK).
                         If set to None, will be automatically determined from
                         the code
    code           --    uinput code
    value          --    uinput value
    syn            --    emit SYN (defaults to True)
    """
    ev_type = uinput.EV_KEY
    if target == MOUSE and code in [ uinput.REL_X, uinput.REL_Y ]:
        if logger.level == logging.DEBUG:
            logger.debug("UINPUT mouse event at %s, code = %d, val = %d, syn = %s" % ( target, code, value, str(syn) ) )
        ev_type = uinput.EV_REL
    elif target == JOYSTICK and code in [ uinput.ABS_X, uinput.ABS_Y ]:
        if logger.level == logging.DEBUG:
            logger.debug("UINPUT joystick event at %s, code = %d, val = %d, syn = %s" % ( target, code, value, str(syn) ) )
        ev_type = uinput.EV_ABS
    else:        
        if logger.level == logging.DEBUG:
            logger.debug("UINPUT uinput keyboard event at %s, code = %d, val = %d, syn = %s" % ( target, code, value, str(syn) ) )
    uinput_devices[target].uinput_device.emit(ev_type, code, value, syn)
    
def __check_devices():
    
    codes = { }
    
    for device_type in DEVICE_TYPES:
        codes[device_type] = []
        for registration_id, reg_codes in registered_keys[device_type].items():
            for code in reg_codes:
                codes[device_type].append(code)
    
    for device_type in DEVICE_TYPES:
        if device_type in uinput_devices and len(codes[device_type]) == 0:
            # Codes no longer registered for this device, close it
            logger.debug("Closing UINPUT device %s because nothing is using it anymore" % device_type)
            del uinput_devices[device_type]
        elif len(codes[device_type]) > 0 and ( not device_type in uinput_devices or ( device_type in uinput_devices and codes[device_type] != uinput_devices[device_type].codes) ):
            logger.debug("Opening UINPUT device for %s as there are now keys (%s) that use it. old codes (%s)" % ( device_type, str(codes[device_type]), str(uinput_devices[device_type].codes) if device_type in uinput_devices else "NONE" ))
            
            # Mouse            
            abs_parms = { }                    
            if device_type == MOUSE:
                caps = {
                    uinput.EV_REL: [uinput.REL_X, uinput.REL_Y],
                    uinput.EV_KEY: codes[device_type],
                }
            # Mouse
            elif device_type == JOYSTICK:
                caps = {
                    uinput.EV_ABS: [uinput.ABS_X, uinput.ABS_Y],
                    uinput.EV_KEY: codes[device_type],
                }
                # TODO get these from those registered
                abs_parms = {                                  
                    uinput.ABS_X: (0, 255, 0, 0), # min, max, fuzz, flat
                    uinput.ABS_Y: (0, 255, 0, 0)
                }
            else:
                caps = {
                    uinput.EV_ABS: [uinput.ABS_X, uinput.ABS_Y],
                    uinput.EV_KEY: codes[device_type],
                }
 
            uinput_device = uinput.Device(name="gnome15-%s" % device_type,
                                          capabilities = caps,
                                          abs_parameters = abs_parms)                
            dev = OpenDevice(list(codes[device_type]), uinput_device)        
            uinput_devices[device_type] = dev    
        