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
 
import dbus

from lxml import etree
import time
import logging
logger = logging.getLogger("dbusmenu")


'''
DBUSMenu property names
'''
VISIBLE = "visible"
ICON_NAME = "icon-name"
TYPE = "type"
LABEL = "label"

TYPE_SEPARATOR = "separator"
TYPE_ROOT = "root"

class DBUSMenuEntry():
    def __init__(self, id, properties, menu):
        self.id = id
        self.menu = menu
        self.set_properties(properties)
        self.children = []
        
    def set_properties(self, properties):
        self.properties = properties
        if not VISIBLE in self.properties:
            self.properties[VISIBLE] = True
        self.label = self.properties[LABEL] if LABEL in self.properties else None
        self.icon = None
        self.type = self.properties[TYPE] if TYPE in self.properties else TYPE_ROOT
        
    def flatten(self, include_self = False):
        flat_list = []
        if include_self:
            self._flatten(self, flat_list)
        else:
            for c in self.children:
                self._flatten(c, flat_list)
        return flat_list
    
    def about_to_show(self):
        return self.menu.dbus_menu.AboutToShow(self.id)
    
    def activate(self, variant = 0):
        self.menu.dbus_menu.Event(self.id, "clicked", variant, int(time.time()))
    
    def hover(self, variant = 0):
        self.menu.dbus_menu.Event(self.id, "hovered", variant, int(time.time()))
    
    def _flatten(self, element, flat_list):
        flat_list.append(element)
        for c in element.children:
            _flatten(c, flat_list)
        
    def is_visible(self):
        return VISIBLE in self.properties and self.properties[VISIBLE]
        
    def get_label(self):
        return self.label
        
    def get_icon(self):
        return self.icon
    
    def get_alt_label(self):
        return ""
        
    def get_icon_name(self):
        return self.properties[ICON_NAME] if ICON_NAME in self.properties else None
        
class DBUSMenu():
    
    def __init__(self, session_bus, object_name, path, interface, on_change = None, natty = False):
        self.natty = natty
        self.session_bus = session_bus
        self.on_change = on_change
        self.messages_menu = self.session_bus.get_object(object_name, path)
        self.dbus_menu = dbus.Interface(self.messages_menu, interface)
        
        self.dbus_menu.connect_to_signal("ItemUpdated", self._item_updated)
        self.dbus_menu.connect_to_signal("ItemPropertyUpdated", self._item_property_updated)
        self.dbus_menu.connect_to_signal("LayoutUpdated", self._layout_updated)    
        self.dbus_menu.connect_to_signal("ItemActivationRequested", self._item_activation_requested)
        
        # From Natty onwards
        self.dbus_menu.connect_to_signal("ItemPropertiesUpdated", self._item_properties_updated)  
        
        self._get_layout()
        
    def create_entry(self, id, properties):
        return DBUSMenuEntry(id, properties, self) 
    
    '''
    Private
    '''
     
    def _item_activation_requested(self, id, timestamp):
        logger.warning("TODO - implement item activation request for %s on %d" % ( id, timestamp ) )
        
    def _layout_updated(self, revision, parent):
        self._get_layout()
        if self.on_change != None:
            self.on_change()
    
    def _item_updated(self, id):
        if str(id) in self.menu_map:
            menu = self.menu_map[str(id)]
            menu.set_properties(self.dbus_menu.GetProperties(id, []))
            if self.on_change != None:
                self.on_change(menu)
        else:
            logger.warning("Update request for item not in map")
    
    def _item_properties_updated(self, updated_properties, removed_properties):
        for id, properties in updated_properties:
            if str(id) in self.menu_map:
                menu = self.menu_map[str(id)]
                for prop in properties:
                    value = properties[prop]
                    if not prop in menu.properties or value != menu.properties[prop]:
                        menu.properties[prop] = value
                        menu.set_properties(menu.properties)
                        if self.on_change != None:
                            self.on_change(menu, prop, value)
            else:
                logger.warning("Update request for item not in map")
                
#        for id, properties in removed_properties:
#            print "Removed: ",str(id),str(properties)
    
    def _item_property_updated(self, id, prop, value):
        if str(id) in self.menu_map:
            menu = self.menu_map[str(id)]
            if not prop in menu.properties or value != menu.properties[prop]:
                menu.properties[prop] = value
                menu.set_properties(menu.properties)
                if self.on_change != None:
                    self.on_change(menu, prop, value)
        else:
            logger.warning("Update request for item not in map")
        
    def _get_layout(self):
        self.menu_map = {}
        if self.natty:
            revision, layout = self.dbus_menu.GetLayout(0, 3, [])
            self.root_item = self._load_menu_struct(layout, self.menu_map)
        else:
            revision, menu_xml = self.dbus_menu.GetLayout(0)
            self.root_item = self._load_xml_menu(etree.fromstring(menu_xml), self.menu_map)
            
    def _load_menu_struct(self, layout, map):
        id  = layout[0]
        properties = layout[1]
        menu = self.create_entry(id, dict(properties))
        map[str(id)] = menu
        children = layout[2]
        for item in children:
            menu.children.append(self._load_menu_struct(item, map))
        return menu
        
    def _load_xml_menu(self, element, map):
        id = int(element.get("id"))
        menu = self.create_entry(id, dict(self.dbus_menu.GetProperties(id, [])))
        map[str(id)] = menu
        for child in element:
            try :
                menu.children.append(self._load_xml_menu(child, map))
            except DBUSException as e:
                logger.warning("Failed to get child menu." % str(e))
        return menu
