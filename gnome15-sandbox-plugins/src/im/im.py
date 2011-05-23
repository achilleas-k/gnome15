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
#
# Notes
# =====
#
# The program "contact-selector" was a big help in getting this working. The ContactList
# class is very loosely based on this, with many modifications. These are licensed under 
# LGPL. See http://telepathy.freedesktop.org/wiki/Contact%20selector


import gnome15.g15_util as g15util
import gnome15.g15_theme as g15theme
import gnome15.g15_driver as g15driver
import gnome15.g15_screen as g15screen
import gnome15.g15_globals as g15globals
import os
import sys
import dbus
import cairo
import traceback
import base64
import time
import telepathy
from telepathy.interfaces import (
        CHANNEL,
        CHANNEL_INTERFACE_GROUP,
        CHANNEL_TYPE_CONTACT_LIST,
        CONNECTION,
        CONNECTION_INTERFACE_ALIASING,
        CONNECTION_INTERFACE_CONTACTS,
        CONNECTION_INTERFACE_REQUESTS,
        CONNECTION_INTERFACE_SIMPLE_PRESENCE)

from telepathy.constants import (
        CONNECTION_PRESENCE_TYPE_AVAILABLE,
        CONNECTION_PRESENCE_TYPE_AWAY,
        CONNECTION_PRESENCE_TYPE_BUSY,
        CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
        HANDLE_TYPE_LIST)

# Logging
import logging
logger = logging.getLogger("im")

# Plugin details - All of these must be provided
id="im"
name="Instant Messenger"
description="Integrates with a number of instant messengers, showing " + \
            "buddy lists and messages on your LCD. Currently supports all " + \
            "clients that use the Telepathy framework."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2011 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110 ]

# Other constants
POSSIBLE_ICON_NAMES = [ "im-user", "empathy", "pidgin", "emesene", "system-config-users", "im-message-new" ]
CONNECTION_PRESENCE_TYPE_OFFLINE = 1

IMAGE_DIR = 'images'
STATUS_MAP = {
        ( CONNECTION_PRESENCE_TYPE_OFFLINE, None ): [ "offline" , "Offline"],
        ( CONNECTION_PRESENCE_TYPE_AVAILABLE, None ): [ "user-available", "Available" ],
        ( CONNECTION_PRESENCE_TYPE_AVAILABLE, "chat" ): [ "im-message-new", "Chatty" ],
        ( CONNECTION_PRESENCE_TYPE_AWAY, None ): [ "user-idle", "Idle" ],
        ( CONNECTION_PRESENCE_TYPE_BUSY, None ): [ "user-busy", "Busy" ],
        ( CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY, None ): [ "user-away", "Away" ]
                                                 }

MODE_ALL = "all"
MODE_ONLINE = "online"
MODE_AVAILABLE = "available"
MODE_LIST= [ MODE_ONLINE, MODE_AVAILABLE, MODE_ALL ]
MODES = {
         MODE_ALL : [ "All", "All Contacts" ],
         MODE_ONLINE : [ "Online", "Online Contacts" ],
         MODE_AVAILABLE : [ "Available", "Available Contacts" ]
         }

def create(gconf_key, gconf_client, screen):
    """
    Create the plugin instance
    
    gconf_key -- GConf key that may be used for plugin preferences
    gconf_client -- GConf client instance
    """
    return G15Im(gconf_client, gconf_key, screen)

"""
Holds list of contacts for a single connection
"""
class ContactList:

    def __init__(self, list_store, conn, screen, page):
        self._menu = list_store
        self._conn = conn
        self._screen = screen
        self._page = page
        self._contact_list = {}
        self._conn.call_when_ready(self._connection_ready_cb)

    def _connection_ready_cb(self, conn):
        if CONNECTION_INTERFACE_SIMPLE_PRESENCE not in conn:
            logger.warning("SIMPLE_PRESENCE interface not available on %s" %
                    conn.service_name)
            return
        if CONNECTION_INTERFACE_REQUESTS not in conn:
            logger.warning("REQUESTS interface not available on %s" %
                    conn.service_name)
            return

        conn[CONNECTION_INTERFACE_SIMPLE_PRESENCE].connect_to_signal(
            "PresencesChanged", self._contact_presence_changed_cb)
        self._ensure_channel()

    def _ensure_channel(self):
        groups = ["subscribe", "publish"]
        for group in groups:
            requests = {
                    CHANNEL + ".ChannelType": CHANNEL_TYPE_CONTACT_LIST,
                    CHANNEL + ".TargetHandleType": HANDLE_TYPE_LIST,
                    CHANNEL + ".TargetID": group}
            self._conn[CONNECTION_INTERFACE_REQUESTS].EnsureChannel(
                    requests,
                    reply_handler = self._ensure_channel_cb,
                    error_handler = self._error_cb)

    def _ensure_channel_cb(self, is_yours, channel, properties):
        channel = telepathy.client.Channel(
                service_name = self._conn.service_name,
                object_path = channel)
        DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'
        channel[DBUS_PROPERTIES].Get(
                CHANNEL_INTERFACE_GROUP,
                'Members',
                reply_handler = self._request_contact_info,
                error_handler = self._error_cb)

    def _request_contact_info(self, handles):
        interfaces = [CONNECTION,
                CONNECTION_INTERFACE_ALIASING,
                CONNECTION_INTERFACE_SIMPLE_PRESENCE]
        self._conn[CONNECTION_INTERFACE_CONTACTS].GetContactAttributes(
            handles,
            interfaces,
            False,
            reply_handler = self._get_contact_attributes_cb,
            error_handler = self._error_cb)

    def _get_contact_attributes_cb(self, attributes):
        for handle, member in attributes.iteritems():
            contact_info = self._parse_member_attributes(member)
            contact, alias, presence = contact_info
            if handle not in self._contact_list:
                self._add_contact(handle, contact, presence, str(alias))

    def _parse_member_attributes(self, member):
        contact_id, alias, presence = None, None, None
        for key, value in member.iteritems():
            if key == CONNECTION + '/contact-id':
                contact_id = value
            elif key == CONNECTION_INTERFACE_ALIASING + '/alias':
                alias = value
            elif key == CONNECTION_INTERFACE_SIMPLE_PRESENCE + '/presence':
                presence = value

        return (contact_id, alias, presence)

    def _add_contact(self, handle, contact, presence, alias):
        logger.debug("Add contact %s" %(str(contact)))
        self._contact_list[handle] = contact
        self._menu.add_contact(self._conn, handle, contact, presence, alias)

    def _contact_presence_changed_cb(self, presences):
        for handle, presence in presences.iteritems():
            if handle in self._contact_list:
                self._update_contact_presence(handle, presence)
            else:
                self._request_contact_info([handle])

    def _update_contact_presence(self, handle, presence):
        self._menu.update_contact_presence(self._conn, handle, presence)
        self._screen.redraw(self._page)

    def _error_cb(self, *args):
        logger.error("Error happens: %s" % args)

"""
Represents a contact as a single item in a menu
"""
class ContactMenuItem():    
    def __init__(self, conn, handle, contact, presence, alias):
        self.conn = conn
        self.handle = handle
        self.contact=  contact
        self.presence = presence
        self.alias = alias  
        
    def set_presence(self, presence):
        logger.debug("Setting presence of %s to %s" % (str(self.contact), str(presence)))
        self.presence = presence      
        
"""
Compare a single contact based on it's alias and presence
"""
def compare_contacts(a, b):
    if ( a is None and b is not None ):
        val = 1
    elif ( b is None and a is not None ):
        val = -1
    elif ( b is None and a is  None ):
        val = 0
    else:
        val = cmp(a.presence[0], a.presence[0])
        if val == 0:
            val = cmp(a.alias, b.alias)
        
    return val
    
