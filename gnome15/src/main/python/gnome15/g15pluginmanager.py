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
import g15globals as pglobals
import g15driver as g15driver
import gconf
import g15util
import traceback
import threading

# Logging
import logging
logger = logging.getLogger("plugins")

imported_plugins = []
            
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

for plugindir in get_extra_plugin_dirs() + list_plugin_dirs(os.path.expanduser("~/.gnome15/plugins")) +  \
            list_plugin_dirs(os.path.expanduser("~/.config/gnome15/plugins")) + list_plugin_dirs(pglobals.plugin_dir): 
    plugin_name = os.path.basename(plugindir)
    pluginfiles = [fname[:-3] for fname in os.listdir(plugindir) if fname == plugin_name + ".py"]
    if not plugindir in sys.path:
        sys.path.insert(0, plugindir)
    try :
        for mod in ([__import__(fname) for fname in pluginfiles]):
            imported_plugins.append(mod)
    except Exception as e:
        logger.error("Failed to load plugin module %s. %s" % (plugindir, str(e)))
        if logger.level == logging.DEBUG:                  
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

def is_default_enabled(plugin_module):
    try :
        return plugin_module.default_enabled
    except AttributeError: 
        pass 
    return False
 
def get_actions(plugin_module):
    try :
        return plugin_module.actions
    except AttributeError: 
        pass 
    return {}

class G15Plugins():
    def __init__(self, screen):
        self.lock = threading.RLock()
        self.screen = screen
        self.conf_client = screen.conf_client
        self.mgr_started = False
        self.mgr_active = False
        self.started = []
        self.activated = []
        self.conf_client.add_dir(self._get_plugin_key(), gconf.CLIENT_PRELOAD_NONE)
        self.module_map = {}
        self.plugin_map = {}
        
    def _get_plugin_key(self, subkey = None):
        if subkey:
            return "/apps/gnome15/%s/plugins/%s" % ( self.screen.device.uid, subkey )
        else:
            return "/apps/gnome15/%s/plugins" % self.screen.device.uid
        
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
        self.lock.acquire()
        try : 
            self.mgr_started = False
            self.started = []
            for mod in imported_plugins:
                plugin_dir_key = self._get_plugin_key(mod.id) 
                self.conf_client.add_dir(plugin_dir_key, gconf.CLIENT_PRELOAD_NONE)
                key = "%s/enabled" % plugin_dir_key
                self.conf_client.notify_add(key, self._plugin_changed);
                if self.conf_client.get(key) == None:
                    self.conf_client.set_bool(key, is_default_enabled(mod))
                if self.conf_client.get_bool(key):
                    try :
                        instance = self._create_instance(mod, plugin_dir_key)
                        if self.screen.driver.get_model_name() in get_supported_models(mod):
                            self.started.append(instance)
                    except Exception as e:
                        self.conf_client.set_bool(key, False)
                        logger.error("Failed to load plugin %s. %s" % (mod.id, str(e)))                    
                        traceback.print_exc(file=sys.stderr) 
        finally:
            self.lock.release()
        logger.info("Started plugin manager")
                
    def _plugin_changed(self, client, connection_id, entry, args):
        self.lock.acquire()
        try : 
            path = entry.key.split("/")
            plugin_id = path[5]
            now_enabled = entry.value.get_bool()
            plugin = get_module_for_id(plugin_id)
            instance = None
            if plugin_id in self.module_map:
                instance = self.module_map[plugin_id]
            if now_enabled and instance == None:
                instance = self._create_instance(plugin, self._get_plugin_key(plugin_id))
                self.started.append(instance)
                if self.mgr_active == True:
                    self._activate_instance(instance)
            elif not now_enabled and instance != None:
                if instance in self.activated:
                    self._deactivate_instance(instance)
                if instance in self.started:
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
                logger.info("Plugin %s handled key %s (%d), %s" % (str(plugin), str(key), state, str(post)))
                return True 
        return False
    
    def activate(self, callback=None):
        logger.info("Activating plugins")
        self.lock.acquire()
        try :
            self.mgr_active = True
            self.activated = []
            idx = 0
            for plugin in self.started:
                mod = self.plugin_map[plugin]
                self._activate_instance(plugin, callback, idx)
                idx += 1
        finally:
            self.lock.release()
        logger.debug("Activated plugins")
        
    def _deactivate_instance(self, plugin):
        mod = self.plugin_map[plugin]
        logger.debug("De-activating %s" % mod.id)
        if not plugin in self.activated:
            raise Exception("%s is not activated" % mod.id)
        try :
            plugin.deactivate()
        except:
            logger.warning("Failed to deactive plugin properly.")           
            traceback.print_exc(file=sys.stderr)
        finally:                    
            mod_id = self.plugin_map[plugin].id
            if mod_id in self.screen.service.active_plugins:
                del self.screen.service.active_plugins[mod_id]
        self.activated.remove(plugin)
    
    def deactivate(self):
        logger.info("De-activating plugins")
        self.lock.acquire()
        try :
            self.mgr_active = False
            for plugin in list(self.activated):
                self._deactivate_instance(plugin)
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
            
    def _activate_instance(self, instance, callback=None, idx=0):
        mod = self.plugin_map[instance] 
        logger.info("Activating %s" % mod.id)
        try :             
            if self._is_single_instance(mod):
                logger.info("%s may only be run once, checking if there is another instance" % mod.id)
                if  mod.id in self.screen.service.active_plugins:
                    raise Exception("Plugin may %s only run on one device at a time." % mod.id)
            instance.activate()
            self.screen.service.active_plugins[mod.id] = True
            self.activated.append(instance)
            if callback != None:
                callback(idx, len(self.started), mod.name)
        except Exception as e:
            logger.error("Failed to activate plugin %s. %s" % (mod.id, str(e)))   
            self.conf_client.set_bool(self._get_plugin_key("%s/enabled" % mod.id ), False)              
            traceback.print_exc(file=sys.stderr)
        
    def _is_single_instance(self, module):
        try :
            return module.single_instance
        except AttributeError: 
            pass
        return False
            
    def _create_instance(self, module, key):
        logger.info("Loading %s" % module.id)
        instance = module.create(key, self.conf_client, screen=self.screen)
        self.module_map[module.id] = instance
        self.plugin_map[instance] = module
        logger.info("Loaded %s" % module.id)
        return instance
    