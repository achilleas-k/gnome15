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
import traceback

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
            
            
        
def get_module_for_id(id):
    for mod in imported_plugins:
        if mod.id == id:
            return mod

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
        
    def has_plugin(self, id):
        return id in self.module_map
        
    def get_plugin(self, id):
        if id in self.module_map:
            return self.module_map[id]
        
    
    def get_started(self):
        return self.mgr_started
    
    def get_active(self):
        return self.mgr_active
            
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
                self.conf_client.set_bool(key, False)
            if self.conf_client.get_bool(key):
                try :
                    instance = self.create_instance(mod, plugin_dir_key)
                    self.started.append(instance)
                except Exception as e:
                    self.conf_client.set_bool(key, False)
                    print "Failed to load plugin %s. %s" % ( mod.id, str(e))                    
                    traceback.print_exc(file=sys.stderr) 
                
    def plugin_changed(self, client, connection_id, entry, args):
        path = entry.key.split("/")
        plugin_id = path[4]
        now_enabled = entry.value.get_bool()
        plugin = get_module_for_id(plugin_id)
        instance = None
        if plugin_id in self.module_map:
            instance = self.module_map[plugin_id]
        if now_enabled and instance == None:
            instance = self.create_instance(plugin, self.plugin_key + "/" + plugin_id)
            self.started.append(instance)
            if self.mgr_active == True:
                self.activate_instance(instance)
        elif not now_enabled and instance != None:
            if instance in self.activated:
                instance.deactivate()
                self.activated.remove(instance)
            self.started.remove(instance)
            del self.module_map[plugin_id]
            instance.destroy()
            
    def activate_instance(self, instance, callback = None, idx = 0):
        mod = self.plugin_map[instance]
        try : 
            instance.activate()
            self.activated.append(instance)
            if callback != None:
                callback(idx, len(self.started))
        except Exception as e:
            print "Failed to activate plugin %s. %s" % ( mod.id, str(e))   
            self.conf_client.set_bool(self.plugin_key + "/" + mod.id + "/enabled", False)              
            traceback.print_exc(file=sys.stderr)
            
    def create_instance(self, module, key):
        instance = module.create(key, self.conf_client, screen=self.screen)
        self.module_map[module.id] = instance
        self.plugin_map[instance] = module
        return instance
    
    def handle_key(self, key, state, post=False):
        for plugin in self.started:
            can_handle_keys = False
            try :
                getattr(plugin, "handle_key") != None 
                can_handle_keys = True
            except AttributeError: 
                pass
            if can_handle_keys and plugin.handle_key(key, state, post):
                return True 
        return False
    
    def activate(self, callback = None):
        self.mgr_active = True
        self.activated = []
        idx = 0
        for plugin in self.started:
            module = self.plugin_map[plugin]
            self.activate_instance(plugin, callback, idx)
            idx += 1
    
    def deactivate(self):
        self.mgr_active = False
        print "Deactivating",self.activated
        for plugin in list(self.activated):
            module = self.plugin_map[plugin]
            print "    ",module.id
            plugin.deactivate()
            self.activated.remove(plugin)
    
    def destroy(self):
        for plugin in self.started:
            self.started.remove(plugin)
            plugin.destroy()
        self.mgr_started = False