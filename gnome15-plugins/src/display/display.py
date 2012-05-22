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

import gnome15.g15driver as g15driver
import gnome15.g15theme as g15theme
import gnome15.g15plugin as g15plugin
import gnome15.g15devices as g15devices
import gnome15.g15actions as g15actions
import gnome15.g15util as g15util
import logging
import os
import re
logger = logging.getLogger("xrandr")

# Custom actions
SELECT_PROFILE = "select-profile"

# Register the action with all supported models
g15devices.g15_action_keys[SELECT_PROFILE] = g15actions.ActionBinding(SELECT_PROFILE, [ g15driver.G_KEY_L1 ], g15driver.KEY_STATE_HELD)
g15devices.g19_action_keys[SELECT_PROFILE] = g15actions.ActionBinding(SELECT_PROFILE, [ g15driver.G_KEY_BACK ], g15driver.KEY_STATE_HELD)

# Plugin details - All of these must be provided
id="display"
name=_("Display Resolution")
description=_("Allows selection of the resolution for your display.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
default_enabled=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_Z10, g15driver.MODEL_G11, g15driver.MODEL_MX5500, g15driver.MODEL_G930 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous item"), 
         g15driver.NEXT_SELECTION : _("Next item"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page"),
         g15driver.SELECT : _("Select resolution")
         }

def create(gconf_key, gconf_client, screen):
    return G15XRandR(gconf_client, gconf_key, screen)

"""
Represents a resolution as a single item in a menu
"""
class ResolutionMenuItem(g15theme.MenuItem):    
    def __init__(self, index, size, refresh_rate, plugin, id):
        g15theme.MenuItem.__init__(self, id)
        self.current = False
        self.size = size
        self.index = index
        self.refresh_rate = refresh_rate
        self._plugin = plugin
        
    def get_theme_properties(self):
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = "%s x %s @ %s" % ( self.size[0], self.size[1], self.refresh_rate) 
        item_properties["item_radio"] = True
        item_properties["item_radio_selected"] = self.current
        item_properties["item_alt"] = ""
        return item_properties
    
    def on_configure(self):        
        self.set_theme(g15theme.G15Theme(self.parent.get_theme().dir, "menu-entry" if self.group else "menu-child-entry"))
    
    def activate(self):
        os.system("xrandr -s %sx%s -r %s" % (self.size[0], self.size[1], self.refresh_rate ))
        self._plugin._reload_menu()
        

"""
XRANDR plugin class
"""
class G15XRandR(g15plugin.G15MenuPlugin):
    
    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, [ "display", "gnome-display-properties", "system-config-display", "video-display", "xfce4-display", "display-capplet" ], id, _("Display"))
    
    def activate(self):
        self._timer = None
        self._current_active = None
        g15plugin.G15MenuPlugin.activate(self)
        
    def deactivate(self): 
        self._cancel_timer()
        g15plugin.G15MenuPlugin.deactivate(self)
        
    def load_menu_items(self):
        self._cancel_timer()
        items = []
        i = 0
        status, output = self._get_status_output("xrandr")
        if status == 0:
            old_active = self._current_active
            new_active = None
            for line in output.split('\n'):
                if line.startswith("  "):
                    arr = re.findall(r'\S+', line)
                    size = self._parse_size(arr[0])
                    for a in range(1, len(arr)):
                        word = arr[a]
                        refresh_rate = float(word[:-1]) if word.endswith("*") else float(word) 
                        item = ResolutionMenuItem(i, size, refresh_rate, self, "profile-%d-%s" % ( i, refresh_rate ) )      
                        item.current = word.endswith("*")
                        items.append(item)
                        if item.current:
                            new_active = item
                    i += 1
                    
            if old_active is None or ( new_active is not None and new_active.id != old_active.id ):
                self.menu.set_children(items)
                if new_active is not None:
                    self.menu.set_selected_item(new_active)
                    self._current_active = new_active
                
            self._schedule_check()
        else:
            raise Exception("Failed to query XRandR. Is the xrandr command installed, and do you have the XRandR extension enabled in your X configuration?")
        
    '''
    Private
    '''         
    def _cancel_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        
    def _schedule_check(self):
        g15util.schedule("CheckResolution", 10.0, self.load_menu_items)
        
    def _parse_size(self, line):
        arr = line.split("x")
        return int(arr[0].strip()), int(arr[1].strip())

    def _reload_menu(self):
        self.load_menu_items()
        self.screen.redraw(self.page)
            
    def _get_item_for_current_resolution(self):
        return g15util.find(lambda m: m.current, self.menu.get_children())

    def _get_status_output(self, cmd):
        # TODO something like this is used in sense.py as well, make it a utility
        pipe = os.popen('{ ' + cmd + '; } 2>/dev/null', 'r')
        text = pipe.read()
        sts = pipe.close()
        if sts is None: sts = 0
        if text[-1:] == '\n': text = text[:-1]
        return sts, text        