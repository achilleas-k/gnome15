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
Calendar backend that retrieves event data from Evolution
"""
 
import gnome15.g15locale as g15locale
import gnome15.g15accounts as g15accounts
_ = g15locale.get_translation("cal-evolution", modfile = __file__).ugettext
import cal
import gtk
import os
from threading import Lock
 
"""
Plugin definition
"""
id="cal-evolution"
name=_("Calendar (Evolution support)")
description=_("Calendar for Evolution. Adds Evolution as a source for calendars \
to the Calendar plugin")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=False
global_plugin=True
passive=True
unsupported_models=cal.unsupported_models

"""
Calendar Back-end module functions
"""
def create_options(account, account_ui):
    return EvolutionCalendarOptions(account, account_ui)

def create_backend(account, account_manager):
    return EvolutionBackend()

class EvolutionCalendarOptions(g15accounts.G15AccountOptions):
    def __init__(self, account, account_ui):
        g15accounts.G15AccountOptions.__init__(self, account, account_ui)
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "cal-evolution.glade"))
        self.component = self.widget_tree.get_object("OptionPanel")
        try :
            self.event.valarm
            self.alarm = True
        except AttributeError:
            pass

class EvolutionEvent(cal.CalendarEvent):
    
    def __init__(self, parsed_event):
        cal.CalendarEvent.__init__(self)
        
        self.start_date = parsed_event.dtstart.value
        if parsed_event.dtend:
            self.end_date = parsed_event.dtend.value
        else:
            self.end_date = datetime.datetime(self.start_date.year,self.start_date.month,self.start_date.day, 23, 59, 0)
            
        self.summary = parsed_event.summary.value
        self.alt_icon = os.path.join(os.path.dirname(__file__), "icon.png")
        
class EvolutionBackend(cal.CalendarBackend):
    
    def __init__(self):
        cal.CalendarBackend.__init__(self)
        self._lock = Lock()
        
    def get_events(self, now):
        # Has to run in gobject thread
        if g15util.is_gobject_thread():
            return self._do_get_events(now)            
        else:
            self._lock.acquire()
            gobject.idle_add(self._do_get_events, now, True)
            self._lock.acquire()
            self._lock.release()
        
    def _do_get_events(self, now, release_lock = False):
        event_days = {}
        try:
            import evolution.ecal
            import vobject
            
            # Get all the events for this month
            for i in evolution.ecal.list_calendars():
                ecal = evolution.ecal.open_calendar_source(i[1], evolution.ecal.CAL_SOURCE_TYPE_EVENT)
                for i in ecal.get_all_objects():
                    parsed_event = vobject.readOne(i.get_as_string())
                    self.check_and_add(EvolutionEvent(parsed_event), now, event_days)
        finally:
            if release_lock:
                self._lock.release()
                        
        return event_days