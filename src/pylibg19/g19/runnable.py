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

import threading

class Runnable(object):
    '''Helper object to create thread content objects doing periodic tasks, or
    tasks supporting premature termination.

    Override execute() in inherited class.  This will be called until the
    thread is stopped.  A Runnable can be started multiple times opposed to
    threading.Thread.

    To write a non-periodic task that should support premature termination,
    simply override run() and call is_about_to_stop() at possible termination
    points.

    '''

    def __init__(self):
        self.__keepRunning = True
        self.__mutex = threading.Lock()

    def execute(self):
        '''This method must be implemented and will be executed in an infinite
        loop as long as stop() was not called.

        An implementation is free to check is_about_to_stop() at any time to
        allow a clean termination of current processing before reaching the end
        of execute().
        
        '''
        pass

    def is_about_to_stop(self):
        '''Returns whether this thread will terminate after completing the
        current execution cycle.

        @return True if thread will terminate after current execution cycle.

        '''
        self.__mutex.acquire()
        val = self.__keepRunning
        self.__mutex.release()
        return not val

    def run(self):
        '''Implements the infinite loop.  Do not override, but override
        execute() instead.

        '''
        while not self.is_about_to_stop():
            self.execute()

    def start(self):
        '''Starts the thread.  If stop() was called, but start() was not, run()
        will do nothing.

        '''
        self.__mutex.acquire()
        self.__keepRunning = True
        self.__mutex.release()

    def stop(self):
        '''Flags this thread to be terminated after next completed execution
        cycle.  Calling this method will NOT stop the thread instantaniously,
        but will complete the current operation and terminate in a clean way.

        '''
        self.__mutex.acquire()
        self.__keepRunning = False
        self.__mutex.release()
