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


import gnome15.g15locale as g15locale
_ = g15locale.get_translation("im", modfile = __file__).ugettext

import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15plugin as g15plugin
import dbus
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
name=_("Instant Messenger")
description=_("Integrates with a number of instant messengers, showing \
            buddy lists and messages on your LCD. Currently supports all \
            clients that use the Telepathy framework.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2011 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous contact"), 
         g15driver.NEXT_SELECTION : _("Next contact"), 
         g15driver.VIEW : _("Toggle mode"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page")
         }

# Other constants
POSSIBLE_ICON_NAMES = [ "im-user", "empathy", "pidgin", "emesene", "system-config-users", "im-message-new" ]
CONNECTION_PRESENCE_TYPE_OFFLINE = 1

IMAGE_DIR = 'images'
STATUS_MAP = {
        ( CONNECTION_PRESENCE_TYPE_OFFLINE, None ): [ [ "offline", "user-offline-panel" ] , _("Offline")],
        ( CONNECTION_PRESENCE_TYPE_AVAILABLE, None ): [ "user-available", _("Available") ],
        ( CONNECTION_PRESENCE_TYPE_AVAILABLE, "chat" ): [ "im-message-new", _("Chatty") ],
        ( CONNECTION_PRESENCE_TYPE_AWAY, None ): [ "user-idle", _("Idle") ],
        ( CONNECTION_PRESENCE_TYPE_BUSY, None ): [ "user-busy", _("Busy") ],
        ( CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY, None ): [ "user-away", _("Away") ]
                                                 }

