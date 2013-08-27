#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2012 Brett Smith <tanktarta@blueyonder.co.uk>
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
Classes and utilities for monitoring the current state of the network, allowing
plugins that declare "needs_network" to be enabled or disabled depending on this
state.

This is done using the NetworkManager DBUS interface, although the number of
states available is reduced to connected/disconnected
'''

import dbus

# Logging
import logging
logger = logging.getLogger("network")

_system_bus = dbus.SystemBus()

NM_BUS_NAME       = 'org.freedesktop.NetworkManager'
NM_OBJECT_PATH    = '/org/freedesktop/NetworkManager'
NM_INTERFACE_NAME = 'org.freedesktop.NetworkManager'
NM_STATE_INDEX = {  0: 'Unknown',
                   10: 'Asleep', 
                   20: 'Disconnected',
                   30: 'Disconnecting',
                   40: 'Connecting',
                   50: 'Connected (Local)',
                   60: 'Connected (Site)',
                   70: 'Connected (Global)' }

class NetworkManager():
    def __init__(self, screen):
        self._screen = self
        self.listeners = []
        self._state = -1
        try:
            _manager = _system_bus.get_object(NM_BUS_NAME, NM_OBJECT_PATH)
            self._interface = dbus.Interface(_manager, NM_INTERFACE_NAME)
            self._set_state(self._interface.state())
            self._handle = self._interface.connect_to_signal('StateChanged', self._set_state)
        except dbus.DBusException as e:
            if logger.level == logging.DEBUG:
                logger.warning("NetworkManager DBUS interface could not be contacted. All plugins will assume the network is available, and may behave unexpectedly. %s" % e)
            else:
                logger.warning("NetworkManager DBUS interface could not be contacted. All plugins will assume the network is available, and may behave unexpectedly.")
                
            # Assume connected
            self._state = 70

    def _set_state(self, state):
        if state in NM_STATE_INDEX:
            logger.info("New network state is %s" % NM_STATE_INDEX[state])
            s = state
        else:
            logger.info("New network state is unknown")
            s = 0
        if s != self._state and s in [ 0, 20, 60, 70 ]:
            self._state = s
            for l in self.listeners:
                l(self.is_network_available())
            
    def is_network_available(self):
        return self._state in [ 60, 70 ]
        
    def is_internet_available(self):
        return self._state == 70