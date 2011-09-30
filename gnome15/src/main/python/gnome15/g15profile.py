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
import g15util
import g15devices
import g15uinput
import ConfigParser
import codecs
import os.path
import errno
import pyinotify
import logging
import uinput
import re
 
logger = logging.getLogger("macros")
active_profile = None
conf_client = gconf.client_get_default()

# Create macro profiles directory
conf_dir = os.path.expanduser("~/.config/gnome15/macro_profiles")
try:
    os.makedirs(conf_dir)
except OSError as exc: # Python >2.5
    if exc.errno == errno.EEXIST:
        pass
    else: 
        raise
    
    
'''
Watch for changes in macro configuration directory.
Observers can add a callback function to profile_listeners
to be informed when macro profiles change
'''

profile_listeners = []

wm = pyinotify.WatchManager()
mask = pyinotify.IN_DELETE | pyinotify.IN_MODIFY | pyinotify.IN_CREATE | pyinotify.IN_ATTRIB  # watched events

class EventHandler(pyinotify.ProcessEvent):
    
    def _get_profile_ids(self, event):
        path = os.path.basename(event.pathname)
        device_uid = os.path.basename(os.path.dirname(event.pathname))
        if path.endswith(".macros") and not path.startswith("."):
            id_no = path.split(".")[0]
            if id_no.isdigit():
                return ( int(id_no), device_uid )
    
    def _notify(self, event):
        ids = self._get_profile_ids(event)
        if ids:
            for profile_listener in profile_listeners:
                profile_listener(ids[0], ids[1])
        
    def process_IN_MODIFY(self, event):
        self._notify(event)
        
    def process_IN_CREATE(self, event):
        self._notify(event)
        
    def process_IN_ATTRIB(self, event):
        self._notify(event)

    def process_IN_DELETE(self, event):
        self._notify(event)

notifier = pyinotify.ThreadedNotifier(wm, EventHandler())
notifier.name = "PyInotify"
notifier.setDaemon(True)
notifier.start()
wdd = wm.add_watch(conf_dir, mask, rec=True)

def get_profiles(device):
    '''
    Get list of all configured macro profiles
    
    Keyword arguments:
    '''
    profiles = []
    for profile in os.listdir(_get_profile_dir(device)):
        if not profile.startswith(".") and profile.endswith(".macros"):
            id = profile.split(".")[0]
            if id.isdigit():
                profiles.append(G15Profile(device, int(id)))
    return profiles

def _get_profile_dir(device):
    return "%s/%s" % (conf_dir, device.uid)

def create_default(device):
    if not get_profile(device, 0):
        logger.info("No default macro profile. Creating one")
        default_profile = G15Profile(device, id = 0)
        default_profile.name = "Default"
        default_profile.device = device
        default_profile.activate_on_focus = True
        create_profile(default_profile)

def create_profile(profile):
    if profile.id == -1:
        profile.id = int(time.time())
    logger.info("Creating profile %d, %s" % ( profile.id, profile.name ))
    profile.save()
    
def get_profile(device, id):
    path = "%s/%s/%d.macros" % ( conf_dir, device.uid, id )
    if os.path.exists(path):
        return G15Profile(device, id);

def get_active_profile(device):
    val= conf_client.get("/apps/gnome15/%s/active_profile" % device.uid)
    if val != None:
        return get_profile(device, val.get_int())
    else:
        return get_default_profile(device)
      
def get_default_profile(device):
    return get_profile(device, 0)

def get_keys_from_key(key_list_key):
    return key_list_key.split("_")

def get_keys_key(keys):
    return "_".join(keys)

'''
Macro types
'''

MACRO_COMMAND="command"
MACRO_SIMPLE="simple"
MACRO_SCRIPT="script"
MACRO_MAPPED_TO_KEY="mapped-to-key"
            
