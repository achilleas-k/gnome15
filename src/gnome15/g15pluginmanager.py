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

"""
This module handles the loading, starting, stopping and general management of 
plugins.

There are two types of plugins supported :-

Device Plugins        - These are plugins that require an actual keyboard device
                        to work. For example, they might add a new screen,
                        or listen for key events. There may be one instance of
                        each plugin per connected device.
                        
Global Plugins        - These are plugins that are not tied to any specific device.
                        Only one instance may be running at a time.
                        
Plugins are looked for in a number of locations.

* g15globals.plugin_dir              - This is where official plugins installed with Gnome15 reside
* $XDG_DATA_HOME/gnome15/plugins     - This is where users can put their own local plugins
* $XDG_CONFIG_HOME/gnome15/plugins   - This is a deprecated place where users can put
                                       their own local plugins. It will be removed on a future
                                       version of Gnome15
* $G15_PLUGINS_DIR                   - If it exists allows custom locations to be added
* g15pluginmanager.extra_plugin_dirs - Allows other plugins to dynamically register new plugin
                                       locations
                        
The lifecycle of all plugins consists of 5 stages. 

1. Loading - When the python module is loaded. This happens to all plugins,
regardless of whether they are enabled or not. Any plugins that fail this
stage will not be visible.

2. Initialise - This is when the plugin instance is created. All enabled
plugins will go through this stage *once*. If a plugin is de-activated, and
then re-activated, it will not be re-initialised unless the device it is
attached to is completely stopped (not necessarily because of shutdown).

3. Activation - Occurs during start-up of all enabled plugins. If a plugin is
de-activated, and then re-activated. The activate() function is called again.

4. De-activation - Occurs when the plugin is de-activated for some reason. 
This may be because the user disabled it, or if the device is attached to is
stopped, or when Gnome15 itself is shutting down.

5. Destruction - Occurs when the device the plugin is attached to is stopped,
or if Gnome15 itself is closing down. 

"""
 
import os.path
import sys
import g15globals
import g15driver
import g15actions
import gconf
import threading

# Logging
import logging
logger = logging.getLogger("plugins")

imported_plugins = []

"""
This list may be added to dynamically to add new plugin locations
"""
extra_plugin_dirs = []

# Plugin manager states
UNINITIALISED = 0
STARTING = 1
STARTED = 2
ACTIVATING = 3
ACTIVATED = 4
DEACTIVATING = 5
DEACTIVATED = 6
DESTROYING = 7
            
def list_plugin_dirs(path):
    """
    List all plugin directories in a given path.
    
    Keyword arguments:
    path -- path to look for plugins
    """ 
    plugindirs = []
    if os.path.exists(path):
        for p_dir in os.listdir(path):
            plugin_path = os.path.join(path, p_dir)
            if os.path.isdir(plugin_path):
                plugindirs.append(os.path.realpath(plugin_path))
    else:
        logger.debug("Plugin path %s does not exist." % path)
    return plugindirs

def get_extra_plugin_dirs():    
    """
    Get a list of all directories plugin directories may be found in. This
    will included any dynamically registered using the 
    g15pluginmanager.extra_plugin_dirs list, and all paths that are found
    in the G15_PLUGINS environment variable.
    """
    plugindirs = []
    plugindirs += extra_plugin_dirs
    if "G15_PLUGINS" in os.environ:
        for p_dir in os.environ["G15_PLUGINS"].split(":"):
            plugindirs += list_plugin_dirs(p_dir)
    return plugindirs 
        
def get_module_for_id(module_id):
    """
    Get a plugin module given it's ID.
    
    Keyword arguments:
    module_id -- plugin module ID
    """
    for mod in imported_plugins:
        if mod.id == module_id:
            return mod
        
def get_supported_models(plugin_module):    
    """
    Get a list of models that a plugin supports. This takes into account
    the supported_models and unsupported_models attributes to provide a list
    of the actual model ID's that can be used. See g15driver.MODLES and other
    contants.
    
    Keyword arguments:
    plugin_module -- plugin module instance
    """
    supported_models = []
    try:
        supported_models += plugin_module.supported_models
    except Exception as e:
        logger.debug("Error while reading supported models", exc_info = e)
        supported_models += g15driver.MODELS
    try:
        for p in plugin_module.unsupported_models:
            supported_models.remove(p)
    except Exception as e:
        logger.debug("Error while reading unsupported models", exc_info = e)
        pass        
    return supported_models

def is_needs_network(plugin_module):
    """
    Get if the provided plugin_module instance requires the network to be available.
    If the plugin doesn't declare this, it is assumed to be False
    
    Keyword arguments:
    plugin_module -- plugin module instance
    """
    try :
        return plugin_module.needs_network
    except AttributeError as e:
        logger.debug("Error when reading need_network attribute", exc_info = e)
        pass 
    return False

