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
 
import switk.switk as switk
import gnome15.g15_globals as pglobals
 
# Plugin details - All of these must be provided
id="tk-test"
name="Toolkit testing"
description="Plugin to test the SVG toolkit components"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True

IF_NAME="org.freedesktop.Notifications"
BUS_NAME="/org/freedesktop/Notifications"

def create(gconf_key, gconf_client, screen):
    return G15TkTest(gconf_client, gconf_key, screen)        
            
class G15TkTest(dbus.service.Object):
    
    def __init__(self, gconf_client,gconf_key, screen):
        self.screen = screen;
        self.gconf_key = gconf_key

    def activate(self):
        self.page = self.screen.new_page(self._paint, priority=g15screen.PRI_NORMAL, id="TkTest")
    
    def deactivate(self):
        self.screen.del_page(self.page)
        
    def destroy(self):
        pass 
        
    def reload_theme(self):   
        dir = os.path.join(os.path.dirname(__file__), "default")
        
        self.theme = g15theme.G15Theme(dir, self.screen, self.last_variant)
        self.s_theme = switk.STheme(dir, self.screen.driver.get_model_name())
        
        self.panel = switk.SContainer(self.s_theme, layout = switk.SBorderLayout())
        self.panel.add(switk.SLabel(self.s_theme, "Hello World"), switk.CENTER)
        
    def _paint(self, canvas):
        self.panel.paint(canvas)