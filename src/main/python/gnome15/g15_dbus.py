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
 
import dbus
import g15_globals as pglobals

BUS_NAME="org.gnome15.Gnome15"
NAME="/org/gnome15/Service"
IF_NAME="org.gnome15.Service"

class G15DBUSService(dbus.service.Object):
    
    def __init__(self, service):
        bus = dbus.SessionBus()
        self.service = service
        bus_name = dbus.service.BusName(BUS_NAME, bus=bus, replace_existing=True, allow_replacement=True, do_not_queue=True)
        dbus.service.Object.__init__(self, bus_name, NAME)
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ( pglobals.name, "Gnome15 Project", pglobals.version, "1.0" )
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='s')
    def GetDriverName(self):
        return self.service.driver.get_name() if self.service.driver != None else None
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def GetDriverConnected(self):
        return self.service.driver.is_connected() if self.service.driver != None else False
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='s')
    def GetLastError(self):
        return str(self.service.get_last_error())