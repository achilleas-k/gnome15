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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("gnome15").ugettext

import usb
import g15driver
import g15actions
import g15util
import g15drivermanager

# Logging
import logging
logger = logging.getLogger("service")
 
'''
Keyboard layouts 
'''

z10_key_layout = []

g11_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3 ],
                  [ g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6 ],
                  [ g15driver.G_KEY_G7, g15driver.G_KEY_G8, g15driver.G_KEY_G9 ],
                  [ g15driver.G_KEY_G10, g15driver.G_KEY_G11, g15driver.G_KEY_G12 ],
                  [ g15driver.G_KEY_G13, g15driver.G_KEY_G14, g15driver.G_KEY_G15 ],
                  [ g15driver.G_KEY_G16, g15driver.G_KEY_G17, g15driver.G_KEY_G18 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]

g11_action_keys = {
                   g15driver.MEMORY_1: g15actions.ActionBinding(g15driver.MEMORY_1, [ g15driver.G_KEY_M1 ], g15driver.KEY_STATE_UP),
                   g15driver.MEMORY_2: g15actions.ActionBinding(g15driver.MEMORY_2, [ g15driver.G_KEY_M2 ], g15driver.KEY_STATE_UP),
                   g15driver.MEMORY_3: g15actions.ActionBinding(g15driver.MEMORY_3, [ g15driver.G_KEY_M3 ], g15driver.KEY_STATE_UP)
                  }

g15v1_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3 ],
                  [ g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6 ],
                  [ g15driver.G_KEY_G7, g15driver.G_KEY_G8, g15driver.G_KEY_G9 ],
                  [ g15driver.G_KEY_G10, g15driver.G_KEY_G11, g15driver.G_KEY_G12 ],
                  [ g15driver.G_KEY_G13, g15driver.G_KEY_G14, g15driver.G_KEY_G15 ],
                  [ g15driver.G_KEY_G16, g15driver.G_KEY_G17, g15driver.G_KEY_G18 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4, g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]

g510_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3 ],
                  [ g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6 ],
                  [ g15driver.G_KEY_G7, g15driver.G_KEY_G8, g15driver.G_KEY_G9 ],
                  [ g15driver.G_KEY_G10, g15driver.G_KEY_G11, g15driver.G_KEY_G12 ],
                  [ g15driver.G_KEY_G13, g15driver.G_KEY_G14, g15driver.G_KEY_G15 ],
                  [ g15driver.G_KEY_G16, g15driver.G_KEY_G17, g15driver.G_KEY_G18 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4, g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]

g15v2_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3 ],
                  [ g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4, g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]          

g13_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3, g15driver.G_KEY_G4, g15driver.G_KEY_G5, g15driver.G_KEY_G6, g15driver.G_KEY_G7 ],
                  [ g15driver.G_KEY_G8, g15driver.G_KEY_G9, g15driver.G_KEY_G10, g15driver.G_KEY_G11, g15driver.G_KEY_G12, g15driver.G_KEY_G13, g15driver.G_KEY_G14 ],
                  [ g15driver.G_KEY_G15, g15driver.G_KEY_G16, g15driver.G_KEY_G17, g15driver.G_KEY_G18, g15driver.G_KEY_G19 ],
                  [ g15driver.G_KEY_G20, g15driver.G_KEY_G21, g15driver.G_KEY_G22 ],
                  [ g15driver.G_KEY_L1, g15driver.G_KEY_L2, g15driver.G_KEY_L3, g15driver.G_KEY_L4, g15driver.G_KEY_L5 ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]         

g930_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2, g15driver.G_KEY_G3 ]
                  ]

