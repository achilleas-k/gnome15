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
_ = g15locale.get_translation("keyhelp", modfile = __file__).ugettext

import gnome15.g15driver as g15driver
import gnome15.g15theme as g15theme
import gnome15.g15plugin as g15plugin
import gnome15.g15actions as g15actions
import gnome15.g15devices as g15devices
import gnome15.g15profile as g15profile
import logging
import os
logger = logging.getLogger("macros")

# Actions
SHOW_KEY_HELP = 'key-help'

# Register the action with all supported models
g15devices.g15_action_keys[SHOW_KEY_HELP] = g15actions.ActionBinding(SHOW_KEY_HELP, [ g15driver.G_KEY_M1 ], g15driver.KEY_STATE_HELD)
g15devices.z10_action_keys[SHOW_KEY_HELP] = g15actions.ActionBinding(SHOW_KEY_HELP, [ g15driver.G_KEY_L1 ], g15driver.KEY_STATE_HELD)
g15devices.g19_action_keys[SHOW_KEY_HELP] = g15actions.ActionBinding(SHOW_KEY_HELP, [ g15driver.G_KEY_M1 ], g15driver.KEY_STATE_HELD)

# Plugin details - All of these must be provided
id="keyhelp"
name=_("Key Help Screen")
description=_("Displays key bindings on the current screen showing what\n\
actions are available for a particular plugin.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_MX5500, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         SHOW_KEY_HELP : _("Show Key Help"), 
         }

def create(gconf_key, gconf_client, screen):
    return G15KeyHelp(gconf_client, gconf_key, screen)


class G15KeyHelp(g15plugin.G15Plugin):

    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15Plugin.__init__(self, gconf_client, gconf_key, screen)

    def activate(self):
        self._keyhelp = None
        g15plugin.G15Plugin.activate(self)
        self.screen.key_handler.action_listeners.append(self) 
    
    def deactivate(self):
        self._hide_keyhelp()
        g15plugin.G15Plugin.deactivate(self)
        self.screen.key_handler.action_listeners.remove(self)
        
    def action_performed(self, binding):
        if binding.action == SHOW_KEY_HELP:
            if self._keyhelp is None:
                self._show_keyhelp()
            else:
                self._hide_keyhelp()
            return True
        
    def _hide_keyhelp(self):
        if self._keyhelp is not None:
            self._keyhelp.remove_from_parent()
            self._keyhelp = None
            
    def _get_theme_properties(self):
        if self.screen.driver.get_model_name() == g15driver.MODEL_G19:
            return { "up": self._get_key_help(g15driver.G_KEY_UP, g15driver.KEY_STATE_UP),
                 "down": self._get_key_help(g15driver.G_KEY_DOWN, g15driver.KEY_STATE_UP),
                 "left": self._get_key_help(g15driver.G_KEY_LEFT, g15driver.KEY_STATE_UP),
                 "right": self._get_key_help(g15driver.G_KEY_RIGHT, g15driver.KEY_STATE_UP),
                 "select": self._get_key_help(g15driver.G_KEY_OK, g15driver.KEY_STATE_UP),
                 "view": self._get_key_help(g15driver.G_KEY_SETTINGS, g15driver.KEY_STATE_UP),
                 "clear": self._get_key_help(g15driver.G_KEY_BACK, g15driver.KEY_STATE_UP)
                 }
            
        # TODO
        return {}
    
    def _get_key_help(self, key, state):
        page = self.screen.get_visible_page()
        originating_plugin = page.originating_plugin
        if originating_plugin:
            import gnome15.g15pluginmanager as g15pluginmanager
            actions = g15pluginmanager.get_actions(g15pluginmanager.get_module_for_id(originating_plugin.__module__), self.screen.device)
            active_profile = g15profile.get_active_profile(self.screen.driver.device) if self.screen.driver is not None else None
            for action_id in actions:
                # First try the active profile to see if the action has been re-mapped
                action_binding = active_profile.get_binding_for_action(state, action_id)
                if action_binding is None:
                    # No other keys bound to action, try the device defaults
                    device_info = g15devices.get_device_info(self.screen.driver.get_model_name())                
                    if action_id in device_info.action_keys:
                        action_binding = device_info.action_keys[action_id]
                
                if action_binding is not None and key in action_binding.keys:
                    return actions[action_id]
            
        return "?"
        
    def _show_keyhelp(self):
        self._keyhelp = g15theme.Component("glasspane")
        self._keyhelp.get_theme_properties = self._get_theme_properties
        page = self.screen.get_visible_page()
        page.add_child(self._keyhelp)
        self._keyhelp.set_theme(g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default")))
        page.redraw()