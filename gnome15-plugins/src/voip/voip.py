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
_ = g15locale.get_translation("voip", modfile=__file__).ugettext

import gnome15.g15globals as g15globals
import gnome15.g15util as g15util
import gnome15.g15scheduler as g15scheduler
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15plugin as g15plugin
import gnome15.g15screen as g15screen
import os
import traceback
import time
import gnome15.colorpicker as colorpicker
from math import pi
import base64
import cairo
import gtk

# Logging
import logging
logger = logging.getLogger("voip")

# Actions
MUTE_INPUT = "voip-mute-input"
MUTE_OUTPUT = "voip-mute-ouptut"

# Plugin details - All of these must be provided
id = "voip"
name = _("VoIP")
description = _("Provides integration with VoIP clients such as TeamSpeak3, showing \n\
buddy lists, microphone status and more.\n\n\
Note, TeamSpeak3 is currently the only supported client, but the intention is\n\
to add support for others such as Mumble")
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = _("Copyright (C)2012 Brett Smith")
site = "http://www.russo79.com/gnome15"
has_preferences = True
needs_network=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions = { 
         g15driver.PREVIOUS_SELECTION : _("Previous contact"),
         g15driver.NEXT_SELECTION : _("Next contact"),
         g15driver.VIEW : _("Show settings"),
         g15driver.SELECT : _("Buddy options"),
         g15driver.CLEAR : _("Toggle buddies/messages"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page"),
         MUTE_INPUT : _("Mute Input (Microphone)"),
         MUTE_OUTPUT : _("Mute Output (Headphones/Speakers)")
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
MODE_LIST = [ MODE_ONLINE, MODE_TALKING, MODE_ALL ]
MODES = {
         MODE_ALL : [ "All", _("All") ],
         MODE_ONLINE : [ "Online", _("Online") ],
         MODE_TALKING : [ "Talking", _("Talking") ]
         }


def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "voip.glade"))
    dialog = widget_tree.get_object("VoipDialog")
    dialog.set_transient_for(parent)
    g15util.configure_checkbox_from_gconf(gconf_client, "%s/raise_on_talk_status_change" % gconf_key, "RaiseOnTalkStatusChange", False, widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, "%s/raise_on_chat_message" % gconf_key, "RaiseOnChatMessage", False, widget_tree)
    dialog.run()
    dialog.hide()
    
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

def get_backlight_key(gconf_key, buddy):
    """
    Get the gconf key used to store the buddy backlight color
    
    Keyword arguments:
    gconf_key          -- key root (from plugin)
    buddy              -- buddy menuitem object
    """
    enc_name = base64.b16encode(buddy.nickname)
    return "%s/backlight_colors/%s" % (gconf_key, enc_name)

   
def compare_buddies(a, b):
    """
    Compare two buddies based on their alias and presence
    
    Keyword arguments:
    a                -- buddy 1
    b                -- buddy 2
    """
    if ( a is None and b is not None ):
        val = 1
    elif ( b is None and a is not None ):
        val = -1
    elif ( b is None and a is  None ):
        val = 0
    else:
        val = cmp(a.talking, b.talking)
        if val == 0:
            val = cmp(a.away, b.away)
        
    return val
    
     
class VoipBackend():
    
    def __init__(self):
        pass
    
    def get_name(self):
        """
        Get the backend name
        """
        raise Exception("Not implemented")
    
    def get_current_channel(self):
        """
        Get the current channel
        """
        raise Exception("Not implemented")
    
    def get_talking(self):
        """
        Get who is talking
        """
        raise Exception("Not implemented")
    
    def get_me(self):
        """
        Get the local user's buddy entry
        """
        raise Exception("Not implemented")
    
    def get_channels(self):
        raise Exception("Not implemented")
    
    def get_buddies(self, current_channel=True):
        raise Exception("Not implemented")
    
    def start(self, plugin):
        raise Exception("Not implemented")
    
    def stop(self):
        raise Exception("Not implemented")
    
    def get_icon(self):
        raise Exception("Not implemented")
    
    def set_audio_input(self, mute):
        raise Exception("Not implemented")
    
    def set_audio_output(self, mute):
        raise Exception("Not implemented")
    
    def away(self):
        raise Exception("Not implemented")
    
    def online(self):
        raise Exception("Not implemented")

