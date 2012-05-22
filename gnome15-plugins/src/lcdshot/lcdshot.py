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
_ = g15locale.get_translation("lcdshot", modfile = __file__).ugettext

import gnome15.g15driver as g15driver
import gnome15.g15devices as g15devices
import gnome15.g15globals as g15globals
import gnome15.g15actions as g15actions
import os.path 
import logging
import gtk
import gnome15.g15util as g15util
logger = logging.getLogger("lcdshot")

# Custom actions
SCREENSHOT = "screenshot"

# Register the action with all supported models
g15devices.g15_action_keys[SCREENSHOT] = g15actions.ActionBinding(SCREENSHOT, [ g15driver.G_KEY_MR ], g15driver.KEY_STATE_HELD)
g15devices.g19_action_keys[SCREENSHOT] = g15actions.ActionBinding(SCREENSHOT, [ g15driver.G_KEY_MR ], g15driver.KEY_STATE_HELD)
 
# Plugin details - All of these must be provided
id="lcdshot"
name=_("LCD Screenshot")
description=_("Takes a screenshot of the LCD and places it in the configured directory.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_MX5500, g15driver.MODEL_G930 ]
actions={ 
         SCREENSHOT : "Take LCD screenshot"
         }


''' 
This simple plugin takes a screenshot of the LCD
'''

def create(gconf_key, gconf_client, screen):
    return G15LCDShot(screen, gconf_client, gconf_key)

def show_preferences(parent, driver, gconf_client, gconf_key):
    LCDShotPreferences(parent, driver, gconf_client, gconf_key)
    
class LCDShotPreferences():
    def __init__(self, parent, driver, gconf_client, gconf_key):
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "lcdshot.glade"))
        dialog = widget_tree.get_object("LCDShotDialog")
        dialog.set_transient_for(parent)        
        chooser = gtk.FileChooserDialog("Open..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        chooser_button = widget_tree.get_object("FileChooserButton")        
        chooser_button.dialog = chooser 
        chooser_button.connect("file-set", self.file_set)
        chooser_button.connect("file-activated", self.file_activated)
        chooser_button.connect("current-folder-changed", self.file_activated)
        bg_img = g15util.get_string_or_default(self.gconf_client, "%s/folder" % self.gconf_key, os.path.expanduser("~/Desktop"))
        chooser_button.set_filename(bg_img)
        dialog.run()
        dialog.hide()
          
    def file_set(self, widget):
        self.gconf_client.set_string(self.gconf_key + "/folder", widget.get_filename())  
        
    def file_activated(self, widget):
        self.gconf_client.set_string(self.gconf_key + "/folder", widget.get_filename())
        
            
class G15LCDShot():
    
    def __init__(self, screen, gconf_client, gconf_key):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key

    def activate(self):
        self._screen.key_handler.action_listeners.append(self) 
    
    def deactivate(self):
        self._screen.key_handler.action_listeners.remove(self)
        
    def destroy(self):
        pass
    
    def action_performed(self, binding):
        # TODO better key
        if binding.action == SCREENSHOT:
            if self._screen.old_surface:
                self._screen.draw_lock.acquire()
                dir = g15util.get_string_or_default(self._gconf_client, "%s/folder" % \
                            self._gconf_key, os.path.expanduser("~/Desktop"))
                try:
                    for i in range(1, 9999):
                        path = "%s/%s-%s-%d.png" % ( dir, \
                                                    g15globals.name, self._screen.get_visible_page().title, i )
                        if not os.path.exists(path):
                            self._screen.old_surface.write_to_png(path)
                            logger.info("Written to screenshot to %s" % path)
                            g15util.notify(_("LCD Screenshot"), _("Screenshot saved to %s") % path, "dialog-info")
                            return True
                    logger.warning("Too many screenshots in destination directory")
                except Exception as e:
                    logger.error("Failed to save screenshot. %s" % str(e))
                    self._screen.error_on_keyboard_display(_("Failed to save screenshot to %s. %s") % (dir, str(e)))
                finally:
                    self._screen.draw_lock.release()
                    
                return True
        