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
import g15_driver as g15driver

'''
Keyboard layouts 
'''

z10_key_layout = []

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
              [ g15driver.G_KEY_G6, g15driver.G_KEY_G12 ],
              [ g15driver.G_KEY_UP ],
              [ g15driver.G_KEY_LEFT, g15driver.G_KEY_OK, g15driver.G_KEY_RIGHT ],
              [ g15driver.G_KEY_DOWN ],
              [ g15driver.G_KEY_MENU, g15driver.G_KEY_BACK, g15driver.G_KEY_SETTINGS ],
              [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3, g15driver.G_KEY_MR ],
              ]

device_list = { 
                  g15driver.MODEL_G19 : [ (0x046d, 0xc229), g19_key_layout, 16, ( 320, 240 ) ], 
                  g15driver.MODEL_G15_V1 : [ (0x046d, 0xc222), g15v1_key_layout, 1, ( 160, 43 ) ], 
                  g15driver.MODEL_G15_V2 : [ (0x046d, 0xc227), g15v2_key_layout, 1, ( 160, 43 ) ],
                  g15driver.MODEL_G13 : [ (0x046d, 0xc21c), g13_key_layout, 1, ( 160, 43 ) ],
                  g15driver.MODEL_G510 : [ (0x046d, 0xc22e), g510_key_layout, 1, ( 160, 43 ) ],
                  g15driver.MODEL_G510_AUDIO : [ (0x046d, 0xc22e), g510_key_layout, 1, ( 160, 43 ) ],
                  g15driver.MODEL_Z10 : [ (0x046d, 0x0a07), z10_key_layout, 1, ( 160, 43 ) ],
                  g15driver.MODEL_G110 : [ (0x046d, 0xc225), g110_key_layout, 0, ( 0, 0 ) ],
                   }

'''
Locates which Logitech devices are available by examining the USB bus
'''

class Device():
    def __init__(self, device, model_name):
        device_info = device_list[model_name]
        
        self.model_name = model_name
        self.device = device
        self.usb_ib = device_info[0]
        self.key_layout = device_info[1]  
        self.bpp = device_info[2]
        self.lcd_size = device_info[3]

def find_device():
    for lg_model in device_list:
        id = device_list[lg_model][0]
        device = _find_device(id[0], id[1])
        if device:
            return Device(device, lg_model)
        
def _find_device(idVendor, idProduct):
    for bus in usb.busses():
        for dev in bus.devices:
            if dev.idVendor == idVendor and \
                    dev.idProduct == idProduct:
                return dev
    return None
