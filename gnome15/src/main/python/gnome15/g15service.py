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
 
import sys
import pygtk
from gnome15 import g15desktop
pygtk.require('2.0')
import os
import gobject
import g15globals
import g15screen
import g15profile
import g15dbus
import g15devices
import g15desktop
import traceback
import gconf
import g15util
import Xlib.X 
import Xlib.XK
import Xlib.display
import Xlib.protocol
import time
import dbus
import signal
import g15pluginmanager
from threading import Thread

# Logging
import logging
logger = logging.getLogger("service")
    
NAME = "Gnome15"
VERSION = g15globals.version
SERVICE_QUEUE = "serviceQueue"

special_X_keysyms = {
    ' ' : "space",
    '\t' : "Tab",
    '\n' : "Return", # for some reason this needs to be cr, not lf
    '\r' : "Return",
    '\e' : "Escape",
    '\b' : "BackSpace",
    '!' : "exclam",
    '#' : "numbersign",
    '%' : "percent",
    '$' : "dollar",
    '&' : "ampersand",
    '"' : "quotedbl",
    '\'' : "apostrophe",
    '(' : "parenleft",
    ')' : "parenright",
    '*' : "asterisk",
    '=' : "equal",
    '+' : "plus",
    ',' : "comma",
    '-' : "minus",
    '.' : "period",
    '/' : "slash",
    ':' : "colon",
    ';' : "semicolon",
    '<' : "less",
    '>' : "greater",
    '?' : "question",
    '@' : "at",
    '[' : "bracketleft",
    ']' : "bracketright",
    '\\' : "backslash",
    '^' : "asciicircum",
    '_' : "underscore",
    '`' : "grave",
    '{' : "braceleft",
    '|' : "bar",
    '}' : "braceright",
    '~' : "asciitilde"
    }

class G15Service(Thread):
    
    def __init__(self, service_host, no_trap=False):
        Thread.__init__(self)
        self.name = "Service"
        self.active_plugins = {}
        self.session_active = True
        self.service_host = service_host
        self.active_window = None
        self.shutting_down = False
        self.starting_up = True
        self.conf_client = gconf.client_get_default()
        self.screens = []
        self.logging_out = False        
        self.service_listeners = []
        self.use_x_test = None
        self.x_test_available = None
        self.notify_handles = []
        self.font_faces = {}
                
        # Expose Gnome15 functions via DBus
        logger.debug("Starting the DBUS service")
        self.dbus_service = g15dbus.G15DBUSService(self)
        
        # Watch for signals
        if not no_trap:
            signal.signal(signal.SIGINT, self.sigint_handler)
            signal.signal(signal.SIGTERM, self.sigterm_handler)
        
        # Start this thread, which runs the gobject loop. This is 
        # run first, and in a thread, as starting the Gnome15 will send
        # DBUS events (which are sent on the loop). 
        self.loop = gobject.MainLoop()
        self.start()
        
    def start_loop(self):
        logger.info("Starting GLib loop")
        try:
            self.loop.run()
        except:
            traceback.print_stack()
        logger.info("Exited GLib loop")
        
    def start_service(self):
        try:
            self._do_start_service()
