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
import logging
logger = logging.getLogger("driver")

# Find all drivers
drivers_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "drivers"))
logger.info("Loading drivers from %s" % drivers_dir)
imported_drivers = {}

driverfiles = [fname[:-3] for fname in os.listdir(drivers_dir) if fname.endswith(".py") and fname.startswith("driver_")]
for d in driverfiles:
    try :
        driver_mod = __import__("gnome15.drivers.%s" % d , fromlist=[])
        mod = getattr(getattr(driver_mod, "drivers"), d)
        imported_drivers[d] = mod
    except Exception as e:
        logger.warning("Failed to load driver. %s" % str(e))
    


#driverfiles = [fname[:-3] for fname in os.listdir(drivers_dir) if fname.endswith(".py") and fname.startswith("driver_")]
#driver_mods = __import__("gnome15.drivers", fromlist=list(driverfiles))
#for d in driverfiles:
#    try :
#        mod = getattr(driver_mods, d)
#        imported_drivers[d] = mod
#    except Exception as e:
#        logger.warning("Failed to load driver. %s" % str(e))
        
def get_driver_mod(id):
    '''
    Get a driver module given it's ID.
    
    Keyword arguments:
    id    --    driver ID
    '''
    for driver_mod in imported_drivers.values():
        if driver_mod.id == id:
            return driver_mod

def get_configured_driver(device, force_config = False):
    '''
    Get the configured driver, starting the setup dialog if no driver is set, or
    if configuration is force
    '''

    driver_name = gconf.client_get_default().get_string("/apps/gnome15/%s/driver" % device.uid)
    if driver_name != None and driver_name != "" and not ( "driver_" + driver_name ) in imported_drivers:
        force_config = True
    if driver_name == None or driver_name == "" or force_config:
        setup = g15setup.G15Setup(None, True, driver_name == None or driver_name == "")
        driver_name = setup.setup()
    return driver_name if driver_name != None and driver_name != "" else None

def get_best_driver(conf_client, device, on_close = None):
    for driver_mod_key in imported_drivers:
        driver_mod = imported_drivers[driver_mod_key]
        driver = driver_mod.Driver(device, on_close = on_close)
        if device.model_id in driver.get_model_names():
#            driver.set_controls_from_configuration(conf_client)
            return driver
    
def get_driver(conf_client, device, on_close = None):
    '''
    Called by clients to create the configured driver
    '''
    driver_name = conf_client.get_string("/apps/gnome15/%s/driver" % device.uid)
    if not driver_name:
        # If no driver has yet been configured, always use the best driver
        driver = get_best_driver(conf_client, device, on_close)
        if driver == None:
            raise Exception(_("No drivers support the model %s") % device.model_id)
            
        logger.info("Using first available driver for %s, %s" % ( device.model_id, driver.get_name()))
        return driver
    
    driver_mod_key = "driver_" + driver_name
    if not driver_mod_key in imported_drivers:
        raise Exception(_("Driver %s is not available. Do you have to appropriate package installed?") % driver_name)
    driver_mod = imported_drivers[driver_mod_key]
    driver = driver_mod.Driver(device, on_close = on_close)
    
    if not device.model_id in driver.get_model_names():
        # If the configured driver is now incorrect for the device model, just use the best driver
        # If no driver has yet been configured, always use the best driver
        driver = get_best_driver(conf_client, device, on_close)
        if driver == None:
            raise Exception(_("No drivers support the model %s") % device.model_id)
        logger.warning("Ignoring configured driver %s, as the model is not supported by it. Looking for best driver" % driver)
        return driver
    else:
        # Configured driver is OK to use    
#        driver.set_controls_from_configuration(conf_client)
        return driver