class MessageMenuItem(g15theme.MenuItem):    
    def __init__(self, sender, text, highlight):        
        g15theme.MenuItem.__init__(self, "message-%s" % time.time(), text, highlight)
        self._text = text
        self._highlight = highlight
        self._sender = sender
        
    def get_theme_properties(self):
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["highlight"] = self._highlight
        item_properties["sender"] = self._sender
        item_properties["line"] = self._text
        return item_properties
    
    def on_configure(self):        
        self.set_theme(g15theme.G15Theme(self.parent.get_theme().dir, "message-menu-entry"))
        
class ChannelMenuItem(g15theme.MenuItem):    
    def __init__(self, component_id, name, backend, icon = None):
        g15theme.MenuItem.__init__(self, component_id, icon = icon)
        self.name = name
        self.topic = None
        self.backend = backend
        self.radio = True
        
    def get_theme_properties(self):
        p = g15theme.MenuItem.get_theme_properties(self)
        p["item_radio"] = self.radio
        if self.radio:
            p["item_radio_selected"] = self == self.backend.get_current_channel()
        return p
        
    def activate(self):
        ret = self.on_activate()
        self.get_root().delete()
        return ret
        
    def on_activate(self):
        return True

class BuddyMenuItem(g15theme.MenuItem):    
    def __init__(self, component_id, nickname, channel, plugin):
        self.nickname = nickname
        self._plugin = plugin
        g15theme.MenuItem.__init__(self, component_id)
        self.input_muted = None
        self.output_muted = None
        self.away = False
        self.talking = False
        self.channel = channel
        
    def activate(self):
        self._plugin.activate_item(self)
        return True
    
    def on_configure(self):        
        self.set_theme(g15theme.G15Theme(self.parent.get_theme().dir, "menu-entry" if self.group else "menu-child-entry"))
        
    def is_showing(self):
        menu = self.parent
        if not menu:
            return False
        is_showing_status = (menu.mode == MODE_TALKING and self.talking) or \
            (menu.mode == MODE_ONLINE and not self.away) or \
            menu.mode == MODE_ALL            
        is_showing_channel = self.channel == self._plugin.backend.get_current_channel()
        return is_showing_status and is_showing_channel

    def get_theme_properties(self):
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        
        if self.away and isinstance(self.away, str):
            item_properties["item_name"] = "%s - %s" % (self.nickname, self.away)
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
        self.backend = None
        self.message_menu = None
        self.active = True

        self._talking = None
        self._backlight_ctrl = self.screen.driver.get_control("backlight_colour")        
        self._backlight_acq = None
        self._raise_timer = None
        self._connected = False
        self._connection_timer = None  
        
        self.screen.key_handler.action_listeners.append(self)                  
        self.reload_theme()
        self._attempt_connection()
        
    def _attempt_connection(self):
        try:
            if self._raise_timer is not None:
                self._raise_timer.cancel()
            # For now, TS3 only backend
            self.backend = get_backend("teamspeak3").create_backend()
            self.set_icon(self.backend.get_icon())
            if self.backend.start(self):
                self.show_menu()
                self._connected = True
            else:
                self._connection_timer = g15scheduler.schedule("ReconnectVoip", 5, self._attempt_connection)
        except:          
            traceback.print_exc()
            self._connection_timer = g15scheduler.schedule("ReconnectVoip", 5, self._attempt_connection)
            
    def create_menu(self):    
        return BuddyMenu()
    
    def create_page(self):
        page = g15plugin.G15MenuPlugin.create_page(self)
        m = g15theme.Menu("messagesMenu")
        m.focusable = True
        page.add_child(m)
        self.message_menu = m
        page.add_child(g15theme.MenuScrollbar("messagesScrollbar", self.message_menu))
        return page
    
    def deactivate(self):
        if self._backlight_acq:
            self.screen.driver.release_control(self._backlight_acq)
            self._backlight_acq = None
        if self._connection_timer is not None:
            self._connection_timer.cancel()
        if self.backend is not None:
            self.backend.stop()
        self.screen.key_handler.action_listeners.remove(self)
        g15plugin.G15MenuPlugin.deactivate(self)
        
    def load_menu_items(self):
        g15plugin.G15MenuPlugin.load_menu_items(self)
        self._load_buddy_list()
        
    def action_performed(self, binding):
        if not self._connected:
            return False
        
        if self.page != None and self.page.is_visible():
            
            if binding.action == g15driver.VIEW:
                MeOperationMenu(self.gconf_client, self.gconf_key, self.screen, self.backend, self.menu, self)
                return True
            
            if binding.action == g15driver.CLEAR and self.page != None and self.page.is_visible():
                self.page.next_focus()
                return True
            
            if self.menu.is_focused():
                return self.menu.action_performed(binding)
    
    def get_theme_properties(self):
        props = g15plugin.G15MenuPlugin.get_theme_properties(self)
        props["mode"] = MODES[self.menu.mode][1]
        props["name"] = self.backend.get_name() if self.backend is not None else ""
        props["channel"] = self.backend.get_current_channel().name if self.backend is not None else ""
        
        if self.menu.get_showing_count() == 0:
            if self.menu.mode == MODE_ALL:
                props["emptyMessage"] = _("Nobody connected")
            elif self.menu.mode == MODE_ONLINE:
                props["emptyMessage"] = _("Nobody online")
            elif self.menu.mode == MODE_TALKING:
                props["emptyMessage"] = _("Nobody talking")
        else:
            props["emptyMessage"] = ""
        
        # Get what mode to switch to
        mode_index = MODE_LIST.index(self.menu.mode) + 1
        if mode_index >= len(MODE_LIST):
            mode_index = 0
            
        props["list"] = MODES[MODE_LIST[mode_index]][0]
        
        talking_buddy = self.backend.get_talking()
        me = self.backend.get_me()
        
        props["talking"] = talking_buddy.nickname if talking_buddy is not None else ""
        props["talking_avatar"] = talking_buddy.avatar if talking_buddy is not None else (me.avatar if me is not None and me.avatar is not None else self.backend.get_icon())
        props["talking_avatar_icon"] = g15util.get_icon_path(RECORD_ICONS) if talking_buddy is not None else None 
        
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
    

    """
    Backends may call these functions when they get events internally 
    """    
    def buddy_left(self, buddy_item):
        if buddy_item.channel.name == self.backend.get_current_channel().name:
            self.message_received(self.backend.get_name(), _("%s left channel" % buddy_item.nickname), True)
        if self.menu is not None:
            self.menu.remove_child(buddy_item)
    
    def redraw(self):
        """
        Redraw the page
        """
        if self.page is not None:
            self.page.mark_dirty()
            self.page.redraw()
    
    def message_received(self, sender, message, highlight = False):
        """
        Add a message to the message list
        
        Keyword arguments:
        sender             -- sender
        message            -- message
        """
        if self.message_menu is not None:
            while self.message_menu.get_child_count() > 20:
                self.message_menu.remove_child_at(0)
            self.message_menu.add_child(MessageMenuItem(sender, message, highlight))
            self.message_menu.select_last_item()
            self.page.mark_dirty()  
            if g15util.get_bool_or_default(self.gconf_client, "%s/raise_on_chat_message" % self.gconf_key, False):   
                self._popup() 
            
    def activate_item(self, item):
        """
        Activate a buddy item, showing the menu
        
        Keyword arugments:
        item            -- buddy menu item object
        """
        BuddyOperationMenu(self.gconf_client, self.gconf_key, self.screen, self.backend, item, self)
        
    def reload_buddies(self):
        """
        Reload all buddies
        """
        if self.page is not None:
            self._load_buddy_list()
            self.redraw()
        
    def new_buddy(self, buddy_item):
        """
        A new buddy has entered view
        
        Keyword arguments:
        buddy_item    -- new buddy
        """        
        if buddy_item.channel.name == self.backend.get_current_channel().name:
            self.message_received(self.backend.get_name(), _("%s entered channel" % buddy_item.nickname), True)
        if self.menu is not None:
            items = self.menu.get_children()
            items.append(buddy_item)
            self.menu.set_children(sorted(items, cmp=compare_buddies))
            
        self.redraw()    
        
    def new_channel(self, channel_item):
        """
        A new channel has been created
        
        Keyword arugments:
        channel_item            -- channel menu item object
        """ 
        self.redraw()    
        
    def channel_removed(self, channel_item):
        """
        A channel has been removed
        
        Keyword arugments:
        channel_item            -- channel menu item object
        """      
        self.redraw()    
        
    def channel_updated(self, channel_item):
        """
        A channel has been updated
        
        Keyword arugments:
        channel_item            -- channel menu item object
        """        
        self.redraw() 
        
    def channel_moved(self, channel_item):
        """
        A channel has been moved

        Keyword arugments:
        channel_item            -- channel menu item object
        """
        self.redraw()

    def moved_channels(self, buddy_item, old_channel, new_channel):
        """
        A buddy has moved channels
        
        Keyword arugments:
        buddy_item               -- buddy menu item object
        old_channel              -- old channel menu item object
        new_channel              -- new channel menu item object
        """         