#            self.start()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            logger.error("Failed to start service. %s" % str(e))
        
    def run(self):        
        # Now start the service, which will connect to all devices and
        # start their plugins
        self.start_service()
    
    def sigint_handler(self, signum, frame):
        logger.info("Got SIGINT signal, shutting down")
        self.shutdown()
    
    def sigterm_handler(self, signum, frame):
        logger.info("Got SIGTERM signal, shutting down")
        self.shutdown()
        
    def stop(self):
        for h in self.notify_handles:
            self.conf_client.notify_remove(h)
        try :
            logger.info("Stopping file change notification")
            g15profile.notifier.stop()
        except Exception:
            pass
        logger.info("Informing listeners we are stopping")
        for listener in self.service_listeners:
            listener.service_stopping()
            
        logger.info("Stopping screens")
        for screen in self.screens:
            screen.stop()
        g15util.stop_queue(SERVICE_QUEUE)
        
    def shutdown(self):
        logger.info("Shutting down")
        self.shutting_down = True
        self.stop()
        logger.info("Stopping all schedulers")
        g15util.stop_all_schedulers()
        for listener in self.service_listeners:
            listener.service_stopped()
        logger.info("Quiting loop")
        self.loop.quit() 
        logger.info("Stopping DBus service")
        self.dbus_service.stop()
        
    def handle_macro(self, macro):
        # Get the latest focused window if not using XTest
        if not self.use_x_test or not self.x_test_available:
            self.init_xtest()
            self.window = self.local_dpy.get_input_focus()._data["focus"]; 
        
        if macro.type == g15profile.MACRO_COMMAND:
            logger.warning("Running external command '%s'" % macro.command)
            os.system(macro.command)
        elif macro.type == g15profile.MACRO_SIMPLE:
            self.send_simple_macro(macro)
        else:
            self.send_macro(macro)
        
        
    def send_simple_macro(self, macro):
        logger.debug("Simple macro '%s'" % macro.simple_macro)
        esc = False
        i = 0
    
        press_delay = 0.0 if not macro.profile.fixed_delays else ( float(macro.profile.press_delay) / 1000.0 )
        release_delay = 0.0 if not macro.profile.fixed_delays else ( float(macro.profile.release_delay) / 1000.0 )
                        
        for c in macro.simple_macro:
            if c == '\\' and not esc:
                esc = True
            else:                     
                if esc and c == 'p':
                    time.sleep(release_delay + press_delay)
                else:                          
                    if i > 0:
                        if logger.level == logging.DEBUG:
                            logger.debug("Release delay of %f" % release_delay)
                        time.sleep(release_delay)
                        
                    if esc and c == 't':
                        c = '\t'                  
                    elif esc and c == 'r':
                        c = '\r'              
                    elif esc and c == 'n':
                        c = '\r'    
                    elif esc and c == 'b':
                        c = '\b' 
                    elif esc and c == 'e':
                        c = '\e'
                        
                    if c in special_X_keysyms:
                        c = special_X_keysyms[c]
                        
                    self.send_string(c, True)
                    time.sleep(press_delay)
                    if logger.level == logging.DEBUG:
                        logger.debug("Press delay of %f" % press_delay)
                    self.send_string(c, False)
                    
                    i += 1
                     
                esc = False
        
    def send_macro(self, macro):
        
        macros = macro.macro.split("\n")
        i = 0
        for macro_text in macros:
            split = macro_text.split(" ")
            op = split[0]
            if len(split) > 1:
                val = split[1]
                if op == "Delay" and macro.profile.send_delays and not macro.profile.fixed_delays:
                    time.sleep(float(val) / 1000.0 if not macro.profile.fixed_delays else macro.profile.delay_amount)
                elif op == "Press":
                    if i > 0:
                        delay = 0 if not macro.profile.fixed_delays else ( float(macro.profile.release_delay) / 1000.0 )
                        if logger.level == logging.DEBUG:
                            logger.debug("Release delay of %f" % delay) 
                        time.sleep(delay)
                    self.send_string(val, True)
                    delay = 0.0 if not macro.profile.fixed_delays else ( float(macro.profile.press_delay) / 1000.0 )
                    if logger.level == logging.DEBUG:
                        logger.debug("Press delay of %f" % delay) 
                    time.sleep(delay)
                elif op == "Release":
                    self.send_string(val, False)
                i += 1
    
    def get_keysym(self, ch) :
        keysym = Xlib.XK.string_to_keysym(ch)
        if keysym == 0 :
            # Unfortunately, although this works to get the correct keysym
            # i.e. keysym for '#' is returned as "numbersign"
            # the subsequent display.keysym_to_keycode("numbersign") is 0.
            keysym_name = special_X_keysyms[ch]
            keysym = Xlib.XK.string_to_keysym(keysym_name)
        return keysym
    
    def is_shifted(self, ch) :
        if ch.isupper() :
            return True
        if "~!@#$%^&*()_+{}|:\"<>?".find(ch) >= 0 :
            return True
        return False
    
    def get_x_display(self):
        self.init_xtest()
        return self.local_dpy
    
    def init_xtest(self):
        if self.x_test_available == None:
            logger.info("Initialising macro output system")
    
            # Determine whether to use XTest for sending key events to X
            self.x_test_available  = True
            try :
                import Xlib.ext.xtest
            except ImportError:
                self.x_test_available = False
                 
            self.local_dpy = Xlib.display.Display()
            
            if self.x_test_available  and not self.local_dpy.query_extension("XTEST") :
                logger.warn("Found XTEST module, but the X extension could not be found")
                self.x_test_available = False
                
    def char_to_keycode(self, ch) :        
        self.init_xtest()
        if str(ch).startswith("["):
            keysym_code = int(ch[1:-1])
            # AltGr
            if keysym_code == 65027:
                keycode = 108
            else:
                logger.warn("Unknown keysym %d",keysym_code)
                keycode = 0
        else:
            keysym = self.get_keysym(ch)
            keycode = 0 if keysym == 0 else self.local_dpy.keysym_to_keycode(keysym)        
        if keycode == 0 :
            logger.warning("Sorry, can't map (character %d)", ord(ch))
    
        if self.is_shifted(ch):
            shift_mask = Xlib.X.ShiftMask
        else :
            shift_mask = 0
    
        return keycode, shift_mask

            
    def send_string(self, ch, press) :
        keycode, shift_mask = self.char_to_keycode(ch)
        if logger.level == logging.DEBUG:
            logger.debug("Sending keychar %s keycode %d, press = %s" % (ch, int(keycode), str(press)))
        if (self.x_test_available and self.use_x_test) :
            if press:
                if shift_mask != 0 :
                    Xlib.ext.xtest.fake_input(self.local_dpy, Xlib.X.KeyPress, 50)
                Xlib.ext.xtest.fake_input(self.local_dpy, Xlib.X.KeyPress, keycode)
            else:
                Xlib.ext.xtest.fake_input(self.local_dpy, Xlib.X.KeyRelease, keycode)
                if shift_mask != 0 :
                    Xlib.ext.xtest.fake_input(self.local_dpy, Xlib.X.KeyRelease, 50)
        else :
            if press:
                event = Xlib.protocol.event.KeyPress(
                                                         time=int(time.time()),
                                                         root=self.local_dpy.screen().root,
                                                         window=self.window,
                                                         same_screen=0, child=Xlib.X.NONE,
                                                         root_x=0, root_y=0, event_x=0, event_y=0,
                                                         state=shift_mask,
                                                         detail=keycode
                                                         )
                self.window.send_event(event, propagate=True)
            else:
                event = Xlib.protocol.event.KeyRelease(
                                                           time=int(time.time()),
                                                           root=self.local_dpy.screen().root,
                                                           window=self.window,
                                                           same_screen=0, child=Xlib.X.NONE,
                                                           root_x=0, root_y=0, event_x=0, event_y=0,
                                                           state=shift_mask,
                                                           detail=keycode
                    )
                self.window.send_event(event, propagate=True)
                
        self.local_dpy.sync() 
        
    def application_changed(self, old, object_name):
        if object_name != "":
            app = self.session_bus.get_object("org.ayatana.bamf", object_name)
            view = dbus.Interface(app, 'org.ayatana.bamf.view')
            try :
                if view.IsActive() == 1:
                    for screen in self.screens:
                        screen.application_changed(view)
            except dbus.DBusException:
                pass
        
    def timeout_callback(self, event=None):
        try:
            if not self.defeat_profile_change:
                import wnck
                window = wnck.screen_get_default().get_active_window()
                choose_profile = None
                if window != None:
                    title = window.get_name()                                    
                    for profile in g15profile.get_profiles():
                        if not profile.get_default() and profile.activate_on_focus and len(profile.window_name) > 0 and title.lower().find(profile.window_name.lower()) != -1:
                            choose_profile = profile 
                            break
                            
                active_profile = g15profile.get_active_profile()
                if choose_profile == None:
                    default_profile = g15profile.get_default_profile()
                    if (active_profile == None or active_profile.id != default_profile.id) and default_profile.activate_on_focus:
                        default_profile.make_active()
                elif active_profile == None or choose_profile.id != active_profile.id:
                    choose_profile.make_active()
            
        except Exception:
            logger.warning("Failed to activate profile for active window")
            traceback.print_exc(file=sys.stdout)
            
        gobject.timeout_add(500, self.timeout_callback, self)
        
    """
    Private
    """
    def _check_state_of_all_devices(self):
        for d in g15devices.find_all_devices():
            self._check_device_state(d)
            
    def _do_start_service(self):
        for listener in self.service_listeners:
            listener.service_starting_up()
        
        # If running on GNOME, look for the logout signal
        if "gnome" == g15util.get_desktop():
            try:
                import gnome.ui
                gnome.program_init(g15globals.name, g15globals.version)
                client = gnome.ui.master_client()
                service = self
                def save_yourself(self, *args):
                    service.logging_out = True
                    g15util.queue(SERVICE_QUEUE, "saveYourself", 0.0, service._check_state_of_all_devices)
                    
                def shutdown_cancelled(self, *args):
                    logger.info("Shutdown cancelled")
                    service.logging_out = False
                    g15util.queue(SERVICE_QUEUE, "saveYourself", 0.0, service._check_state_of_all_devices)
                
                def die(self, *args):
                    g15util.queue(SERVICE_QUEUE, "saveYourself", 0.0, service.shutdown)
                    
                client.connect('save-yourself', save_yourself)
                client.connect('shutdown-cancelled', shutdown_cancelled)
                client.connect('die', die)
            except Exception as e:
                logger.warning("Could not connect to GNOME desktop session. %s" % str(e))
        
        self.session_bus = dbus.SessionBus()
        
        # Create a screen for each device        
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        devices = g15devices.find_all_devices()
        if len(devices) == 0:
            logger.error("No devices found. Gnome15 will now exit")
            self.shutdown()
            return
        else:
            for device in devices:
                val = self.conf_client.get("/apps/gnome15/%s/enabled" % device.uid)
                h = self.conf_client.notify_add("/apps/gnome15/%s/enabled" % device.uid, self._device_enabled_configuration_changed, device)
                self.notify_handles.append(h)
                if ( val == None and device.model_id != "virtual" ) or ( val is not None and val.get_bool() ):
                    self._add_screen(device)
            if len(self.screens) == 0:
                logger.warning("No screens found yet. Will stay running waiting for one to be enabled.")
                
        # Load hidden configuration and monitor for changes
        self._load_hidden_configuration()
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/scroll_delay", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/scroll_amount", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/animation_delay", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/key_hold_delay", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/text_boxes", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/use_x_test", self._hidden_configuration_changed))
        
        # Start each screen's plugin manager
        for screen in self.screens:
            screen.start()
            
        # Watch for logout (should probably move this to a plugin)
        try :
            self.session_bus.add_signal_receiver(self._session_over, dbus_interface="org.gnome.SessionManager", signal_name="SessionOver")
        except Exception as e:
            logger.warning("GNOME session manager not available, will not detect logout signal for clean shutdown. %s" % str(e))
            
        # Monitor active application    
        logger.info("Attempting to set up BAMF")
        try :
            self.bamf_matcher = self.session_bus.get_object("org.ayatana.bamf", '/org/ayatana/bamf/matcher')   
            self.session_bus.add_signal_receiver(self.application_changed, dbus_interface="org.ayatana.bamf.matcher", signal_name="ActiveApplicationChanged")
            logger.info("Will be using BAMF for window matching")
        except:
            logger.warning("BAMF not available, falling back to WNCK")
            try :                
                import wnck
                wnck.__file__
                gobject.timeout_add(500, self.timeout_callback, self)
            except:
                logger.warning("Python Wnck not available either, no automatic profile switching")
                
        self.starting_up = False
        for listener in self.service_listeners:
            listener.service_started_up()
            
        self._monitor_session()
            
    def _monitor_session(self):
        # Monitor active session (we shut down the driver when becoming inactive)
        try :
            logger.info("Connecting to system bus") 
            system_bus = dbus.SystemBus()
            system_bus.add_signal_receiver(self._active_session_changed, dbus_interface="org.freedesktop.ConsoleKit.Seat", signal_name="ActiveSessionChanged")
            console_kit_object = system_bus.get_object("org.freedesktop.ConsoleKit", '/org/freedesktop/ConsoleKit/Manager')
            console_kit_manager = dbus.Interface(console_kit_object, 'org.freedesktop.ConsoleKit.Manager')
            logger.info("Seats %s " % str(console_kit_manager.GetSeats())) 
            self.this_session_path = console_kit_manager.GetSessionForCookie (os.environ['XDG_SESSION_COOKIE'])
            logger.info("This session %s " % self.this_session_path)
            
            # TODO GetCurrentSession doesn't seem to work as i would expect. Investigate. For now, assume we are the active session
