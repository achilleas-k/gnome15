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
_ = g15locale.get_translation("voip", modfile = __file__).ugettext

import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15plugin as g15plugin
import gnome15.g15screen as g15screen
import os
import traceback
import time

# Logging
import logging
logger = logging.getLogger("voip")


# Plugin details - All of these must be provided
id="voip"
name=_("VoIP")
description=_("Provides integration with VoIP clients such as TeamSpeak3, showing \n\
buddy lists, microphone status and more.\n\n\
Note, TeamSpeak3 is currently the only support client, but the intention is\n\
to add support for others such as Mumble")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous contact"), 
         g15driver.NEXT_SELECTION : _("Next contact"), 
         g15driver.VIEW : _("Toggle mode"), 
         g15driver.CLEAR : _("Toggle buddies/messages"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page")
         }

# Other constants
POSSIBLE_ICON_NAMES = [ "im-user", "empathy", "pidgin", "emesene", "system-config-users", "im-message-new" ]
MUTED_ICONS = ["microphone-sensitivity-muted", "microphone-sensitivity-muted-symbolic", \
               "audio-input-microphone-muted", "audio-input-microphone-muted-symbolic", \
               os.path.join(os.path.dirname(__file__), "g19_microphone-sensitivity-muted.png")]
UNMUTED_ICONS = ["microphone-sensitivity-high", "microphone-sensitivity-high-symbolic", \
                 "audio-input-microphone-high", "audio-input-microphone-high-symbolic", \
               os.path.join(os.path.dirname(__file__), "g19_microphone-sensitivity-high.png")]
RECORD_ICONS = [ "media-record", "player_record" ]
MONO_RECORD_ICON = os.path.join(os.path.dirname(__file__), "default_record.gif")
MONO_MIC_UNMUTED = os.path.join(os.path.dirname(__file__), "default_microphone-sensitivity-high.gif")
MONO_MIC_MUTED = os.path.join(os.path.dirname(__file__), "default_microphone-sensitivity-muted.gif")
MONO_SPKR_UNMUTED = os.path.join(os.path.dirname(__file__), "default_audio-high.gif")
MONO_SPKR_MUTED = os.path.join(os.path.dirname(__file__), "default_audio-muted.gif")
MONO_AWAY = os.path.join(os.path.dirname(__file__), "default_away.gif")
MONO_ONLINE = os.path.join(os.path.dirname(__file__), "default_available.gif")

IMAGE_DIR = 'images'

MODE_ALL = "all"
MODE_ONLINE = "online"
MODE_TALKING = "talking"
MODE_LIST= [ MODE_ONLINE, MODE_TALKING, MODE_ALL ]
MODES = {
         MODE_ALL : [ "All", _("All") ],
         MODE_ONLINE : [ "Online", _("Online") ],
         MODE_TALKING : [ "Talking", _("Talking") ]
         }

def create(gconf_key, gconf_client, screen):
    """
    Create the plugin instance
    
    gconf_key -- GConf key that may be used for plugin preferences
    gconf_client -- GConf client instance
    """
    return G15Voip(gconf_client, gconf_key, screen)

def get_backend(backend_type):
    """
    Get the backend plugin module, given the backend_type
    
    Keyword arguments:
    backend_type          -- backend type
    """
    import gnome15.g15pluginmanager as g15pluginmanager
    return g15pluginmanager.get_module_for_id("voip-%s" % backend_type)

def get_available_backends():
    """
    Get the "backend type" names that are available by listing all of the voip
    backend plugins that are installed 
    """
    l = []
    import gnome15.g15pluginmanager as g15pluginmanager
    for p in g15pluginmanager.imported_plugins:
        if p.id.startswith("voip-"):
            l.append(p.id[5:])
    return l

     