""" 
Unfortunately we have to leave L1 clear for g15daemon for the moment 
"""
g15_action_keys = { g15driver.NEXT_SELECTION: g15actions.ActionBinding(g15driver.NEXT_SELECTION, [ g15driver.G_KEY_L4 ], g15driver.KEY_STATE_UP),
                    g15driver.PREVIOUS_SELECTION: g15actions.ActionBinding(g15driver.PREVIOUS_SELECTION, [ g15driver.G_KEY_L3 ], g15driver.KEY_STATE_UP),
                    g15driver.SELECT: g15actions.ActionBinding(g15driver.SELECT, [ g15driver.G_KEY_L5 ], g15driver.KEY_STATE_UP),
                    g15driver.MENU: g15actions.ActionBinding(g15driver.MENU, [ g15driver.G_KEY_L1 ], g15driver.KEY_STATE_UP),
                    g15driver.CLEAR: g15actions.ActionBinding(g15driver.CLEAR, [ g15driver.G_KEY_L2 ], g15driver.KEY_STATE_HELD),
                    g15driver.VIEW: g15actions.ActionBinding(g15driver.VIEW, [ g15driver.G_KEY_L2 ], g15driver.KEY_STATE_UP),
                    g15driver.NEXT_PAGE: g15actions.ActionBinding(g15driver.NEXT_PAGE, [ g15driver.G_KEY_L4 ], g15driver.KEY_STATE_HELD),
                    g15driver.PREVIOUS_PAGE: g15actions.ActionBinding(g15driver.PREVIOUS_PAGE, [ g15driver.G_KEY_L3 ], g15driver.KEY_STATE_HELD),
                    g15driver.MEMORY_1: g15actions.ActionBinding(g15driver.MEMORY_1, [ g15driver.G_KEY_M1 ], g15driver.KEY_STATE_UP),
                    g15driver.MEMORY_2: g15actions.ActionBinding(g15driver.MEMORY_2, [ g15driver.G_KEY_M2 ], g15driver.KEY_STATE_UP),
                    g15driver.MEMORY_3: g15actions.ActionBinding(g15driver.MEMORY_3, [ g15driver.G_KEY_M3 ], g15driver.KEY_STATE_UP)
                   }

"""
G110 - Only actions we need really are the memory bank ones
"""
g110_action_keys = { 
                    g15driver.MEMORY_1: g15actions.ActionBinding(g15driver.MEMORY_1, [ g15driver.G_KEY_M1 ], g15driver.KEY_STATE_UP),
                    g15driver.MEMORY_2: g15actions.ActionBinding(g15driver.MEMORY_2, [ g15driver.G_KEY_M2 ], g15driver.KEY_STATE_UP),
                    g15driver.MEMORY_3: g15actions.ActionBinding(g15driver.MEMORY_3, [ g15driver.G_KEY_M3 ], g15driver.KEY_STATE_UP)
                   }

g110_key_layout = [
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G7 ],
                  [ g15driver.G_KEY_G2, g15driver.G_KEY_G8 ], 
                  [ g15driver.G_KEY_G3, g15driver.G_KEY_G9 ],
                  [ g15driver.G_KEY_G4, g15driver.G_KEY_G10 ],
                  [ g15driver.G_KEY_G5, g15driver.G_KEY_G11], 
                  [ g15driver.G_KEY_G6, g15driver.G_KEY_G12 ],
                  [ g15driver.G_KEY_MIC_MUTE, g15driver.G_KEY_HEADPHONES_MUTE ],
                  [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ]
                  ]

"""
G19
"""
g19_key_layout = [
              [ g15driver.G_KEY_G1, g15driver.G_KEY_G7 ],
              [ g15driver.G_KEY_G2, g15driver.G_KEY_G8 ],
              [ g15driver.G_KEY_G3, g15driver.G_KEY_G9 ],
              [ g15driver.G_KEY_G4, g15driver.G_KEY_G10 ],
              [ g15driver.G_KEY_G5, g15driver.G_KEY_G11 ],
              [ g15driver.G_KEY_G6, g15driver.G_KEY_G12 ],
              [ g15driver.G_KEY_UP ],
              [ g15driver.G_KEY_LEFT, g15driver.G_KEY_OK, g15driver.G_KEY_RIGHT ],
              [ g15driver.G_KEY_DOWN ],
              [ g15driver.G_KEY_MENU, g15driver.G_KEY_BACK, g15driver.G_KEY_SETTINGS ],
              [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ],
              ]
