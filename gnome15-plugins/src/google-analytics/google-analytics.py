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
 
import gnome15.g15locale as g15locale
_ = g15locale.get_translation("cal", modfile = __file__).ugettext

import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15screen as g15screen
import gnome15.g15accounts as g15accounts
import datetime
import time
import os
import gobject
import calendar
import gtk\

# Logging
import logging
logger = logging.getLogger("google-analytics")

 
id="google-analytics"
name=_("Google Analytics")
description=_("Displays some summary information about sites being monitored\n\
by Google Analytics. You will require a Google Account, and the ID of the sites\n\
you wish to monitor.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.gnome15.org/"
has_preferences=True
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous day/Event"), 
         g15driver.NEXT_SELECTION : _("Next day/Event"), 
         g15driver.VIEW : _("Toggle between calendar\nand events"),
         g15driver.NEXT_PAGE : _("Next week"),
         g15driver.PREVIOUS_PAGE : _("Previous week")
         }
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_MX5500, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

# Configuration
CONFIG_PATH = "~/.config/gnome15/plugin-data/google-analytics/accounts.xml"
CONFIG_ITEM_NAME = "accounts"

"""
Functions
"""

def create(gconf_key, gconf_client, screen):
    return G15GoogleAnalytics(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    G15GoogleAnalyticsPreferences(parent, gconf_client, gconf_key)
    
class Site():
    
    def __init__(self):
        self.name = "Unknown"

class SiteMenuItem(g15theme.MenuItem):
    
    def __init__(self,  event, component_id):
        g15theme.MenuItem.__init__(self, component_id)
        self.site = site
    
    def get_default_theme_dir(self):
        return os.path.join(os.path.dirname(__file__), "default")
        
    def get_theme_properties(self):        
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self.site.name
        item_properties["item_alt"] = "XXXXX"
#        item_properties["item_icon"] = g15util.get_icon_path([ "stock_alarm", "alarm-clock", "alarm-timer", "dialog-warning" ])
        return item_properties
    
    def activate(self):
        self.event.activate()
    

class GoogleAnalyticsOptions(g15accounts.G15AccountOptions):
    def __init__(self, account, account_ui):
        g15accounts.G15AccountOptions.__init__(self, account, account_ui)
                
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "google-analytics.glade"))
        self.component = self.widget_tree.get_object("OptionPanel")
        
        username = self.widget_tree.get_object("Username")
        username.connect("changed", self._username_changed)
        username.set_text(self.account.get_property("username", ""))
        
    def _username_changed(self, widget):
        self.account.properties["username"] = widget.get_text()
        self.account_ui.save_accounts()
        
class G15GoogleAnalyticsPreferences(g15accounts.G15AccountPreferences):
    '''
    Configuration UI
    '''    
    
    def __init__(self, parent, gconf_client, gconf_key):
        g15accounts.G15AccountPreferences.__init__(self, parent, gconf_client, \
                                                   gconf_key, \
                                                   CONFIG_PATH, \
                                                   CONFIG_ITEM_NAME)
        
    def get_account_types(self):
        return [ "google-analytics" ]
    
    def get_account_type_name(self, account_type):
        return _(account_type)
        
    def create_options_for_type(self, account, account_type):
        return GoogleAnalyticsOptions(account, self)
        
