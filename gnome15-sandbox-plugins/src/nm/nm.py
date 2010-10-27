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
 
import gnome15.g15_theme as g15theme
import gnome15.g15_screen as g15screen
import os

# Plugin details - All of these must be provided
id="nm"
name="Network Manager"
description="Displays current status of your network connections."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=False

def create(gconf_key, gconf_client, screen):
    return G15NM(gconf_client, gconf_key, screen)

class MenuItem():
    
    def __init__(self, page):
        self.page = page
        self.thumbnail = None

class G15NM():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
    
    def activate(self):
        self._reload_theme()
        self.page = self.screen.new_page(self.paint, id=id, priority = g15screen.PRI_EXCLUSIVE)
        self.screen.redraw(self.page)
    
    def deactivate(self):
        if self.page != None:
            self.screen.del_page(self.page)
            self.page = None
        
    def destroy(self):
        pass
    
    def paint(self, canvas):
        self.theme.draw(canvas, {})
        
    def _reload_theme(self):        
        self.theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self.screen)