#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2011 Brett Smith <tanktarta@blueyonder.co.uk>
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

import logging
import cairo
import os
logger = logging.getLogger(__name__)
import sys
from gi.repository import GLib, GObject, Gio
from gi.repository import Dee
# FIXME: Some weird bug in Dee or PyGI makes Dee fail unless we probe
#        it *before* we import the Unity module... ?!
_m = dir(Dee.SequenceModel)
from gi.repository import Unity
from gnome15 import g15devices
from gnome15 import util.g15os as g15os
from gnome15 import util.g15icontools as g15icontools
from gnome15 import g15screen
from gnome15 import g15globals
from cStringIO import StringIO
import base64

#
# The primary bus name we grab *must* match what we specify in our .place file
#
BUS_NAME = "org.gnome15.Gnome15Lens"

# These category ids must match the order in which we add them to the lens
CATEGORY_PAGES = 0
CATEGORY_TOOLS = 1
 
# Plugin details - All of these must be provided
id="lens"
name="Unity Lens"
description="Integrates Gnome15 with Unity"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
global_plugin=True

# Cached 
cache_dir = os.path.join(g15globals.user_cache_dir, "lens")
if not os.path.exists(cache_dir):
    g15os.mkdir_p(cache_dir)

def create(gconf_key, gconf_client, service):
    return G15Lens(service, gconf_client, gconf_key)
            
