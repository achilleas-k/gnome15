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
import sys
import g15_globals as pglobals
import g15_driver as g15driver
import gconf
import traceback
import threading

# Logging
import logging
logger = logging.getLogger("plugins")

imported_plugins = []
plugin_key = "/apps/gnome15/plugins"
            
def list_plugin_dirs(path):
    plugindirs = []
    if os.path.exists(path):
        for dir in os.listdir(path):
            plugin_path = os.path.join(path, dir)
            if os.path.isdir(plugin_path):
                plugindirs.append(os.path.realpath(plugin_path))
    else:
        logger.debug("Plugin path %s does not exist." % path)
    return plugindirs

def get_extra_plugin_dirs():
    plugindirs = []
    if "G15_PLUGINS" in os.environ:
        for dir in os.environ["G15_PLUGINS"].split(":"):
            plugindirs += list_plugin_dirs(dir)
    return plugindirs

for plugindir in get_extra_plugin_dirs() + list_plugin_dirs(os.path.expanduser("~/.gnome15/plugins")) + list_plugin_dirs(pglobals.plugin_dir): 
    plugin_name = os.path.basename(plugindir)
    pluginfiles = [fname[:-3] for fname in os.listdir(plugindir) if fname == plugin_name + ".py"]
    if not plugindir in sys.path:
        sys.path.insert(0, plugindir)
    try :
        for mod in ([__import__(fname) for fname in pluginfiles]):
            imported_plugins.append(mod)
    except Exception as e:
        logger.error("Failed to load plugin module %s. %s" % ( plugindir, str(e) ) )                    
        traceback.print_exc(file=sys.stderr) 
        
def get_module_for_id(id):
    for mod in imported_plugins:
        if mod.id == id:
            return mod
        
def get_supported_models(plugin):
    supported_models = []
    try:
        supported_models += plugin.supported_models
    except:
        supported_models += g15driver.MODELS
    try:
        for p in plugin.unsupported_models:
            supported_models.remove(p)
    except:
        pass        
    return supported_models
        
def is_key_reserved(key, gconf_client):
    if key in [ g15driver.G_KEY_M1, g15driver.G_KEY_M2, g15driver.G_KEY_M3  ]:
        return True
    for mod in imported_plugins:  
        enabled_key = plugin_key + "/" + mod.id + "/enabled"
        if gconf_client.get_bool(enabled_key):  
            try :
                keys = getattr(mod, "reserved_keys")
                if key in keys:
                    return True
            except AttributeError: 
                pass

class G15Plugins():
    def __init__(self, screen):
        self.lock = threading.RLock()
        self.screen = screen
        self.conf_client = gconf.client_get_default()
        self.mgr_started = False
        self.mgr_active = False
        self.started = []
        self.activated = []
        self.conf_client.add_dir(plugin_key, gconf.CLIENT_PRELOAD_NONE)
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
        logger.info("Starting plugin manager")
        self.lock.acquire()
        try : 
            self.mgr_started = False
            self.started = []
            for mod in imported_plugins:
                plugin_dir_key = plugin_key + "/" + mod.id
                self.conf_client.add_dir(plugin_dir_key, gconf.CLIENT_PRELOAD_NONE)
                key = plugin_dir_key + "/enabled"
                self.conf_client.notify_add(key, self.plugin_changed);
                if self.conf_client.get(key) == None:
                    self.conf_client.set_bool(key, False)
                if self.conf_client.get_bool(key):
                    try :
                        instance = self._create_instance(mod, plugin_dir_key)
                        if self.screen.service.driver.get_model_name() in get_supported_models(mod):
                            self.started.append(instance)
                    except Exception as e:
                        self.conf_client.set_bool(key, False)
                        logger.error("Failed to load plugin %s. %s" % ( mod.id, str(e) ) )                    
                        traceback.print_exc(file=sys.stderr) 
        finally:
            self.lock.release()
        logger.info("Started plugin manager")
                
    def plugin_changed(self, client, connection_id, entry, args):
        self.lock.acquire()
        try : 
            path = entry.key.split("/")
            plugin_id = path[4]
            now_enabled = entry.value.get_bool()
            plugin = get_module_for_id(plugin_id)
            instance = None
            if plugin_id in self.module_map:
                instance = self.module_map[plugin_id]
            if now_enabled and instance == None:
                instance = self._create_instance(plugin, plugin_key + "/" + plugin_id)
                self.started.append(instance)
                if self.mgr_active == True:
                    self._activate_instance(instance)
            elif not now_enabled and instance != None:
                if instance in self.activated:
                    instance.deactivate()
                    self.activated.remove(instance)
                self.started.remove(instance)
                del self.module_map[plugin_id]
                instance.destroy()
        finally:
            self.lock.release()
    
    def handle_key(self, key, state, post=False):
        for plugin in self.started:
            can_handle_keys = False
            try :
                getattr(plugin, "handle_key") 
                can_handle_keys = True
            except AttributeError: 
                pass
            if can_handle_keys and plugin.handle_key(key, state, post):
                return True 
        return False
    
    def activate(self, callback = None):
        logger.info("Activating plugins")
        self.lock.acquire()
        try :
            self.mgr_active = True
            self.activated = []
            idx = 0
            for plugin in self.started:
                mod = self.plugin_map[plugin]
                logger.debug("Activating %s" % mod.id)
                self._activate_instance(plugin, callback, idx)
                idx += 1
        finally:
            self.lock.release()
        logger.debug("Activated plugins")
    
    def deactivate(self):
        logger.info("De-activating plugins")
        self.lock.acquire()
        try :
            self.mgr_active = False
            traceback.print_exc(file=sys.stderr)
            for plugin in list(self.activated):
                logger.debug("De-activating %s" % self.plugin_map[plugin].id)
                try :
                    plugin.deactivate()
                except:
                    logger.warning("Failed to deactive plugin properly.")           
                    traceback.print_exc(file=sys.stderr)
                self.activated.remove(plugin)
        finally:
            self.lock.release()
        logger.info("De-activated plugins")
    
    def destroy(self):
        for plugin in self.started:
            self.started.remove(plugin)
            plugin.destroy()
        self.mgr_started = False
        
    '''
    Private
    '''
            
    def _activate_instance(self, instance, callback = None, idx = 0):
        mod = self.plugin_map[instance]
        try : 
            instance.activate()
            self.activated.append(instance)
            if callback != None:
                callback(idx, len(self.started), mod.name)
        except Exception as e:
            logger.error("Failed to activate plugin %s. %s" % ( mod.id, str(e)))   
            self.conf_client.set_bool(plugin_key + "/" + mod.id + "/enabled", False)              
            traceback.print_exc(file=sys.stderr)
        
            
    def _create_instance(self, module, key):
        logger.info("Loading %s" % module.id)
        instance = module.create(key, self.conf_client, screen=self.screen)
        self.module_map[module.id] = instance
        self.plugin_map[instance] = module
        return instance