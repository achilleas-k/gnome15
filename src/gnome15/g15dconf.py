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


"""
This class provides a way of retrieving and monitoring dconf without using
the GI bindings, which may no longer be mixed with static bindings (that
Gnome15 uses).

This class is stop gap until a better solution can be found
"""

import dbus
import os
import gobject

# Logging
import logging
logger = logging.getLogger("dconf")

PASSIVE_MATCH_STRING="type='method_call',interface='ca.desrt.dconf.Writer',member='Change'"
EAVESDROP_MATCH_STRING="eavesdrop='true',%s" % PASSIVE_MATCH_STRING

class GSettingsCallback():
    
    def __init__(self, handle, key, callback):
        self.handle = handle
        self.key = key
        self.callback = callback

class GSettings():
    
    def __init__(self, schema_id):
        self.schema_id = schema_id
        self._handle = 1
        # DBUS session instance must be private or monitoring will not work properly
        self._session_bus = dbus.SessionBus(private=True)
        self._writer = dbus.Interface(self._session_bus.get_object("ca.desrt.dconf", "/ca/desrt/dconf/Writer/user"), "ca.desrt.dconf.Writer")
        self._monitors = {}
        
        self._match_string = EAVESDROP_MATCH_STRING
        try:
            self._session_bus.add_match_string(self._match_string)
        except Exception as e:
            logger.debug('Could not add EAVESDROP match rule. Trying PASSIVE', exc_info = e)
            self._match_string = PASSIVE_MATCH_STRING
            self._session_bus.add_match_string(self._match_string)
        self._session_bus.add_message_filter(self._msg_cb)
        
    def connect(self, key, callback):
        l = key.split(":")
        if l[0] != "changed":
            raise Exception("Only currently supported changed events")
        key = l[2]
        handle = self._handle
        self._handle += 1
        self._monitors[handle] = GSettingsCallback(handle, key, callback)
        return handle
    
    def disconnect(self, handle):
        if handle in self._monitors:
            del self._monitors[handle]
        
    def get_string(self, key):
        _, result = self._get_status_output("gsettings get %s %s" % (self.schema_id, key))         
        if len(result) > 0:
            result = result.replace("\n", "")
            if result.startswith("'"):
                return result[1:-1]
            return result
            
    def _get_status_output(self, cmd):
        pipe = os.popen('{ ' + cmd + '; } 2>/dev/null', 'r')
        try:
            text = pipe.read()
        finally:
            sts = pipe.close()
        if sts is None:
            sts = 0
        if text[-1:] == '\n':
            text = text[:-1]
        return sts, text
    
    def _changed(self, key):
        s = ""
        for b in key:
            if b == 0:
                break
            else:
                s += chr(b)
        li = s.rfind("/")
        if li > 0:
            s_id = s[:li][1:].replace("/", ".")
            k = s[li + 1:].replace("-", "_")
            if s_id == self.schema_id:
                for m in self._monitors:
                    mon = self._monitors[m]
                    if mon.key == k:
                        # Bit rubbish, but we need to give dconf time to update
                        gobject.timeout_add(1000, mon.callback)
            
    def _msg_cb(self, bus, msg):
        # Only interested in method calls
        if isinstance(msg, dbus.lowlevel.MethodCallMessage):
            if msg.get_member() == "Change":
                self._changed(*msg.get_args_list())
                
    def __del__(self):
        self._session_bus.remove_match_string(self._match_string)