class G15Lens():
    
    def __init__(self, service, gconf_client, gconf_key):
        self._service = service
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self.listeners = []

    def activate(self):
        
        session_bus_connection = Gio.bus_get_sync (Gio.BusType.SESSION, None)
        session_bus = Gio.DBusProxy.new_sync (session_bus_connection, 0, None,
                                          'org.freedesktop.DBus',
                                          '/org/freedesktop/DBus',
                                          'org.freedesktop.DBus', None)
        result = session_bus.call_sync('RequestName',
                                   GLib.Variant ("(su)", (BUS_NAME, 0x4)),
                                   0, -1, None)
                                   
        # Unpack variant response with signature "(u)". 1 means we got it.
        result = result.unpack()[0]
    
        if result != 1 :
            print >> sys.stderr, "Failed to own name %s. Bailing out." % BUS_NAME
            raise Exception("Failed to own name %s. Bailing out." % BUS_NAME)
        
        self._lens = Unity.Lens.new("/org/gnome15/Gnome15Lens", "Gnome15Lens")
        self._scope = Unity.PlaceEntryInfo.new ("/org/gnome15/Gnome15Lens/scope/main")
    #
        self._lens.props.search_hint = "LCD Page name ..."
        self._lens.props.visible = True
        self._lens.props.search_in_global = True
        
        # Populate categories
        cats = []
        cats.append (Unity.Category.new ("Pages",
                                         Gio.ThemedIcon.new("display"),
                                         Unity.CategoryRenderer.VERTICAL_TILE))
        cats.append (Unity.Category.new ("Tools",
                                         Gio.ThemedIcon.new("configuration-section"),
                                         Unity.CategoryRenderer.VERTICAL_TILE))
        self._lens.props.categories = cats
        
        # Listen for changes and requests
        self._scope.connect ("notify::active-search", self._on_search_changed)
        self._scope.connect ("notify::active-global-search", self._on_global_search_changed)
        
        self._lens.add_local_scope (self._scope);
        self._lens.export ();
    
    def do_activate(self, *args):
        print "activate:", args
        return Unity.ActivationStatus.ACTIVATED_HIDE_DASH
        
    def _activation(self, uri):
        print uri
        return True
        
    def screen_removed(self, screen):
        for l in self.listeners:
            if l.screen == screen:
                self.listeners.remove(l)
                return
    
    def service_stopped(self):
        pass
        
    def screen_added(self, screen):
        self._add_screen(screen)
    
    def service_stopping(self):
        pass
    
    def service_starting_up(self):
        pass
    
    def service_started_up(self):
        pass
    
    def get_search_string (self):
        search = self._scope.props.active_search
        return search.get_search_string() if search else None
    
    def get_global_search_string (self):
        search = self._scope.props.active_global_search
        return search.get_search_string() if search else None
    
    def search_finished (self):
        search = self._scope.props.active_search
        if search:
            search.emit ("finished")
    
    def global_search_finished (self):
        search = self._scope.props.active_global_search
        if search:
            search.emit("finished")
            
    """
    Private
    """
    def _on_activation(self, uri, callback, callback_target):
        print "URI %s, %s, %s" % ( uri, str(callback), str(callback_target))
    
    def _add_screen(self, screen):
        listener = MenuScreenChangeListener(self, screen)
        self.listeners.append(listener)
        screen.add_screen_change_listener(listener)
    
    def _on_sections_synchronized (self, sections_model, *args):
        # Column0: display name
        # Column1: GIcon in string format
        sections_model.clear ()
        for device in g15devices.find_all_devices():
            if device.model_id == 'virtual':
                icon_file = g15icontools.get_icon_path(["preferences-system-window", "preferences-system-windows", "gnome-window-manager", "window_fullscreen"])
            else:
                icon_file = g15icontools.get_app_icon(self._gconf_client,  device.model_id)
            icon = Gio.FileIcon(Gio.File(icon_file))
            sections_model.append (device.model_fullname,
                                   icon.to_string())
    
    def _on_groups_synchronized (self, groups_model, *args):
        groups_model.clear ()
        groups_model.append ("UnityDefaultRenderer",
                             "Screens",
                             Gio.ThemedIcon("display").to_string())
        groups_model.append ("UnityDefaultRenderer",
                             "Tools",
                             Gio.ThemedIcon("preferences-system").to_string())
    
    def _on_global_groups_synchronized (self, global_groups_model, *args):
        # Just the same as the normal groups
        self._on_groups_synchronized (global_groups_model)
    
    def _on_search_changed (self, *args):        
        search = self.get_search_string()
        results = self._entry.props.results_model
        
        print "Search changed to: '%s'" % search
        
        self._update_results_model (search, results)
        self.search_finished()
    
    def _on_global_search_changed (self, entry, param_spec):
        search = self.get_global_search_string()
        results = self._entry.props.global_renderer_info.props.results_model
        
        print "Global search changed to: '%s'" % search
        
        self._update_results_model (search, results)
        self.global_search_finished()
        
    def _update_results_model (self, search, model):
        model.clear ()
        search = search.lower()
        print "Search> %s" % search
        for listener in self.listeners:
            print "   L[%s]" % str(listener)
            for page in listener.screen.pages:
                if len(search) == 0 or search in page.title.lower(): 
                    icon_hint = listener._get_page_filename(page)
                    uri = "gnome15://%s" % base64.encodestring(page.id)
                    print "      URI %s" % uri
                    model.append (uri,    # uri
                                  icon_hint,        # string formatted GIcon
                                  CATEGORY_PAGES,   # numeric group id
                                  "text/html",      # mimetype
                                  page.title,       # display name
                                  page.title,       # comment,
                                  uri)              # FIXME WHATSTHIS?
            
        print str(model)
    
    def deactivate(self):
        pass
        
    def destroy(self):
        pass
        
class MenuScreenChangeListener(g15screen.ScreenChangeAdapter):
    def __init__(self, plugin, screen):
        self.plugin = plugin
        self.screen = screen
        for page in screen.pages:
            self._add_page(page)
        
    def new_page(self, page):
        print "Adding page %s for screen %s" % (page.id, self.screen.device.uid)
        self._add_page(page)
        
    def title_changed(self, page, title):        
        self._update_page(page)
    
    def del_page(self, page):
        filename = self._get_page_filename(page)
        logger.info("Removing page thumbnail image" % filename)
        os.remove(filename)
            
    """
    Private
    """
    def _get_page_filename(self, page):
        return "%s/%s.png" % ( cache_dir, base64.encodestring(page.id) )
    
    def _add_page(self, page):
        self._update_page(page)
        
    def _update_page(self, page):
        if page.thumbnail_painter != None:
            img = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.screen.width, self.screen.height)
            thumb_canvas = cairo.Context(img)
            try :
                if page.thumbnail_painter(thumb_canvas, self.screen.height, True):
                    filename = self._get_page_filename(page) 
                    logger.info("Writing thumbnail to %s" % filename)
                    img.write_to_png(filename)
            except Exception as e:
                logger.warning("Problem with painting thumbnail.", exc_info = e)
