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
 

import os
import gconf
import g15setup as g15setup
import logging
logger = logging.getLogger("driver")

# Find all drivers
drivers_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "drivers"))
imported_drivers = {}
driverfiles = [fname[:-3] for fname in os.listdir(drivers_dir) if fname.endswith(".py") and fname.startswith("driver_")]
driver_mods = __import__("gnome15.drivers", fromlist=list(driverfiles))
for d in driverfiles:
    try :
        mod = getattr(driver_mods, d)
        imported_drivers[d] = mod
    except Exception as e:
        logger.warning("Failed to load driver. %s" % str(e))
    
'''
Get the configured driver, starting the setup dialog if no driver is set, or
if configuration is force
'''

def get_configured_driver(force_config = False):
    driver_name = gconf.client_get_default().get_string("/apps/gnome15/driver")
    if driver_name != None and driver_name != "" and not ( "driver_" + driver_name ) in imported_drivers:
        force_config = True
    if driver_name == None or driver_name == "" or force_config:
        setup = g15setup.G15Setup(None, True, driver_name == None or driver_name == "")
        driver_name = setup.setup()
    return driver_name if driver_name != None and driver_name != "" else None
    
'''
Called by clients to create the configured driver
'''
def get_driver(conf_client, on_close = None):
    driver = conf_client.get_string("/apps/gnome15/driver")
    driver_mod_key = "driver_" + driver
    if not driver_mod_key in imported_drivers:
        raise Exception("Driver " + driver + " is not available. Do you have to appropriate package installed?")
    driver_mod = imported_drivers[driver_mod_key]
    driver = driver_mod.Driver(on_close = on_close)
    driver.set_controls_from_configuration(conf_client)
    return driver