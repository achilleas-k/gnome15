#!/usr/bin/env python
 
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
 

import usb
import g15driver
import g15drivermanager

class ActionBinding():
    def __init__(self, action, keys, state):
        self.action = action
        self.state = state
        self.keys = keys

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

""" 
Unfortunately we have to leave L1 clear for g15daemon for the moment
"""
g15_action_keys = { g15driver.NEXT_SELECTION: ActionBinding(g15driver.NEXT_SELECTION, [ g15driver.G_KEY_L4 ], g15driver.KEY_STATE_UP),
                    g15driver.PREVIOUS_SELECTION: ActionBinding(g15driver.PREVIOUS_SELECTION, [ g15driver.G_KEY_L3 ], g15driver.KEY_STATE_UP),
                    g15driver.SELECT: ActionBinding(g15driver.SELECT, [ g15driver.G_KEY_L5 ], g15driver.KEY_STATE_UP),
                    g15driver.MENU: ActionBinding(g15driver.MENU, [ g15driver.G_KEY_L2 ], g15driver.KEY_STATE_HELD),
                    g15driver.CLEAR: ActionBinding(g15driver.CLEAR, [ g15driver.G_KEY_L5 ], g15driver.KEY_STATE_HELD),
                    g15driver.VIEW: ActionBinding(g15driver.VIEW, [ g15driver.G_KEY_L2 ], g15driver.KEY_STATE_UP),
                    g15driver.NEXT_PAGE: ActionBinding(g15driver.NEXT_PAGE, [ g15driver.G_KEY_L4 ], g15driver.KEY_STATE_HELD),
                    g15driver.PREVIOUS_PAGE: ActionBinding(g15driver.PREVIOUS_PAGE, [ g15driver.G_KEY_L3 ], g15driver.KEY_STATE_HELD)
                   }

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
g19_action_keys = { g15driver.NEXT_SELECTION: ActionBinding(g15driver.NEXT_SELECTION, [ g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_DOWN),
                    g15driver.PREVIOUS_SELECTION: ActionBinding(g15driver.PREVIOUS_SELECTION, [ g15driver.G_KEY_UP ], g15driver.KEY_STATE_DOWN),
                    g15driver.SELECT: ActionBinding(g15driver.SELECT, [ g15driver.G_KEY_OK ], g15driver.KEY_STATE_DOWN),
                    g15driver.MENU: ActionBinding(g15driver.MENU, [ g15driver.G_KEY_MENU ], g15driver.KEY_STATE_DOWN),
                    g15driver.CLEAR: ActionBinding(g15driver.CLEAR, [ g15driver.G_KEY_BACK ], g15driver.KEY_STATE_DOWN),
                    g15driver.VIEW: ActionBinding(g15driver.VIEW, [ g15driver.G_KEY_SETTINGS ], g15driver.KEY_STATE_DOWN),
                    g15driver.NEXT_PAGE: ActionBinding(g15driver.NEXT_PAGE, [ g15driver.G_KEY_RIGHT ], g15driver.KEY_STATE_DOWN),
                    g15driver.PREVIOUS_PAGE: ActionBinding(g15driver.PREVIOUS_PAGE, [ g15driver.G_KEY_LEFT ], g15driver.KEY_STATE_DOWN)
                   }

"""
MX5500

Only two keys near the LCD, so various combinrations of keys and holding keys is used to
provide the 6 most basic actions
"""

mx5500_key_layout = [
                     [ g15driver.G_KEY_UP, g15driver.G_KEY_DOWN ]
                     ]
mx5500_action_keys = { g15driver.NEXT_SELECTION: ActionBinding(g15driver.NEXT_SELECTION, [ g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_UP),
                    g15driver.PREVIOUS_SELECTION: ActionBinding(g15driver.PREVIOUS_SELECTION, [ g15driver.G_KEY_UP ], g15driver.KEY_STATE_UP),
                    g15driver.SELECT: ActionBinding(g15driver.SELECT, [ g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_HELD),
                    g15driver.MENU: ActionBinding(g15driver.MENU, [ g15driver.G_KEY_UP ], g15driver.KEY_STATE_HELD),
                    g15driver.CLEAR: ActionBinding(g15driver.CLEAR, [ g15driver.G_KEY_UP, g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_HELD),
                    g15driver.VIEW: ActionBinding(g15driver.VIEW, [ g15driver.G_KEY_UP, g15driver.G_KEY_DOWN ], g15driver.KEY_STATE_UP)
                   }

# Registered Logitech models
device_list = { }
device_by_usb_id = {}

class DeviceInfo():
    """
    Represents the characteristics of a single model of a Logitech device.  
    """
    def __init__(self, model_id, usb_id, key_layout, bpp, lcd_size, model_fullname, action_keys):
        """
        Creates a new DeviceInfo and add's it to the registered device types
        
        Keyword arguments
        model_id          --    model ID (as found in g15driver constants)
        usb_id            --    tuple with vendor and product codes
        key_layout        --    keyboard layout
        bpp               --    the number of bits per pixel (or 0 for no LCD)
        lcd_size          --    the size of the LCD (or None for no LCD)
        model_fullname    --    full name of the model
        action_keys       --    default keybinds to use for actions
        """
        self.model_id = model_id
        self.usb_id = usb_id
        self.key_layout = key_layout
        self.bpp = bpp
        self.lcd_size = lcd_size
        self.action_keys = action_keys
        self.model_fullname = model_fullname
        device_list[self.model_id] = self
        device_by_usb_id[self.usb_id] = self
        
        self.all_keys = []
        for row in self.key_layout:
            for key in row:
                self.all_keys.append(key)
           
class Device():
    """
    Represents a single discovered device.
    
    Keyword arguments
    usb_device        --    the USB device
    device_info       --    DeviceInfo object containing static model information
    """
    def __init__(self, usb_device, index, device_info):
        self.usb_device = usb_device 
        self.index = index
        self.uid = "%s_%d" % ( device_info.model_id, index )
        self.model_id = device_info.model_id     
        self.usb_id = device_info.usb_id
        self.key_layout = device_info.key_layout  
        self.bpp = device_info.bpp
        self.lcd_size = device_info.lcd_size
        self.model_fullname = device_info.model_fullname
        self.all_keys = device_info.all_keys
        self.action_keys = device_info.action_keys
        
    def get_key_index(self, key):
        self.all_keys.index(key)
        
    def __repr__(self):
        return "Device [%s] %s model: %s (%s) on device %s:%s. Has a %d BPP screen of %dx%d. " %  \
            ( str(self.usb_device), self.uid, self.model_id, self.model_fullname, hex(self.usb_id[0]), hex(self.usb_id[1]), self.bpp, self.lcd_size[0], self.lcd_size[1])
    
def get_device_info(model_id):
    return device_list[model_id]

def is_enabled(conf_client, device):    
    val = conf_client.get("/apps/gnome15/%s/enabled" % device.uid)
    return ( val == None and device.model_id != "virtual" ) or ( val is not None and val.get_bool() )
        
def set_enabled(conf_client, device, enabled):
    conf_client.set_bool("/apps/gnome15/%s/enabled" % device.uid, enabled)
    
def find_all_devices():
    """
    Get a list of Device objects, one for each supported device that is plugged in.
    There may be more than one device of the same type.
    """
    
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
                devices.append(Device(usb_device, index, device_info))
                indices[device_key] = index + 1
            
 
    """
    If the GTK driver is installed, add a virtual device as well
    """
    if g15drivermanager.get_driver_mod("gtk"): 
        devices.append(Device(None, 0, device_list['virtual']))
    
    return devices

def find_device(models):
    for lg_model in find_all_devices():
        for model in models:
            if lg_model.model_name == model:
                return lg_model

"""
Register all supported models
"""
if g15drivermanager.get_driver_mod("gtk"): 
    DeviceInfo('virtual', (0x0000, 0x0000), [], 0, ( 0,    0 ), "Virtual LCD Window", None)
DeviceInfo(g15driver.MODEL_G11, (0x046d, 0xc225), g11_key_layout,   0,  ( 0,    0 ),    "Logitech G11 Keyboard", None)
DeviceInfo(g15driver.MODEL_G19, (0x046d, 0xc229), g19_key_layout,   16, ( 320,  240 ),  "Logitech G19 Gaming Keyboard", g19_action_keys)
DeviceInfo(g15driver.MODEL_G15_V1, (0x046d, 0xc221), g15v1_key_layout, 1,  ( 160,  43 ),   "Logitech G15 Gaming Keyboard (version 1)", g15_action_keys) 
DeviceInfo(g15driver.MODEL_G15_V2, (0x046d, 0xc227), g15v2_key_layout, 1,  ( 160,  43 ),   "Logitech G15 Gaming Keyboard (version 2)", g15_action_keys)
DeviceInfo(g15driver.MODEL_G13, (0x046d, 0xc21c), g13_key_layout,   1,  ( 160,  43 ),   "Logitech G13 Advanced Gameboard", g15_action_keys)
DeviceInfo(g15driver.MODEL_G510, (0x046d, 0xc22d), g510_key_layout,  1,  ( 160,  43 ),   "Logitech G510 Keyboard", g15_action_keys)
DeviceInfo(g15driver.MODEL_G510_AUDIO, (0x046d, 0xc22e), g510_key_layout,  1,  ( 160,  43 ),   "Logitech G510 Keyboard (audio)", g19_action_keys)
DeviceInfo(g15driver.MODEL_Z10, (0x046d, 0x0a07), z10_key_layout,   1,  ( 160,  43 ),   "Logitech Z10 Speakers", g19_action_keys)
DeviceInfo(g15driver.MODEL_G110, (0x046d, 0xc225), g110_key_layout,  0,  ( 0,    0 ),    "Logitech G110 Keyboard", None)

# When I get hold of an MX5500, I will add Bluetood detection as well
DeviceInfo(g15driver.MODEL_MX5500, (0x0000, 0x0000), mx5500_key_layout,  1,  ( 136,    32 ),    "Logitech MX5500", mx5500_action_keys)

if __name__ == "__main__":
    for device in find_all_devices():
        print str(device)
        