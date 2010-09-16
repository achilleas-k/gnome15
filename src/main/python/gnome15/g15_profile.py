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
 
import gconf
import time
 
active_profile = None

conf_client = gconf.client_get_default()
conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
conf_client.add_dir("/apps/gnome15/profiles", gconf.CLIENT_PRELOAD_NONE)

def get_profiles():
    profiles = []
            
    profile_list = conf_client.get_list("/apps/gnome15/profile_list", gconf.VALUE_INT)
    if profile_list != None:
        for profile in profile_list:
            profiles_key = "/apps/gnome15/profiles/" + str(profile)
            conf_client.add_dir(profiles_key, gconf.CLIENT_PRELOAD_NONE)
            name = conf_client.get_string(profiles_key +  "/name")
            profiles.append(G15Profile(name, profile))
            
    return profiles

def create_default():
    profile_list = conf_client.get_list("/apps/gnome15/profile_list", gconf.VALUE_INT)
    if profile_list == None:
        profile_list = []
    if not 0 in profile_list:
        create_profile(G15Profile("Default", id=0))

def create_profile(profile):
    profile_list = conf_client.get_list("/apps/gnome15/profile_list", gconf.VALUE_INT)
    if profile_list == None:
        profile_list = []
    if profile.id == -1:
        profile.id = int(time.time())
    dir_key = "/apps/gnome15/profiles/" + str(profile.id)
    conf_client.add_dir(dir_key, gconf.CLIENT_PRELOAD_NONE)
    profile_list.append(profile.id)
    conf_client.set_list("/apps/gnome15/profile_list", gconf.VALUE_INT, profile_list)
    conf_client.set_string(dir_key + "/name", profile.name)
    
def get_profile(id):
    dir_key = "/apps/gnome15/profiles/" + str(id)
    return G15Profile(conf_client.get_string(dir_key + "/name"), id)    

def get_active_profile():
    val= conf_client.get("/apps/gnome15/active_profile")
    if val != None:
        return get_profile(val.get_int())
      
def get_default_profile():
    return get_profile(0)
            
class G15Macro:
    
    def __init__(self, profile, memory, key):
        
        self.key_dir = profile.profile_dir + "/keys/m" + str(memory) + "/" + str(key)
            
        self.memory = memory
        self.key = key
        self.name = conf_client.get_string(self.key_dir + "/name")
        self.profile = profile
        self.macro = conf_client.get_string(self.key_dir + "/macro")
        
    def save(self):
        conf_client.set_string(self.key_dir + "/name", self.name)
        
    def delete(self):
        conf_client.remove_dir(self.key_dir)
        key_list = conf_client.get_list(profle.profile_dir + "/key_list_" + str(memory), gconf.VALUE_INT)
        key_list.remove(self.key)
        conf_client.set_list(profle.profile_dir + "/key_list_" + str(memory), gconf.VALUE_INT, key_list)
 
class G15Profile():
    
    def __init__(self, name, id=-1):
        self.id = id
        self.name = name;
        self.macros = []
        self.profile_dir = "/apps/gnome15/profiles/" + str(self.id)
        for j in range(1, 4):
            conf_client.add_dir(self.profile_dir + "/keys/m" + str(j), gconf.CLIENT_PRELOAD_NONE)
        self.load()
        
    def get_default(self):
        return self.id == 0
        
    def save(self):
         
        if self.window_name == None:
            self.window_name = ""
        conf_client.set_string(self.profile_dir + "/window_name", self.window_name)
        conf_client.set_bool(self.profile_dir + "/activate_on_focus", self.activate_on_focus)
        conf_client.set_bool(self.profile_dir + "/send_delays", self.send_delays)
        
    def delete(self):
        conf_client.remove_dir(self.profile_dir)
        profile_list = conf_client.get_list("/apps/gnome15/profile_list", gconf.VALUE_INT)
        if profile_list != None:
            profile_list.remove(self.id)
        conf_client.set_list("/apps/gnome15/profile_list", gconf.VALUE_INT, profile_list)
        
    def delete_macro(self, memory, key):
        key_dir = self.profile_dir + "/keys/m" + str(memory) + "/" + str(key)
        conf_client.remove_dir(key_dir)
        key_list = conf_client.get_list(self.profile_dir + "/key_list_" + str(memory), gconf.VALUE_INT)
        if key in key_list:
            key_list.remove(key);
        conf_client.set_list(self.profile_dir + "/key_list_" + str(memory), gconf.VALUE_INT, key_list)
        
    def create_macro(self, memory, key, name, macro):
        key_list = conf_client.get_list(self.profile_dir + "/key_list_" + str(memory), gconf.VALUE_INT)
        if key in key_list:
            self.delete_macro(memory, key)  
            key_list.remove(key)
                      
        key_list.append(key)
        conf_client.set_list(self.profile_dir + "/key_list_" + str(memory), gconf.VALUE_INT, key_list)
        keys_dir = self.profile_dir + "/keys/m" + str(memory)
        key_dir = keys_dir + "/" + str(key);
        conf_client.add_dir(key_dir, gconf.CLIENT_PRELOAD_NONE)
        conf_client.set_string(key_dir + "/name", name)
        conf_client.set_string(key_dir + "/macro", macro)
        new_macro = G15Macro(self, memory, key)
        self.macros[memory - 1].append(new_macro)
        return new_macro
    
    def get_macro(self, memory, key):
        key_list = conf_client.get_list(self.profile_dir + "/key_list_" + str(memory), gconf.VALUE_INT)
        if key in key_list:
            return G15Macro(self, memory, key)
        
    def make_active(self):
        conf_client.set_int("/apps/gnome15/active_profile", self.id)
        
    def load(self):        
        self.macros = []
        
        self.activate_on_focus = conf_client.get_bool(self.profile_dir + "/activate_on_focus")
        self.window_name = conf_client.get_string(self.profile_dir + "/window_name")
        if self.window_name == None:
            self.window_name = ""
        self.send_delays = conf_client.get_bool(self.profile_dir + "/send_delays")
        for j in range(1, 4):
            key_list = conf_client.get_list(self.profile_dir + "/key_list_" + str(j), gconf.VALUE_INT)
            keys_dir = self.profile_dir + "/keys/m" + str(j)
            memory_macros = []
            self.macros.append(memory_macros)
            for key in key_list:
                key_dir = keys_dir + "/" + str(key)
                conf_client.add_dir(key_dir, gconf.CLIENT_PRELOAD_NONE)
                memory_macros.append(G15Macro(self, j, key))


# Create the default
create_default()