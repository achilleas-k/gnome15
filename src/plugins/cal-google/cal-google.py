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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("cal-evolution", modfile = __file__).ugettext

import gnome15.g15accounts as g15accounts
import gnome15.g15globals as g15globals
import cal
import gtk
import os
import datetime
import calendar
import gdata.calendar.data
import gdata.calendar.client
import gdata.acl.data
import gdata.service
import iso8601
import subprocess
import socket

# Logging
import logging
logger = logging.getLogger(__name__)
 
"""
Plugin definition
"""
id="cal-google"
name=_("Calendar (Google support)")
description=_("Adds your Google Calendar as a source for the Gnome15 Calendar plugin")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2012 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=False
passive=True
needs_network=True
global_plugin=True
requires="cal"
unsupported_models=cal.unsupported_models

"""
Calendar Back-end module functions
"""
def create_options(account, account_ui):
    return GoogleCalendarOptions(account, account_ui)

def create_backend(account, account_manager):
    return GoogleCalendarBackend(account, account_manager)

# How often refresh from the evolution calendar. This can be a slow process, so not too often
REFRESH_INTERVAL = 15 * 60

class GoogleCalendarOptions(g15accounts.G15AccountOptions):
    def __init__(self, account, account_ui):
        g15accounts.G15AccountOptions.__init__(self, account, account_ui)
                
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "cal-google.ui"))
        self.component = self.widget_tree.get_object("OptionPanel")
        
        username = self.widget_tree.get_object("Username")
        username.connect("changed", self._username_changed)
        username.set_text(self.account.get_property("username", ""))
        
        calendar = self.widget_tree.get_object("Calendar")
        calendar.connect("changed", self._calendar_changed)
        calendar.set_text(self.account.get_property("calendar", ""))
        
    def _username_changed(self, widget):
        self.account.properties["username"] = widget.get_text()
        self.account_ui.save_accounts()
        
    def _calendar_changed(self, widget):
        self.account.properties["calendar"] = widget.get_text()
        self.account_ui.save_accounts()

class GoogleEvent(cal.CalendarEvent):
    
    def __init__(self, when, parsed_event, color, url):
        cal.CalendarEvent.__init__(self)
        self.start_date = iso8601.parse_date(when.start)
        if when.end:
            # Cal plugin dates are inclusive, but googles seem to be exclusive
            d = iso8601.parse_date(when.end)
            if d.hour == 0 and d.minute == 0 and d.second == 0:
                d = d - datetime.timedelta(0, 1)
                
            self.end_date = d
        else:
            self.end_date = datetime.datetime(self.start_date.year,self.start_date.month,self.start_date.day, 23, 59, 0)
            
        self.link = url
        self.color = color
        self.summary = parsed_event.title.text
        self.alarm = len(when.reminder) > 0
        self.alt_icon = os.path.join(os.path.dirname(__file__), "icon.png")
        
    def activate(self):
        logger.info("xdg-open '%s'", self.link)
        subprocess.Popen(['xdg-open', self.link])

        
class GoogleCalendarBackend(cal.CalendarBackend):
    
    def __init__(self, account, account_manager):
        cal.CalendarBackend.__init__(self)
        self.account = account
        self.account_manager = account_manager
        
    def get_events(self, now):
        self.cal_client = gdata.calendar.client.CalendarClient(source='%s-%s' % ( g15globals.name, g15globals.version ) )
        
        # Reload the account
        self.account = self.account_manager.by_name(self.account.name)
        
        for i in range(0, 3):
            for j in range(0, 2):
                password = self.account_manager.retrieve_password(self.account, "www.google.com", None, i > 0)
                if password == None or password == "":
                    raise Exception(_("Authentication cancelled"))
                
                try :
                    return self._retrieve_events(now, password)
                except gdata.client.BadAuthentication as e:
                    logger.debug("Error authenticating", exc_info = e)
                    pass
                
        raise Exception(_("Authentication attempted too many times"))  
        
        
    def _retrieve_events(self, now, password):
        event_days = {}
        self.cal_client.ClientLogin(self.account.get_property("username", ""), password, self.cal_client.source)
        self.account_manager.store_password(self.account, password, "www.google.com", None)
        start_date = datetime.date(now.year, now.month, 1)
        end_date = datetime.date(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        feeds = self.cal_client.GetAllCalendarsFeed()
        
        for i, a_calendar in zip(xrange(len(feeds.entry)), feeds.entry):
            query = gdata.calendar.client.CalendarEventQuery(start_min=start_date, start_max=end_date)
            logger.info("Retrieving events from %s to %s", str(start_date), str(end_date))
            feed = self.cal_client.GetCalendarEventFeed(a_calendar.content.src, q = query)
            
            # TODO - Color doesn't seem to work 
            color = None
            
            for i, an_event in zip(xrange(len(feed.entry)), feed.entry):
                logger.info('Adding event %s (%s)', an_event.title.text, str(an_event.when))
                
                """
                An event may have multiple times. cal doesn't support multiple times, so we add multiple events instead
                """
                for a_when in an_event.when:
                    self.check_and_add(GoogleEvent(a_when, an_event, color, a_calendar.content.src), now, event_days)
                
        return event_days
        