#        if buddy_item.channel.name == self.backend.get_current_channel().name:
#            self.message_received(self.backend.get_name(), _("%s changed channels" % buddy_item.nickname), True)
        self.redraw()
        
    def talking_status_changed(self, talking):
        """
        Current talking buddy has changed.
        
        Keyword arguments:
        talking                -- new buddy talking
        """
        if (self._talking is None and talking is not None) or \
           (talking is None and self._talking is not None) or \
           (talking is not None and talking != self._talking):
            self._talking = talking
            if self._backlight_acq is not None and self._talking is None:
                self.screen.driver.release_control(self._backlight_acq)
                self._backlight_acq = None
            if self._talking is not None:
                hex_color = g15util.get_string_or_default(self.gconf_client, get_backlight_key(self.gconf_key, self._talking), "")
                if hex_color != "":
                    if self._backlight_acq is None:
                        self._backlight_acq = self.screen.driver.acquire_control(self._backlight_ctrl)
                    self._backlight_acq.set_value(g15util.to_rgb(hex_color))
                     
        self.redraw()   
        if g15util.get_bool_or_default(self.gconf_client, "%s/raise_on_talk_status_change" % self.gconf_key, False):   
            self._popup()
        
    """
    Private
    """      
            
    def _popup(self):
        self._raise_timer = self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after=6.0)
    
    def _load_buddy_list(self):
        items = self.backend.get_buddies()
        self.menu.set_children(sorted(items, cmp=compare_buddies))
        if len(items) > 0:
            self.menu.selected = items[0]
        else:
            self.menu.selected = None
            
    def _disconnected(self):
        self._connected = False
        self.hide_menu()
        self._attempt_connection()
        