class VoipBackend():
    
    def __init__(self):
        pass
    
    def get_me(self):
        """
        Get the local user's buddy entry
        """
        raise Exception("Not implemented")
    
    def get_buddies(self):
        raise Exception("Not implemented")
    
    def start(self, plugin):
        raise Exception("Not implemented")
    
    def stop(self):
        raise Exception("Not implemented")
    
    def get_icon(self):
        raise Exception("Not implemented")

class MessageMenuItem(g15theme.MenuItem):    
    def __init__(self, text):        
        g15theme.MenuItem.__init__(self, "message-%s" % time.time(), text )
        self._text = text
        
    def get_theme_properties(self):
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["line"] = self._text
        return item_properties
    
    def on_configure(self):        
        self.set_theme(g15theme.G15Theme(self.parent.get_theme().dir, "message-menu-entry"))

class BuddyMenuItem(g15theme.MenuItem):    
    def __init__(self, db_id, clid, nickname, client_type):
        self.db_id = db_id
        self.clid = clid
        self.nickname = nickname
        self.client_type = client_type
        g15theme.MenuItem.__init__(self, "client-%s" % clid )
        self.input_muted = None
        self.output_muted = None
        self.away = False
        self.talking = False
    
    def on_configure(self):        
        self.set_theme(g15theme.G15Theme(self.parent.get_theme().dir, "menu-entry" if self.group else "menu-child-entry"))
        
    def is_showing(self):
        menu = self.parent
        return ( menu.mode == MODE_TALKING and self.talking ) or \
            ( menu.mode == MODE_ONLINE and not self.away ) or \
            menu.mode == MODE_ALL

    def get_theme_properties(self):
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        
        if self.away and isinstance(self.away, str):
            item_properties["item_name"] = "%s - %s" % ( self.nickname, self.away )
        else:
            item_properties["item_name"] = self.nickname
        
        item_properties["item_alt"] = ""
        item_properties["item_type"] = ""
        
        if self.get_screen().device.bpp == 1:
            item_properties["item_talking_icon"] = MONO_RECORD_ICON if self.talking else ""
            item_properties["item_input_muted_icon"] = MONO_MIC_MUTED if self.input_muted else MONO_MIC_UNMUTED
            item_properties["item_output_muted_icon"] = MONO_SPKR_MUTED if self.output_muted else MONO_SPKR_UNMUTED
            item_properties["item_icon"] = MONO_ONLINE if not self.away else MONO_AWAY
        else:
            item_properties["item_input_muted_icon"] = g15util.get_icon_path(MUTED_ICONS if self.input_muted else UNMUTED_ICONS)
            item_properties["item_output_muted_icon"] = g15util.get_icon_path("audio-volume-muted" if self.output_muted else "audio-volume-high")
            item_properties["item_icon"] = g15util.get_icon_path("user-available" if not self.away else "user-away")
            item_properties["item_talking_icon"] = g15util.get_icon_path(RECORD_ICONS) if self.talking else ""
        
        return item_properties
        
        
class BuddyMenu(g15theme.Menu):

    def __init__(self):
        g15theme.Menu.__init__(self, "menu")
        self.mode = MODE_ONLINE
        self.focusable = True
        
