#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2010 Brett Smith <tanktarta@blueyonder.co.uk>
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
_ = g15locale.get_translation("volume", modfile = __file__).ugettext

import gnome15.g15screen as g15screen
import gnome15.util.g15scheduler as g15scheduler
import gnome15.util.g15uigconf as g15uigconf
import gnome15.util.g15gconf as g15gconf
import gnome15.util.g15icontools as g15icontools
import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.g15devices as g15devices
import gnome15.g15actions as g15actions

import alsaaudio
import select
import os
import gtk
import time
import logging
logger = logging.getLogger("volume")

from threading import Thread

# Custom actions
VOLUME_UP = "volume-up"
VOLUME_DOWN = "volume-down"
MUTE = "mute"

# Register the action with all supported models
g15devices.g15_action_keys[VOLUME_UP] = g15actions.ActionBinding(VOLUME_UP, [ g15driver.G_KEY_VOL_UP ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[VOLUME_UP] = g15actions.ActionBinding(VOLUME_UP, [ g15driver.G_KEY_VOL_UP ], g15driver.KEY_STATE_UP)
g15devices.g15_action_keys[VOLUME_DOWN] = g15actions.ActionBinding(VOLUME_DOWN, [ g15driver.G_KEY_VOL_DOWN ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[VOLUME_DOWN] = g15actions.ActionBinding(VOLUME_DOWN, [ g15driver.G_KEY_VOL_DOWN ], g15driver.KEY_STATE_UP)
g15devices.g15_action_keys[MUTE] = g15actions.ActionBinding(MUTE, [ g15driver.G_KEY_MUTE ], g15driver.KEY_STATE_UP)
g15devices.g19_action_keys[MUTE] = g15actions.ActionBinding(MUTE, [ g15driver.G_KEY_MUTE ], g15driver.KEY_STATE_UP)

# Plugin details - All of these must be provided
id="volume"
name=_("Volume Monitor")
description=_("Uses the M-Key lights as a volume meter. If your model has \
a screen, a page will also popup showing the current volume. \
You may choose the mixer that is monitored in the preferences for this plugin.\n\n \
This plugin also registers some actions that may be assigned to macro keys. \
The actions volume-up, volume-down and mute all work directly on the mixer, \
so may be used control the master volume when full screen games are running too.")
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright=_("Copyright (C)2010 Brett Smith")
site="http://www.russo79.com/gnome15"
has_preferences=True
default_enabled=True
unsupported_models = [ g15driver.MODEL_G930, g15driver.MODEL_G35 ]
actions={ 
         VOLUME_UP : "Increase the volume",
         VOLUME_DOWN : "Decrease the volume",
         MUTE : "Mute",
         }


''' 
This plugin displays a high priority screen when the volume is changed for a 
fixed number of seconds
'''

def create(gconf_key, gconf_client, screen):
    return G15Volume(screen, gconf_client, gconf_key)

def show_preferences(parent, driver, gconf_client, gconf_key):
    def refresh_devices(widget):
        new_card_name = soundcard[widget.get_active()][0]
        new_card_index = alsa_soundcards.index(new_card_name)
        '''
        We temporarily block the handler for the mixer_combo 'changed' signal, since we are going
        to change the combobox contents.
        '''
        mixer_combo.handler_block(changed_handler_id)
        model.clear()
        for mixer in alsaaudio.mixers(new_card_index):
            model.append([mixer])
        # Now we can unblock the handler
        mixer_combo.handler_unblock(changed_handler_id)
        # And since the list of mixers has changed, we select the first one by default
        mixer_combo.set_active(0)

    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "volume.glade"))    
    dialog = widget_tree.get_object("VolumeDialog") 
    soundcard_combo = widget_tree.get_object('CardCombo')
    mixer_combo = widget_tree.get_object('DeviceCombo')
    soundcard = widget_tree.get_object("SoundCard")
    model = widget_tree.get_object("DeviceModel")   
    alsa_soundcards = alsaaudio.cards()
    current_card_name = g15gconf.get_string_or_default(gconf_client,
                                                       gconf_key + "/soundcard",
                                                       str(alsa_soundcards[0]))
    current_card_index = alsa_soundcards.index(current_card_name)
    current_card_mixers = alsaaudio.mixers(current_card_index)

    for card in alsa_soundcards:
        soundcard.append([card])
    for mixer in current_card_mixers:
        model.append([mixer])

    g15uigconf.configure_combo_from_gconf(gconf_client, \
                                          gconf_key + "/soundcard", \
                                          "CardCombo", \
                                          str(alsa_soundcards[0]), \
                                          widget_tree)

    changed_handler_id = g15uigconf.configure_combo_from_gconf(gconf_client, \
                                                               gconf_key + "/mixer", \
                                                               "DeviceCombo", \
                                                                str(current_card_mixers[0]), \
                                                                widget_tree)
    soundcard_combo.connect('changed', refresh_devices)

    dialog.set_transient_for(parent)
    dialog.run()
    dialog.hide()
            
class G15Volume():
    
    def __init__(self, screen, gconf_client, gconf_key):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._volume = 0.0
        self._volthread = None
        self._mute = False
        self._light_controls = None
        self._lights_timer = None
        self._reload_config_timer = None

    def activate(self):
        self._screen.key_handler.action_listeners.append(self) 
        self._activated = True
        self._read_config()
        self._start_monitoring()
        self._notify_handler = self._gconf_client.notify_add(self._gconf_key, self._config_changed); 
    
    def deactivate(self):
        self._screen.key_handler.action_listeners.remove(self)
        self._activated = False
        self._stop_monitoring()
        self._gconf_client.notify_remove(self._notify_handler)
        
    def destroy(self):
        pass
    
    def action_performed(self, binding):
        if binding.action in [ VOLUME_UP, VOLUME_DOWN, MUTE ]:
            vol_mixer = self._open_mixer()
            try :
                if binding.action == MUTE:      
                    # Handle mute        
                    mute = False
                    mutes = None
                    try :
                        mutes = vol_mixer.getmute()
                    except alsaaudio.ALSAAudioError:
                        if vol_mixer is not None:
                            vol_mixer.close()
                        # Some pulse weirdness maybe?
                        vol_mixer = self._open_mixer("PCM", self.current_card_index)
                        try :
                            mutes = vol_mixer.getmute()
                        except alsaaudio.ALSAAudioError:
                            logger.warning("No mute switch found")
                    if mutes != None:        
                        for ch_mute in mutes:
                            if ch_mute:
                                mute = True
                        vol_mixer.setmute(1 if not mute else 0)
                else:
                    volumes = vol_mixer.getvolume()        
                    total = 0
                    for vol in volumes:
                        total += vol
                    volume = total / len(volumes)
                    
                    if binding.action == VOLUME_UP and volume < 100:
                        volume += 10
                        vol_mixer.setvolume(min(volume, 100))
                    elif binding.action == VOLUME_DOWN and volume > 0:
                        volume -= 10
                        vol_mixer.setvolume(max(volume, 0))
                
            finally :
                if vol_mixer is not None:
                    vol_mixer.close()
            
            
        
    ''' Functions specific to plugin
    ''' 
    def _start_monitoring(self):        
        self._volthread = VolumeThread(self)
        self._volthread.start()
    
    def _config_changed(self, client, connection_id, entry, args):    
        '''
        If the user changes the soundcard on the preferences dialog this method
        would be called two times. A first time for the soundcard change, and a
        second time because the first mixer of the newly selected soundcard is
        automatically selected.
        The volume monitoring would then be restarted twice, which makes no sense.
        Instead of restarting the monitoring as soon as this method is called,
        we put it as a task on a queue for 1 second. If during that time, any
        other change happens to the configuration, the previous restart request
        is cancelled, and another one takes it's place.
        This way, the monitoring is only restarted once when the user selects another
        sound card.
        '''
        if self._reload_config_timer is not None:
           if not self._reload_config_timer.is_complete():
               self._reload_config_timer.cancel()
           self._reload_config_timer = None

        self._reload_config_timer = g15scheduler.queue('VolumeMonitorQueue',
                                                       'RestartVolumeMonitoring',
                                                       1.0,
                                                       self._restart_monitoring)

    def _restart_monitoring(self):
        self._stop_monitoring()
        self._read_config()
        time.sleep(1.0)
        self._start_monitoring()

    def _read_config(self):
        self.soundcard_name = g15gconf.get_string_or_default(self._gconf_client, \
                                                             self._gconf_key + "/soundcard", \
                                                             str(alsaaudio.cards()[0]))
        self.soundcard_index = alsaaudio.cards().index(self.soundcard_name)

        self.mixer_name = g15gconf.get_string_or_default(self._gconf_client, \
                                                         self._gconf_key + "/mixer", \
                                                         str(alsaaudio.mixers(self.soundcard_index)[0]))
        if not self.mixer_name in alsaaudio.mixers(self.soundcard_index):
            self.mixer_name = str(alsaaudio.mixers(self.soundcard_index)[0])
            self._gconf_client.set_string(self._gconf_key + "/mixer", self.mixer_name)

            
    def _stop_monitoring(self):
        if self._volthread != None:
            self._volthread._stop_monitoring()
        
    def _get_theme_properties(self):
        properties = {}
        icon = "audio-volume-muted"
        if not self._mute:
            if self._volume < 34:
                icon = "audio-volume-low"
            elif self._volume < 67:
                icon = "audio-volume-medium"
            else:
                icon = "audio-volume-high"
        else:
            properties [ "muted"] = True
        icon_path = g15icontools.get_icon_path(icon, self._screen.driver.get_size()[0])
        properties["state"] = icon
        properties["icon"] = icon_path
        properties["vol_pc"] = self._volume
        for i in range(0, int( self._volume / 10 ) + 1, 1):            
            properties["bar" + str(i)] = True
        return properties
            
    def _release_lights(self):
        if self._light_controls is not None:
            self._screen.driver.release_control(self._light_controls)
            self._light_controls = None
            
    def _open_mixer(self, mixer_name = None):
        mixer_name = self.mixer_name if mixer_name is None else mixer_name
        if not mixer_name or mixer_name == "":
            mixer_name = "Master"
            
        logger.info("Opening soundcard %s mixer %s" % (self.soundcard_name, mixer_name))
        
        vol_mixer = alsaaudio.Mixer(mixer_name, cardindex=self.soundcard_index)
        return vol_mixer
    
    def _popup(self):
        if not self._activated:
            logger.warning("Cannot popup volume when it is deactivated. This suggests the volume thread has not died.")
            return
        
        if not self._light_controls:
            self._light_controls = self._screen.driver.acquire_control_with_hint(g15driver.HINT_MKEYS)
        if self._lights_timer is not None:
            self._lights_timer.cancel()
        if self._light_controls is not None:
            self._lights_timer = g15scheduler.schedule("ReleaseMKeyLights", 3.0, self._release_lights)
        
        page = self._screen.get_page(id)
        if page == None:
            if self._screen.driver.get_bpp() != 0:
                page = g15theme.G15Page(id, self._screen, priority=g15screen.PRI_HIGH, title="Volume", theme = g15theme.G15Theme(self), \
                                        theme_properties_callback = self._get_theme_properties,
                                        originating_plugin = self)
                self._screen.delete_after(3.0, page)
                self._screen.add_page(page)
        else:
            self._screen.raise_page(page)
            self._screen.delete_after(3.0, page)
        
       
        vol_mixer = self._open_mixer()
        mute_mixer = None
        
        try :
        
            # Handle mute        
            mute = False
            mutes = None
            try :
                mutes = vol_mixer.getmute()
            except alsaaudio.ALSAAudioError:
                # Some pulse weirdness maybe?
                mute_mixer = alsaaudio.Mixer("PCM", cardindex=self.soundcard_index)
                try :
                    mutes = mute_mixer.getmute()
                except alsaaudio.ALSAAudioError:
                    logger.warning("No mute switch found")
            if mutes != None:        
                for ch_mute in mutes:
                    if ch_mute:
                        mute = True
    
            
            # TODO  better way than averaging
            volumes = vol_mixer.getvolume()
        finally :
            vol_mixer.close()
            if mute_mixer:
                mute_mixer.close()
            
        total = 0
        for vol in volumes:
            total += vol
        volume = total / len(volumes)
        
        self._volume = volume              
        
        if self._light_controls is not None:
            if self._volume > 90:
                self._light_controls.set_value(g15driver.MKEY_LIGHT_MR | g15driver.MKEY_LIGHT_1 | g15driver.MKEY_LIGHT_2 | g15driver.MKEY_LIGHT_3)        
            elif self._volume > 75:
                self._light_controls.set_value(g15driver.MKEY_LIGHT_1 | g15driver.MKEY_LIGHT_2 | g15driver.MKEY_LIGHT_3)        
            elif self._volume > 50:
                self._light_controls.set_value(g15driver.MKEY_LIGHT_1 | g15driver.MKEY_LIGHT_2)        
            elif self._volume > 25:
                self._light_controls.set_value(g15driver.MKEY_LIGHT_1)        
            else:
                self._light_controls.set_value(0)
          
        self._mute = mute
        
        self._screen.redraw(page)
            
class VolumeThread(Thread):
    def __init__(self, volume):
        Thread.__init__(self)
        self.name = "VolumeThread"
        self.setDaemon(True)
        self._volume = volume
        
        logger.info("Opening soundcard %s mixer %s" % (volume.soundcard_name, volume.mixer_name))
        
        self._mixer = alsaaudio.Mixer(volume.mixer_name, cardindex=volume.soundcard_index)
        self._poll_desc = self._mixer.polldescriptors()
        self._poll = select.poll()
        self._fd = self._poll_desc[0][0]
        self._event_mask = self._poll_desc[0][1]
        self._open = os.fdopen(self._fd)
        self._poll.register(self._open, select.POLLIN)
        self._stop = False
        
    def _stop_monitoring(self):
        self._stop = True
        self._open.close()
        self._mixer.close()
        
    def run(self):
        try :
            while not self._stop:
                if self._poll.poll(5):
                    if self._stop:
                        break
                    g15scheduler.schedule("popupVolume", 0, self._volume._popup)
                    if not self._open.read():
                        break
        finally:
            try :
                self._poll.unregister(self._open)
            except :
                pass
            self._open.close()