g19_action_keys = { g15driver.NEXT_SELECTION: g15actions.ActionBinding(g15driver.NEXT_SELECTION, [ g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_DOWN),
                    g15driver.PREVIOUS_SELECTION: g15actions.ActionBinding(g15driver.PREVIOUS_SELECTION, [ g15driver.G_KEY_UP ], g15driver.KEY_STATE_DOWN),
                    g15driver.SELECT: g15actions.ActionBinding(g15driver.SELECT, [ g15driver.G_KEY_OK ], g15driver.KEY_STATE_UP),
                    g15driver.MENU: g15actions.ActionBinding(g15driver.MENU, [ g15driver.G_KEY_MENU ], g15driver.KEY_STATE_UP),
                    g15driver.CLEAR: g15actions.ActionBinding(g15driver.CLEAR, [ g15driver.G_KEY_BACK ], g15driver.KEY_STATE_UP),
                    g15driver.VIEW: g15actions.ActionBinding(g15driver.VIEW, [ g15driver.G_KEY_SETTINGS ], g15driver.KEY_STATE_UP),
                    g15driver.NEXT_PAGE: g15actions.ActionBinding(g15driver.NEXT_PAGE, [ g15driver.G_KEY_RIGHT ], g15driver.KEY_STATE_UP),
                    g15driver.PREVIOUS_PAGE: g15actions.ActionBinding(g15driver.PREVIOUS_PAGE, [ g15driver.G_KEY_LEFT ], g15driver.KEY_STATE_UP),
                    g15driver.MEMORY_1: g15actions.ActionBinding(g15driver.MEMORY_1, [ g15driver.G_KEY_M1 ], g15driver.KEY_STATE_UP),
                    g15driver.MEMORY_2: g15actions.ActionBinding(g15driver.MEMORY_2, [ g15driver.G_KEY_M2 ], g15driver.KEY_STATE_UP),
                    g15driver.MEMORY_3: g15actions.ActionBinding(g15driver.MEMORY_3, [ g15driver.G_KEY_M3 ], g15driver.KEY_STATE_UP)
                   }

"""
MX5500

Only two keys near the LCD, so various combinations of keys and holding keys is used to
provide the 6 most basic actions
"""

mx5500_key_layout = [
                     [ g15driver.G_KEY_UP, g15driver.G_KEY_DOWN ]
                     ]
mx5500_action_keys = { g15driver.NEXT_SELECTION: g15actions.ActionBinding(g15driver.NEXT_SELECTION, [ g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_UP),
                    g15driver.PREVIOUS_SELECTION: g15actions.ActionBinding(g15driver.PREVIOUS_SELECTION, [ g15driver.G_KEY_UP ], g15driver.KEY_STATE_UP),
                    g15driver.SELECT: g15actions.ActionBinding(g15driver.SELECT, [ g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_HELD),
                    g15driver.MENU: g15actions.ActionBinding(g15driver.MENU, [ g15driver.G_KEY_UP ], g15driver.KEY_STATE_HELD),
                    g15driver.CLEAR: g15actions.ActionBinding(g15driver.CLEAR, [ g15driver.G_KEY_UP, g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_HELD),
                    g15driver.VIEW: g15actions.ActionBinding(g15driver.VIEW, [ g15driver.G_KEY_UP, g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_UP)
                   }

# Registered Logitech models
device_list = { }
device_by_usb_id = { }
__cached_devices = []

class DeviceInfo():
    """
    Represents the characteristics of a single model of a Logitech device.  
    """
    def __init__(self, model_id, usb_id_list, controls_usb_id_list, key_layout, bpp, lcd_size, macros, model_fullname, action_keys):
        """
        Creates a new DeviceInfo and add's it to the registered device types
        
        Keyword arguments
        model_id          --    model ID (as found in g15driver constants)
        usb_id_list       --    list or single tuple with vendor and product codes (this is the device searched for). 
        controls_usb_id_list    --    tuple with vendor and product codes for the controls device
        key_layout        --    keyboard layout
        bpp               --    the number of bits per pixel (or 0 for no LCD)
        lcd_size          --    the size of the LCD (or None for no LCD)
        macros            --    the model has macro keys (G-Keys)
        model_fullname    --    full name of the model
        action_keys       --    default keybinds to use for actions
        """
        self.model_id = model_id
        self.key_layout = key_layout
        self.macros = macros
        self.bpp = bpp
        self.lcd_size = lcd_size
        self.action_keys = action_keys
        self.model_fullname = model_fullname
        device_list[self.model_id] = self
        
        # Some devices (1 currently) use a different USBID for controls
        if controls_usb_id_list is None:
            controls_usb_id_list = usb_id_list
        
        # Some devices may have multiple usb ID's (for audio mode)
        if not isinstance(usb_id_list, list):
            usb_id_list = [usb_id_list]
        if not isinstance(controls_usb_id_list, list):
            controls_usb_id_list = [controls_usb_id_list]
        if not len(usb_id_list) == len(controls_usb_id_list):
            raise Exception("Controls USB ID list is not the same length as USB ID list")
        self.usb_id_list = usb_id_list
        self.controls_usb_id_list = controls_usb_id_list
        
        # Map all the devices
        for c in self.usb_id_list:
            device_by_usb_id[c] = self
        
        # Gather all keys in the layout
        self.all_keys = []
        for row in self.key_layout:
            for key in row:
                self.all_keys.append(key)
                
    def matches(self, usb_id):
        return usb_id in self.controls_usb_id_list or usb_id in self.usb_id_list
        
    def __repr__(self):
        return "DeviceInfo [%s/%s] model: %s (%s). Has a %d BPP screen of %dx%d. " %  \
            ( str(self.usb_id_list), str(self.controls_usb_id_list), self.model_id, self.model_fullname, self.bpp, self.lcd_size[0], self.lcd_size[1])
           
class Device():
    """
    Represents a single discovered device.
    
    Keyword arguments
    usb_id            --    the actual ID
    usb_device        --    the USB device
    device_info       --    DeviceInfo object containing static model information
    """
    def __init__(self, usb_id, controls_usb_id, usb_device, index, device_info):
        self.usb_id = usb_id  
        self.controls_usb_id = controls_usb_id
        
        self.usb_device = usb_device 
        self.index = index
        self.uid = "%s_%d" % ( device_info.model_id, index )
        self.model_id = device_info.model_id
        self.key_layout = device_info.key_layout  
        self.bpp = device_info.bpp
        self.lcd_size = device_info.lcd_size
        self.model_fullname = device_info.model_fullname
        self.all_keys = device_info.all_keys
        self.action_keys = device_info.action_keys
        
    def get_key_index(self, key):
        if key in self.all_keys:
            self.all_keys.index(key)
            
    def __hash__(self):
        return self.ui.__hash()
    
    def __eq__(self, o):
        try:
            return o is not None and self.uid == o.uid
        except AttributeError:
            return False
        
    def __repr__(self):
        usb_str = hex(self.usb_id[0]) if self.usb_id is not None and len(self.usb_id) > 0 else "Unknown"
        usb_str2 = hex(self.usb_id[1]) if self.usb_id is not None and len(self.usb_id) > 1 else "Unknown"
        sz1 = self.lcd_size[0] if self.lcd_size is not None and len(self.lcd_size) > 0 else "??"
        sz2 = self.lcd_size[1] if self.lcd_size is not None and len(self.lcd_size) > 1 else "??"
        return "Device [%s] %s model: %s (%s) on USB ID %s:%s. Has a %d BPP screen of %dx%d. " %  \
            ( str(self.usb_device), self.uid, self.model_id, self.model_fullname, usb_str, usb_str2, self.bpp, sz1, sz2)
    
def are_keys_reserved(model_id, keys):
    if len(keys) < 1:
        raise Exception("Empty key list provided")
    device_info = get_device_info(model_id)
    if device_info is None:
        raise Exception("No device with ID of %s"  % model_id)
    for action_binding in device_info.action_keys.values():
        if sorted(keys) == sorted(action_binding.keys):
            return True
    return False
                        
def get_device_info(model_id):
    return device_list[model_id]

def is_enabled(conf_client, device):    
    val = conf_client.get("/apps/gnome15/%s/enabled" % device.uid)
    return ( val == None and device.model_id != "virtual" ) or ( val is not None and val.get_bool() )
        
def set_enabled(conf_client, device, enabled):
    conf_client.set_bool("/apps/gnome15/%s/enabled" % device.uid, enabled)
    
def get_device(uid):
    """
    Find the device with the specified UID.
    """
    for d in find_all_devices():
        if d.uid == uid:
            return d
    
def find_all_devices(do_cache = True):
    global __cached_devices
        
    """
    Get a list of Device objects, one for each supported device that is plugged in.
    There may be more than one device of the same type.
    """
    
    # If we have pydev, we can cache the devices
    if do_cache and have_udev and len(__cached_devices) != 0:
        return __cached_devices
    
    device_map = {}
    
    # Find all supported devices plugged into USB
    for bus in usb.busses():
        for usb_device in bus.devices:
            key =  ( usb_device.idVendor, usb_device.idProduct )
            # Is a supported device
            if not key in device_map:
                device_map[key] = []
            device_map[key].append(usb_device)
    
    # Turn the found USB devices into Device objects
    devices = []
    indices = {}
    
    for device_key in device_map:
        usb_devices = device_map[device_key]
        for usb_device in usb_devices:
            if device_key in device_by_usb_id:     
                device_info = device_by_usb_id[device_key]
                """
                Take the quirk of the G11/G15 into account. This check means that only one of each
                type can exist at a time, but any more is pretty unlikely
                """
                if device_info.model_id == g15driver.MODEL_G15_V1 and not (0x046d, 0xc222) in device_map:
                    # Actually a G11
                    device_info = device_list[g15driver.MODEL_G11]
                elif device_info.model_id == g15driver.MODEL_G11 and (0x046d, 0xc222) in device_map:
                    # Actually a G15v1
                    device_info = device_list[g15driver.MODEL_G15_V1]
                
                """
                Now create the device instance that will be used by the caller
                """
                index = 0 if not device_key in indices else indices[device_key] 
                controls_usb_id = device_info.controls_usb_id_list[device_info.usb_id_list.index(device_key)]
                devices.append(Device(device_key, controls_usb_id, usb_device, index, device_info))
                indices[device_key] = index + 1
            
 
    """
    If the GTK driver is installed, add a virtual device as well
    """
    if g15drivermanager.get_driver_mod("gtk"): 
        devices.append(Device(None, None, None, 0, device_list['virtual']))
    
    # If we have pydev, we can cache the devices
    if have_udev and do_cache:
        __cached_devices += devices
        
    return devices

def find_device(models):
    for lg_model in find_all_devices():
        for model in models:
            if lg_model.model_name == model:
                return lg_model
            
def _get_cached_device_by_usb_id(usb_id):
    for c in __cached_devices:
        if c.usb_id == usb_id:
            return c
            
"""
Register all supported models
"""
if g15drivermanager.get_driver_mod("gtk"): 
    DeviceInfo('virtual',               (0x0000, 0x0000),       None,               [],                 0,  ( 0,    0 ),    False,  _("Virtual LCD Window"),                        None)
DeviceInfo(g15driver.MODEL_G11,         (0x046d, 0xc225),       None,               g11_key_layout,     0,  ( 0,    0 ),    True,   _("Logitech G11 Keyboard"),                     g11_action_keys)
DeviceInfo(g15driver.MODEL_G19,         (0x046d, 0xc229),       None,               g19_key_layout,     16, ( 320,  240 ),  True,   _("Logitech G19 Gaming Keyboard"),              g19_action_keys)
DeviceInfo(g15driver.MODEL_G15_V1,      (0x046d, 0xc221),       (0x046d, 0xc222),   g15v1_key_layout,   1,  ( 160,  43 ),   True,   _("Logitech G15 Gaming Keyboard (version 1)"),  g15_action_keys) 
DeviceInfo(g15driver.MODEL_G15_V2,      (0x046d, 0xc227),       None,               g15v2_key_layout,   1,  ( 160,  43 ),   True,   _("Logitech G15 Gaming Keyboard (version 2)"),  g15_action_keys)
DeviceInfo(g15driver.MODEL_G13,         (0x046d, 0xc21c),       None,               g13_key_layout,     1,  ( 160,  43 ),   True,   _("Logitech G13 Advanced Gameboard"),           g15_action_keys)
DeviceInfo(g15driver.MODEL_G510,        [ (0x046d, 0xc22d), 
                                          (0x046d, 0xc22e) ],   None,               g510_key_layout,    1,  ( 160,  43 ),   True,   _("Logitech G510 Keyboard"),                    g15_action_keys)
DeviceInfo(g15driver.MODEL_Z10,         (0x046d, 0x0a07),       None,               z10_key_layout,     1,  ( 160,  43 ),   False,  _("Logitech Z10 Speakers"),                     g19_action_keys)
DeviceInfo(g15driver.MODEL_G110,        (0x046d, 0xc22b),       None,               g110_key_layout,    0,  ( 0,    0 ),    True,   _("Logitech G110 Keyboard"),                    g110_action_keys)
DeviceInfo(g15driver.MODEL_GAMEPANEL,   (0x046d, 0xc251),       None,               g15v1_key_layout,   1,  ( 160,  43 ),   True,   _("Logitech GamePanel"),                        g15_action_keys)
DeviceInfo(g15driver.MODEL_G930,        (0x046d, 0xa1f),        None,               g930_key_layout,    0,  ( 0,  0 ),      True,   _("Logitech G930 Headphones"),                  {})
DeviceInfo(g15driver.MODEL_G35,         (0x046d, 0xa15),        None,               g930_key_layout,    0,  ( 0,  0 ),      True,   _("Logitech G35 Headphones"),                   {})

# When I get hold of an MX5500, I will add Bluetooth detection as well
DeviceInfo(g15driver.MODEL_MX5500,      (0x0000, 0x0000),   (0x0000, 0x0000),   mx5500_key_layout,  1,  ( 136,    32 ), False,  _("Logitech MX5500"),                           mx5500_action_keys)

# If we have pyudev, we can monitor for devices being plugged in and unplugged
have_udev = False
device_added_listeners = []
device_removed_listeners = []
    
def __device_added(observer, device):
    if "uevent" in device.attributes:
        uevent = g15util.parse_as_properties(device.attributes["uevent"])
        if "PRODUCT" in uevent:
            if "subsystem" in device.attributes and device.attributes["subsystem"] == "usb":
                major,minor,_ = uevent["PRODUCT"].split("/")
            else:
                _,major,minor,_ = uevent["PRODUCT"].split("/")
            for c in device_list:
                device_info = device_list[c]
                usb_id = (int(major, 16), int(minor, 16))
                if device_info.matches(usb_id):
                    if not _get_cached_device_by_usb_id(usb_id):
                        del __cached_devices[:]
                        find_all_devices()
                        for r in reversed(__cached_devices):
                            if r.usb_id == usb_id:
                                logger.info("Added device %s" % r)
                                for l in device_added_listeners:
                                    l(r)
                                break
                    break
                        
def __device_removed(observer, device):
    current_devices = list(__cached_devices)
    new_devices = find_all_devices(do_cache = False)
    found = False
    for d in current_devices:
        for e in new_devices:
            if e.uid == d.uid:
                found = True
                break
        if not found:
            if d in __cached_devices:
                __cached_devices.remove(d)
            for l in device_removed_listeners:
                l(d)
            break

try:
    import pyudev.glib
    __context = pyudev.Context()
    __monitor = pyudev.Monitor.from_netlink(__context)
    __observer = pyudev.glib.GUDevMonitorObserver(__monitor)
    __observer.connect('device-added', __device_added)
    __observer.connect('device-removed', __device_removed)
    find_all_devices()
    have_udev = True
    __monitor.start()
except:
    logger.info("Failed to get PyUDev context, hot plugging support not available")
    
if __name__ == "__main__":
    for device in find_all_devices():
        print str(device)
        