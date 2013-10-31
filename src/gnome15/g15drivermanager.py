#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2010 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 
'''
This module is responsible for loading the available hardware drivers, and
choosing the best one to use. 

The best driver is always used when no driver is yet configured, other the 
configured driver is always used if possible. If it is not available,
or no longer supports the model for the associated device, then it will revert
back to using the best driver.

The "best driver" is simply the first driver that supports the associated
device. 
'''

import os
import logging
logger = logging.getLogger(__name__)

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
        logger.warning("Failed to load driver.", exc_info = e)
    

def get_driver_mod(driver_id):
    '''
    Get a driver module given it's ID.
    
    Keyword arguments:
    driver_id    --    driver ID
    '''
    for driver_mod in imported_drivers.values():
        if driver_mod.id == driver_id:
            return driver_mod
    
def get_driver(conf_client, device, on_close = None):
    '''
    Called by clients to create the configured driver. If the configured
    driver is not available, it will fallback to using the "best driver".
    
    Keyword arguments:
    conf_client        -- configuration client
    device             -- device to find driver for
    on_close -- callback passed to driver that is executed when the driver closes.
    '''
    driver_name = conf_client.get_string("/apps/gnome15/%s/driver" % device.uid)
    if not driver_name:
        # If no driver has yet been configured, always use the best driver
        driver = _get_best_driver(device, on_close)
        if driver == None:
            raise Exception(_("No drivers support the model %s") % device.model_id)
            
        logger.info("Using first available driver for %s, %s" % ( device.model_id, driver.get_name()))
        return driver
    
    driver_mod_key = "driver_" + driver_name
    if not driver_mod_key in imported_drivers:
        # If the previous driver is no longer installed, get the best remaining driver
        driver = _get_best_driver(device, on_close)
        if driver == None:        
            raise Exception(_("Driver %s is not available. Do you have to appropriate package installed?") % driver_name)
        else:            
            logger.info("Configured driver %s is not available, using %s instead" % ( driver_mod_key, driver.get_name()))
    else:
        driver = imported_drivers[driver_mod_key].Driver(device, on_close = on_close)
    
    if not device.model_id in driver.get_model_names():
        # If the configured driver is now incorrect for the device model, just use the best driver
        # If no driver has yet been configured, always use the best driver
        driver = _get_best_driver(device, on_close)
        if driver == None:
            raise Exception(_("No drivers support the model %s") % device.model_id)
        logger.warning("Ignoring configured driver %s, as the model is not supported by it. Looking for best driver" % driver)
        return driver
    else:
        # Configured driver is OK to use    
        return driver
    
def _get_best_driver(device, on_close = None):
    '''
    Get the "best driver" available. This will be the first driver that
    supports the provided device.
    
    Keyword arguments:
    device -- device to find driver for
    on_close -- callback passed to driver that is executed when the driver closes.
    '''
    for driver_mod_key in imported_drivers:
        driver = imported_drivers[driver_mod_key].Driver(device, on_close = on_close)
        if device.model_id in driver.get_model_names():
            return driver