"""
Theme menu for displaying all contacts across all monitored
connections.
"""
class ContactMenu(g15theme.Menu):

    def __init__(self, screen, page, mode):
        """
        Create the plugin instance
        
        Keyword arguments:
        screen -- screen instance
        page -- page object
        mode -- display mode
        """
        g15theme.Menu.__init__(self, "menu", screen)
        self.mode = mode
        if not self.mode:
            self.mode = MODE_ONLINE
        self._screen = screen
        self._page = page
        self._contacts = []
        self._contact_lists = {}
        self._connections = []
        for connection in telepathy.client.Connection.get_connections():
            self._connect(connection)
            
    def new_connection(self, bus_name, bus):
        """
        Add a new connection to those monitored for contacts.
        
        Keyword arguments:
        bus_name -- connection bus name
        bus -- dbus instance
        """
        connection = telepathy.client.Connection(bus_name, "/%s" % bus_name.replace(".", "/"), bus)
        self._connect(connection)
        
    
    def remove_connection(self, bus_name):
        """
        Remove a connection given its name. All contacts attached to this connection
        will be removed, and the menu reloaded
        
        Keyword arguments:
        bus_name -- bus name
        """
        for connection in list(self._connections):
            if connection.service_name == bus_name:
                del self._contact_lists[connection]
                self._connections.remove(connection)
                for item in list(self._contacts):
                    if item.conn == connection:
                        self._contacts.remove(item)
                self.reload()
                self._screen.redraw(self._page)
                return
            
    def is_connected(self, bus_name):
        """
        Determine if the given connection name exists in the list of
        connections currently being maintained
        
        Keyword arguments:
        bus_name -- bus name
        """
        for connection in self._connections:
            if connection.service_name == bus_name:
                return True
        return False
    
    def reload(self):
        """
        Build up the filter menu item list from the stored contacts. Only
        contacts that are approriate for the current mode will be added
        """
        logger.debug("Reloading contacts")
        self.items = []
        for item in self._contacts:
            if self._is_presence_included(item.presence):
                self.items.append(item)
        self.sort_items()
        self.select_first()
        
    def sort_items(self):
        """
        Sort items based on their alias and presence
        """
        self.items = sorted(self.items, cmp=compare_contacts)
     
    def _connect(self, connection):
        """
        Connect to the given path. Events will then be received to add new contacts
        
        Keyword arguments:
        connection -- connection object 
        """
        self._contact_lists[connection] = ContactList(self, connection, self._screen, self._page)
        self._connections.append(connection)

    def add_contact(self, conn, handle, contact, presence, alias):
        """
        Add a new contact to the menu
        
        Keyword arguments:
        conn -- connection
        handle -- contact handle
        contact -- contact id
        alias - alias or real name 
        """
        item = ContactMenuItem(conn, handle, contact, presence, alias)
        self._contacts.append(item)
        if self._is_presence_included(item.presence):
            self.items.append(item)
            self.sort_items()
            self._screen.redraw(self._page)
            
    def _is_presence_included(self, presence):
        """
        Determine if presence is appropriate for the current mode
        
        Keyword arguments:
        presence -- presence
        """
        return ( self.mode == MODE_ONLINE and presence[0] != 1 ) or \
            ( self.mode == MODE_AVAILABLE and presence[0] == CONNECTION_PRESENCE_TYPE_AVAILABLE ) or \
            self.mode == MODE_ALL

    def update_contact_presence(self, conn, handle, presence):
        """
        Update a contact's presence in the list and reload
        
        Keyword arguments:
        conn -- connection
        handle -- contact handle
        prescence -- presence object
        """
        for row in self._contacts:
            if row.handle == handle:
                logger.debug("Updating presence to %s" % str(presence))
                row.set_presence(presence)
                self.selected = row
                self.reload()
                return
        logger.warning("Got presence update for unknown contact %s" %(str(presence)))
        
    def load_theme(self):
       
        """
        Load the menu item theme
        """ 
        self.entry_theme = g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), self._screen, "menu-entry")
    
    def render_item(self, item, selected, canvas, properties, attributes, group = False): 
        """
        Render a single menu item
        
        Keyword arguments:
        item -- item object
        selected -- selected item object
        canvas -- canvas to draw on
        properties -- properties to pass to theme
        attribtes -- attributes to pass to theme
        
        """       
        item_properties = {}
        if selected == item:
            item_properties["item_selected"] = True
        item_properties["item_name"] = item.alias
        item_properties["item_alt"] = self._get_status_text(item.presence)
        item_properties["item_type"] = ""
        item_properties["item_icon"] = g15util.get_icon_path(self._get_status_icon_name(item.presence))
        self.entry_theme.draw(canvas, item_properties)
        return self.entry_theme.bounds[3]
    
    """
    Private
    """

    def _get_status_icon_name(self, presence):
        key = ( presence[0], presence[1] ) 
        if key in STATUS_MAP:
            return STATUS_MAP[key][0]
        key = ( presence[0], None ) 
        if key in STATUS_MAP:
            return STATUS_MAP[key][0]
        logger.warning("Unknown presence %d = %s" % (presence[0], presence[1]))
        return "dialog-warning"

    def _get_status_text(self, presence):        
        key = ( presence[0], presence[1] ) 
        if key in STATUS_MAP:
            return STATUS_MAP[key][1]
        key = ( presence[0], None ) 
        if key in STATUS_MAP:
            return STATUS_MAP[key][1]
        logger.warning("Unknown presence %d = %s" % (presence[0], presence[1]))
        return "Unknown"