class G15GoogleAnalytics():  
    
    def __init__(self, gconf_key, gconf_client, screen):
        
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._timer = None
        self._thumb_icon = g15util.load_surface_from_file(g15util.get_icon_path(["calendar", "evolution-calendar", "office-calendar", "stock_calendar" ]))
        
    def activate(self):
        self._active = True
        self._page = None
        self._theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), auto_dirty = False)
        self._loaded = 0
        
        # Backend
        self._account_manager = g15accounts.G15AccountManager(CONFIG_PATH, CONFIG_ITEM_NAME)
        self._account_manager.add_change_listener(self._accounts_changed)
        
        # Menu
        self._menu = g15theme.Menu("menu")
        self._menu.focusable = True
        
        # Page
        self._page = g15theme.G15Page(name, self._screen, on_shown = self._on_shown, \
                                     on_hidden = self._on_hidden, theme_properties_callback = self._get_properties,
                                     thumbnail_painter = self._paint_thumbnail)
        self._page.set_title("Google Analytics")
        self._page.set_theme(self._theme)
        self._screen.key_handler.action_listeners.append(self)
        gobject.idle_add(self._first_load)
        
    def deactivate(self):
        self._account_manager.remove_change_listener(self._accounts_changed)
        self._screen.key_handler.action_listeners.remove(self)
        if self._timer != None:
            self._timer.cancel()
        if self._page != None:
            g15screen.run_on_redraw(self._screen.del_page, self._page)
        
    def destroy(self):
        pass
                    
    """
    Private
    """
    
    def _accounts_changed(self, account_manager):
        self._loaded = 0
        self._redraw()
                    
    def _first_load(self):
        self._load_site_data(datetime.datetime.now())
        self._page.add_child(self._menu)
        self._page.add_child(self._calendar)
        self._page.add_child(g15theme.Scrollbar("viewScrollbar", self._menu.get_scroll_values))
        self._screen.add_page(self._page)
        self._redraw()
    
    def _get_properties(self):
        now = datetime.datetime.now()
        calendar_date = self._get_calendar_date()
        properties = {}
        properties["time_24"] = now.strftime("%H:%M") 
        properties["full_time_24"] = now.strftime("%H:%M:%S") 
        properties["time_12"] = now.strftime("%I:%M %p") 
        properties["full_time_12"] = now.strftime("%I:%M:%S %p")
        properties["short_date"] = now.strftime("%a %d %b")
        properties["full_date"] = now.strftime("%A %d %B")
        properties["locale_date"] = now.strftime("%x")
        properties["locale_time"] = now.strftime("%X")
        properties["year"] = now.strftime("%Y")
        properties["short_year"] = now.strftime("%y")
        properties["week"] = now.strftime("%W")
        properties["month"] = now.strftime("%m")
        properties["month_name"] = now.strftime("%B")
        properties["short_month_name"] = now.strftime("%b")
        properties["day_name"] = now.strftime("%A")
        properties["short_day_name"] = now.strftime("%a")
        properties["day_of_year"] = now.strftime("%d")
        properties["cal_year"] = calendar_date.strftime("%Y")
        properties["cal_month"] = calendar_date.strftime("%m")
        properties["cal_month_name"] = calendar_date.strftime("%B")
        properties["cal_short_month_name"] = calendar_date.strftime("%b")
        properties["cal_year"] = calendar_date.strftime("%Y")
        properties["cal_short_year"] = calendar_date.strftime("%y")
        properties["cal_locale_date"] = calendar_date.strftime("%x")
        if self._event_days is None or not str(calendar_date.day) in self._event_days:
            properties["message"] = "No events"
        else:
            properties["events"] = True
        return properties
    
    def _load_site_data(self, now):
        for acc in self._account_manager.accounts:
            # TODO
            pass
        g15screen.run_on_redraw(self._rebuild_components, now)
        self._page.mark_dirty()
        
    def _rebuild_components(self, now):
#        self._menu.remove_all_children()
#        if str(now.day) in self._event_days:
#            events = self._event_days[str(now.day)]
#            i = 0
#            for event in events:
#                self._menu.add_child(EventMenuItem(event, "menuItem-%d" % i))
#                i += 1
            
        self._page.redraw()
        
    def _schedule_redraw(self):
        if self._screen.is_visible(self._page):
            if self._timer is not None:
                self._timer.cancel()
            self._timer = g15util.schedule("CalRedraw", 60 - time.gmtime().tm_sec, self._redraw)
        
    def _on_shown(self):
        self._hidden = False
        self._redraw()
        
    def _on_hidden(self):
        if self._timer != None:
            self._timer.cancel()
        self._loaded_minute = -1
        
    def _redraw(self):
        t = time.time()
        if t > self._loaded + REFRESH_INTERVAL:
            self._loaded = t                        
            gobject.idle_add(self._redraw_now)
        else:
            self._page.mark_dirty()
            self._screen.redraw(self._page)
            self._schedule_redraw()
            
    def _redraw_now(self):
        self._load_month_events(datetime.datetime.now())
        self._screen.redraw(self._page)
        self._schedule_redraw()
    
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._page != None and self._thumb_icon != None and self._screen.driver.get_bpp() == 16:
            return g15util.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)
        

