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

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("mounts", modfile = __file__).ugettext

import gnome15.g15plugin as g15plugin
import gnome15.g15util as g15util
import gnome15.g15ui_gconf as g15ui_gconf
import gnome15.g15scheduler as g15scheduler
import gnome15.g15gconf as g15gconf
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15screen as g15screen
import gio
import gtk
import os.path
import gobject

# Logging
import logging
logger = logging.getLogger("mounts")

# Plugin details - All of these must be provided
id="mounts"
name=_("Mounts")
description=_("Shows mount points, allows mounting, unmounting \
and ejecting of removable media. Also displays \
free, used or total disk space on mounted media.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2011 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous mount"), 
         g15driver.NEXT_SELECTION : _("Next mount"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page"),
         g15driver.SELECT : _("Mount, unmount or eject"),
         g15driver.VIEW : _("Toggle between free,\navailable and used"),
         }


def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "mounts.glade"))
    dialog = widget_tree.get_object("MountsDialog")
    dialog.set_transient_for(parent)
    g15ui_gconf.configure_checkbox_from_gconf(gconf_client, "%s/raise" % gconf_key, "RaisePageCheckbox", True, widget_tree)
    dialog.run()
    dialog.hide()

def create(gconf_key, gconf_client, screen):
    return G15Places(gconf_client, gconf_key, screen)

POSSIBLE_ICON_NAMES = [ "folder" ]

MODES = { "free" : _("Free"), "used" : _("Used"), "size" : _("Size") }
MODE_LIST = list(MODES.keys())

"""
Represents a mount as a single item in a menu
"""
class MountMenuItem(g15theme.MenuItem):    
    def __init__(self, id, mount, plugin):
        g15theme.MenuItem.__init__(self, id)
        self.mount = mount
        self._plugin = plugin
        self._refresh()
        
    def _refresh(self):
        self.disk_size = 0
        self.disk_free = 0
        self.disk_used = 0
        self.disk_used_pc = 0
        root = self.mount.get_root()
        try:
            self.fs_attr = root.query_filesystem_info("*")
            self.disk_size = float(max(1, self.fs_attr.get_attribute_uint64(gio.FILE_ATTRIBUTE_FILESYSTEM_SIZE)))
            self.disk_free = float(self.fs_attr.get_attribute_uint64(gio.FILE_ATTRIBUTE_FILESYSTEM_FREE))
            self.disk_used = float(self.disk_size - self.disk_free)
            self.disk_used_pc = int ( ( self.disk_used / self.disk_size ) * 100.0 )
        except:
            pass
        
    def get_theme_properties(self):       
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.mount.get_name()
        item_properties["item_type"] = ""     
        icon_names = []
        icon = self.mount.get_icon()
        if isinstance(icon, gio.FileIcon):
            icon_names.append(icon.get_file().get_path())
        else:
            icon_names += icon.get_names()
            
        icon_names += "gnome-dev-harddisk"
        item_properties["item_icon"] = g15util.get_icon_path(icon_names)
        item_properties["disk_usage"] = self.disk_used_pc
        item_properties["sel_disk_usage"] = self.disk_used_pc
        item_properties["disk_used_mb"] =  "%4.2f" % (self.disk_used / 1024.0 / 1024.0 )
        item_properties["disk_free_mb"] =  "%4.2f" % (self.disk_free / 1024.0 / 1024.0 )
        item_properties["disk_size_mb"] =  "%4.2f" % (self.disk_size / 1024.0 / 1024.0 )
        item_properties["disk_used_gb"] =  "%4.1f" % (self.disk_used / 1024.0 / 1024.0 / 1024.0 )
        item_properties["disk_free_gb"] =  "%4.1f" % (self.disk_free / 1024.0 / 1024.0 / 1024.0 )
        item_properties["disk_size_gb"] =  "%4.1f" % (self.disk_size / 1024.0 / 1024.0 / 1024.0 )
        suffix = "G" if self.disk_size >= ( 1 * 1024.0 * 1024.0 * 1024.0 ) else "M"
        item_properties["disk_used"] = "%s %s" % ( item_properties["disk_used_gb"], suffix ) 
        item_properties["disk_free"] = "%s %s" % ( item_properties["disk_free_gb"], suffix )
        item_properties["disk_size"] = "%s %s" % ( item_properties["disk_size_gb"], suffix )
        
        if self._plugin._mode == "free":
            item_properties["item_alt"] = item_properties["disk_free"]
        elif self._plugin._mode == "used":
            item_properties["item_alt"] = item_properties["disk_used"]
        elif self._plugin._mode == "size":
            item_properties["item_alt"] = item_properties["disk_size"]
            
        return item_properties
    
    def activate(self):
        if self.mount.can_eject():
            self.mount.eject(self._ejected, flags = gio.MOUNT_UNMOUNT_NONE)
        else:
            if self.mount.can_unmount():
                self.mount.unmount(self._unmounted, flags = gio.MOUNT_UNMOUNT_NONE)
        return True
            
    def _ejected(self, arg1, arg2):
        logger.info("Ejected %s %s %s" % (self.mount.get_name(), str(arg1), str(arg2)))
            
    def _unmounted(self, arg1, arg2):
        logger.info("Unmounted %s %s %s" % (self.mount.get_name(), str(arg1), str(arg2)))
        
