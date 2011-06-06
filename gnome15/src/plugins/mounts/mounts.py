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
#

import gnome15.g15plugin as g15plugin
import gnome15.g15util as g15util
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15screen as g15screen
import gio
import os.path

# Logging
import logging
logger = logging.getLogger("mounts")

# Plugin details - All of these must be provided
id="mounts"
name="Mounts"
description="Shows mount points, allows mounting, unmounting " + \
            "and ejecting of removable media. Also displays " + \
            "free, used or total disk space on mounted media."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2011 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]

def create(gconf_key, gconf_client, screen):
    return G15Places(gconf_client, gconf_key, screen)

POSSIBLE_ICON_NAMES = [ "folder" ]
FS_ICONS = { "" }

MODES = { "free" : "Free", "used" : "Used", "size" : "Size"}
MODE_LIST = list(MODES.keys())

"""
Represents a mount as a single item in a menu
"""
class MountMenuItem(g15theme.MenuItem):    
    def __init__(self, mount, plugin):
        g15theme.MenuItem.__init__(self)
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
        
    def draw(self, selected, canvas, menu_properties, menu_attributes):       
        item_properties = {}
        item_properties["item_selected"] = selected == self
        item_properties["item_name"] = self.mount.get_name()
        item_properties["item_type"] = ""        
        item_properties["item_icon"] = g15util.get_icon_path([ self.mount.get_icon().get_names()[0], "gnome-dev-harddisk" ])
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
        self.theme.draw(canvas, item_properties)
        return self.theme.bounds[3]
    
    def get_default_theme_dir(self):
        return os.path.join(os.path.dirname(__file__), "default")
    
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
    def __init__(self, volume):
        g15theme.MenuItem.__init__(self)
        self.volume = volume
        
    def draw(self, selected, canvas, menu_properties, menu_attributes):       
        item_properties = {}
        if selected == self:
            item_properties["item_selected"] = True
        item_properties["item_name"] = self.volume.get_name()
        item_properties["item_alt"] = ""
        item_properties["item_type"] = ""
        
        item_properties["item_icon"] = g15util.get_icon_path([ self.volume.get_icon().get_names()[0], "gnome-dev-harddisk" ])
        self.theme.draw(canvas, item_properties)
        return self.theme.bounds[3]
    
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
        
        # Get the initial list of volumes and mounts
        self.volume_monitor = gio.VolumeMonitor()
        for mount in self.volume_monitor.get_mounts():
            self._add_mount(mount)
        if len(self.menu.get_items()) > 0:
            self.menu.add_separator()
        for volume in self.volume_monitor.get_volumes():
            if volume.get_mount() == None:
                self._add_volume(volume)
                
        # Watch for changes
        self.volume_monitor.connect("mount_added", self._on_mount_added)
        self.volume_monitor.connect("mount_removed", self._on_mount_removed)
        
        # Refresh disk etc space every minute
        self._handle = g15util.schedule("DiskRefresh", 60.0, self._refresh)
        
    def deactivate(self):
        g15plugin.G15MenuPlugin.deactivate(self)
        for handle in self._signal_handles:
            self.session_bus.remove_signal_receiver(handle)
        if self._handle:
            self._handle.cancel()
            self._handle = None
            
    def get_theme_path(self):
        return os.path.join(os.path.dirname(__file__), "default")
    
    def get_theme_properties(self, properties):
        properties = g15plugin.G15MenuPlugin.get_theme_properties(self, properties)
        properties["mode"] = MODES[self._mode]        
        idx = MODE_LIST.index(self._mode) + 1
        properties["list"] = MODES[MODE_LIST[0] if idx == len(MODE_LIST) else MODE_LIST[idx]]        
        if isinstance(self.menu.selected, VolumeMenuItem):
            properties["sel"] = "Mount"
        elif isinstance(self.menu.selected, MountMenuItem):
            properties["sel"] = "Eject" if self.menu.selected.mount.can_eject() else "Unmo."
        else:
            properties["sel"] = ""
        return properties
            
    def handle_key(self, keys, state, post):        
        if not post and state == g15driver.KEY_STATE_DOWN and self.page == self.screen.get_visible_page(): 
            if g15plugin.G15MenuPlugin.handle_key(self, keys, state, post):
                return True
            elif g15driver.G_KEY_L3 in keys or g15driver.G_KEY_SETTINGS in keys:
                idx = MODE_LIST.index(self._mode) + 1
                self._mode = MODE_LIST[0] if idx == len(MODE_LIST) else MODE_LIST[idx]
                self.screen.redraw(self.page)
                return True    
                
        return False
            
    """
    Private functions
    """
    
    def _refresh(self):
        """
        Refresh the free space etc for all items
        """
        for item in self.menu.get_items():
            if isinstance(item, MountMenuItem):
                item._refresh()
        self.screen.redraw(self.page)
        
    def _on_mount_added(self, monitor, mount, *args):
            
        """
        Invoked when new mount is available
        """
        self._add_mount(mount)
        
        # Remove the volume for this remove
        for item in self.menu.get_items():
            if isinstance(item, VolumeMenuItem) and self._get_key(item.volume) == self._get_key(mount):
                self._remove_volume(item.volume)
                
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
        if not self.page.is_visible():
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
        self.menu.remove_item(self._get_item_for_volume(volume))
        self.screen.redraw(self.page)
        
    def _remove_mount(self, mount):
        """
        Remove a mount from the menu
        """ 
        logger.info("Removing mount %s" % str(mount))
        self.menu.remove_item(self._get_item_for_mount(mount))
        self.screen.redraw(self.page)
        
    def _get_item_for_mount(self, mount):
        """
        Get the menu item for the given mount
        """
        for item in self.menu.get_items():
            if isinstance(item, MountMenuItem) and self._get_key(mount) == self._get_key(item.mount):
                return item
        
    def _get_item_for_volume(self, volume):
        """
        Get the menu item for the given volume
        """
        for item in self.menu.get_items():
            if isinstance(item, VolumeMenuItem) and self._get_key(volume) == self._get_key(item.volume):
                return item
        
    def _add_volume(self, volume):
        """
        Add a new volume to the menu
        """ 
        logger.info("Adding volume %s" % str(volume))
        item = VolumeMenuItem(volume)
        self.menu.add_item(item)
        self.screen.redraw(self.page)
    
    def _add_mount(self, mount):
        """
        Add a new mount to the menu
        """ 
        logger.info("Adding mount %s" % str(mount))
        item = MountMenuItem(mount, self)
        self.menu.insert_item(0, item)
        self.screen.redraw(self.page)