#            current_session = console_kit_manager.GetCurrentSession()
#            logger.info("Current session %s " % current_session)            
#            self.session_active = current_session == self.this_session_path
            self.session_active = True
             
            logger.info("Connected to system bus") 
        except Exception as e:
            logger.warning("ConsoleKit not available, will not track active desktop session. %s" % str(e))
            self.session_active = True
            
    def _add_screen(self, device):
        try:
            screen = g15screen.G15Screen(g15pluginmanager, self, device)
            self.screens.append(screen)
            for listener in self.service_listeners:
                listener.screen_added(screen)
            return screen
        except Exception:
            traceback.print_exc(file=sys.stdout)
            logger.error("Failed to load driver for device %s." % device.uid)
            
    def _hidden_configuration_changed(self, client, connection_id, entry, device):
        self._load_hidden_configuration()
        
    def _load_hidden_configuration(self):
        self.scroll_delay = float(g15util.get_int_or_default(self.conf_client, '/apps/gnome15/scroll_delay', 300)) / 1000.0
        self.scroll_amount = g15util.get_int_or_default(self.conf_client, '/apps/gnome15/scroll_amount', 2)
        self.animation_delay = g15util.get_int_or_default(self.conf_client, '/apps/gnome15/animation_delay', 100) / 1000.0
        self.key_hold_duration = g15util.get_int_or_default(self.conf_client, '/apps/gnome15/key_hold_duration', 2000) / 1000.0
        self.text_boxes = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/text_boxes', True)
        self.use_x_test = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/use_x_test', True)
        self.fade_screen_on_close = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/fade_screen_on_close', True)
        self.fade_keyboard_backlight_on_close = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/fade_keyboard_backlight_on_close', True)
            
    def _device_enabled_configuration_changed(self, client, connection_id, entry, device):
        g15util.queue(SERVICE_QUEUE, "deviceStateChanged", 0, self._check_device_state, device)
        
    def _check_device_state(self, device):
        enabled = g15devices.is_enabled(self.conf_client, device) and not self.logging_out and self.session_active
        screen = self._get_screen_for_device(device)
        logger.info("EN device %s = %s = %s" % (device.uid, str(enabled), str(screen)))
        if enabled and not screen:
            logger.info("Enabling device %s" % device.uid)
            # Enable screen
            screen = self._add_screen(device)
            if screen:
                screen.start()
                logger.info("Enabled device %s" % device.uid)
        elif not enabled and screen:
            # Disable screen
            logger.info("Disabling device %s" % device.uid)
            screen.stop()
            self.screens.remove(screen)
            for listener in self.service_listeners:
                listener.screen_removed(screen)
            logger.info("Disabled device %s" % device.uid)
            
    def _get_screen_for_device(self, device):
        for screen in self.screens:
            if screen.device.uid == device.uid:
                return screen
            
    def _session_over(self, object_path):        
        logger.info("Logout")
        self.shutdown()
            
    def _active_session_changed(self, object_path):        
        logger.debug("Adding seat %s" % object_path)
        self.session_active = object_path == self.this_session_path
        if self.session_active:
            logger.info("g15-desktop service is running on the active session")
        else:
            logger.info("g15-desktop service is NOT running on the active session")
        g15util.queue(SERVICE_QUEUE, "activeSessionChanged", 0.0, self._check_state_of_all_devices)
        
        
    def __del__(self):
        for screen in self.screens:
            if screen.plugins.get_active():
                screen.plugins.deactivate()
            if screen.plugins.get_started():
                screen.plugins.destroy()
        del self.screens