MODE_ALL = "all"
MODE_ONLINE = "online"
MODE_AVAILABLE = "available"
MODE_LIST= [ MODE_ONLINE, MODE_AVAILABLE, MODE_ALL ]
MODES = {
         MODE_ALL : [ "All", _("All Contacts") ],
         MODE_ONLINE : [ "Online", _("Online Contacts") ],
         MODE_AVAILABLE : [ "Available", _("Available Contacts") ]
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

    def __init__(self, list_store, conn, screen):
        self.menu = list_store
        self._conn = conn
        self.screen = screen
        self._contact_list = {}
        self._conn.call_when_ready(self._connection_ready_cb)
        
    def deactivate(self):
        pass

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
        logger.debug("Requesting contact info for %s" %(str(handles)))
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
        logger.debug("Received contact attributes for %s" %(str(attributes)))
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
        logger.debug("Add contact %s (%s)" %(str(contact),str(handle)))
        self._contact_list[handle] = contact
        self.menu.add_contact(self._conn, handle, contact, presence, alias)

    def _contact_presence_changed_cb(self, presences):
        logger.debug("Contact presence changed %s" %(str(presences)))
        for handle, presence in presences.iteritems():
            if handle in self._contact_list:
                self._update_contact_presence(handle, presence)
            else:
                self._request_contact_info([handle])

    def _update_contact_presence(self, handle, presence):
        logger.debug("Updating contact presence for %s" %(str(handle)))
        self.menu.update_contact_presence(self._conn, handle, presence)

    def _error_cb(self, *args):
        logger.error("Error happens: %s" % args)

"""
Represents a contact as a single item in a menu
"""
class ContactMenuItem(g15theme.MenuItem):    
    def __init__(self, conn, handle, contact, presence, alias):
        g15theme.MenuItem.__init__(self, "contact-%s-%s" % ( str(conn), str(handle) ) )
        self.conn = conn
        self.handle = handle
        self.contact=  contact
        self.presence = presence
        self.alias = alias  
        
    def get_theme_properties(self):
        """
        Render a single menu item
        
        Keyword arguments:
        item -- item object
        selected -- selected item object
        canvas -- canvas to draw on
        properties -- properties to pass to theme
        attribtes -- attributes to pass to theme
        
        """       
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.alias
        item_properties["item_alt"] = self._get_status_text(self.presence)
        item_properties["item_type"] = ""
        item_properties["item_icon"] = g15util.get_icon_path(self._get_status_icon_name(self.presence))
        return item_properties
        
    def set_presence(self, presence):
        logger.debug("Setting presence of %s to %s" % (str(self.contact), str(presence)))
        self.presence = presence   
        
    '''
    Private
    '''

    def _get_status_text(self, presence):        
        key = ( presence[0], presence[1] ) 
        if key in STATUS_MAP:
            return STATUS_MAP[key][1]
        key = ( presence[0], None ) 
        if key in STATUS_MAP:
            return STATUS_MAP[key][1]
        logger.warning("Unknown presence %d = %s" % (presence[0], presence[1]))
        return "Unknown"
    
    def _get_status_icon_name(self, presence):
        key = ( presence[0], presence[1] ) 
        if key in STATUS_MAP:
            return STATUS_MAP[key][0]
        key = ( presence[0], None ) 
        if key in STATUS_MAP:
            return STATUS_MAP[key][0]
        logger.warning("Unknown presence %d = %s" % (presence[0], presence[1]))
        return "dialog-warning"   
        
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

    def __init__(self, mode):
        """
        Create the menu instance
        
        Keyword arguments:
        screen -- screen instance
        page -- page object
        mode -- display mode
        """
        g15theme.Menu.__init__(self, "menu")
        self.mode = mode
        self.on_update = None
        if not self.mode:
            self.mode = MODE_ONLINE
        self._contacts = []
        self._contact_lists = {}
        self._connections = []
        for connection in telepathy.client.Connection.get_connections():
            self._connect(connection)

    def deactivate(self):
        for c in self._connections:
            if c in self._contact_lists:
                self._contact_lists[c].deactivate()
            if c._status_changed_connection:
                c._status_changed_connection.remove()
                c._status_changed_connection = None
        self._connections = []
        self._contact_lists = {}
        self._contacts = []
            
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
                if self.on_update:
                    self.on_update()
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
        contacts that are appropriate for the current mode will be added
        """
        logger.debug("Reloading contacts")
        c = []
        for item in self._contacts:
            if self._is_presence_included(item.presence):
                c.append(item)
        self.sort_items(c)
        self.select_first()
        self.mark_dirty()
        
    def sort_items(self, children):
        """
        Sort items based on their alias and presence
        """
        self.set_children(sorted(children, cmp=compare_contacts))

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
        self.reload()
        if self.on_update:
            self.on_update()

    def update_contact_presence(self, conn, handle, presence):
        """
        Update a contact's presence in the list and reload
        
        Keyword arguments:
        conn -- connection
        handle -- contact handle
        prescence -- presence object
        """
        for row in self._contacts:
            if row.handle == handle and row.conn == conn:
                logger.debug("Updating presence of %s to %s" % (str(row.contact), str(presence)))
                row.set_presence(presence)
                self.selected = row
                self.reload()
                if self.on_update:
                    self.on_update()
                return
        logger.warning("Got presence update for unknown contact %s" %(str(presence)))
    
        
    '''
    Private
    '''
        
     
    def _connect(self, connection):
        """
        Connect to the given path. Events will then be received to add new contacts
        
        Keyword arguments:
        connection -- connection object 
        """
        self._contact_lists[connection] = ContactList(self, connection, self.screen)
        self._connections.append(connection)
            
    def _is_presence_included(self, presence):
        """
        Determine if presence is appropriate for the current mode
        
        Keyword arguments:
        presence -- presence
        """
        return ( self.mode == MODE_ONLINE and presence[0] != 1 ) or \
            ( self.mode == MODE_AVAILABLE and presence[0] == CONNECTION_PRESENCE_TYPE_AVAILABLE ) or \
            self.mode == MODE_ALL

"""
Instant Messenger plugin class
"""

class G15Im(g15plugin.G15MenuPlugin):

    def __init__(self, gconf_client, gconf_key, screen):
        """
        Constructor
        
        Keyword arguments:
        gconf_client -- GConf client instance
        gconf_key -- gconf_key for storing plugin preferences
        screen -- screen manager
        """
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, POSSIBLE_ICON_NAMES, id, name)
        
        self.hidden = False
        self._session_bus = dbus.SessionBus()
        self._signal_handle = None

    def activate(self):
        """
        Activate the plugin
        """
        g15plugin.G15MenuPlugin.activate(self)
        self.screen.key_handler.action_listeners.append(self)
        self._signal_handle = self._session_bus.add_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')
            
    def create_menu(self):    
        mode = self.gconf_client.get_string(self.gconf_key + "/mode")
        return ContactMenu(mode)
    
    def deactivate(self):
        self.screen.key_handler.action_listeners.remove(self)
        g15plugin.G15MenuPlugin.deactivate(self)
        if self._signal_handle:
            self._session_bus.remove_signal_receiver(self._signal_handle)
        
    def action_performed(self, binding):
        """
        Handle actions. Most actions will be handle by the abstract menu plugin class, 
        but we want to switch the mode when the "View" action is selected.
         
        Keyword arguments:
        binding -- binding
        """
        if binding.action == g15driver.VIEW and self.page != None and self.page.is_visible(): 
            mode_index = MODE_LIST.index(self.menu.mode) + 1
            if mode_index >= len(MODE_LIST):
                mode_index = 0
            self.menu.mode = MODE_LIST[mode_index]
            logger.info("Mode is now %s" % self.menu.mode)
            self.gconf_client.set_string(self.gconf_key + "/mode", self.menu.mode)
            self.menu.reload()
            self.screen.redraw(self.page)
            return True
    
    def get_theme_properties(self):
        props = g15plugin.G15MenuPlugin.get_theme_properties(self)
        props["title"] = MODES[self.menu.mode][1]
        
        # Get what mode to switch to
        mode_index = MODE_LIST.index(self.menu.mode) + 1
        if mode_index >= len(MODE_LIST):
            mode_index = 0
        props["list"] = MODES[MODE_LIST[mode_index]][0]
        return props 
    
    """
    DBUS callbacks functions
    """
        
    def _name_owner_changed(self, name, old_owner, new_owner):
        """
        If the change is a telepathy connection, determine if it is
        a connection that is to be removed, or a new connection to
        be added
        """
        if name.startswith("org.freedesktop.Telepathy.Connection"):
            logger.info("Telepathy Name owner changed for %s from %s to %s", name, old_owner, new_owner)
            connected = self.menu.is_connected(name)
            if new_owner == "" and connected:
                logger.info("Removing %s" % name)
                g15util.schedule("RemoveConnection", 5.0, self.menu.remove_connection, name)
            elif old_owner == "" and not connected:
                logger.info("Adding %s" % name)
                g15util.schedule("NewConnection", 5.0, self.menu.new_connection, name, self._session_bus)
        