class G15Macro:
    
    def __init__(self, profile, memory, key_list_key):
        self.keys = key_list_key.split("_")
        self.key_list_key = key_list_key
        self.memory = memory
        self.profile = profile
        self.name = ""
        self.macro = ""
        self.mapped_key = ""
        self.map_type = g15uinput.MOUSE
        self.type = MACRO_SCRIPT
        self.command = ""
        self.simple_macro = ""
        section_name = "m%d" % self.memory
        if not self.profile.parser.has_section(section_name):
            self.profile.parser.add_section(section_name)
    
    def __ne__(self, macro):
        return not self.__eq__(macro)
    
    def __eq__(self, macro):
        return macro is not None and self.profile.id == macro.profile.id and self.key_list_key == macro.key_list_key
            
    def compare(self, o):
        return self._get_total(self.keys) - self._get_total(o.keys)
    
    def _get_total(self, keys):
        t = 0
        for i in range(0, len(keys)):
            if keys[i] != "":
                t += self._get_key_val(keys[i])
        return t
            
    def _get_key_val(self, key):
        if(key == ""):
            return 0        
        elif re.match("g[0-9]+.*", key):
            return int(key[1:])
        elif re.match("m[1-3]", key):
            return 50 + int(key[1:])
        elif key == "mr":
            return 55        
        elif re.match("l[0-9]+.*", key):
            return 100 + int(key[1:])
        else:
            ki = self.profile.device.get_key_index(key)
            if ki is None:
                ki = 200
            return 200 + ki
        
    def get_uinput_code(self):
        return uinput.capabilities.CAPABILITIES[self.mapped_key] if self.mapped_key in uinput.capabilities.CAPABILITIES else 0
    
    def set_keys(self, keys):
        section_name = "m%d" % self.memory     
        self.profile._delete_key(section_name, self.key_list_key)
        self.keys = keys
        self.key_list_key = get_keys_key(keys)
        self.save()
        
    def _remove_option(self, section_name, option_key):
        if self.profile.parser.has_option(section_name, option_key):
            self.profile.parser.remove_option(section_name, option_key)
        
    def _store(self): 
        section_name = "m%d" % self.memory
        self.profile.parser.set(section_name, "keys_" + self.key_list_key + "_name", self._encode_val(self.name))
        self.profile.parser.set(section_name, "keys_" + self.key_list_key + "_macro", self._encode_val(self.macro))
        self.profile.parser.set(section_name, "keys_" + self.key_list_key + "_mappedkey", self.mapped_key)
        self.profile.parser.set(section_name, "keys_" + self.key_list_key + "_maptype", self.map_type)
        self.profile.parser.set(section_name, "keys_" + self.key_list_key + "_type", self.type)
        self.profile.parser.set(section_name, "keys_" + self.key_list_key + "_command", self._encode_val(self.command))
        self.profile.parser.set(section_name, "keys_" + self.key_list_key + "_simplemacro", self._encode_val(self.simple_macro))
        
    def _encode_val(self, val):
        val = val.encode('utf8')
        return val
    
    def _decode_val(self, val):
        return val
        
    def _load(self):
        self.type = self._get("type", MACRO_SCRIPT)
        self.command = self._decode_val(self._get("command", ""))
        self.simple_macro = self._decode_val(self._get("simplemacro", ""))
        self.mapped_key = self._get("mappedkey", "")
        self.map_type = self._get("maptype", "")
        self.name = self._decode_val(self._get("name", ""))
        self.macro = self._decode_val(self._get("macro", ""))
        
    def _get(self, key, default_value):
        section_name = "m%d" % self.memory
        option_key = "keys_" + self.key_list_key + "_" + key
        return self.profile.parser.get(section_name, option_key) if self.profile.parser.has_option(section_name, option_key) else default_value
        
    def save(self):
        self._store()
        self.profile.save()
        
    def delete(self):     
        self.profile.delete_macro(self.memory, self.key_list_key)
 
