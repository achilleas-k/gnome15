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
import gnome15.util.g15convert as g15convert
import gnome15.util.g15gconf as g15gconf
import gnome15.util.g15scheduler as g15scheduler
import gnome15.util.g15cairo as g15cairo
import gnome15.util.g15icontools as g15icontools
import gnome15.g15screen as g15screen
import gnome15.g15accounts as g15accounts
import gnome15.g15globals as g15globals
import datetime
import time
import os
import gobject
import calendar
import gtk
import gdata.analytics.client
import cairoplot
import cairo

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
site="http://www.russo79.com/gnome15"
has_preferences=True
needs_network=True
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous site"), 
         g15driver.NEXT_SELECTION : _("Next site"), 
         }
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_MX5500, g15driver.MODEL_G930, g15driver.MODEL_G35 ]

SOURCE_APP_NAME = '%s-%s' % ( g15globals.name, g15globals.version )
CONFIG_PATH = "~/.config/gnome15/plugin-data/google-analytics/accounts.xml"
CONFIG_ITEM_NAME = "accounts"
ACC_MGR_HOSTNAME = "www.google.com"

"""
Functions
"""

def create(gconf_key, gconf_client, screen):
    return G15GoogleAnalytics(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    G15GoogleAnalyticsPreferences(parent, gconf_client, gconf_key)
    
def get_update_time(gconf_client, gconf_key):
    val = gconf_client.get_int(gconf_key + "/update_time")
    if val == 0:
        val = 10
    return val
    
class Site():
    
    def __init__(self):
        self.name = "Unknown"

class SiteMenuItem(g15theme.MenuItem):
    
    def __init__(self,  entry, account):
        g15theme.MenuItem.__init__(self, entry.GetProperty('ga:webPropertyId').value)
        self._entry = entry
        self._account = account
        self.aggregates = {}
    
    def get_default_theme_dir(self):
        return os.path.join(os.path.dirname(__file__), "default")
        
    def get_theme_properties(self):        
        
        item_properties = g15theme.MenuItem.get_theme_properties(self)
        item_properties["item_name"] = self._entry.GetProperty('ga:accountName').value
        item_properties["item_alt"] = self._account.name
        
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


class G15VisitsGraph(g15theme.Component):
    
    def __init__(self, component_id, plugin):
        g15theme.Component.__init__(self, component_id)
        self.plugin = plugin

    def get_colors(self):
        series_colors = None
        fill_colors = None
        if self.plugin._screen.driver.get_control_for_hint(g15driver.HINT_HIGHLIGHT): 
            highlight_color = self.plugin._screen.driver.get_color_as_ratios(g15driver.HINT_HIGHLIGHT, (255, 0, 0 ))
            series_colors = (highlight_color[0],highlight_color[1],highlight_color[2], 1.0)
            fill_colors = (highlight_color[0],highlight_color[1],highlight_color[2], 0.50)
        return series_colors, fill_colors
        
    def create_plot(self, graph_surface):
        series_color, fill_color = self.get_colors()
        alt_series_color = g15convert.get_alt_color(series_color)
        alt_fill_color = g15convert.get_alt_color(fill_color)
        
        selected = self.plugin._menu.selected
        pie_data = {}
        if selected:
            new_visits = float(selected.aggregates["ga:percentNewVisits"])
            returning = 100.0 - new_visits
            pie_data[_("New %0.2f%%" % new_visits)] = new_visits
            pie_data[_("Returning %0.2f%%" % returning)] = returning
            
        plot = cairoplot.PiePlot(graph_surface, pie_data, 
                                 self.view_bounds[2], 
                                 self.view_bounds[3], 
                                 background = None,
                                 colors = [ series_color, alt_series_color ])
        plot.font_size = 18
        return plot
        
    def paint(self, canvas):
        g15theme.Component.paint(self, canvas)    
        if self.view_bounds:
            graph_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 
                                               int(self.view_bounds[2]), 
                                               int(self.view_bounds[3]))
            plot =  self.create_plot(graph_surface)
            plot.line_width = 2.0
            plot.line_color = self.plugin._screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, (255, 255, 255))
            plot.label_color = self.plugin._screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, (255, 255, 255))
            plot.shadow = True
            plot.bounding_box = False
            plot.render()
            plot.commit()
            
            canvas.save()    
            canvas.translate(self.view_bounds[0], self.view_bounds[1])
            canvas.set_source_surface(graph_surface, 0.0, 0.0)
            canvas.paint()
            canvas.restore()


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
        self._icon_path = g15icontools.get_icon_path([ "redhat-office", "package_office", "gnome-applications", "xfce-office", "baobab" ])
        self._thumb_icon = g15cairo.load_surface_from_file(self._icon_path)
        self._timer = None
        
    def activate(self):
        self._active = True
        self._page = None
        self._theme = g15theme.G15Theme(os.path.join(os.path.dirname(__file__), "default"), auto_dirty = False)
        self._loaded = 0
        
        self.pie_data = []
        
        # Backend
        self._account_manager = g15accounts.G15AccountManager(CONFIG_PATH, CONFIG_ITEM_NAME)
        self._account_manager.add_change_listener(self._accounts_changed)
        
        # Menu
        self._menu = g15theme.Menu("menu")
        self._menu.focusable = True
        self._menu.on_selected = self._on_menu_selected
        
        # Page
        self._page = g15theme.G15Page(name, self._screen, theme_properties_callback = self._get_properties,
                                     thumbnail_painter = self._paint_thumbnail,
                                     originating_plugin = self)
        self._page.set_title(_("Google Analytics"))
        self._page.set_theme(self._theme)
        self._screen.key_handler.action_listeners.append(self)
        self._page.add_child(G15VisitsGraph("visitsGraph", self))
        self._page.add_child(self._menu)
        self._page.add_child(g15theme.MenuScrollbar("viewScrollbar", self._menu))
        self._screen.add_page(self._page)
        self._schedule_refresh(0)
        
    def deactivate(self):
        self._account_manager.remove_change_listener(self._accounts_changed)
        self._screen.key_handler.action_listeners.remove(self)
        self._cancel_refresh()
        self._page.delete()
        
    def destroy(self):
        pass
    
    def action_performed(self, binding):
        if self._page and self._page.is_visible():
            pass
                    
    """
    Private
    """
    def _on_menu_selected(self):
        self._gconf_client.set_string("%s/selected_site" % self._gconf_key, self._menu.selected.id)
        
    def _cancel_refresh(self):
        if self._timer != None:
            self._timer.cancel()
            
    def _do_refresh(self):
        if self._page:
            self._load_site_data()
            self._page.redraw()
            self._schedule_refresh(get_update_time(self._gconf_client, self._gconf_key) * 60.0) 
            selected = g15gconf.get_string_or_default(self._gconf_client, "%s/selected_site" % self._gconf_key, None)
            if selected:
                for m in self._menu.get_children():
                    if m.id == selected:
                        self._menu.set_selected_item(m)
        
    def _schedule_refresh(self, time):
        self._timer = g15scheduler.schedule("AnalyticsRedraw", time, self._do_refresh)
    
    def _accounts_changed(self, account_manager):        
        self._cancel_refresh()
        self._do_refresh()
                    
    def _get_properties(self):
        properties = {}
        properties["icon"] = self._icon_path 
        properties["title"] = self._page.title
        properties["alt_title"] = ""
        properties["message"] = _("No sites configured") if len(self._menu.get_children()) == 0 else ""
        sel = self._menu.selected
        if sel:
            properties["visits"] = sel.aggregates["ga:visits"]
            properties["unique"] = sel.aggregates["ga:newVisits"]
            properties["views"] = sel.aggregates["ga:pageviews"]
            properties["pagesVisit"] = "%0.2f" % float(sel.aggregates["ga:pageviewsPerVisit"])
            properties["avgDuration"] = str(datetime.timedelta(seconds=int(float(sel.aggregates["ga:avgTimeOnSite"]))))
            properties["bounce"] = "%0.2f" % float(sel.aggregates["ga:visitBounceRate"])
            properties["uniquePercent"] = "%0.2f" % float(sel.aggregates["ga:percentNewVisits"])
        else:
            properties["visits"] = ""
            properties["unique"] = ""
            properties["views"] = ""
            properties["pagesVisit"] = ""
            properties["avgDuration"] = ""
            properties["bounce"] = ""
            properties["uniquePercent"] = ""
            
        return properties
    
    def _load_site_data(self):
        items = []
        for acc in self._account_manager.accounts:
            self._load_account_site_data(items, acc)
        self._menu.set_children(items)
        self._page.mark_dirty()
        
    def _load_account_site_data(self, items, account):
        self._client = gdata.analytics.client.AnalyticsClient(source=SOURCE_APP_NAME)
        ex = None
        for i in range(0, 3):
            for j in range(0, 2):
                password = self._account_manager.retrieve_password(account, ACC_MGR_HOSTNAME, None, i > 0)
                if password == None or password == "":
                    raise Exception(_("Authentication cancelled"))
                
                try :
                    return self._retrieve_site_data(items, account, password)
                except gdata.client.BadAuthentication as e:
                    ex = e
                    
        if ex is not None:
            raise ex
        
    def _retrieve_site_data(self, items, account, password):
        username = account.get_property("username", "")
        logger.info("Logging in as %s / %s for %s on %s" % (username, password, account, self._client.source))
        self._client.ClientLogin(username, password, self._client.source)
        account_query = gdata.analytics.client.AccountFeedQuery()
        self._account_manager.store_password(account, password, ACC_MGR_HOSTNAME, None)
        self.feed = self._client.GetAccountFeed(account_query)

        for entry in self.feed.entry:
            item = SiteMenuItem(entry, account)
            items.append(item)
            end_date = datetime.date.today()
            start_date = datetime.date(2005,01,01)
            data_query = gdata.analytics.client.DataFeedQuery({
                    'ids': entry.table_id.text,
                    'start-date': start_date.isoformat(),
                    'end-date': end_date.isoformat(),
                    'max-results': 0,
                    'dimensions': 'ga:date',
                    'metrics': 'ga:visits,ga:newVisits,ga:pageviews,ga:pageviewsPerVisit,ga:avgTimeOnSite,ga:visitBounceRate,ga:percentNewVisits'})
            
            feed = self._client.GetDataFeed(data_query)                
            aggregates = feed.aggregates
            for m in aggregates.metric:
                item.aggregates[m.name] = m.value
        
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._page != None and self._thumb_icon != None and self._screen.driver.get_bpp() == 16:
            return g15cairo.paint_thumbnail_image(allocated_size, self._thumb_icon, canvas)
        

