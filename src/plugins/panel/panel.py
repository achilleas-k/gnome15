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
 
import gnome15.g15_screen as g15screen 
import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import datetime
from threading import Timer
import cairo
import gtk
import os
import sys
import time
import Image

# Plugin details - All of these must be provided
id="panel"
name="Panel"
description="Adds a small area at the bottom of the screen for other plugins to add permanent components to. " \
        + "This plugin only works on the G19. "
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False
        
def create(gconf_key, gconf_client, screen):
    return G15Panel(gconf_key, gconf_client, screen)

class G15Panel():    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.panel_applets = []
        self.active = False
    
    def activate(self):    
        if self.screen.driver.get_bpp() == 1:
            raise Exception("Panel not supported on low-res LCD")
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)
        self.screen.set_available_size((self.screen.width, self.screen.height - self.theme.bounds[3]))
        self.active = True
        self.chained_painter = self.screen.set_foreground_painter(self.paint)
        self.screen.redraw()
        for panel_applet in self.panel_applets:
            panel_applet.panel_changed()
            
    def is_active(self):
        return self.active
    
    def deactivate(self):
        self.active = False
        self.screen.set_foreground_painter(self.chained_painter)
        self.screen.set_available_size((self.screen.width, self.screen.height + self.theme.bounds[3]))
        self.screen.redraw()
        for panel_applet in self.panel_applets:
            panel_applet.panel_changed()
        
    def destroy(self):
        pass
    
    def get_enabled(self, panel_applet):
        # TODO - allow disabling of panel applets in panel preferences
        return True
        
    def paint(self, canvas):
        panel_height = self.theme.bounds[3]
        canvas.save()        
        canvas.translate(0, self.screen.height - panel_height)
        self.theme.draw(canvas, {})
        
        gap = panel_height / 10.0
        
        for panel_applet in self.panel_applets:
            canvas.translate(gap, gap)
            panel_applet.draw_panel_applet(canvas, panel_height - ( gap * 2 ), True)
            canvas.translate(-gap, -gap)
            
        canvas.restore()        
        
        if self.chained_painter != None:
            self.chained_painter(canvas)   