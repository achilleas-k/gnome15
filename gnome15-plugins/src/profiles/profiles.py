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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("profiles", modfile = __file__).ugettext

import gnome15.g15profile as g15profile
import gnome15.g15driver as g15driver
import gnome15.g15theme as g15theme
import gnome15.g15plugin as g15plugin
import gnome15.g15util as g15util
import gnome15.g15devices as g15devices
import gnome15.g15actions as g15actions
from gnome15.g15util import find
import os
import logging
logger = logging.getLogger("macros")

# Custom actions
SELECT_PROFILE = "select-profile"

# Register the action with all supported models
g15devices.g15_action_keys[SELECT_PROFILE] = g15actions.ActionBinding(SELECT_PROFILE, [ g15driver.G_KEY_L1 ], g15driver.KEY_STATE_HELD)
g15devices.g19_action_keys[SELECT_PROFILE] = g15actions.ActionBinding(SELECT_PROFILE, [ g15driver.G_KEY_BACK ], g15driver.KEY_STATE_HELD)

# Plugin details - All of these must be provided
id="profiles"
name=_("Profile Selector")
description=_("Allows selection of the currently active profile. You may also \n\
lock a profile to the device it is running on, preventing\n\
changes triggered by active window changes and other\n\
automatic profile selection methods.\n\n\
You may also use this plugin to set the window title that\n\
activates the current profile by making the required\n\
window foreground, and the pressing the key bound to\n\
'Select current window as activator' (see below).")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
default_enabled=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_Z10, g15driver.MODEL_G11, g15driver.MODEL_MX5500, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         SELECT_PROFILE : _("Show profile selector"),
         g15driver.PREVIOUS_SELECTION : _("Previous item"), 
         g15driver.NEXT_SELECTION : _("Next item"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page"),
         g15driver.VIEW : _("Lock profile"),
         g15driver.SELECT : _("Activate profile"),
         g15driver.CLEAR : _("Set current window as activator")
         }

def create(gconf_key, gconf_client, screen):
    return G15Profiles(gconf_client, gconf_key, screen)

"""
Represents a profile as a single item in a menu
"""
class ProfileMenuItem(g15theme.MenuItem):    
    def __init__(self, profile, plugin, id):
        g15theme.MenuItem.__init__(self, id)
        self.profile = profile
        self._plugin = plugin
        
    def get_theme_properties(self):
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.profile.name
        item_properties["item_radio"] = True
        item_properties["item_radio_selected"] = self.profile.is_active()
        item_properties["item_icon"] = g15util.load_surface_from_file(self.profile.get_profile_icon_path(16), self.theme.bounds[3])
        item_properties["item_locked"] = self.profile.is_active() and g15profile.is_locked(self._plugin.screen.device)
        item_properties["item_alt"] = ""
        return item_properties
    
    def on_configure(self):        
        self.set_theme(g15theme.G15Theme(self.parent.get_theme().dir, "menu-entry" if self.group else "menu-child-entry"))
    
    def activate(self):
        locked = g15profile.is_locked(self._plugin.screen.device)
        if locked:
            g15profile.set_locked(self._plugin.screen.device, False)
        self.profile.make_active()
        if locked:
            g15profile.set_locked(self._plugin.screen.device, True)
        
        # Raise the macros page if it is enabled and not raised
        macros_page = self._plugin.screen.get_page("macros")
        if macros_page is not None and not macros_page.is_visible():
            self._plugin.screen.raise_page(macros_page)
        

"""
Profiles plugin class
"""
class G15Profiles(g15plugin.G15MenuPlugin):
    
    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, [ "user-bookmarks" ], id, _("Profiles"))
    
    def activate(self):
        g15plugin.G15MenuPlugin.activate(self)
        g15profile.profile_listeners.append(self._stored_profiles_changed)
        self.delete_timer = None     
        self.screen.key_handler.action_listeners.append(self)
        self._notify_handles = []
        self._notify_handles.append(self.gconf_client.notify_add("/apps/gnome15/%s/active_profile" % self.screen.device.uid, self._profiles_changed))
        self._notify_handles.append(self.gconf_client.notify_add("/apps/gnome15/%s/locked" % self.screen.device.uid, self._profiles_changed))
        
    def deactivate(self): 
        g15plugin.G15MenuPlugin.deactivate(self)
        g15profile.profile_listeners.remove(self._stored_profiles_changed)
        self.screen.key_handler.action_listeners.remove(self)
        for h in self._notify_handles:
            self.gconf_client.notify_remove(h)
        
    def action_performed(self, binding):
        if self.page != None and self.page.is_visible():
            if binding.action == g15driver.VIEW:
                active = g15profile.get_active_profile(self.screen.device)
                if active.id == self.menu.selected.profile.id:
                    g15profile.set_locked(self.screen.device, not g15profile.is_locked(self.screen.device))
                else:
                    if g15profile.is_locked(self.screen.device):
                        g15profile.set_locked(self.screen.device, False)
                    self.menu.selected.profile.make_active()
                    g15profile.set_locked(self.screen.device, True)
                return True
            elif binding.action == g15driver.CLEAR:
                profile = self.menu.selected.profile
                if self.screen.service.active_application_name is not None:
                    self._configure_profile_with_window_name(profile, self.screen.service.active_application_name)
                    profile.save()
                elif self.screen.service.active_window_title is not None:
                    self._configure_profile_with_window_name(profile, self.screen.service.active_window_title)
                    profile.save()
                return True
                
                
    def show_menu(self):
        active_profile = g15profile.get_active_profile(self.screen.device)
        g15plugin.G15MenuPlugin.show_menu(self)
        if active_profile:
            item = find(lambda m: m.profile == active_profile, self.menu.get_children())
            if item:
                self.menu.set_selected_item(item)

    def load_menu_items(self):
        items = []
        profile_list = g15profile.get_profiles(self.screen.device) 
        for profile in profile_list:
            items.append(ProfileMenuItem(profile, self, "profile-%s" % profile.id ))
        items = sorted(items, key=lambda item: item.profile.name)
        self.menu.set_children(items)
        if len(items) > 0:
            self.menu.selected = items[0]
        else:
            self.menu.selected = None
                
    def get_theme_properties(self): 
        p = g15plugin.G15MenuPlugin.get_theme_properties(self)
        p["profile_locked"] = g15profile.is_locked(self.screen.device)
        return p
        
    '''
    Private
    '''    
    def _configure_profile_with_window_name(self, profile, window_name):
        profile.activate_on_focus = True
        profile.activate_on_launch = False
        profile.launch_pattern = None
        profile.window_name = window_name
         
    def _profiles_changed(self, arg0 = None, arg1 = None, arg2 = None, arg3 = None):
        self.screen.redraw(self.page)
        
    def _stored_profiles_changed(self, profile_id, device):
        self._reload_menu()
                    
    def _reload_menu(self):
        self.load_menu_items()
        self.screen.redraw(self.page)
        