class BuddyActionMenuItem(g15theme.MenuItem):    
    def __init__(self, component_id, name, buddy, backend, icon=None):
        g15theme.MenuItem.__init__(self, component_id, True, name, icon=icon)
        self.buddy = buddy
        self.backend = backend  
    
class KickBuddyMenuItem(BuddyActionMenuItem):    
    def __init__(self, buddy, backend):
        BuddyActionMenuItem.__init__(self, 'kick', _('Kick'), buddy, backend, icon=g15util.get_icon_path(['force-exit', 'gnome-panel-force-quit'], include_missing=False))
        
    def _confirm(self, arg):
        self.backend.kick(self.buddy)
        self.get_root().delete()
        
    def activate(self):
        g15theme.ConfirmationScreen(self.get_screen(), _("Kick Buddy"), _("Are you sure you want to kick\n%s from the server") % self.buddy.nickname,
                                    self.backend.get_icon(), self._confirm, None)

class BanBuddyMenuItem(BuddyActionMenuItem):    
    def __init__(self, buddy, backend):
        BuddyActionMenuItem.__init__(self, 'ban', _('Ban'), buddy, backend, icon=g15util.get_icon_path(['audio-volume-muted-blocked', 'mail_spam', 'stock_spam'], include_missing=False))
        
    def _confirm(self, arg):
        self.backend.ban(self.buddy)
        self.get_root().delete()
        
    def activate(self):
        g15theme.ConfirmationScreen(self.get_screen(), _("Ban Buddy"), _("Are you sure you want to ban\n%s from the server") % self.buddy.nickname,
                                    self.backend.get_icon(), self._confirm, None)
      
      