"""
Instance Messenger plugin class
"""
class G15Im():

    def __init__(self, gconf_client, gconf_key, screen):
        """
        Constructor
        
        Keyword arguments:
        gconf_client -- GConf client instance
        gconf_key -- gconf_key for storing plugin preferences
        screen -- screen manager
        """
        self._screen = screen
        self.hidden = False
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._session_bus = dbus.SessionBus()
        self._icon_path = g15util.get_icon_path(POSSIBLE_ICON_NAMES)
        
    def activate(self):
        """
        Activate the plugin
        """
        self._page = None        
        self._reload_theme()
        self._show_menu()
        self._session_bus.add_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')  
    
    def deactivate(self):
        """
        Deactivate the plugin
        """
        if self._page != None:
            self._hide_menu()

    def destroy(self):
        """
        Destroy the plugin
        """
        pass
            
    def handle_key(self, keys, state, post):
        """
        Handle key events. This is called four times in total for every key stroke. Twice when
        the key is pressed, the second of which will set post to True. Then twice
        again when the key is released, again with post set to True on the second call. Acting
        on post=False allows overriding of other key mappings.
        
        True should be returned if the key is considered "handled" and should not be passed on
        to other key listeners.
         
        Keyword arguments:
        keys -- list of key codes
        state -- keystate (up or down)
        post -- boolean indicating if this is in the pre or post processing phase
        """
        if not post and state == g15driver.KEY_STATE_DOWN:              
            if self._screen.get_visible_page() == self._page:    
                if self._menu.handle_key(keys, state, post):
                    return True           
                elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                    return True
                elif g15driver.G_KEY_L3 in keys or g15driver.G_KEY_SETTINGS in keys:
                    mode_index = MODE_LIST.index(self._menu.mode) + 1
                    if mode_index >= len(MODE_LIST):
                        mode_index = 0
                    self._menu.mode = MODE_LIST[mode_index]
                    self._gconf_client.set_string(self._gconf_key + "/mode", self._menu.mode)
                    self._menu.reload()
                    self._screen.redraw(self._page)
                
        return False
    
    """
    Private functions
    """
        
    def _name_owner_changed(self, name, old_owner, new_owner):
        """
        If the change is a telepathy connection, determine if it is
        a connection that is to be removed, or a new connection to
        be added
        """
        if name.startswith("org.freedesktop.Telepathy.Connection"):
            logger.info("Telepathy Name owner changed for %s from %s to %s", name, old_owner, new_owner)
            connected = self._menu.is_connected(name)
            if new_owner == "" and connected:
                logger.info("Removing %s" % name)
                g15util.schedule("RemoveConnection", 5.0, self._menu.remove_connection, name)
            elif old_owner == "" and not connected:
                logger.info("Adding %s" % name)
                g15util.schedule("NewConnection", 5.0, self._menu.new_connection, name, self._session_bus)
        
    def _paint(self, canvas):
        props = { "icon" :  self._icon_path,
                 "mode" : self._menu.mode, 
                 "title" : MODES[self._menu.mode][1] }
        
        # Get what mode to switch to
        mode_index = MODE_LIST.index(self._menu.mode) + 1
        if mode_index >= len(MODE_LIST):
            mode_index = 0
        props["list"] = MODES[MODE_LIST[mode_index]][0]
        
        # Draw the page
        self._theme.draw(canvas, props, 
                        attributes = {
                                      "items" : self._menu.items,
                                      "selected" : self._menu.selected
                                      })
        
    def _reload_theme(self):
        """
        Reload the SVG theme and configure it
        """
        
        # Get the mode that was last used
        mode = self._gconf_client.get_string(self._gconf_key + "/mode")
        
        # Create the menu
        self._menu = ContactMenu(self._screen, self._page, mode)
        self._menu.on_selected = self._on_selected
        
        # Setup the theme
        self._theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), self._screen)
        self._theme.add_component(self._menu)
        self._theme.add_component(g15theme.Scrollbar("viewScrollbar", self._menu.get_scroll_values))
        
        
    def _on_selected(self):
        self._screen.redraw(self._page)
        
    def _show_menu(self):  
        """
        Create a new page for the menu and draw it
        """      
        self._page = self._screen.new_page(self._paint, id=name, priority = g15screen.PRI_NORMAL)
        self._screen.redraw(self._page)
    
    def _hide_menu(self):
        """
        Delete the page
        """     
        self._screen.del_page(self._page)
        self._page = None