class G15Profile():
    
    def __init__(self, device, id=-1):
        self.id = id
        self.device = device
        self.parser = ConfigParser.ConfigParser({
                                                     })        
        self.name = None
        self.icon = None
        self.background = None
        self.author = ""
        self.macros = []        
        self.mkey_color = {}
        self.activate_on_focus = False
        self.window_name = ""
        self.base_profile = -1
        self.load()
        
    def are_keys_in_use(self, memory, keys, exclude = None):
        bank = self.macros[memory - 1]
        for macro in bank:
            if ( exclude == None or ( exclude != None and not self.is_excluded(exclude, macro) ) ) and sorted(keys) == sorted(macro.keys):
                return True
        return False
    
    def is_excluded(self, excluded, macro):
        for e in excluded:
            if e == macro:
                return True

    def get_default(self):
        return self.id == 0
        
    def save(self):
        logger.info("Saving macro profile %d, %s" % ( self.id, self.name ))
    
        if self.window_name == None:
            self.window_name = ""
        if self.icon == None:
            self.icon = ""
        
        # Set the profile options
        self.parser.set("DEFAULT", "name", self.name)
        self.parser.set("DEFAULT", "icon", self.icon)
        self.parser.set("DEFAULT", "window_name", self.window_name)    
        self.parser.set("DEFAULT", "base_profile", str(self.base_profile))
        self.parser.set("DEFAULT", "icon", self.icon)
        self.parser.set("DEFAULT", "background", self.background)
        self.parser.set("DEFAULT", "author", self.author)
        self.parser.set("DEFAULT", "activate_on_focus", str(self.activate_on_focus))
        self.parser.set("DEFAULT", "send_delays", str(self.send_delays))
        self.parser.set("DEFAULT", "fixed_delays", str(self.fixed_delays))
        self.parser.set("DEFAULT", "press_delay", str(self.press_delay))
        self.parser.set("DEFAULT", "release_delay", str(self.release_delay))
        
        # Remove and re-add the bank sections
        for i in range(1, 4): 
            section_name = "m%d" % i
            if not self.parser.has_section(section_name):
                self.parser.add_section(section_name) 
            col = self.mkey_color[str(i)] if str(i) in self.mkey_color else None
            if col:
                self.parser.set(section_name, "backlight_color", g15util.rgb_to_string(col))
            elif self.parser.has_option(section_name, "backlight_color"):
                self.parser.remove_option(section_name, "backlight_color")
                
        # Add the macros
        for macro_bank in self.macros:
            for macro in macro_bank:
                macro._store()
                
        self._write()
            
    def set_mkey_color(self, bank, rgb):
        self.mkey_color[str(bank)] = rgb
        
    def get_mkey_color(self, bank):
        return self.mkey_color[str(bank)] if str(bank) in self.mkey_color else None
        
    def delete(self):
        os.remove(self._get_filename())
        
    def _delete_key(self, section_name, key_list_key):
        for option in self.parser.options(section_name):
            if option.startswith("keys_" + key_list_key + "_"):
                self.parser.remove_option(section_name, option)
        
    def delete_macro(self, memory, keys):  
        section_name = "m%d" % memory     
        key_list_key = get_keys_key(keys)
        logger.info("Deleting macro M%d, for %s" % ( memory, key_list_key ))
        self._delete_key(section_name, key_list_key)
        self._write()
        bank_macros = self.macros[memory - 1] 
        for macro in bank_macros:
            if macro.key_list_key == key_list_key and macro in bank_macros:
                bank_macros.remove(macro)
        
    def get_profile_icon_path(self, height):
        icon = self.icon
        if icon == None or icon == "":
            icon = "preferences-desktop-keyboard-shortcuts"
        return g15util.get_icon_path(icon, height)
        
    def create_macro(self, memory, keys, name, type, content):
        key_list_key = get_keys_key(keys)  
        section_name = "m%d" % memory
        logger.info("Creating macro M%d, for %s" % ( memory, key_list_key ))
        new_macro = G15Macro(self, memory, key_list_key)
        new_macro.name = name
        new_macro.type = type
        if type == MACRO_COMMAND:
            new_macro.command = content
        elif type == MACRO_SIMPLE:
            new_macro.simple_command = content
        else:
            new_macro.macro = content
        self.macros[memory - 1].append(new_macro)
        new_macro.save()
        return new_macro
    
    def get_macro(self, memory, keys):
        bank = self.macros[memory - 1]
        for macro in bank:
            key_count = 0
            for k in macro.keys:
                if k in keys:
                    key_count += 1
            if key_count == len(macro.keys) and key_count == len(keys):
                return macro
        
    def make_active(self):
        conf_client.set_int("/apps/gnome15/%s/active_profile" % self.device.uid, self.id)
        
    def load(self):
                 
        # Initial values
        self.macros = []
        self.mkey_color = {}
        
        # Load macro file        
        if self.id != -1:
            if os.path.exists(self._get_filename()):
                self.parser.readfp(codecs.open(self._get_filename(), "r", "utf8"))
        
        # Info section
        self.name = self.parser.get("DEFAULT", "name").strip() if self.parser.has_option("DEFAULT", "name") else ""
        self.icon = self.parser.get("DEFAULT", "icon").strip() if self.parser.has_option("DEFAULT", "icon") else ""
        self.background = self.parser.get("DEFAULT", "background").strip() if self.parser.has_option("DEFAULT", "background") else ""
        self.author = self.parser.get("DEFAULT", "author").strip() if self.parser.has_option("DEFAULT", "author") else ""
        self.window_name = self.parser.get("DEFAULT", "window_name").strip() if self.parser.has_option("DEFAULT", "window_name") else ""
        
        self.activate_on_focus = self.parser.getboolean("DEFAULT", "activate_on_focus") if self.parser.has_option("DEFAULT", "activate_on_focus") else False
        self.send_delays = self.parser.getboolean("DEFAULT", "send_delays") if self.parser.has_option("DEFAULT", "send_delays") else False
        self.fixed_delays = self.parser.getboolean("DEFAULT", "fixed_delays") if self.parser.has_option("DEFAULT", "fixed_delays") else False
        
        self.base_profile = self._get_int("base_profile", -1, "DEFAULT")
        self.press_delay = self._get_int("press_delay", 50)
        self.release_delay = self._get_int("release_delay", 50)
        
        # Bank sections
        for i in range(1, 4):
            section_name = "m%d" % i
            if not self.parser.has_section(section_name):
                self.parser.add_section(section_name)
            self.mkey_color[str(i)] = g15util.to_rgb(self.parser.get(section_name, "backlight_color")) if self.parser.has_option(section_name, "backlight_color") else None
            memory_macros = []
            self.macros.append(memory_macros)
            for option in self.parser.options(section_name):
                if option.startswith("keys_") and option.endswith("_name"):
                    key_list_key = option[5:-5]
                    macro_obj = G15Macro(self, i, key_list_key)
                    macro_obj._load()
                    memory_macros.append(macro_obj)
                    
    '''
    Private
    '''
    def _get_int(self, name, default_value, section = "DEFAULT"):
        try:
            return self.parser.getint(section, name) if self.parser.has_option(section, name) else default_value
        except ValueError as v:
            return default_value
                    
    def __ne__(self, profile):
        return not self.__eq__(profile)
    
    def __eq__(self, profile):
        return profile is not None and self.id == profile.id
        
    def _write(self):
        dir_name = os.path.dirname(self._get_filename())
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
        tmp_file = "%s.tmp" % self._get_filename()
        with open(tmp_file, 'wb') as configfile:
            self.parser.write(configfile)
        os.rename(tmp_file, self._get_filename())
        
    def _get_filename(self):
        return "%s/%s/%d.macros" % ( conf_dir, self.device.uid, self.id )
        
# Create the default for all devices
for device in g15devices.find_all_devices():
    create_default(device)