class SelectChannelMenuItem(g15theme.MenuItem):    
    def __init__(self, gconf_client, gconf_key, backend, plugin):
        g15theme.MenuItem.__init__(self, 'channel', True, _('Select channel / server'), icon=g15util.get_icon_path(['addressbook', 'office-address-book', 'stcok_addressbook', 'x-office-address-book' ], include_missing=False))
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._backend = backend
        self._plugin = plugin
        
    def activate(self):     
        SelectChannelMenu(self._gconf_client, self._gconf_key, self.get_screen(), self._backend, self._plugin)  

class BuddyBacklightMenuItem(BuddyActionMenuItem):    
    def __init__(self, gconf_client, gconf_key, buddy, backend, ctrl, plugin):
        BuddyActionMenuItem.__init__(self, 'color', _('Select backlight'), buddy, backend, icon=g15util.get_icon_path(['preferences-color', 'gtk-select-color', 'color-picker' ], include_missing=False))
        self._ctrl = ctrl
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._plugin = plugin
        
    def activate(self):        
        BuddyBacklightMenu(self._gconf_client, self._gconf_key, self.get_screen(), self.backend, self.buddy, self._ctrl, self._plugin)

class ReturnMenuItem(g15theme.MenuItem):    
    def __init__(self):
        g15theme.MenuItem.__init__(self, 'return', True, _('Back to previous menu'), icon=g15util.get_icon_path(['back', 'gtk-go-back-ltr']))
        
    def activate(self):
        self.get_root().delete()
        
class AudioInputMenuItem(g15theme.MenuItem):    
    def __init__(self, backend):
        g15theme.MenuItem.__init__(self, 'audio-input', False, _("Input"))
        self._backend = backend
        
    def get_theme_properties(self):
        p = g15theme.MenuItem.get_theme_properties(self)
        me = self._backend.get_me()
        if self.get_screen().device.bpp == 1:
            p["item_icon"] = MONO_MIC_MUTED if me.input_muted else MONO_MIC_UNMUTED
        else:
            p["item_icon"] = g15util.get_icon_path(MUTED_ICONS if me.input_muted else UNMUTED_ICONS)
        p["item_name"] = _("Un-mute audio input") if me.input_muted else _("Mute audio input")
        return p
    
    def activate(self):    
        self._backend.set_audio_input(not self._backend.get_me().input_muted)
        self.get_root().delete()
        
class AudioOutputMenuItem(g15theme.MenuItem):    
    def __init__(self, backend):
        g15theme.MenuItem.__init__(self, 'audio-output', False, _("Output"))
        self._backend = backend
        
    def get_theme_properties(self):
        p = g15theme.MenuItem.get_theme_properties(self)
        me = self._backend.get_me()
        if self.get_screen().device.bpp == 1:
            p["item_icon"] = MONO_SPKR_MUTED if me.output_muted else MONO_SPKR_UNMUTED
        else:
            p["item_icon"] = g15util.get_icon_path("audio-volume-muted" if me.output_muted else "audio-volume-high")
        p["item_name"] = _("Un-mute audio output") if me.output_muted else _("Mute audio output")
        return p
    
    def activate(self):    
        self._backend.set_audio_output(not self._backend.get_me().output_muted)
        self.get_root().delete()
        
class AwayStatusMenuItem(g15theme.MenuItem):    
    def __init__(self, backend):
        g15theme.MenuItem.__init__(self, 'away', False, _("Away"), icon=g15util.get_icon_path("user-away"))
        self._backend = backend
        
    def get_theme_properties(self):
        p = g15theme.MenuItem.get_theme_properties(self)
        p["item_radio"] = True
        p["item_radio_selected"] = self._backend.get_me().away
        return p
    
    def activate(self):    
        self._backend.away()
        self.get_root().delete()
        
class OnLineStatusMenuItem(g15theme.MenuItem):    
    def __init__(self, backend):
        g15theme.MenuItem.__init__(self, 'online', False, _("Online"), icon=g15util.get_icon_path("user-available"))
        self._backend = backend
        
    def activate(self):    
        self._backend.online()
        self.get_root().delete()
        
    def get_theme_properties(self):
        p = g15theme.MenuItem.get_theme_properties(self)
        p["item_radio"] = True
        p["item_radio_selected"] = not self._backend.get_me().away
        return p
        
