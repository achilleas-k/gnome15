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
 

import os
import usb
import g15driver
import g15drivermanager

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
                  [ g15driver.G_KEY_G1, g15driver.G_KEY_G2 ],
                  [ g15driver.G_KEY_G3, g15driver.G_KEY_G4 ], 
                  [ g15driver.G_KEY_G5, g15driver.G_KEY_G6 ],
                  [ g15driver.G_KEY_G7, g15driver.G_KEY_G8 ],
                  [ g15driver.G_KEY_G9, g15driver.G_KEY_G10], 
                  [ g15driver.G_KEY_G11, g15driver.G_KEY_G12 ],
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

device_list = { 
                'virtual':                    [ (0x0000, 0x0000), [],               0,  ( 0,    0 ),    "Virtual LCD Window" ],
                g15driver.MODEL_G11 :         [ (0x046d, 0xc225), g11_key_layout,   0,  ( 0,    0 ),    "Logitech G11 Keyboard" ],
                g15driver.MODEL_G19 :         [ (0x046d, 0xc229), g19_key_layout,   16, ( 320,  240 ),  "Logitech G19 Gaming Keyboard" ], 
                g15driver.MODEL_G15_V1 :      [ (0x046d, 0xc221), g15v1_key_layout, 1,  ( 160,  43 ),   "Logitech G15 Gaming Keyboard (version 1)" ], 
                g15driver.MODEL_G15_V2 :      [ (0x046d, 0xc227), g15v2_key_layout, 1,  ( 160,  43 ),   "Logitech G15 Gaming Keyboard (version 2)" ],
                g15driver.MODEL_G13 :         [ (0x046d, 0xc21c), g13_key_layout,   1,  ( 160,  43 ),   "Logitech G13 Advanced Gameboard" ],
                g15driver.MODEL_G510 :        [ (0x046d, 0xc22d), g510_key_layout,  1,  ( 160,  43 ),   "Logitech G510 Keyboard" ],
                g15driver.MODEL_G510_AUDIO :  [ (0x046d, 0xc22e), g510_key_layout,  1,  ( 160,  43 ),   "Logitech G510 Keyboard (audio)" ],
                g15driver.MODEL_Z10 :         [ (0x046d, 0x0a07), z10_key_layout,   1,  ( 160,  43 ),   "Logitech Z10 Speakers" ],
                g15driver.MODEL_G110 :        [ (0x046d, 0xc225), g110_key_layout,  0,  ( 0,    0 ),    "Logitech G110 Keyboard" ],
                }

'''
Locates which Logitech devices are available by examining the USB bus
'''

class Device():
    def __init__(self, devices, uid, model_name, device_info):
        self.devices = devices 
        self.uid = uid
        self.model_name = model_name
        
        self.usb_id = device_info[0]
        self.key_layout = device_info[1]  
        self.bpp = device_info[2]
        self.lcd_size = device_info[3]
        self.model_fullname = device_info[4]
        
    def __repr__(self):
        return "Device %s model: %s (%s) on device %s:%s. Has a %d BPP screen of %dx%d. " %  \
            ( self.uid, self.model_name, self.model_fullname, hex(self.usb_id[0]), hex(self.usb_id[1]), self.bpp, self.lcd_size[0], self.lcd_size[1])
    
        
def is_enabled(conf_client, device):    
    val = conf_client.get("/apps/gnome15/%s/enabled" % device.uid)
    return val == None or val.get_bool()
        
def set_enabled(conf_client, device, enabled):
    conf_client.set_bool("/apps/gnome15/%s/enabled" % device.uid, enabled)
    
def find_all_devices():
    device_map = {}
    for bus in usb.busses():
        for dev in bus.devices:
            device_map[( dev.idVendor, dev.idProduct ) ] = dev
    devices = {}
    
    for device_key in device_map:
        for model_name in device_list:
            device_info = device_list[model_name]
            usb_id = device_info[0]
            if usb_id == device_key:
                """
                TODO - Check - G11 may be a special case, it is a G15v1 with a missing device (LCD), and uses same ID's.
                Unfortunately, this means this code cannot determine which is which if both are plugged in (hopefully
                very unlikley!)
                """
                if model_name == g15driver.MODEL_G15_V1 and not (0x046d, 0xc222) in device_map:
                    # Actually a G11
                    pass
                elif model_name == g15driver.MODEL_G11 and (0x046d, 0xc222) in device_map:
                    # Actually a G15
                    pass
                else:
                    usb_device = device_map[device_key] 
                    devices[usb_id] = Device(usb_device, model_name, model_name, device_info)
                
    """
    If the GTK driver is installed, add a virtual device as well
    """
    if g15drivermanager.get_driver_mod("gtk"): 
        devices[(0, 0)] = Device(None, 'virtual', 'virtual', device_list['virtual'])
    
    return devices.values()

def find_device(models):
    for lg_model in find_all_devices():
        for model in models:
            if lg_model.model_name == model:
                return lg_model


if __name__ == "__main__":
    for device in find_all_devices():
        print str(device)