"""
Represents a volumne as a single item in a menu
"""
class VolumeMenuItem(g15theme.MenuItem):    
    def __init__(self, id, volume):
        g15theme.MenuItem.__init__(self, id)
        self.volume = volume
        
    def get_theme_properties(self):       
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.volume.get_name()
        item_properties["item_alt"] = ""
        item_properties["item_type"] = ""
        
        item_properties["item_icon"] = g15util.get_icon_path([ self.volume.get_icon().get_names()[0], "gnome-dev-harddisk" ])
        return item_properties
    
    def activate(self):
        if self.volume.can_mount():
            self.volume.mount(None, self._mounted, flags = gio.MOUNT_UNMOUNT_NONE)
        return True
    
    def _mounted(self, arg1, arg2):
        logger.info("Mounted %s %s %s" % (self.volume.get_name(), str(arg1), str(arg2)))


"""
Places plugin class
"""
class G15Places(g15plugin.G15MenuPlugin):

    def __init__(self, gconf_client, gconf_key, screen):
        g15plugin.G15MenuPlugin.__init__(self, gconf_client, gconf_key, screen, POSSIBLE_ICON_NAMES, id, name)
        self._signal_handles = []
        self._handle = None
        self._modes = [ "free", "used", "size" ]
        self._mode = "free"
        
    def activate(self):
        g15plugin.G15MenuPlugin.activate(self)
        self.screen.key_handler.action_listeners.append(self)
        
        # Get the initial list of volumes and mounts
        gobject.idle_add(self._do_activate)
        
    def _do_activate(self):
        self.volume_monitor = gio.VolumeMonitor()
        for mount in self.volume_monitor.get_mounts():
            if not mount.is_shadowed():
                self._add_mount(mount)
        if len(self.menu.get_children()) > 0:
            self.menu.add_separator()
        for volume in self.volume_monitor.get_volumes():
            if volume.get_mount() == None:
                self._add_volume(volume)
                
        # Watch for changes
        self.volume_monitor.connect("mount_added", self._on_mount_added)
        self.volume_monitor.connect("mount_removed", self._on_mount_removed)
        
        # Refresh disk etc space every minute
        self._handle = g15scheduler.schedule("DiskRefresh", 60.0, self._refresh)
        
    def deactivate(self):
        g15plugin.G15MenuPlugin.deactivate(self)
        self.screen.key_handler.action_listeners.remove(self)
        for handle in self._signal_handles:
            self.session_bus.remove_signal_receiver(handle)
        if self._handle:
            self._handle.cancel()
            self._handle = None
            
    def get_theme_properties(self):
        properties = g15plugin.G15MenuPlugin.get_theme_properties(self)
        properties["alt_title"] = MODES[self._mode]        
        idx = MODE_LIST.index(self._mode) + 1
        properties["list"] = MODES[MODE_LIST[0] if idx == len(MODE_LIST) else MODE_LIST[idx]]        
        if isinstance(self.menu.selected, VolumeMenuItem):
            properties["sel"] = _("Mount")
        elif isinstance(self.menu.selected, MountMenuItem):
            properties["sel"] = _("Eject") if self.menu.selected.mount.can_eject() else _("Unmo.")
        else:
            properties["sel"] = ""
        return properties
    
    def action_performed(self, binding):
        if binding.action == g15driver.VIEW:
            idx = MODE_LIST.index(self._mode) + 1
            self._mode = MODE_LIST[0] if idx == len(MODE_LIST) else MODE_LIST[idx]
            self.screen.redraw(self.page)
    
            
    """
    Private functions
    """

    def _refresh(self):
        """
        Refresh the free space etc for all items
        """
        for item in self.menu.get_children():
            if isinstance(item, MountMenuItem):
                item._refresh()
        self.screen.redraw(self.page)
        
    def _on_mount_added(self, monitor, mount, *args):
        
        # Remove the volume for this remove
        for item in self.menu.get_children():
            if isinstance(item, VolumeMenuItem) and self._get_key(item.volume) == self._get_key(mount):
                self._remove_volume(item.volume)
                
            
        """
        Invoked when new mount is available
        """
        self._remove_mount(mount)
        self._add_mount(mount)
        
        self._popup()
        
    def _on_mount_removed(self, monitor, mount, *args):
        """
        Invoked when a mount is removed
        """
        self._remove_mount(mount)
        
        # Look for new volumes
        for volume in self.volume_monitor.get_volumes():
            if not self._get_item_for_volume(volume) and volume.get_mount() == None:
                self._add_volume(volume)
                
        self._popup()
                 
    def _popup(self): 
        if not self.page.is_visible() and g15gconf.get_bool_or_default(self.gconf_client,"%s/raise" % self.gconf_key, True):
            self._raise_timer = self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 4.0)
            self.screen.redraw(self.page)
                
    def _get_key(self, item):
        """
        Get a unique key for volume / mount
        """
        return "%s-%s" % ( str(item.get_uuid()), str(item.get_name()))
        
    def _remove_volume(self, volume):
        """
        Remove a volume from the menu
        """ 
        logger.info("Removing volume %s" % str(volume))
        self.menu.remove_child(self._get_item_for_volume(volume))
        self.screen.redraw(self.page)
        
    def _remove_mount(self, mount):
        """
        Remove a mount from the menu
        """ 
        logger.info("Removing mount %s" % str(mount))
        mnt = self._get_item_for_mount(mount)
        if mnt:
            self.menu.remove_child(mnt)
        self.screen.redraw(self.page)
        
    def _get_item_for_mount(self, mount):
        """
        Get the menu item for the given mount
        """
        for item in self.menu.get_children():
            if isinstance(item, MountMenuItem) and self._get_key(mount) == self._get_key(item.mount):
                return item
        
    def _get_item_for_volume(self, volume):
        """
        Get the menu item for the given volume
        """
        for item in self.menu.get_children():
            if isinstance(item, VolumeMenuItem) and self._get_key(volume) == self._get_key(item.volume):
                return item
        
    def _add_volume(self, volume):
        """
        Add a new volume to the menu
        """ 
        logger.info("Adding volume %s" % str(volume))
        item = VolumeMenuItem("volumeitem-%s" % self._get_key(volume), volume)
        self.menu.add_child(item)
        self.screen.redraw(self.page)
    
    def _add_mount(self, mount):
        """
        Add a new mount to the menu
        """ 
        logger.info("Adding mount %s" % str(mount))
        item = MountMenuItem("mountitem-%s" % self._get_key(mount), mount, self)
        self.menu.add_child(item, 0)
        self.screen.redraw(self.page)