class SelectModeMenuItem(g15theme.MenuItem):    
    def __init__(self, gconf_client, gconf_key, mode, mode_name, backend, buddy_menu):
        g15theme.MenuItem.__init__(self, 'mode-%s' % mode, False, mode_name)
        self._buddy_menu = buddy_menu
        self._mode = mode
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
           
    def get_theme_properties(self):
        p = g15theme.MenuItem.get_theme_properties(self)
        p["item_radio"] = True
        p["item_radio_selected"] = self._mode == g15util.get_string_or_default(self._gconf_client, "%s/mode" % self._gconf_key, MODE_ONLINE)
        return p
        
    def activate(self):      
        self._buddy_menu.mode = self._mode
        logger.info("Mode is now %s" % self._mode)
        self._gconf_client.set_string(self._gconf_key + "/mode", self._mode)
        self._buddy_menu.get_screen().redraw(self._buddy_menu.get_root())
        self.get_root().delete()

class ColorMenuItem(BuddyActionMenuItem):    
    def __init__(self, gconf_client, gconf_key, color, color_name, buddy, backend):
        fmt_color = "%02x%02x%02xff" % color
        BuddyActionMenuItem.__init__(self, 'color-%s' % fmt_color, color_name, buddy, backend)
        self.icon = self.color_square(color, 16, 2)
        self.color = color
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        
    def activate(self):
        self._gconf_client.set_string(get_backlight_key(self._gconf_key, self.buddy), g15util.rgb_to_string(self.color))
        self.get_root().delete()
        
    def color_square(self, color, size, radius=0):
        surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, size, size)
        cr = cairo.Context(surface)
        cr.set_source_rgba(color[0] / 255.0,
                          color[1] / 255.0,
                          color[2] / 255.0, 1.0)
        cr.move_to(radius, 0)
        cr.line_to(size - radius, 0)
        cr.arc(size - radius, radius, radius, 3 * pi / 2, 2 * pi) 
        cr.line_to(size, size - radius)
        cr.arc(size - radius, size - radius, radius, 0, pi / 2)
        cr.line_to(radius, size)
        cr.arc(radius, size - radius, radius, pi / 2, pi)
        cr.line_to(0, radius)
        cr.arc(radius, radius, radius, pi, 3 * pi / 2)
        cr.close_path()
        cr.fill()
        return surface
    

class SelectChannelMenu(g15theme.G15Page):
    
    def __init__(self, gconf_client, gconf_key, screen, backend, plugin):
        g15theme.G15Page.__init__(self, _("Server/Channel"), screen, priority=g15screen.PRI_HIGH, \
                                     theme=g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), "menu-screen"),
                                     originating_plugin = plugin)
        self.theme_properties = { 
                           "title": _("Server/Channel"),
                           "icon": backend.get_icon(),
                           "alt_title": ''
                      }
        self.menu = g15theme.Menu("menu")
        self.get_screen().add_page(self)
        self.add_child(self.menu)
        for c in backend.get_channels():
            self.menu.add_child(c)
            if c == backend.get_current_channel():
                self.menu.set_selected_item(c)
        self.menu.add_child(ReturnMenuItem())
        self.add_child(g15theme.MenuScrollbar("viewScrollbar", self.menu))

