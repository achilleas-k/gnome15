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

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("tails", modfile = __file__).ugettext

import gnome15.util.g15gconf as g15gconf
import gnome15.util.g15cairo as g15cairo
import gnome15.util.g15icontools as g15icontools
import gnome15.util.g15markup as g15markup
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15screen as g15screen
import subprocess
import time
import tailer
import os
import gtk
import gconf
import logging
import xdg.Mime as mime
from threading import Thread
logger = logging.getLogger("rss")

# Plugin details - All of these must be provided
id = "tails"
name = _("Tails")
description = _("Monitor multiple files, updating when they change. Just \
like the <b>tail</b> command.\n\n\
\
Warning: When monitoring large files that grow quickly, this plugin may \
cause massive memory usage.\n\n\
Uses the pytailer library (http://code.google.com/p/pytailer/), licensed \
under the LGPL. See %s and %s for more details." % ( os.path.join(__file__, "LICENSE" ), os.path.join(__file__, "README" ) ) )
author = "Brett Smith <tanktarta@blueyonder.co.uk>"
copyright = _("Copyright (C)2011 Brett Smith, Michael Thornton")
site = "http://www.russo79.com/gnome15"
has_preferences = True
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11, g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         g15driver.PREVIOUS_SELECTION : _("Previous line"), 
         g15driver.NEXT_SELECTION : _("Next line"),
         g15driver.NEXT_PAGE : _("Next page"),
         g15driver.PREVIOUS_PAGE : _("Previous page"),
         g15driver.SELECT : _("Open file in browser")
         }
 
def create(gconf_key, gconf_client, screen):
    return G15Tails(gconf_client, gconf_key, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    G15TailsPreferences(parent, driver, gconf_client, gconf_key)

def changed(widget, key, gconf_client):
    gconf_client.set_bool(key, widget.get_active())
    
class G15TailsPreferences():
    
    def __init__(self, parent, driver, gconf_client, gconf_key):
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "tails.ui"))
        
        # Feeds
        self.file_model = widget_tree.get_object("FileModel")
        self.reload_model()
        self.file_list = widget_tree.get_object("FileList")
        self.file_renderer = widget_tree.get_object("FileRenderer")
        
        # Lines
        self.lines_adjustment = widget_tree.get_object("LinesAdjustment")
        self.lines_adjustment.set_value(g15gconf.get_int_or_default(self._gconf_client, "%s/lines" % self._gconf_key, 10))
        
        # Connect to events
        self.lines_adjustment.connect("value-changed", self.lines_changed)
        self.file_renderer.connect("edited", self.file_edited)
        widget_tree.get_object("NewFile").connect("clicked", self.new_file)
        widget_tree.get_object("RemoveFile").connect("clicked", self.remove_file)
        
        # Show dialog
        self.dialog = widget_tree.get_object("TailsDialog")
        self.dialog.set_transient_for(parent)
        
        ah = gconf_client.notify_add(gconf_key + "/files", self.files_changed);
        self.dialog.run()
        self.dialog.hide()
        gconf_client.notify_remove(ah);
        
    def lines_changed(self, widget):
        self._gconf_client.set_int(self._gconf_key + "/lines", int(widget.get_value()))
        
    def add_file(self, file_path):
        files = self._gconf_client.get_list(self._gconf_key + "/files", gconf.VALUE_STRING)
        if file_path in files:
            files.remove(file_path)
        files.append(file_path)
        self._gconf_client.set_list(self._gconf_key + "/files", gconf.VALUE_STRING, files)
        
    def file_edited(self, widget, row_index, value):
        files = self._gconf_client.get_list(self._gconf_key + "/files", gconf.VALUE_STRING)
        row_index = int(row_index)
        if value != "":
            if self.file_model[row_index][0] != value:
                self.file_model.set_value(self.file_model.get_iter(row_index), 0, value)
                files[row_index] = value
                self._gconf_client.set_list(self._gconf_key + "/files", gconf.VALUE_STRING, files)
        else:
            self.file_model.remove(self.file_model.get_iter(row_index))
            del files[row_index]
            self._gconf_client.set_list(self._gconf_key + "/files", gconf.VALUE_STRING, files)
        
    def files_changed(self, client, connection_id, entry, args):
        self.reload_model()
        
    def reload_model(self):
        self.file_model.clear()
        for url in self._gconf_client.get_list(self._gconf_key + "/files", gconf.VALUE_STRING):
            self.file_model.append([ url, True ])
        
    def new_file(self, widget):
        dialog = gtk.FileChooserDialog(_("Add file to monitor.."),
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.dialog)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.file_model.append([dialog.get_filename(), True])
            self.add_file(dialog.get_filename())
            
        dialog.destroy()
        
    def remove_file(self, widget):        
        (model, path) = self.file_list.get_selection().get_selected()
        file = model[path][0]
        files = self._gconf_client.get_list(self._gconf_key + "/files", gconf.VALUE_STRING)
        if file in files:
            files.remove(file)
            self._gconf_client.set_list(self._gconf_key + "/files", gconf.VALUE_STRING, files)   
        
        
class G15TailMenuItem(g15theme.MenuItem):
    def __init__(self, id, line, file_path):
        g15theme.MenuItem.__init__(self, id)
        self.line = line
        self.file = file_path
        
    def on_configure(self):
        self.set_theme(g15theme.G15Theme(self.parent.get_theme().dir, "menu-entry"))
        
    def get_theme_properties(self):        
        element_properties = g15theme.MenuItem.get_theme_properties(self)
        element_properties["line"] = self.line
        return element_properties 
    
    def activate(self):
        logger.info("xdg-open '%s'" % self.file)
        subprocess.Popen(['xdg-open', self.file])
        return True
        
