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
 
import gnome15.g15globals as g15globals
import gnome15.g15screen as g15screen
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15plugin as g15plugin
import gobject
import time
import dbus
import os
import gtk
import Image
import gnome15.dbusmenu as dbusmenu

from lxml import etree

# Plugin details - All of these must be provided
id="tweak"
name="Tweak Gnome15"
description="Allows configuration of some hidden settings. These are mostly " + \
            "performance tweaks. If Gnome15 is using too much CPU, " + \
            "you will find adjusting some of these may reduce it. " 
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=True
 
def create(gconf_key, gconf_client, screen):
    return G15Tweak()

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "tweak.glade"))
    dialog = widget_tree.get_object("TweakDialog")
    dialog.set_transient_for(parent)
    g15util.configure_adjustment_from_gconf(gconf_client, "/apps/gnome15/scroll_delay", "ScrollDelayAdjustment", 500, widget_tree)
    g15util.configure_adjustment_from_gconf(gconf_client, "/apps/gnome15/scroll_amount", "ScrollAmountAdjustment", 5, widget_tree)
    g15util.configure_adjustment_from_gconf(gconf_client, "/apps/gnome15/animation_delay", "AnimationDelayAdjustment", 100, widget_tree)
    g15util.configure_adjustment_from_gconf(gconf_client, "/apps/gnome15/key_hold_duration", "KeyHoldDurationAdjustment", 2000, widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/use_xtest", "UseXTest", True, widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/disable_svg_glow", "DisableSVGGlow", False, widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/fade_screen_on_close", "FadeScreenOnClose", True, widget_tree)
    g15util.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/fade_keyboard_backlight_on_close", "FadeKeyboardBacklightOnClose", True, widget_tree)
    dialog.run()
    dialog.hide()
        
class G15Tweak():
    
    def __init__(self):
        pass

    def activate(self):
        pass
            
    def deactivate(self):
        pass
            
    def destroy(self):
        pass   