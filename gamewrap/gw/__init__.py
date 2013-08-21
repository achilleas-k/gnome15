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
 
import gobject
import subprocess
import signal
import sys
import dbus.service
import threading
import re

# Logging
import logging
logger = logging.getLogger("gamewrapper")
    
NAME = "GameWrap"
VERSION = "0.1"
BUS_NAME = "org.gnome15.GameWrap"
OBJECT_PATH = "/org/gnome15/GameWrap"
IF_NAME = "org.gnome15.GameWrap"

class RunThread(threading.Thread):
    
    def __init__(self, controller):
        threading.Thread.__init__(self, name = "ExecCommand")
        self.controller = controller
        
    def run(self):
        logger.info("Running '%s'" % str(self.controller.args))
        self.process = subprocess.Popen(self.controller.args, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        logger.info("Process started OK")
        while True:
            line = self.process.stdout.readline(1024)
            if line: 
                logger.info(">%s<" % line)
                for pattern_id in self.controller.patterns:
                    pattern = self.controller.patterns[pattern_id]
                    match = re.search(pattern, line)
                    if match:
                        logger.info("Match! %s" % str(match))
                        gobject.idle_add(self.controller.PatternMatched(patter_id, line))
            else:
                break
        logger.info("Waiting for process to complete")
        self.controller.status = self.process.wait()
        logger.info("Process complete with %s" % self.controller.status)
        self.controller.Stop()
            
class G15GameWrapperServiceController(dbus.service.Object):
    
    def __init__(self, args, bus, no_trap=False):
        bus_name = dbus.service.BusName(BUS_NAME, bus=bus, replace_existing=False, allow_replacement=False, do_not_queue=True)
        dbus.service.Object.__init__(self, None, OBJECT_PATH, bus_name)
        
        self._page_sequence_number = 1
        self._bus = bus
        self.args = args
        self.status = 0
        self.patterns = {}

        logger.info("Exposing service for '%s'. Wait for signal to wait" % str(args))
        
        if not no_trap:
            signal.signal(signal.SIGINT, self.sigint_handler)
            signal.signal(signal.SIGTERM, self.sigterm_handler)
            
        self._loop = gobject.MainLoop()
        
    def start_loop(self):
        logger.info("Starting GLib loop")
        self._loop.run()
        logger.debug("Exited GLib loop")
        
    def sigint_handler(self, signum, frame):
        logger.info("Got SIGINT signal, shutting down")
        self.shutdown()
    
    def sigterm_handler(self, signum, frame):
        logger.info("Got SIGTERM signal, shutting down")
        self.shutdown()
        
    """
    DBUS API
    """
    @dbus.service.method(IF_NAME)
    def Start(self):
        RunThread(self).start()
    
    @dbus.service.method(IF_NAME)
    def Stop(self):
        gobject.idle_add(self._shutdown())
        
    @dbus.service.method(IF_NAME, in_signature='ss')
    def AddPattern(self, pattern_id, pattern):
        logger.info("Adding pattern '%s' with id '%s'" % (pattern, pattern_id))
        if pattern_id in self.patterns:
            raise Exception("Pattern with ID %s already registered." % pattern_id)
        self.patterns[pattern_id] = pattern
        
    @dbus.service.method(IF_NAME, in_signature='s')
    def RemovePattern(self, pattern_id):
        logger.info("Removing pattern with id '%s'" % (pattern_id))
        if not pattern_id in self.patterns:
            raise Exception("Pattern with ID %s not registered." % pattern_id)
        del self.patterns[id]
        
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssssas')
    def GetInformation(self):
        return ("GameWrapper Service", "Gnome15 Project", VERSION, "1.0", self.args)
    

    """
    Signals
    """
    
    """
    DBUS Signals
    """
    @dbus.service.signal(SCREEN_IF_NAME, signature='ss')
    def PatternMatch(self, pattern_id, line):
        pass
        
    """
    Private
    """
        
    def _shutdown(self):
        logger.info("Shutting down")
        self._loop.quit()
        sys.exit(self.status)