class G15TailThread(Thread):
    def __init__(self, page):
        Thread.__init__(self)
        self.page = page
        self.fd = None
        self.line_seq = 0
        self.setDaemon(True)
        self.setName("Monitor%s" % self.page.file_path)
        self._stopped = False
        
    def stop_monitoring(self):
        self._stopped = True
        if self.fd is not None:
            self.fd.close()
        
    def run(self):
        for line in tailer.tail(open(self.page.file_path), self.page.plugin.lines):
            g15screen.run_on_redraw(self._add_line, line)
        self.fd = open(self.page.file_path)
        try:
            for line in tailer.follow(self.fd):
                if self._stopped:
                    break
                g15screen.run_on_redraw(self._add_line, line)
                if self._stopped:
                    break
        except ValueError as e:
            logger.debug("Error while reading", exc_info = e)
            if not self._stopped:
                raise e
        self.page.redraw()
            
    def _add_line(self, line):
        line = line.strip()
        if len(line) > 0 and not self._stopped:
            line  = g15markup.html_escape(line)
            while self.page._menu.get_child_count() > self.page.plugin.lines:
                self.page._menu.remove_child_at(0)
            self.page._menu.add_child(G15TailMenuItem("Line-%d" % self.line_seq, line, self.page.file_path))
            self.page._menu.select_last_item()
            self.line_seq += 1
        
class G15TailPage(g15theme.G15Page):
    
    def __init__(self, plugin, file_path):   
        
        self._gconf_client = plugin._gconf_client        
        self._gconf_key = plugin._gconf_key
        self._screen = plugin._screen
        self._icon_surface = None
        self._icon_embedded = None
        self.plugin = plugin
        self.file_path = file_path
        self.thread =  None
        self.index = -1
        self._menu = g15theme.Menu("menu")
        g15theme.G15Page.__init__(self, os.path.basename(file_path), self._screen,
                                     thumbnail_painter=self._paint_thumbnail,
                                     theme=g15theme.G15Theme(self, "menu-screen"), theme_properties_callback=self._get_theme_properties,
                                     originating_plugin = plugin)
        self.add_child(self._menu)
        self.add_child(g15theme.MenuScrollbar("viewScrollbar", self._menu))
        self._reload() 
        self._screen.add_page(self)
        self._screen.redraw(self)
        self.on_deleted = self._stop
            
    """
    Private
    """
        
    def _reload(self):
        icons = []
        mime_type = mime.get_type(self.file_path)
        if mime_type != None:
            icons.append(str(mime_type).replace("/","-"))
        icons.append("text-plain")
        icons.append("panel-searchtool")
        icons.append("gnome-searchtool")
        icon = g15icontools.get_icon_path(icons, size=self.plugin._screen.height)
        
        if icon is None:
            self._icon_surface = None
            self._icon_embedded = None
        else:
            try :
                icon_surface = g15cairo.load_surface_from_file(icon)
                self._icon_surface = icon_surface
                self._icon_embedded = g15icontools.get_embedded_image_url(icon_surface)
            except Exception as e:
                logger.warning("Failed to get icon %s", str(icon), exc_info = e)
                self._icon_surface = None
                self._icon_embedded = None
        
        self._stop()
        if os.path.exists(self.file_path):
            self._subtitle =  time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(self.file_path)))
            self._message = ""
            self.thread = G15TailThread(self)
            self.thread.start()
        else:
            self._subtitle = ""
            self._message = "File does not exist"
            
    def _stop(self):
        if self.thread is not None:
            self.thread.stop_monitoring()
            self.thread = None
            
    def _get_theme_properties(self):
        properties = {}
        properties["title"] = self.title
        properties["icon"] = self._icon_embedded
        properties["subtitle"] = self._subtitle
        properties["message"] = self._message
        properties["alt_title"] = ""
        return properties 
        
    def _paint_thumbnail(self, canvas, allocated_size, horizontal):
        if self._icon_surface:
            return g15cairo.paint_thumbnail_image(allocated_size, self._icon_surface, canvas)
            
class G15Tails():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self._screen = screen;
        self._gconf_key = gconf_key
        self._gconf_client = gconf_client

    def activate(self):
        self._pages = {}       
        self._lines_changed_handle = self._gconf_client.notify_add(self._gconf_key + "/lines", self._lines_changed)
        self._files_changed_handle = self._gconf_client.notify_add(self._gconf_key + "/files", self._files_changed)
        self._load_files()
    
    def deactivate(self):
        self._gconf_client.notify_remove(self._lines_changed_handle);
        self._gconf_client.notify_remove(self._files_changed_handle);
        for page in self._pages:
            self._screen.del_page(self._pages[page])
        self._pages = {}
    
    '''
    Private
    '''
        
    def destroy(self):
        pass 
    
    def _lines_changed(self, client, connection_id, entry, args):
        self._load_files()
        
    def _files_changed(self, client, connection_id, entry, args):
        self._load_files()
    
    def _load_files(self):
        self.lines = g15gconf.get_int_or_default(self._gconf_client, "%s/lines" % self._gconf_key, 10)
        file_list = self._gconf_client.get_list(self._gconf_key + "/files", gconf.VALUE_STRING)
        
        def init():
            # Add new pages
            for file_path in file_list:
                if not file_path in self._pages:
                    pg = G15TailPage(self, file_path)
                    self._pages[file_path] = pg
                else:
                    self._pages[file_path]._reload()
                    
            # Remove pages that no longer exist
            to_remove = []
            for file_path in self._pages:
                page = self._pages[file_path]
                if not page.file_path in file_list:
                    self._screen.del_page(page)
                    to_remove.append(file_path)
            for page in to_remove:
                del self._pages[page]
        g15screen.run_on_redraw(init)
            