def is_default_enabled(plugin_module):
    """
    Get if the provided plugin_module instance should be enabled by default.
    This is used to determine a basic list of plugins to get the user going
    when Gnome15 is first installed.
    
    Keyword arguments:
    plugin_module -- plugin module instance
    """
    try :
        return plugin_module.default_enabled
    except AttributeError as e:
        logger.debug("Error when reading default_enabled attribute", exc_info = e)
        pass 
    return False

def is_global_plugin(plugin_module):
    """
    Get if the provided plugin_module instance should is a "Global Plugin".
    
    Keyword arguments:
    plugin_module -- plugin module instance
    """
    try :
        return plugin_module.global_plugin
    except AttributeError as e:
        logger.debug("Error when reading global_plugin attribute", exc_info = e)
        pass 
    return False

def is_passive_plugin(plugin_module):
    """
    Get if the provided plugin_module instance should is a "Passive Plugin".
    Passive plugins just provide additional classes and functions, probably
    for another plugin. They are always enabled. 
    
    Keyword arguments:
    plugin_module -- plugin module instance
    """
    try :
        return plugin_module.passive
    except AttributeError as e:
        logger.debug("Error when reading passive attribute", exc_info = e)
        pass 
    return False
 
def get_actions(plugin_module, device):
    """
    Get a dictionary of all the "Actions" this plugin uses. The key is
    the action ID, and the value of a textual description of what the action
    is used for in this plugin.
    
    Keyword arguments:
    plugin_module -- plugin module instance
    device        -- device the plugins are for
    """
    
    # First look for actions for the specific device
    if device is not None:
        try:
            return getattr(plugin_module, 'actions_%s' % device.model_id)
        except AttributeError as e:
            logger.debug("Error when reading actions_%s attributes", device.model_id, exc_info = e)
            pass 
    
    try :
        return plugin_module.actions
    except AttributeError as e:
        logger.debug("Error when reading actions attribute", exc_info = e)
        pass 
    
    return {}



"""
Loads the python modules for all plugins for all known locations. This is done
in two phases.

Firstly, the paths of all plugins are added to the python search path.

Secondly, all of these directories are scanned for python files with the same
name as the directory they are in. Each one of these is the main plugin module.

TODO - These should really be using __init__.py
"""
all_plugin_directories = get_extra_plugin_dirs() + \
                         list_plugin_dirs(os.path.expanduser("~/.gnome15/plugins")) + \
                         list_plugin_dirs(os.path.join(g15globals.user_config_dir, "plugins")) + \
                         list_plugin_dirs(os.path.join(g15globals.user_data_dir, "plugins")) + \
                         list_plugin_dirs(g15globals.plugin_dir)
            
# Phase 1
for plugindir in all_plugin_directories:
    if not plugindir in sys.path:
        sys.path.insert(0, plugindir)
       
# Phase 2
for plugindir in all_plugin_directories: 
    plugin_name = os.path.basename(plugindir)
    pluginfiles = [fname[:-3] for fname in os.listdir(plugindir) if fname == plugin_name + ".py"]
    if not plugindir in sys.path:
        sys.path.insert(0, plugindir)
    try :
        for mod in ([__import__(fname) for fname in pluginfiles]):
            imported_plugins.append(mod)
            # TODO - we need to be registering actions for a particular device
            actions = get_actions(mod, None)
            for a in actions:
                if not a in g15actions.actions:
                    g15actions.actions.append(a)
    except Exception as e:
        logger.error("Failed to load plugin module %s.", plugindir, exc_info = e)


