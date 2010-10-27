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

'''
Specialisation of the DBUSMenu module, specifically for the Indicator Messages 
message. This will show waiting messages from applications such as Evolution,
Empathy, Pidgin, Gwibber and others
'''
 
import dbus
import dbusmenu

from lxml import etree

'''
Indicator Messages  DBUSMenu property names
'''

VISIBLE = "visible"
APP_RUNNING = "app-running"
ICON_NAME = "icon-name"
TYPE = "type"
LABEL = "label"
INDICATOR_LABEL = "indicator-label"
INDICATOR_ICON = "indicator-icon"
RIGHT_SIDE_TEXT = "right-side-text"

'''
Indicator Messages DBUSMenu types
'''
TYPE_APPLICATION_ITEM = "application-item"
TYPE_INDICATOR_ITEM = "indicator-item"
TYPE_SEPARATOR = "separator"
TYPE_ROOT = "root"


class IndicatorMessagesMenuItem(dbusmenu.DBUSMenuItem):
    def __init__(self, id, properties):
        dbusmenu.DBUSMenuItem.__init__(self, id, properties)
        
    def set_properties(self, properties):
        dbusmenu.DBUSMenuItem.set_properties(self, properties)        
        self.type = self.properties[TYPE] if TYPE in self.properties else TYPE_ROOT
        
        # Label
        if self.type == TYPE_INDICATOR_ITEM:
            self.label = self.properties[INDICATOR_LABEL]
        elif LABEL in self.properties:
            self.label = self.properties[LABEL]
        else:
            self.label = None
            
        # Icon
        if self.type == TYPE_INDICATOR_ITEM:
            self.icon = self.properties[INDICATOR_ICON] if INDICATOR_ICON in self.properties else None
        else:
            self.icon = None
        
    def get_right_side_text(self):
        return self.properties[RIGHT_SIDE_TEXT] if RIGHT_SIDE_TEXT in self.properties else None
        
    def get_label(self):
        return self.label
        
    def is_app_running(self):
        return self.properties[APP_RUNNING]
        
    def is_visible(self):
        return self.properties[VISIBLE] if VISIBLE in self.properties else False
        
    def get_icon(self):
        return self.icon
        
    def get_icon_name(self):
        return self.properties[ICON_NAME] if ICON_NAME in self.properties else None
        
    def get_type(self):
        return self.properties[TYPE]

class IndicatorMessagesMenu(dbusmenu.DBUSMenu):
    
    def __init__(self, session_bus, on_change = None):
        dbusmenu.DBUSMenu.__init__(self, session_bus, "org.ayatana.indicator.messages", "/org/ayatana/indicator/messages/menu", "org.ayatana.dbusmenu", on_change)
        
    def create_item(self, id, properties):
        return IndicatorMessagesMenuItem(id, properties)
