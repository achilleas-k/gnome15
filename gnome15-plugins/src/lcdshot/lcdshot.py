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

import gnome15.g15driver as g15driver
import os.path 
import logging
logger = logging.getLogger("volume")

# Plugin details - All of these must be provided
id="lcdshot"
name="LCD Screenshot"
description="Takes a screenshot of the LCD"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False

''' 
This simple plugin takes a screenshot of the LCD
'''

def create(gconf_key, gconf_client, screen):
    return G15LCDShot(screen, gconf_client, gconf_key)
            
class G15LCDShot():
    
    def __init__(self, screen, gconf_client, gconf_key):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key

    def activate(self):
        pass 
    
    def deactivate(self):
        pass
        
    def destroy(self):
        pass
    
    def handle_key(self, keys, state, post):
        # TODO better key
        if not post and state == g15driver.KEY_STATE_DOWN and g15driver.G_KEY_G1 in keys:
            if self._screen.old_surface:
                self._screen.draw_lock.acquire()
                try:
                    self._screen.old_surface.write_to_png(os.path.expanduser("~/Desktop/lcd.png"))
                finally:
                    self._screen.draw_lock.release()
            print "Screen shot"
        