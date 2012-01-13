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
pygtk.require('2.0')
import os
import gobject
import g15globals
import g15screen
import g15profile
import g15dbus
import g15devices
import g15desktop
import g15uinput
import traceback
import gconf
import g15util
import Xlib.X 
import Xlib.ext
import Xlib.XK
import Xlib.display
import Xlib.protocol
import time
import dbus
import signal
import g15pluginmanager
from threading import Thread
import gtk.gdk
 
# Used for getting logout  / shutdown signals
master_client = None
if "gnome" == g15util.get_desktop():
    try:
        import gnome.ui
        master_client = gnome.ui.master_client()
    except:
        pass

# Logging
import logging
logger = logging.getLogger("service")

# Upgrade
import g15upgrade
g15upgrade.upgrade()

    
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

class CheckThread(Thread):
    def __init__(self, device, check_function, quickly):
        Thread.__init__(self)
        self.name = "CheckDeviceState%s" % device.uid
        self.device = device
        self.quickly = quickly
        self.check_function = check_function
        self.start()
        
    def run(self):
        self.check_function(self.device, self.quickly)
        
class StartThread(Thread):
    def __init__(self, screen):
        Thread.__init__(self)
        self.name = "StartScreen%s" % screen.device.uid
        self.screen = screen
        self.error = None
    
    def run(self):
        try:
            self.screen.start()
        except Exception as e:
            logger.error("Failed to start screen. %s" % str(e))
            self.error = e