class BuddyBacklightMenu(g15theme.G15Page):
    
    def __init__(self, gconf_client, gconf_key, screen, backend, buddy, ctrl, plugin):
        g15theme.G15Page.__init__(self, _("Backlight"), screen, priority=g15screen.PRI_HIGH, \
                                     theme=g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), "menu-screen"),
                                     originating_plugin = plugin)
        self.theme_properties = { 
                           "title": _("Backlight"),
                           "icon": backend.get_icon() if buddy.avatar is None else buddy.avatar,
                           "alt_title": buddy.nickname
                      }
        self.menu = g15theme.Menu("menu")
        self.get_screen().add_page(self)
        self.add_child(self.menu)
        self.ctrl = ctrl
        self.acq = None
        
        sel_color = g15util.to_rgb(g15util.get_string_or_default(
                gconf_client, get_backlight_key(gconf_key, buddy),
                "255,255,255"))
        for i, c in enumerate(colorpicker.COLORS_FULL):
            c = (c[0], c[1], c[2])
            item = ColorMenuItem(gconf_client, gconf_key, c, 
                                colorpicker.COLORS_NAMES[i], buddy, backend)
            self.menu.add_child(item)
            if c == sel_color:
                self.menu.set_selected_item(item)
        
        self.menu.on_selected = self._handle_selected
        self.on_deleted = self._release_control
        self.menu.add_child(ReturnMenuItem())
        self.add_child(g15theme.MenuScrollbar("viewScrollbar", self.menu))
        self._handle_selected()
        
    def _handle_selected(self):
        self._release_control()
        if isinstance(self.menu.selected, ColorMenuItem):
            self.acq = self.get_screen().driver.acquire_control(self.ctrl)
            self.acq.set_value(self.menu.selected.color)
            
    def _release_control(self):      
        if self.acq is not None:
            self.get_screen().driver.release_control(self.acq)
            self.acq = None
    
class MeOperationMenu(g15theme.G15Page):
    """
    Me to select operations appropriate for the current local user. Includes
    setting channel, status, buddy list mode and others
    """
    
    def __init__(self, gconf_client, gconf_key, screen, backend, buddy_menu, plugin):
        g15theme.G15Page.__init__(self, _("Settings"), screen, priority=g15screen.PRI_HIGH, \
                                     theme=g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), "menu-screen"),
                                     originating_plugin = plugin)
        me = backend.get_me()
        self.theme_properties = { 
                           "title": _("Settings"),
                           "icon": backend.get_icon() if me.avatar is None else me.avatar,
                           "alt_title": me.nickname
                      }
        self.menu = g15theme.Menu("menu")
        self.get_screen().add_page(self)
        self.add_child(self.menu)
        
        
        self.menu.add_child(SelectChannelMenuItem(gconf_client, gconf_key, backend, plugin))
        
        self.menu.add_child(g15theme.MenuItem('audio-status', True, _('Audio'), activatable=False))
        self.menu.add_child(AudioInputMenuItem(backend))
        self.menu.add_child(AudioOutputMenuItem(backend))
        
        self.menu.add_child(g15theme.MenuItem('select-status', True, _('Select Status'), activatable=False))
        self.menu.add_child(OnLineStatusMenuItem(backend))
        self.menu.add_child(AwayStatusMenuItem(backend))
        
        self.menu.add_child(g15theme.MenuItem('select-mode', True, _('Select Buddy List Mode'), activatable=False))
        for i in MODE_LIST:
            self.menu.add_child(SelectModeMenuItem(gconf_client, gconf_key, i, MODES[i][1], backend, buddy_menu))
        
        self.menu.add_child(ReturnMenuItem())
        self.add_child(g15theme.MenuScrollbar("viewScrollbar", self.menu))
    
class BuddyOperationMenu(g15theme.G15Page):
    """
    Menu for operations appropriate for other buddies including kick, ban
    and select backlight
    """
    
    def __init__(self, gconf_client, gconf_key, screen, backend, buddy, plugin):
        g15theme.G15Page.__init__(self, _("Actions"), screen, priority=g15screen.PRI_HIGH, \
                                     theme=g15theme.G15Theme(os.path.join(g15globals.themes_dir, "default"), "menu-screen"),
                                     originating_plugin = plugin)
        self.theme_properties = { 
                           "title": _("Actions"),
                           "icon": backend.get_icon() if buddy.avatar is None else buddy.avatar,
                           "alt_title": buddy.nickname
                      }
        self.menu = g15theme.Menu("menu")
        self.get_screen().add_page(self)
        self.add_child(self.menu)
        self.menu.add_child(KickBuddyMenuItem(buddy, backend))
        self.menu.add_child(BanBuddyMenuItem(buddy, backend))
        ctrl = screen.driver.get_control("backlight_colour")
        if ctrl is not None:
            self.menu.add_child(BuddyBacklightMenuItem(gconf_client, gconf_key, buddy, backend, ctrl, plugin))
        self.menu.add_child(ReturnMenuItem())
        self.add_child(g15theme.MenuScrollbar("viewScrollbar", self.menu))
        