class G15Plugins():
    """
    Managed a set of plugins for either the global set, or the per device
    set (in this case the screen argument must be provided).
    
    In total there will be n+1 instances of this, where n is the number of
    connected and enabled devices.
    """
    def __init__(self, screen, service=None, network_manager = None):
        """
        Create a new plugin manager either for the provided device (screen),
        or globally (when screen is None)
         
        Keyword arguments:
        screen -- screen this plugin managed is attached to, or None for global plugins
        service -- the service this plugin manager is managed by
        """
        self.network_manager = network_manager
        self.lock = threading.RLock()
        self.screen = screen
        self.service = service if service is not None else screen.service
        self.conf_client = self.service.conf_client
        self.started = []
        self.activated = []
        self.conf_client.add_dir(self._get_plugin_key(), gconf.CLIENT_PRELOAD_NONE)
        self.module_map = {}
        self.plugin_map = {}
        self.state = UNINITIALISED
        
    def is_activated(self):
        """
        Get if the plugin manager is currently fully ACTIVATED.
        """
        return self.state == ACTIVATED
        
    def is_started(self):
        """
        Get if the plugin manager is currently fully STARTED or in any ACTIVE
        state.
        """
        return self.is_in_active_state() or self.state == STARTED
        
    def is_in_active_state(self):
        """
        Get if the plugin manager is currently in a state where it is either
        fully ACTIVATED, or partially activated (ACTIVATING, DEACTIVATING).
        """
        return self.state in [ ACTIVATED, DEACTIVATING, ACTIVATING ]
        
    def is_in_started_state(self):
        """
        Get if the plugin manager is currently in a state where it is either
        fully STARTED (or any activated state) or partially STARTED (STARTING, STOPPING)
        """
        return self.is_in_active_state() or self.state in [ STARTED, STARTING, DESTROYING ]
        
    def has_plugin(self, module_id):
        """
        Get if the plugin manager contains a plugin install with the 
        given plugin module ID.
         
        Keyword arguments:
        module_id -- plugin module ID to search for
        """
        return module_id in self.module_map
    
    def get_plugin(self, module_id):
        """
        Get the plugin instance given the plugin module's ID
        
        Keyword arguments:
        id -- plugin module ID to search for
        """
        if module_id in self.module_map:
            return self.module_map[module_id]
    
    def start(self):
        """
        Start all plugins that are currently enabled.
        """
        self.lock.acquire()
        try : 
            self.state = STARTING
            self.started = []
            added = []
            for mod in imported_plugins:
                plugin_dir_key = self._get_plugin_key(mod.id)
                if mod.id in added:
                    logger.warn("Same plugin with ID of %s is already loaded. Only the first copy will be used." % mod.id) 
                else:
                    self.conf_client.add_dir(plugin_dir_key, gconf.CLIENT_PRELOAD_NONE)
                    key = "%s/enabled" % plugin_dir_key
                    self.conf_client.notify_add(key, self._plugin_changed)
                    if (self.screen is None and is_global_plugin(mod)) or \
                       (self.screen is not None and not is_global_plugin(mod)):
                        
                        # If first use, set the default enabled state
                        if self.conf_client.get(key) == None:
                            self.conf_client.set_bool(key, is_default_enabled(mod))
                            
                        # Only actually activate if the plugin is not passive and the network
                        # is in the right state
                        
                        if self.conf_client.get_bool(key) and \
                          not is_passive_plugin(mod):
                            try :
                                instance = self._create_instance(mod, plugin_dir_key)
                                if self.screen is None or self.screen.driver.get_model_name() in get_supported_models(mod):
                                    self.started.append(instance)
                            except Exception as e:
                                self.conf_client.set_bool(key, False)
                                logger.error("Failed to load plugin %s.", mod.id, exc_info = e)
            self.state = STARTED
        except Exception as a:
            self.state = UNINITIALISED
            logger.debug("Error when starting plugins", exc_info = a)
            raise a 
        finally:
            self.lock.release()
        logger.info("Started plugin manager")
    
    def handle_key(self, key, state, post=False):
        """
        Pass the provided key event to all plugins. For each key event, this
        will be called twice, once with post=False, and once with post=True
        
        Keyword arguments:
        key -- key name
        state -- key state
        post -- post processing stage 
        """
        for plugin in self.started:
            can_handle_keys = False
            try :
                getattr(plugin, "handle_key") 
                can_handle_keys = True
            except AttributeError as e:
                logger.debug("Error when reading handle_key attribute", exc_info = e)
                pass
            if can_handle_keys and plugin.handle_key(key, state, post):
                logger.info("Plugin %s handled key %s (%d), %s" % (str(plugin), str(key), state, str(post)))
                return True 
        return False
    
    def activate(self, callback=None, plugin=None):
        """
        Activate all plugins that currently started.
        
        Keyword arguments:
        callback      --     callback function to invoke when each invididual plugin
                            is activated. This is used for the progress bar during initial startup. 
        plugin        --    If None, all started are activated. If a list, 
                            those plugins are activated. If a single plugin, 
                            that plugin is activated. If plugin is either list
                            or None, the state of the plugin manager will also
                            be changed
        """
        
        if plugin is None or isinstance(plugin, list):
            logger.info("Activating plugins")
            self.lock.acquire()
            try :
                self.state = ACTIVATING
                self.activated = []
                idx = 0
                for plugin in plugin if isinstance(plugin, list) else self.started:
                    mod = self.plugin_map[plugin]
                    
                    # Only actually activate if the plugin is not passive and the network
                    # is in the right state
                        
                    needs_net = is_needs_network(mod)
                    if not needs_net or ( needs_net and \
                            self.network_manager.is_network_available() ):
                        self._activate_instance(plugin, callback, idx)
                        
                    idx += 1           
                self.state = ACTIVATED
            except Exception as e:           
                self.state = STARTED
                logger.debug("Error while activating plugin", exc_info = e)
                raise e     
            finally:
                self.lock.release()
            logger.debug("Activated plugins")
        else:
            self._activate_instance(plugin, callback, 0)
            
    
    def deactivate(self, plugin=None):
        """
        De-activate plugins that are currently activated.
        
        Keyword arguments:
        plugin        --    If None, all activated are deactivated. If a list, 
                            those plugins are deactivated. If a single plugin, 
                            that plugin is deactivated. If plugin is either list
                            or None, the state of the plugin manager will also
                            be changed
        """
        if plugin is None or isinstance(plugin, list):
            logger.info("De-activating plugins")
            self.lock.acquire()
            try :
                self.state = DEACTIVATING
                for plugin in plugin if isinstance(plugin, list) else list(self.activated):
                    self._deactivate_instance(plugin)
            finally:
                self.state = DEACTIVATED
                self.lock.release()
            logger.info("De-activated plugins")
        else:
            self._deactivate_instance(plugin)
    
    def destroy(self):
        """
        Destroy all plugins that are currently started.
        """
        try :
            self.state = DESTROYING
            for plugin in self.started:
                self.state = DESTROYING
                self.started.remove(plugin)
                plugin.destroy()
        finally:
            self.state = UNINITIALISED
        
    '''
    Private
    ''' 
    def _deactivate_instance(self, plugin):
        mod = self.plugin_map[plugin]
        logger.debug("De-activating %s" % mod.id)
        if not plugin in self.activated:
            raise Exception("%s is not activated" % mod.id)
        try :
            plugin.deactivate()
        except Exception as e:
            logger.warning("Failed to deactive plugin properly.", exc_info = e)
        finally:                    
            mod_id = self.plugin_map[plugin].id
            if mod_id in self.service.active_plugins:
                del self.service.active_plugins[mod_id]
        self.activated.remove(plugin)
        
    def _get_plugin_key(self, subkey=None):
        folder = self.screen.device.uid if self.screen is not None else "global"
        if subkey:
            return "/apps/gnome15/%s/plugins/%s" % (folder, subkey)
        else:
            return "/apps/gnome15/%s/plugins" % folder
                
    def _plugin_changed(self, client, connection_id, entry, args):
        self.lock.acquire()
        if self.screen is not None:
            self.screen._check_active_plugins()
        try : 
            path = entry.key.split("/")
            plugin_id = path[5]
            now_enabled = entry.value.get_bool()
            plugin = get_module_for_id(plugin_id)
            
            # Check network state, and prevent enable if not in right state
            needs_net = is_needs_network(plugin)
            if now_enabled and needs_net and not self.network_manager.is_network_available():
                now_enabled = False 
            
            instance = None
            if plugin_id in self.module_map:
                instance = self.module_map[plugin_id]
                                
            if not is_passive_plugin(plugin):
                if now_enabled and instance == None:
                    instance = self._create_instance(plugin, self._get_plugin_key(plugin_id))
                    self.started.append(instance)
                    if self.is_in_active_state() == True:
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
            
    def _activate_instance(self, instance, callback=None, idx=0):
        mod = self.plugin_map[instance] 
        logger.info("Activating %s" % mod.id)
        try :             
            if self._is_single_instance(mod):
                logger.info("%s may only be run once, checking if there is another instance" % mod.id)
                if  mod.id in self.service.active_plugins:
                    raise Exception("Plugin may %s only run on one device at a time." % mod.id)
            if callback != None:
                callback(idx, len(self.started), mod.name)
            instance.activate()
            self.service.active_plugins[mod.id] = True
            self.activated.append(instance)
        except Exception as e:
            logger.error("Failed to activate plugin %s.", mod.id, exc_info = e)
            self.conf_client.set_bool(self._get_plugin_key("%s/enabled" % mod.id), False)              
        
    def _is_single_instance(self, module):
        try :
            return module.single_instance
        except AttributeError as e:
            logger.debug("Error while reading single_instance attribute", exc_info = e)
            pass
        return False
            
    def _create_instance(self, module, key):
        logger.info("Loading %s" % module.id)
        if self.screen is not None:
            instance = module.create(key, self.conf_client, screen=self.screen)
        else:
            instance = module.create(key, self.conf_client, service=self.service)
        self.module_map[module.id] = instance
        self.plugin_map[instance] = module
        logger.info("Loaded %s" % module.id)
        return instance
    
