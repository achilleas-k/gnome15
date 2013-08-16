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
_ = g15locale.get_translation("tweak", modfile = __file__).ugettext

import gnome15.util.g15uigconf as g15uigconf
import gtk
import os.path

# Plugin details - All of these must be provided
id="tweak"
name=_("Tweak Gnome15")
description=_("Allows configuration of some hidden settings. These are mostly \
performance tweaks. If Gnome15 is using too much CPU, \
you will find adjusting some of these may reduce it. ") 
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=True
passive=True
global_plugin=True
 
def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "tweak.glade"))
    dialog = widget_tree.get_object("TweakDialog")
    dialog.set_transient_for(parent)
    g15uigconf.configure_adjustment_from_gconf(gconf_client, "/apps/gnome15/scroll_delay", "ScrollDelayAdjustment", 500, widget_tree)
    g15uigconf.configure_adjustment_from_gconf(gconf_client, "/apps/gnome15/scroll_amount", "ScrollAmountAdjustment", 5, widget_tree)
    g15uigconf.configure_adjustment_from_gconf(gconf_client, "/apps/gnome15/animation_delay", "AnimationDelayAdjustment", 100, widget_tree)
    g15uigconf.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/animated_menus", "AnimatedMenus", True, widget_tree)
    g15uigconf.configure_adjustment_from_gconf(gconf_client, "/apps/gnome15/key_hold_duration", "KeyHoldDurationAdjustment", 2000, widget_tree)
    g15uigconf.configure_adjustment_from_gconf(gconf_client, "/apps/gnome15/usb_key_read_timeout", "UsbKeyReadTimeoutAdjustment", 100, widget_tree)
    g15uigconf.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/use_xtest", "UseXTest", True, widget_tree)
    g15uigconf.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/disable_svg_glow", "DisableSVGGlow", False, widget_tree)
    g15uigconf.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/fade_screen_on_close", "FadeScreenOnClose", True, widget_tree)
    g15uigconf.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/fade_keyboard_backlight_on_close", "FadeKeyboardBacklightOnClose", True, widget_tree)
    g15uigconf.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/all_off_on_disconnect", "AllOffOnDisconnect", True, widget_tree)
    g15uigconf.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/start_in_threads", "StartScreensInThreads", False, widget_tree)
    g15uigconf.configure_checkbox_from_gconf(gconf_client, "/apps/gnome15/monitor_desktop_session", "MonitorDesktopSession", True, widget_tree)
    g15uigconf.configure_text_from_gconf(gconf_client, "/apps/gnome15/time_format", "TimeFormat", "", widget_tree)
    g15uigconf.configure_text_from_gconf(gconf_client, "/apps/gnome15/time_format_24hr", "TimeFormatTwentyFour", "", widget_tree)
    g15uigconf.configure_text_from_gconf(gconf_client, "/apps/gnome15/date_format", "DateFormat", "", widget_tree)
    g15uigconf.configure_text_from_gconf(gconf_client, "/apps/gnome15/date_time_format", "DateTimeFormat", "", widget_tree)
    
    dialog.run()
    dialog.hide()
        
