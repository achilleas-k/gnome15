#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2011 Nuno Araujo <nuno.araujo@russo79.com>
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

import datetime
import gnome15.g15notify as g15notify

class G15Timer():
    TIMER_MODE_STOPWATCH = 0
    TIMER_MODE_COUNTDOWN = 1

    def __init__(self):
        self.__enabled = False
        self.__running = False
        self.label = ""
        self.on_finish = None
        self.mode = G15Timer.TIMER_MODE_STOPWATCH
        self.initial_value = datetime.timedelta()
        self.loop = False
        self.reset()

    def set_enabled(self, value):
        if value != self.__enabled:
            self.__enabled = value
            self.pause()
            self.reset()

    def get_enabled(self):
        return self.__enabled

    def value(self):
        rv = self.__value()
        if self.mode == G15Timer.TIMER_MODE_COUNTDOWN:
            # Handle timeout
            if rv >= self.initial_value:
                # Stop timer if not in loop mode
                if not self.loop:
                    self.pause()
                self.reset()
                rv = self.__value()
                if self.on_finish:
                    self.on_finish()
                self.notify()
            rv = self.initial_value - rv
        return rv

    def __value(self):
        if not self.__running:
            rv = self._last_value
        else:
            rv = datetime.datetime.now() - self._last_resume + self._last_value
        return rv

    def toggle(self):
        if self.__running:
            self.pause()
        else:
            self.resume()
            
    def is_running(self):
        return self.__running

    def pause(self):
        self._last_value = self.__value()
        self._last_resume = datetime.datetime.now()
        self.__running = False

    def resume(self):
        self._last_resume = datetime.datetime.now()
        self.__running = True

    def reset(self):
        self._last_value = datetime.timedelta()
        self._last_resume = datetime.datetime.now()

    def notify(self):
        g15notify.notify("Stopwatch", "Timer '" + self.label + "' is over.", timeout = 0)

# vim:set ts=4 sw=4 et:
