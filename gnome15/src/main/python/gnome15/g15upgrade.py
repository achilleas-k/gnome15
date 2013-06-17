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
 
"""
Utility to upgrade from earlier versions of Gnome15. This should be called
upon startup of either g15-config or g15-desktop-service to check whether
any migration needs to take place.
"""
 
import os.path
import g15devices
import g15python_helpers
import logging
import shutil
import sys
import subprocess

logger = logging.getLogger("upgrade")
 
def upgrade():
    version_0_x_0_to_0_7_0()
    version_0_x_0_to_0_8_5()

def version_0_x_0_to_0_8_5():
    """
    Location of mail accounts moved
    """
    old_path = os.path.expanduser("~/.gnome2/gnome15/lcdbiff/mailboxes.xml")
    new_path = os.path.expanduser("~/.config/gnome15/plugin-data/lcdbiff/mailboxes.xml")
    if os.path.exists(old_path) and not os.path.exists(new_path):
        logger.warn("Upgrading to 0.8.5, moving mailboxes")
        os.renames(old_path, new_path)    

def version_0_x_0_to_0_7_0():
    """
    First version to upgrade configuration. This is the version where
    multiple device support was introduced, pushing configuration into 
    sub-directories
    """
    macros_dir = os.path.expanduser("~/.config/gnome15/macro_profiles")
    if os.path.exists(os.path.expanduser("%s/0.macros" % macros_dir)):
        logger.info("Upgrading macros and configuration to 0.7.x format")
        
        """
        If the default macro profile exists at the root of the macro_profiles directory,
        then conversion hasn't yet occurred. So, copy all profiles into all device
        sub-directories
        """
        devices = g15devices.find_all_devices()
        for file in os.listdir(macros_dir):
            if file.endswith(".macros"):
                profile_file = os.path.join(macros_dir, file)
                for device in devices:
                    device_dir = os.path.join(macros_dir, device.uid)
                    if not os.path.exists(device_dir):
                        logger.info("Creating macro_profile directory for %s" % device.uid)
                        os.mkdir(device_dir)
                    logger.info("Copying macro_profile %s to %s " % ( file, device.uid ))
                    shutil.copyfile(profile_file, os.path.join(device_dir, file))
                os.remove(profile_file)
                
        """
        Copy the GConf folders. 
        """
        gconf_dir = os.path.expanduser("~/.gconf/apps/gnome15")
        gconf_file = os.path.join(gconf_dir, "%gconf.xml")
        gconf_plugins_dir = os.path.join(gconf_dir, "plugins")
        for device in devices:
            device_dir = os.path.join(gconf_dir, device.uid)
            if not os.path.exists(device_dir):
                logger.info("Creating GConf directory for %s" % device.uid)
                os.mkdir(device_dir)
            logger.info("Copying settings %s to %s " % ( gconf_file, device.uid ))
            shutil.copyfile(gconf_file, os.path.join(device_dir, "%gconf.xml"))
            logger.info("Copying plugin settings %s to %s " % ( gconf_plugins_dir, device.uid ))
            target_plugins_path = os.path.join(device_dir, "plugins")
            if not os.path.exists(target_plugins_path):
                shutil.copytree(gconf_plugins_dir, target_plugins_path )
        logger.info("Clearing current settings root")
        shutil.rmtree(gconf_plugins_dir)
        f = open(gconf_file, 'w')
        try:
            f.write('<?xml version="1.0">\n')
            f.write('<gconf>\n')
            f.write('</gconf>\n')
        finally:
            f.close()
        
            
        """
        Tell GConf to reload it caches by finding it's process ID and sending it
        SIGHUP
        """
        if sys.version_info > (2, 6):
            process_info = subprocess.check_output(["sh", "-c", "ps -U %d|grep gconfd|head -1" % os.getuid()])
        else:
            import commands
            process_info = commands.getstatusoutput("sh -c \"ps -U %d|grep gconfd|head -1\"" % os.getuid()) 
        if process_info:
            pid = g15python_helpers.split_args(process_info)[0]
            logger.info("Sending process %s SIGHUP" % pid)
            subprocess.check_call([ "kill", "-SIGHUP", pid ])
