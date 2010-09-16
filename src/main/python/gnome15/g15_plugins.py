#!/usr/bin/env python
 
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
 
import os.path
import imp
import sys
import g15_globals as pglobals
import gconf
import gtk

pluginpath = pglobals.plugin_dir
plugindirs = [fname for fname in os.listdir(pluginpath) ]
imported_plugins = []
for plugindir in plugindirs:
    if os.path.isdir(os.path.join(pluginpath, plugindir)):
        plugindir_path = os.path.join(pluginpath, plugindir)
        pluginfiles = [fname[:-3] for fname in os.listdir(plugindir_path) if fname == plugindir + ".py"]
        if not plugindir_path in sys.path:
            sys.path.insert(0, plugindir_path)
        for mod in ([__import__(fname) for fname in pluginfiles]):
            imported_plugins.append(mod)

class G15Plugins():
    def __init__(self, screen):
        self.screen = screen
        self.conf_client = gconf.client_get_default()
        self.mgr_started = False
        self.mgr_active = False
        self.started = []
        self.activated = []
        self.plugin_key = "/apps/gnome15/plugins"
        self.conf_client.add_dir(self.plugin_key, gconf.CLIENT_PRELOAD_NONE)
        self.module_map = {}
        self.plugin_map = {}
        self.selected_id = None
        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(os.path.join(pglobals.glade_dir, 'g15-plugins.glade'))
        self.key_field = self.widget_tree.get_object("MacroScript")
        self.plugin_dialog = self.widget_tree.get_object("PluginDialog")
        self.plugin_model = self.widget_tree.get_object("PluginModel")
        self.plugin_tree = self.widget_tree.get_object("PluginTree")
        self.plugin_enabled_renderer = self.widget_tree.get_object("PluginEnabledRenderer")
        
        # Connect to events
        
        self.plugin_tree.connect("cursor-changed", self.select_plugin)
        self.plugin_enabled_renderer.connect("toggled", self.toggle_plugin)
        self.widget_tree.get_object("PreferencesButton").connect("clicked", self.show_preferences)
        
        # Populate model
        self.load_model()
        
    def show_preferences(self, widget):
        plugin = self.get_selected_plugin()
        if plugin.id in self.module_map:
            instance = self.module_map[plugin.id]
            instance.show_preferences(self.plugin_dialog)
        
    def load_model(self):
        self.plugin_model.clear()
        for mod in imported_plugins:
            key = self.plugin_key + "/" + mod.id + "/enabled"
            enabled = self.conf_client.get_bool(key)
            self.plugin_model.append([enabled, mod.name, mod.id])
            if mod.id == self.selected_id:
                self.plugin_tree.get_selection().select_path(self.plugin_model.get_path(self.plugin_model.get_iter(len(self.plugin_model) - 1)))
        if len(self.plugin_model) > 0 and self.get_selected_plugin() == None:            
            self.plugin_tree.get_selection().select_path(self.plugin_model.get_path(self.plugin_model.get_iter(0)))
        self.select_plugin(None)
        
    def get_started(self):
        return self.mgr_started
    
    def get_active(self):
        return self.mgr_active
            
    def get_index_for_plugin_id(self, id):
        idx = 0
        for row in self.plugin_model:
            if row[2] == id:
                return idx
            idx = idx + 1
        return -1
            
    def get_row_for_plugin_id(self, id):
        for row in self.plugin_model:
            if row[2] == id:
                return row
        
    def get_selected_plugin(self):
        (model, path) = self.plugin_tree.get_selection().get_selected()
        if path != None:
            return self.get_plugin_for_id(model[path][2])
            
    def toggle_plugin(self, widget, path):
        plugin = self.get_plugin_for_id(self.plugin_model[path][2])
        if plugin != None:
            key = self.plugin_key + "/" + plugin.id + "/enabled"
            self.conf_client.set_bool(key, not self.conf_client.get_bool(key))
            
    def select_plugin(self, widget):       
        plugin = self.get_selected_plugin()
        if plugin != None:  
            self.selected_id = plugin.id
            self.widget_tree.get_object("PluginNameLabel").set_text(plugin.name)
            self.widget_tree.get_object("DescriptionLabel").set_text(plugin.description)
            self.widget_tree.get_object("AuthorLabel").set_text(plugin.author)
            self.widget_tree.get_object("CopyrightLabel").set_text(plugin.copyright)
            self.widget_tree.get_object("SiteLabel").set_text(plugin.site)
            self.widget_tree.get_object("PreferencesButton").set_sensitive(plugin.has_preferences and plugin.id in self.module_map)
        else:
            self.widget_tree.get_object("PluginNameLabel").set_text("")
            self.widget_tree.get_object("DescriptionLabel").set_text("")
            self.widget_tree.get_object("AuthorLabel").set_text("")
            self.widget_tree.get_object("CopyrightLabel").set_text("")
            self.widget_tree.get_object("SiteLabel").set_text("")
            self.widget_tree.get_object("PreferencesButton").set_sensitive(False)
        
    def get_plugin_for_id(self, id):
        for mod in imported_plugins:
            if mod.id == id:
                return mod
            
    def configure(self, parent_window=None):
        self.plugin_dialog.set_transient_for(parent_window)
        response = self.plugin_dialog.run()
        self.plugin_dialog.hide()
        
    def start(self):
        idx = 0
        self.mgr_started = False
        self.started = []
        for mod in imported_plugins:
            plugin_dir_key = self.plugin_key + "/" + mod.id
            self.conf_client.add_dir(plugin_dir_key, gconf.CLIENT_PRELOAD_NONE)
            key = plugin_dir_key + "/enabled"
            self.conf_client.notify_add(key, self.plugin_changed);
            if self.conf_client.get(key) == None:
                self.conf_client.set_bool(key, True)
            if self.conf_client.get_bool(key):
                instance = self.create_instance(mod, plugin_dir_key)
                self.started.append(instance)
                
    def plugin_changed(self, client, connection_id, entry, args):
        path = entry.key.split("/")
        plugin_id = path[4]
        now_enabled = entry.value.get_bool()
        plugin = self.get_plugin_for_id(plugin_id)
        row = self.get_index_for_plugin_id(plugin_id)
        instance = None
        if plugin_id in self.module_map:
            instance = self.module_map[plugin_id]
        if now_enabled and instance == None:
            instance = self.create_instance(plugin, self.plugin_key + "/" + plugin_id)
            self.started.append(instance)
            if self.mgr_active == True:
                instance.activate() 
                self.activated.append(instance)
        elif not now_enabled and instance != None:
            if instance in self.activated:
                instance.deactivate()
                self.activated.remove(instance)
            self.started.remove(instance)
            del self.module_map[plugin_id]
            instance.destroy()
        self.load_model()
            
    def create_instance(self, module, key):
        instance = module.create(key, self.conf_client, screen=self.screen)
        self.module_map[module.id] = instance
        self.plugin_map[instance] = module
        return instance
    
    def handle_key(self, key, state, post=False):
        for plugin in self.started:
            try :
                if plugin.handle_key(key, state, post):
                    return True
            except AttributeError:
                pass
        return False
    
    def activate(self):
        self.mgr_active = True
        self.activated = []
        for plugin in self.started:
            module = self.plugin_map[plugin]
            plugin.activate()
            self.activated.append(plugin)
    
    def deactivate(self):
        self.mgr_active = False
        for plugin in self.activated:
            module = self.plugin_map[plugin]
            plugin.deactivate()
            self.activated.remove(plugin)
    
    def destroy(self):
        for plugin in self.started:
            self.started.remove(plugin)
            plugin.destroy()
        self.mgr_started = False