class G15Voip(g15plugin.G15MenuPlugin):

    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, POSSIBLE_ICON_NAMES, id, name)
        
        self.hidden = False

    def activate(self):
        """
        We override default activate behavior as we only want the page to 
        appear once connected to the backend
        """
        self.message_menu = None
        self._raise_timer = None
        self._connected = False
        self.screen.key_handler.action_listeners.append(self)
        self._connection_timer = None                    
        self.reload_theme()
        self._attempt_connection()
        
    def _attempt_connection(self):
        try:
            if self._raise_timer is not None:
                self._raise_timer.cancel()
            # For now, TS3 only backend
            self.backend = get_backend("teamspeak3").create_backend()
            self.set_icon(self.backend.get_icon())
            self.backend.start(self)
            self.show_menu()
            self._load_buddy_list()
            self._connected = True
        except:          
            traceback.print_exc()
            self._connection_timer = g15util.schedule("ReconnectVoip", 5, self._attempt_connection)
            
    def create_menu(self):    
        return BuddyMenu()
    
    def create_page(self):
        page = g15plugin.G15MenuPlugin.create_page(self)
        self.message_menu = g15theme.Menu("messagesMenu")
        self.message_menu.focusable = True
        page.add_child(self.message_menu)
        page.add_child(g15theme.Scrollbar("messagesScrollbar", self.message_menu.get_scroll_values))
        return page
    
    def deactivate(self):
        if self._connection_timer is not None:
            self._connection_timer.cancel()
        self.backend.stop()
        self.screen.key_handler.action_listeners.remove(self)
        g15plugin.G15MenuPlugin.deactivate(self)
        
    def action_performed(self, binding):
        if not self._connected:
            return False
        
        if self.page != None and self.page.is_visible():
            
            if binding.action == g15driver.VIEW: 
                mode_index = MODE_LIST.index(self.menu.mode) + 1
                if mode_index >= len(MODE_LIST):
                    mode_index = 0
                self.menu.mode = MODE_LIST[mode_index]
                logger.info("Mode is now %s" % self.menu.mode)
                self.gconf_client.set_string(self.gconf_key + "/mode", self.menu.mode)
#                self.menu.reload()
                self.screen.redraw(self.page)
                return True
            
            if binding.action == g15driver.CLEAR and self.page != None and self.page.is_visible():
                self.page.next_focus()
                return True
            
            if self.menu.is_focused():
                return self.menu.action_performed(binding)
    
    def get_theme_properties(self):
        props = g15plugin.G15MenuPlugin.get_theme_properties(self)
        props["title"] = MODES[self.menu.mode][1]
        
        # Get what mode to switch to
        mode_index = MODE_LIST.index(self.menu.mode) + 1
        if mode_index >= len(MODE_LIST):
            mode_index = 0
            
        props["list"] = MODES[MODE_LIST[mode_index]][0]
        
        me = self.backend.get_me()
        if self.screen.device.bpp == 1:
            props["talking_icon"] = MONO_RECORD_ICON if me is not None and me.talking else ""
            props["input_muted_icon"] = MONO_MIC_MUTED if me is not None and me.input_muted else MONO_MIC_UNMUTED
            props["output_muted_icon"] = MONO_SPKR_MUTED if me is not None and me.output_muted else MONO_SPKR_UNMUTED
            props["status_icon"] = MONO_ONLINE if me is not None and not me.away else MONO_AWAY
        else:
            props["status_icon"] = g15util.get_icon_path("user-available" if me is not None and not me.away else "user-away")
            props["input_muted_icon"] = g15util.get_icon_path(MUTED_ICONS if me is not None and me.input_muted else UNMUTED_ICONS)
            props["output_muted_icon"] = g15util.get_icon_path("audio-volume-muted" if me is not None and me.output_muted else "audio-volume-high")
            props["talking_icon"] = g15util.get_icon_path(RECORD_ICONS) if me is not None and me.talking else ""
         
        return props
    
    def message_received(self, sender, message):
        if self.message_menu is not None:
            while self.message_menu.get_child_count() > 20:
                self.message_menu.remove_child_at(0)
            self.message_menu.add_child(MessageMenuItem('%s - %s' % (sender, message)))
            self.message_menu.select_last_item()     
            self._popup()       
            
    def _popup(self):
        self._raise_timer = self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 6.0)
        
    """
    Private
    """
    
    def _load_buddy_list(self):
        items = sorted(self.backend.get_buddies(), key=lambda item: item.nickname)
        self.menu.set_children(items)
        if len(items) > 0:
            self.menu.selected = items[0]
        else:
            self.menu.selected = None
            
    def _disconnected(self):
        self._connected = False
        self.hide_menu()
        self._attempt_connection()