class G15Service(g15desktop.G15AbstractService):
    
    def __init__(self, service_host, no_trap=False):
        self.active_plugins = {}
        self.session_active = True
        self.service_host = service_host
        self.active_window = None
        self.shutting_down = False
        self.active_application_name = None
        self.starting_up = True
        self.conf_client = gconf.client_get_default()
        self.screens = []
        self.started = False
        self.service_listeners = []
        self.use_x_test = None
        self.x_test_available = None
        self.notify_handles = []
        self.font_faces = {}
        self.devices = g15devices.find_all_devices()
        self.stopping = False
                
        # Expose Gnome15 functions via DBus
        logger.debug("Starting the DBUS service")
        self.dbus_service = g15dbus.G15DBUSService(self)
        
        # Watch for signals
        if not no_trap:
            signal.signal(signal.SIGINT, self.sigint_handler)
            signal.signal(signal.SIGTERM, self.sigterm_handler)
            
        g15desktop.G15AbstractService.__init__(self)
        self.name = "DesktopService"
        
    def start_service(self):
        try:
            self._do_start_service()
        except Exception as e:
            self.shutdown(True)
            logger.error("Failed to start service. %s" % str(e))
    
    def sigint_handler(self, signum, frame):
        logger.info("Got SIGINT signal, shutting down")
        self.shutdown(True)
    
    def sigterm_handler(self, signum, frame):
        logger.info("Got SIGTERM signal, shutting down")
        self.shutdown(True)
        
    def stop(self, quickly = False):
        if self.started:
            g15uinput.close_devices()
            self.global_plugins.deactivate()
            self.stopping = True
            self.session_active = False
            try :
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
                self._check_state_of_all_devices_async(quickly)     
                logger.info("Screens stopped")
                self.started = False
            finally :
                self.stopping = False
        else:
            logger.warn("Ignoring stop request, already stopped.")
            
        
    def shutdown(self, quickly = False):
        logger.info("Shutting down")
        self.shutting_down = True
        self.global_plugins.destroy()
        self.stop(quickly)
        g15util.stop_queue(SERVICE_QUEUE)   
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
        self.init_xtest()
        if self.virtual_keyboard is None and ( not self.use_x_test or not self.x_test_available ):
            self.window = self.local_dpy.get_input_focus()._data["focus"]; 
        
        if macro.type == g15profile.MACRO_COMMAND:
            logger.warning("Running external command '%s'" % macro.macro)
            os.system(macro.macro)
        elif macro.type == g15profile.MACRO_SIMPLE:
            self.send_simple_macro(macro)
        else:
            self.send_macro(macro)
        
    def send_simple_macro(self, macro):
        logger.debug("Simple macro '%s'" % macro.macro)
        esc = False
        i = 0
    
        press_delay = 0.0 if not macro.profile.fixed_delays else ( float(macro.profile.press_delay) / 1000.0 )
        release_delay = 0.0 if not macro.profile.fixed_delays else ( float(macro.profile.release_delay) / 1000.0 )
                        
        for c in macro.macro:
            if c == '\\' and not esc:
                esc = True
            else:                     
                if esc and c == 'p':
                    time.sleep(release_delay + press_delay)
                else:                          
                    if i > 0:
                        if logger.isEnabledFor(logging.DEBUG):
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
                    elif esc and c == '\\':
                        c = '\\'
                        
                    if c in special_X_keysyms:
                        c = special_X_keysyms[c]
                        
                    self.send_string(c, True)
                    time.sleep(press_delay)
                    if logger.isEnabledFor(logging.DEBUG):
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
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("Release delay of %f" % delay) 
                        time.sleep(delay)
                    self.send_string(val, True)
                    delay = 0.0 if not macro.profile.fixed_delays else ( float(macro.profile.press_delay) / 1000.0 )
                    if logger.isEnabledFor(logging.DEBUG):
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
            if ch in special_X_keysyms:
                keysym_name = special_X_keysyms[ch]
                keysym = Xlib.XK.string_to_keysym(keysym_name)
        return keysym
    
    def get_x_display(self):
        self.init_xtest()
        return self.local_dpy
    
    def init_xtest(self):
        """
        Initialise XTEST if it is available.
        """
        if self.x_test_available == None:
            logger.info("Initialising macro output system")
            
            # Load Python Virtkey if it is available

            # Use python-virtkey for preference
            
            self.virtual_keyboard = None
            try:
                import virtkey
                self.virtual_keyboard = virtkey.virtkey()
                self.x_test_available = False
            except:
                logger.warn("No python-virtkey, macros may be weird. Trying XTest")
    
                # Determine whether to use XTest for sending key events to X
                self.x_test_available  = True
                try :
                    import Xlib.ext.xtest
                except ImportError:
                    logger.warn("No XTest, falling back to raw X11 events")
                    self.x_test_available = False
                     
                self.local_dpy = Xlib.display.Display()
                
                if self.x_test_available  and not self.local_dpy.query_extension("XTEST") :
                    logger.warn("Found XTEST module, but the X extension could not be found")
                    self.x_test_available = False
                
    def char_to_keycodes(self, ch):
        """
        Convert a character from a string into an X11 keycode when possible.
        
        Keyword arguments:
        ch        -- character to convert
        """    
        self.init_xtest()
        shift_mask = 0
        
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
                        
            x_keycodes = self.local_dpy.keysym_to_keycodes(keysym)
            keycode = 0 if keysym == 0 else self.local_dpy.keysym_to_keycode(keysym)
            
            # I have no idea how accurate this is, but it seems more so that
            # the is_shifted() function
            if keysym < 256:
                for x in x_keycodes:
                    if x[1] == 1:
                        shift_mask = Xlib.X.ShiftMask
                        
        if keycode == 0 :
            logger.warning("Sorry, can't map (character %d)", ord(ch))
    
        return keycode, shift_mask

            
    def send_string(self, ch, press):
        """
        Sends a string (character) to the X server as if it was typed. 
        Depending on the configuration virtkey, XTEST or raw events may be used
        
        Keyword arguments:
        ch        --    character to send
        press     --    boolean indicating if this is a PRESS or RELEASE
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Sending string %s" % ch)
            
        if self.virtual_keyboard is not None:
            keysym = self.get_keysym(ch)
            if press:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Sending keychar %s press = %s, keysym = %d (%x)" % (ch, press, keysym, keysym))
                self.virtual_keyboard.press_keysym(keysym)
            else:
                self.virtual_keyboard.release_keysym(self.get_keysym(ch))
        else:
            keycode, shift_mask = self.char_to_keycodes(ch)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Sending keychar %s keycode %d, press = %s, shift = %d" % (ch, int(keycode), str(press), shift_mask))
            if (self.x_test_available and self.use_x_test) :
                if press:
                    if shift_mask != 0 :
                        Xlib.ext.xtest.fake_input(self.local_dpy, Xlib.X.KeyPress, 62)
                    Xlib.ext.xtest.fake_input(self.local_dpy, Xlib.X.KeyPress, keycode)
                else:
                    Xlib.ext.xtest.fake_input(self.local_dpy, Xlib.X.KeyRelease, keycode)
                    if shift_mask != 0 :
                        Xlib.ext.xtest.fake_input(self.local_dpy, Xlib.X.KeyRelease, 62)
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
            
    def get_active_application_name(self):
        return self.active_application_name
        
    """
    Private
    """
        
    def _active_window_changed(self, old, object_name):
        if object_name != "":
            app = self.session_bus.get_object("org.ayatana.bamf", object_name)
            view = dbus.Interface(app, 'org.ayatana.bamf.view')
            for s in self.screens:
                self._check_active_application(s, app, view)
            
    def _check_active_application(self, screen, app, view):
        try :
            if view.IsActive() == 1:
                vn = view.Name()
                logger.debug("Active application is now %s" % self.active_application_name)
                if screen.set_active_application_name(vn):
                    return True
                else:                            
                    parents = view.Parents()
                    for parent in parents:
                        app = self.session_bus.get_object("org.ayatana.bamf", parent)
                        view = dbus.Interface(app, 'org.ayatana.bamf.view')
                        if self._check_active_application(screen, app, view):
                            return True                            
        except dbus.DBusException:
            pass
        
    def _check_active_application_with_wnck(self, event=None):
        try:
            import wnck
            window = wnck.screen_get_default().get_active_window()
            if window is not None and not window.is_skip_pager():
                app = window.get_application()
                active_application_name = app.get_name() if app is not None else ""
                if active_application_name != self.active_application_name:
                    self.active_application_name = active_application_name
                    logger.info("Active application is now %s" % self.active_application_name)
                    for screen in self.screens:
                        screen.set_active_application_name(active_application_name)
        except Exception:
            logger.warning("Failed to activate profile for active window")
            traceback.print_exc(file=sys.stdout)
            
        gobject.timeout_add(500, self._check_active_application_with_wnck)
        
    def _check_state_of_all_devices(self, quickly = False):
        logger.info("Checking state of %d devices" % len(self.devices))
        for d in self.devices:
            self._check_device_state(d, quickly)
            
    def _check_state_of_all_devices_async(self, quickly = False):
        logger.info("Checking state of %d devices" % len(self.devices))
        t = []
        for d in self.devices:
            t.append(CheckThread(d, self._check_device_state, quickly))
        self._join_all(t)
        
    def _do_start_service(self):
        # Global plugins        
        self.session_active = True        
        self.global_plugins = g15pluginmanager.G15Plugins(None, self)
        self.global_plugins.start()
        
        for listener in self.service_listeners:
            listener.service_starting_up()
            
        # UINPUT
        try:
            g15uinput.open_devices()
        except IOError as (errno, strerror):
            if errno == 13:
                raise Exception("Failed to open uinput devices. Do you have the uinput module loaded (try modprobe uinput), and are the permissions of /dev/uinput correct? %s" % strerror)
            else:
                raise
        
        self.session_bus = dbus.SessionBus()
        
        # Create a screen for each device        
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        logger.info("Looking for devices")
        devices = g15devices.find_all_devices()
        if len(devices) == 0:
            logger.error("No devices found. Gnome15 will now exit")
            self.shutdown()
            return
        else:
            # If there is a single device, it is enabled by default
            if len(devices) == 1:
                self.conf_client.set_bool("/apps/gnome15/%s/enabled" % devices[0].uid, True)
                
            errors = 0
            for device in devices:
                val = self.conf_client.get("/apps/gnome15/%s/enabled" % device.uid)
                h = self.conf_client.notify_add("/apps/gnome15/%s/enabled" % device.uid, self._device_enabled_configuration_changed, device)
                self.notify_handles.append(h)
                if ( val == None and device.model_id != "virtual" ) or ( val is not None and val.get_bool() ):
                    screen = self._add_screen(device)
                    if not screen:
                        errors += 1
                        
            if len(self.devices) == errors:
                logger.error("All screens failed to load. Shutting down")
                self.shutdown()
                return
                
            if len(self.screens) == 0:
                logger.warning("No screens found yet. Will stay running waiting for one to be enabled.")
                
        # Load hidden configuration and monitor for changes
        self._load_hidden_configuration()
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/scroll_delay", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/scroll_amount", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/animation_delay", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/key_hold_delay", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/use_x_test", self._hidden_configuration_changed))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/disable_svg_glow", self._hidden_configuration_changed))
            
        # Monitor active application    
        gobject.idle_add(self._configure_window_monitoring)
                
        # Activate global plugins
        self.global_plugins.activate()
        
        # Start each screen's plugin manager
        th = []
        for screen in self.screens:
            t = StartThread(screen)
            if self.start_in_threads:
                t.start()
            else:
                t.run()
            th.append(t)        
        if len(self.screens) == 1:
            if th[0].error is not None:
                raise th[0].error
                
        self.starting_up = False
        for listener in self.service_listeners:
            listener.service_started_up()
        self.started = True
            
        gobject.idle_add(self._monitor_session)
        
    def _join_all(self, threads, timeout = 30):
        for t in threads:
            t.join(timeout)
            
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
            
            
        # GNOME session manager stuff (watch for logout etc)
        try :
            session_manager_object = self.session_bus.get_object("org.gnome.SessionManager", "/org/gnome/SessionManager", "org.gnome.SessionManager")
            client_path = session_manager_object.RegisterClient('Gnome15', '', dbus_interface="org.gnome.SessionManager")
            
            self.session_manager_client_object = self.session_bus.get_object("org.gnome.SessionManager", client_path, "org.gnome.SessionManager.ClientPrivate")
            self.session_manager_client_object.connect_to_signal("QueryEndSession", self._sm_query_end_session)
            self.session_manager_client_object.connect_to_signal("EndSession", self._sm_end_session)
            self.session_manager_client_object.connect_to_signal("CancelEndSession", self._sm_cancel_end_session)
            self.session_manager_client_object.connect_to_signal("Stop", self._sm_stop)
    
            session_manager_client_public_object = self.session_bus.get_object("org.gnome.SessionManager", client_path, "org.gnome.SessionManager.Client")
            sm_client_id = session_manager_client_public_object.GetStartupId()
            gtk.gdk.set_sm_client_id(sm_client_id)
        except Exception as e:
            logger.warning("GNOME session manager not available, will not detect logout signal for clean shutdown. %s" % str(e))
            
    def _sm_query_end_session(self, flags):
        logger.info("Querying for end session")
        self._sm_client_dbus_will_quit(True, "Gnome15 Shutting Down")
        g15util.execute(SERVICE_QUEUE, "SessionEnd", self.stop)
        
    def _sm_cancel_end_session(self):
        logger.info("Cancelled session end, starting up again")
        self.session_active = True
        g15util.execute(SERVICE_QUEUE, "CancelSessionEnd", self.start_service)
        
    def _sm_end_session(self, flags):
        self._sm_client_dbus_will_quit(True, "Gnome15 Shutting Down")
        logger.info("Ending session")
        g15util.execute(SERVICE_QUEUE, "SessionEnd", self.stop)
    
    def _sm_client_dbus_will_quit(self, can_quit=True, reason=""):
        self.session_manager_client_object.EndSessionResponse(can_quit,reason)
            
    def _sm_stop(self):        
        logger.info("Shutdown quickly")
        self.shutdown(True)
            
    def _active_session_changed(self, object_path):        
        logger.debug("Adding seat %s" % object_path)
        if g15util.get_bool_or_default(self.conf_client, "/apps/gnome15/monitor_desktop_session", True):
            self.session_active = object_path == self.this_session_path
            if self.session_active:
                logger.info("g15-desktop service is running on the active session")
            else:
                logger.info("g15-desktop service is NOT running on the active session")
            g15util.queue(SERVICE_QUEUE, "activeSessionChanged", 0.0, self._check_state_of_all_devices)
        
    def _configure_window_monitoring(self):
        logger.info("Attempting to set up BAMF")
        try :
            self.bamf_matcher = self.session_bus.get_object("org.ayatana.bamf", '/org/ayatana/bamf/matcher')
            bamf_matcher_interface = dbus.Interface(self.bamf_matcher, 'org.ayatana.bamf.matcher')  
            self.session_bus.add_signal_receiver(self._active_window_changed, dbus_interface = 'org.ayatana.bamf.matcher', signal_name="ActiveWindowChanged")
            active_window = bamf_matcher_interface.ActiveWindow() 
            logger.info("Will be using BAMF for window matching")
            if active_window:
                self._active_window_changed("", active_window)
        except Exception as e:
            logger.warning("BAMF not available, falling back to polling WNCK. %s" % str(e))
            try :                
                import wnck
                wnck.__file__
                self._check_active_application_with_wnck()
            except:
                logger.warning("Python Wnck not available either, no automatic profile switching")
            
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
        self.scroll_delay = float(g15util.get_int_or_default(self.conf_client, '/apps/gnome15/scroll_delay', 500)) / 1000.0
        self.scroll_amount = g15util.get_int_or_default(self.conf_client, '/apps/gnome15/scroll_amount', 5)
        self.animation_delay = g15util.get_int_or_default(self.conf_client, '/apps/gnome15/animation_delay', 100) / 1000.0
        self.key_hold_duration = g15util.get_int_or_default(self.conf_client, '/apps/gnome15/key_hold_duration', 2000) / 1000.0
        self.use_x_test = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/use_x_test', True)
        self.disable_svg_glow = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/disable_svg_glow', False)
        self.fade_screen_on_close = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/fade_screen_on_close', True)
        self.all_off_on_disconnect = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/all_off_on_disconnect', True)
        self.fade_keyboard_backlight_on_close = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/fade_keyboard_backlight_on_close', True)
        self.start_in_threads = g15util.get_bool_or_default(self.conf_client, '/apps/gnome15/start_in_threads', False)
        self._mark_all_pages_dirty()
        
    def _mark_all_pages_dirty(self):
        for screen in self.screens:
            for page in screen.pages:
                page.mark_dirty()
            
    def _device_enabled_configuration_changed(self, client, connection_id, entry, device):
        g15util.queue(SERVICE_QUEUE, "deviceStateChanged", 0, self._check_device_state, device)
        
    def _check_device_state(self, device, quickly = False):
        enabled = g15devices.is_enabled(self.conf_client, device) and self.session_active
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
            screen.stop(quickly)
            self.screens.remove(screen)
            for listener in self.service_listeners:
                listener.screen_removed(screen)
            logger.info("Disabled device %s" % device.uid)
            
            # If there is a single device, stop the service as well
            if len(self.devices) == 1:
                self.shutdown(False)
            
    def _get_screen_for_device(self, device):
        for screen in self.screens:
            if screen.device.uid == device.uid:
                return screen
        
        
    def __del__(self):
        for screen in self.screens:
            if screen.plugins.is_active():
                screen.plugins.deactivate()
            if screen.plugins.is_started():
                screen.plugins.destroy()
        del self.screens
