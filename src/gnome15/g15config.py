#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2009-2012 Brett Smith <tanktarta@blueyonder.co.uk>
#  Copyright (C) 2013 Gnome15 authors
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
_ = g15locale.get_translation("gnome15").ugettext

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango
import dbus.service
import os
import sys
import g15globals
import g15profile
import gconf
import g15pluginmanager
import g15driver
import g15desktop
import g15drivermanager
import g15macroeditor
import g15devices
import util.g15convert as g15convert
import util.g15scheduler as g15scheduler
import util.g15uigconf as g15uigconf
import util.g15gconf as g15gconf
import util.g15os as g15os
import util.g15icontools as g15icontools
import g15theme
import colorpicker
import subprocess
import shutil
import zipfile
import time

import logging
logger = logging.getLogger(__name__)

# Upgrade
import g15upgrade
g15upgrade.upgrade()

# Determine if appindicator is available, this decides the nature
# of the message displayed when the Gnome15 service is not running
HAS_APPINDICATOR=False
try :
    import appindicator
    appindicator.__path__
    HAS_APPINDICATOR=True
except Exception as e:
    logger.debug('Could not load appindicator module', exc_info = e)
    pass

# Store the temporary profile icons here (for when the icon comes from a window, the filename is not known
icons_dir = os.path.join(g15globals.user_cache_dir, "macro_profiles")
g15os.mkdir_p(icons_dir)

PALE_RED = gtk.gdk.Color(213, 65, 54)


BUS_NAME="org.gnome15.Configuration"
NAME="/org/gnome15/Config"
IF_NAME="org.gnome15.Config"

STOPPED = 0
STARTING = 1
STARTED = 2
STOPPING = 3 

class G15ConfigService(dbus.service.Object):
    """
    DBUS Service used to prevent g15-config from running more than once. Each run will
    test if this service is available, if it is, then the Present function will be 
    called and the runtime exited.
    """
    
    def __init__(self, config):
        self._config = config
        bus_name = dbus.service.BusName(BUS_NAME, bus=config.session_bus, replace_existing=False, allow_replacement=False, do_not_queue=True)
        dbus.service.Object.__init__(self, bus_name, NAME)
        
    @dbus.service.method(IF_NAME, in_signature='', out_signature='')
    def Present(self):
        self._config.main_window.present()
        
    @dbus.service.method(IF_NAME, in_signature='s', out_signature='')
    def PresentWithDeviceUID(self, device_uid):
        self._config._default_device_name = device_uid
        self._config._load_devices()
        self._config.main_window.present()
        
class G15GlobalConfig:
    
    def __init__(self, parent, widget_tree, conf_client):
        self.widget_tree = widget_tree
        self.conf_client = conf_client
        self.selected_id = None
        
        only_show_indicator_on_error = self.widget_tree.get_object("OnlyShowIndicatorOnError")
        start_desktop_service_on_login = self.widget_tree.get_object("StartDesktopServiceOnLogin")
        start_indicator_on_login = self.widget_tree.get_object("StartIndicatorOnLogin")
        start_system_tray_on_login = self.widget_tree.get_object("StartSystemTrayOnLogin")
        global_plugin_enabled_renderer = self.widget_tree.get_object("GlobalPluginEnabledRenderer")
        enable_gnome_shell_extension = self.widget_tree.get_object("EnableGnomeShellExtension")
        
        self.dialog = self.widget_tree.get_object("GlobalOptionsDialog")
        self.global_plugin_model = self.widget_tree.get_object("GlobalPluginModel")
        self.global_plugin_tree = self.widget_tree.get_object("GlobalPluginTree")        
        self.global_plugin_tree.connect("cursor-changed", self._select_plugin)

        self.widget_tree.get_object("GlobalPreferencesButton").connect("clicked", self._show_preferences)
        self.widget_tree.get_object("GlobalAboutPluginButton").connect("clicked", self._show_about_plugin)            
        start_desktop_service_on_login.connect("toggled", self._change_desktop_service, "gnome15")
        start_indicator_on_login.connect("toggled", self._change_desktop_service, "g15-indicator")
        start_system_tray_on_login.connect("toggled", self._change_desktop_service, "g15-systemtray")
        enable_gnome_shell_extension.connect("toggled", self._change_gnome_shell_extension)
        global_plugin_enabled_renderer.connect("toggled", self._toggle_plugin)
        
        # Service options
        gnome_shell = g15desktop.get_desktop() == "gnome-shell"
        shell_extension_installed = g15desktop.is_shell_extension_installed("gnome15-shell-extension@gnome15.org")      
        only_show_indicator_on_error.set_visible(g15desktop.is_desktop_application_installed("g15-indicator") and not gnome_shell)
        start_indicator_on_login.set_visible(g15desktop.is_desktop_application_installed("g15-indicator") and not gnome_shell)
        start_system_tray_on_login.set_visible(g15desktop.is_desktop_application_installed("g15-systemtray") and not gnome_shell)
        enable_gnome_shell_extension.set_visible(gnome_shell and shell_extension_installed)
        start_desktop_service_on_login.set_active(g15desktop.is_autostart_application("gnome15"))
        start_indicator_on_login.set_active(g15desktop.is_autostart_application("g15-indicator"))
        start_system_tray_on_login.set_active(g15desktop.is_autostart_application("g15-systemtray"))
        enable_gnome_shell_extension.set_active(g15desktop.is_gnome_shell_extension_enabled("gnome15-shell-extension@gnome15.org"))
        
        self.dialog.set_transient_for(parent)

    def run(self):
        notify_h = self.conf_client.notify_add("/apps/gnome15/global/plugins", self._plugins_changed)
        # Plugins
        self._load_plugins()

        if len(self.global_plugin_model) == 0:
            self.widget_tree.get_object("GlobalPluginsFrame").set_visible(False)
            self.dialog.set_size_request(-1, -1)
        elif self._get_selected_plugin() == None:
            self.global_plugin_tree.get_selection().select_path(self.global_plugin_model.get_path(self.global_plugin_model.get_iter(0)))
            self._select_plugin()

        self.dialog.run()
        self.dialog.hide()
        self.conf_client.notify_remove(notify_h)
        
    def _show_about_plugin(self, widget):
        plugin = self._get_selected_plugin()
        dialog = self.widget_tree.get_object("AboutPluginDialog")
        dialog.set_title("About %s" % plugin.name)
        dialog.run()
        dialog.hide()
        
    def _show_preferences(self, widget):
        plugin = self._get_selected_plugin()
        plugin.show_preferences(self.dialog, None, self.conf_client, "/apps/gnome15/global/plugins/%s" % plugin.id)
        
    def _get_selected_plugin(self):
        (model, path) = self.global_plugin_tree.get_selection().get_selected()
        if path != None:
            return g15pluginmanager.get_module_for_id(model[path][3])
        
    def _select_plugin(self, widget = None):       
        plugin = self._get_selected_plugin()
        if plugin != None:
            self.selected_id = plugin.id
            self.widget_tree.get_object("GlobalPluginNameLabel").set_text(plugin.name)
            self.widget_tree.get_object("GlobalDescriptionLabel").set_text(plugin.description)
            self.widget_tree.get_object("GlobalDescriptionLabel").set_use_markup(True)
            self.widget_tree.get_object("AuthorLabel").set_text(plugin.author)
            self.widget_tree.get_object("SupportedLabel").set_text(", ".join(g15pluginmanager.get_supported_models(plugin)).upper())
            self.widget_tree.get_object("CopyrightLabel").set_text(plugin.copyright)
            self.widget_tree.get_object("SiteLabel").set_uri(plugin.site)
            self.widget_tree.get_object("SiteLabel").set_label(plugin.site)
            self.widget_tree.get_object("GlobalPreferencesButton").set_sensitive(plugin.has_preferences)
            self.widget_tree.get_object("GlobalPluginDetails").set_visible(True)
        else:
            self.widget_tree.get_object("GlobalPluginDetails").set_visible(False)
        
    def _load_plugins(self):        
        self.global_plugin_model.clear()
        for mod in sorted(g15pluginmanager.imported_plugins, key=lambda key: key.name):
            if g15pluginmanager.is_global_plugin(mod):
                passive = g15pluginmanager.is_passive_plugin(mod)
                enabled = passive or self.conf_client.get_bool("/apps/gnome15/global/plugins/%s/enabled" % mod.id )
                self.global_plugin_model.append([enabled, not passive, mod.name, mod.id])
                if mod.id == self.selected_id:
                    self.global_plugin_tree.get_selection().select_path(self.global_plugin_model.get_path(self.global_plugin_model.get_iter(len(self.global_plugin_model) - 1)))
        
    def _plugins_changed(self, client, connection_id, entry, args):
        self._load_plugins()
        
    def _change_gnome_shell_extension(self, widget):
        g15desktop.set_gnome_shell_extension_enabled("gnome15-shell-extension@gnome15.org", widget.get_active())
        
    def _change_desktop_service(self, widget, application_name):
        g15desktop.set_autostart_application(application_name, widget.get_active())
            
    def _toggle_plugin(self, widget, path):
        plugin = g15pluginmanager.get_module_for_id(self.global_plugin_model[path][3])
        if plugin != None:
            key = "/apps/gnome15/global/plugins/%s/enabled" % plugin.id
            self.conf_client.set_bool(key, not self.conf_client.get_bool(key))
        

class G15Config:
    
    """
    Configuration user interface for Gnome15. Allows selection and configuration
    of the device, macros and enabled plugins.
    """
    
    adjusting = False

    def __init__(self, parent_window=None, service=None, options=None):
        self.parent_window = parent_window
        self._options = options
        self._controls_visible = False
        self.profile_save_timer = None
        self._signal_handles = []
        self.notify_handles = []
        self.control_notify_handles = []
        self.selected_id = None
        self.service = service
        self.conf_client = gconf.client_get_default()
        self.rows = None
        self.adjusting = False
        self.gnome15_service = None
        self.connected = False
        self.color_button = None
        self.screen_services = {}
        self.state = STOPPED
        self.driver = None
        self.selected_device = None
        self._last_no_devices = -1
        
        # Load main Glade file
        g15locale.get_translation("g15-config")
        g15Config = os.path.join(g15globals.ui_dir, 'g15-config.ui')
        self.widget_tree = gtk.Builder()
        self.widget_tree.set_translation_domain("g15-config")
        self.widget_tree.add_from_file(g15Config)
        self.main_window = self.widget_tree.get_object("MainWindow")
        
        # Make sure there is only one g15config running
        self.session_bus = dbus.SessionBus()
        try :
            G15ConfigService(self)
        except dbus.exceptions.NameExistsException as e:
            logger.debug("D-Bus service already running", exc_info = e)
            if self._options is not None and self._options.device_uid != "":
                self.session_bus.get_object(BUS_NAME, NAME).PresentWithDeviceUID(self._options.device_uid)
            else:
                self.session_bus.get_object(BUS_NAME, NAME).Present()
            self.session_bus.close()
            g15profile.notifier.stop()
            sys.exit()
            
        # Get the initially selected device
        self._default_device_name = self.conf_client.get_string("/apps/gnome15/config_device_name") \
            if self._options is None or self._options.device_uid == "" else self._options.device_uid

        # Widgets
        self.site_label = self.widget_tree.get_object("SiteLabel")
        self.cycle_screens = self.widget_tree.get_object("CycleScreens")
        self.cycle_screens_options = self.widget_tree.get_object("CycleScreensOptions")
        self.cycle_seconds = self.widget_tree.get_object("CycleAdjustment")
        self.cycle_seconds_widget = self.widget_tree.get_object("CycleSeconds")
        self.plugin_model = self.widget_tree.get_object("PluginModel")
        self.plugin_tree = self.widget_tree.get_object("PluginTree")
        self.plugin_enabled_renderer = self.widget_tree.get_object("PluginEnabledRenderer")
        self.main_vbox = self.widget_tree.get_object("MainVBox")
        self.profiles_tree = self.widget_tree.get_object("ProfilesTree")
        self.profileNameColumn = self.widget_tree.get_object("ProfileName")
        self.keyNameColumn = self.widget_tree.get_object("KeyName")
        self.macroNameColumn = self.widget_tree.get_object("MacroName")
        self.macro_list = self.widget_tree.get_object("MacroList")
        self.application = self.widget_tree.get_object("ApplicationLocation")
        self.m1 = self.widget_tree.get_object("M1") 
        self.m2 = self.widget_tree.get_object("M2") 
        self.m3 = self.widget_tree.get_object("M3")
        self.window_model = self.widget_tree.get_object("WindowModel")
        self.window_combo = self.widget_tree.get_object("WindowCombo")
        self.window_entry = self.widget_tree.get_object("WindowEntry")
        self.window_name = self.widget_tree.get_object("WindowName")
        self.window_select = self.widget_tree.get_object("WindowSelect")
        self.context_remove_profile = self.widget_tree.get_object("ContextRemoveProfile")
        self.context_activate_profile = self.widget_tree.get_object("ContextActivateProfile")
        self.context_lock_profile = self.widget_tree.get_object("LockProfile")
        self.context_unlock_profile = self.widget_tree.get_object("UnlockProfile")
        self.activate_on_focus = self.widget_tree.get_object("ActivateProfileOnFocusCheckbox")
        self.macro_name_renderer = self.widget_tree.get_object("MacroNameRenderer")
        self.profile_name_renderer = self.widget_tree.get_object("ProfileNameRenderer")
        self.window_label = self.widget_tree.get_object("WindowLabel")
        self.activate_by_default = self.widget_tree.get_object("ActivateByDefaultCheckbox")
        self.send_delays = self.widget_tree.get_object("SendDelaysCheckbox")
        self.fixed_delays = self.widget_tree.get_object("FixedDelaysCheckbox")
        self.release_delay = self.widget_tree.get_object("ReleaseDelay")
        self.press_delay = self.widget_tree.get_object("PressDelay")
        self.press_delay_adjustment = self.widget_tree.get_object("PressDelayAdjustment")
        self.release_delay_adjustment = self.widget_tree.get_object("ReleaseDelayAdjustment")
        self.profile_icon = self.widget_tree.get_object("ProfileIcon")
        self.background = self.widget_tree.get_object("Background")
        self.background_label = self.widget_tree.get_object("BackgroundLabel")
        self.icon_browse_button = self.widget_tree.get_object("BrowseForIcon")
        self.background_browse_button = self.widget_tree.get_object("BrowseForBackground")
        self.clear_icon_button = self.widget_tree.get_object("ClearIcon")
        self.clear_background_button = self.widget_tree.get_object("ClearBackground")
        self.macro_properties_button = self.widget_tree.get_object("MacroPropertiesButton")
        self.new_macro_button = self.widget_tree.get_object("NewMacroButton")
        self.delete_macro_button = self.widget_tree.get_object("DeleteMacroButton")
        self.memory_bank_vbox = self.widget_tree.get_object("MemoryBankVBox")      
        self.macros_model = self.widget_tree.get_object("MacroModel")     
        self.mapped_key_model = self.widget_tree.get_object("MappedKeyModel")
        self.profiles_model = self.widget_tree.get_object("ProfileModel")
        self.profiles_context_menu = self.widget_tree.get_object("ProfileContextMenu")
        self.device_model = self.widget_tree.get_object("DeviceModel")
        self.device_view = self.widget_tree.get_object("DeviceView")
        self.main_pane = self.widget_tree.get_object("MainPane")
        self.main_parent = self.widget_tree.get_object("MainParent")
        self.device_title = self.widget_tree.get_object("DeviceTitle")
        self.device_enabled = self.widget_tree.get_object("DeviceEnabled")
        self.tabs = self.widget_tree.get_object("Tabs")
        self.stop_service_button = self.widget_tree.get_object("StopServiceButton")
        self.driver_model = self.widget_tree.get_object("DriverModel")
        self.driver_combo = self.widget_tree.get_object("DriverCombo")
        self.global_options_button = self.widget_tree.get_object("GlobalOptionsButton")
        self.macro_edit_close_button = self.widget_tree.get_object("MacroEditCloseButton")
        self.key_table = self.widget_tree.get_object("KeyTable")
        self.key_frame = self.widget_tree.get_object("KeyFrame")
        self.memory_bank = self.widget_tree.get_object("MemoryBank")
        self.macros_tab = self.widget_tree.get_object("MacrosTab")
        self.macros_tab_label = self.widget_tree.get_object("MacrosTabLabel")
        self.keyboard_tab = self.widget_tree.get_object("KeyboardTab")
        self.plugins_tab = self.widget_tree.get_object("PluginsTab")
        self.profile_plugins_tab = self.widget_tree.get_object("ProfilePluginsTab")
        self.parent_profile_box = self.widget_tree.get_object("ParentProfileBox")
        self.parent_profile_label = self.widget_tree.get_object("ParentProfileLabel")
        self.parent_profile_model = self.widget_tree.get_object("ParentProfileModel")
        self.parent_profile_combo = self.widget_tree.get_object("ParentProfileCombo")
        self.profile_author = self.widget_tree.get_object("ProfileAuthor")
        self.export_profile = self.widget_tree.get_object("Export")
        self.import_profile = self.widget_tree.get_object("ImportButton")
        self.information_content = self.widget_tree.get_object("InformationContent")
        self.delays_content = self.widget_tree.get_object("DelaysContent")
        self.activation_content = self.widget_tree.get_object("ActivationContent")
        self.launch_pattern_box = self.widget_tree.get_object("LaunchPatternBox")
        self.activate_on_launch = self.widget_tree.get_object("ActivateOnLaunch")
        self.launch_pattern = self.widget_tree.get_object("LaunchPattern")
        self.theme_model = self.widget_tree.get_object("ThemeModel")
        self.theme_label = self.widget_tree.get_object("ThemeLabel")
        self.theme_combo = self.widget_tree.get_object("ThemeCombo")
        self.profile_plugins_mode_model = self.widget_tree.get_object("ProfilePluginsModeModel")
        self.profile_plugins_mode = self.widget_tree.get_object("ProfilePluginsMode")
        self.enabled_profile_plugins_model = self.widget_tree.get_object("EnabledProfilePluginsModel")
        self.enabled_profile_plugins = self.widget_tree.get_object("EnabledProfilePlugins")
        self.enabled_profile_plugins_renderer = self.widget_tree.get_object("EnabledProfilePluginsRenderer")
        self.device_settings = self.widget_tree.get_object("DeviceSettings")
        self.no_device_selected = self.widget_tree.get_object("NoDeviceSelected")
        self.no_driver_available = self.widget_tree.get_object("NoDriverAvailable")
        self.driver_options = self.widget_tree.get_object("DriverOptions")
        
        # Window 
        self.main_window.set_transient_for(self.parent_window)
        self.main_window.set_icon_from_file(g15icontools.get_app_icon(self.conf_client,  "gnome15"))
        
        # Monitor gconf
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        
        # Monitor macro profiles changing
        g15profile.profile_listeners.append(self._profiles_changed)         
        
        # Configure widgets    
        self.profiles_tree.get_selection().set_mode(gtk.SELECTION_SINGLE)        
        self.macro_list.get_selection().set_mode(gtk.SELECTION_SINGLE)   

        # Indicator options
        # TODO move this out of here        
        g15uigconf.configure_checkbox_from_gconf(self.conf_client, "/apps/gnome15/indicate_only_on_error", "OnlyShowIndicatorOnError", False, self.widget_tree, True)
        
        # Bind to events
        self.cycle_seconds.connect("value-changed", self._cycle_seconds_changed)
        self.cycle_screens.connect("toggled", self._cycle_screens_changed)
        self.site_label.connect("activate", self._open_site)
        self.plugin_tree.connect("cursor-changed", self._select_plugin)
        self.plugin_enabled_renderer.connect("toggled", self._toggle_plugin)        
        self.enabled_profile_plugins_renderer.connect("toggled", self._toggle_enabled_profile_plugins)
        self.widget_tree.get_object("PreferencesButton").connect("clicked", self._show_preferences)
        self.widget_tree.get_object("AboutPluginButton").connect("clicked", self._show_about_plugin)
        self.widget_tree.get_object("AddButton").connect("clicked", self._add_profile)
        self.widget_tree.get_object("ContextDuplicateProfile").connect("activate", self._copy_profile)
        self.context_activate_profile.connect("activate", self._activate)
        self.widget_tree.get_object("ContextExportProfile").connect("activate", self._export)
        self.context_unlock_profile.connect("activate", self._unlock_profile)
        self.context_lock_profile.connect("activate", self._lock_profile)
        self.activate_on_focus.connect("toggled", self._activate_on_focus_changed)
        self.activate_by_default.connect("toggled", self._activate_on_focus_changed)
        self.clear_icon_button.connect("clicked", self._clear_icon)
        self.clear_background_button.connect("clicked", self._clear_icon)
        self.delete_macro_button.connect("clicked", self._remove_macro)
        self.icon_browse_button.connect("clicked", self._browse_for_icon)
        self.background_browse_button.connect("clicked", self._browse_for_icon)
        self.macro_properties_button.connect("clicked", self._macro_properties)
        self.new_macro_button.connect("clicked", self._new_macro)
        self.macro_list.connect("cursor-changed", self._select_macro)
        self.macro_name_renderer.connect("edited", self._macro_name_edited)
        self.profile_name_renderer.connect("edited", self._profile_name_edited)
        self.m1.connect("toggled", self._memory_changed)
        self.m2.connect("toggled", self._memory_changed)
        self.m3.connect("toggled", self._memory_changed)
        self.profiles_tree.connect("cursor-changed", self._select_profile)
        self.profiles_tree.connect("button-press-event", self._show_profile_list_context)
        self.context_remove_profile.connect("activate", self._remove_profile)
        self.send_delays.connect("toggled", self._send_delays_changed)
        self.fixed_delays.connect("toggled", self._send_delays_changed)
        self.press_delay_adjustment.connect("value-changed", self._send_delays_changed)
        self.release_delay_adjustment.connect("value-changed", self._send_delays_changed)
        self.window_select.connect("clicked", self._select_window)
        self.window_name.connect("changed", self._window_name_changed)
        self.window_combo.connect("changed", self._window_name_changed)
        self.parent_profile_combo.connect("changed", self._parent_profile_changed)
        self.m1.connect("toggled", self._memory_changed)
        self.profile_author.connect("changed", self._profile_author_changed)
        self.stop_service_button.connect("clicked", self._stop_service)
        self.export_profile.connect("clicked", self._export)
        self.device_view.connect("selection-changed", self._device_selection_changed)
        self.device_enabled.connect("toggled", self._device_enabled_changed)
        self.driver_combo.connect("changed", self._driver_changed)
        self.theme_combo.connect("changed", self._theme_changed)
        self.profile_plugins_mode.connect("changed", self._profile_plugins_mode_changed)
        self.global_options_button.connect("clicked", self._show_global_options)
        self.macro_list.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.macro_list.connect("button_press_event", self._macro_list_clicked)
        self.import_profile.connect("clicked", self._import_profile)
        self.driver_options.connect('clicked', self._show_driver_options)
        
        # Enable profiles to be dropped onto the list
        self.macro_list.enable_model_drag_dest([('text/plain', 0, 0)],
                  gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY)
        self.macro_list.connect("drag-data-received", self._macro_profile_dropped)
        
        # Connection to BAMF for running applications list
        try :
            bamf_object = self.session_bus.get_object('org.ayatana.bamf', '/org/ayatana/bamf/matcher')     
            self.bamf_matcher = dbus.Interface(bamf_object, 'org.ayatana.bamf.matcher')
        except Exception as e:
            logger.warning("BAMF not available, falling back to WNCK", exc_info = e)
            self.bamf_matcher = None            
            import wnck
            self.screen = wnck.screen_get_default()
        
        # Show infobar component to start desktop service if it is not running
        self.infobar = gtk.InfoBar()    
        self.infobar.set_size_request(-1, 64)   
        self.warning_label = gtk.Label()
        self.warning_label.set_size_request(400, -1)
        self.warning_label.set_line_wrap(True)
        self.warning_label.set_alignment(0.0, 0.0)
        self.warning_image = gtk.Image()  
        
        # Start button
        self.stop_service_button.set_sensitive(False)
        button_vbox = gtk.VBox()
        self.start_button = None
        self.start_button = gtk.Button(_("Start Service"))
        self.start_button.connect("clicked", self._start_service)
        self.start_button.show()
        button_vbox.pack_start(self.start_button, False, False)
        
        # Populate model and configure other components
        self._load_devices()
        if len(self.device_model) == 0:
            raise Exception(_("No supported devices could be found. Is the " + \
                            "device correctly plugged in and powered and " + \
                            "do you have all the required drivers installed?"))
        else:
            if len(self.device_model) == 1 and not g15devices.is_enabled(self.conf_client, self.selected_device):
                self.device_enabled.set_active(True)
        
        # Build the infobar content
        content = self.infobar.get_content_area()
        content.pack_start(self.warning_image, False, False)
        content.pack_start(self.warning_label, True, True)
        content.pack_start(button_vbox, False, False)  
        
        # Add the bar to the glade built UI
        self.main_vbox.pack_start(self.infobar, False, False)
        self.warning_box_shown = False
        self.infobar.hide_all()
        
        self.gnome15_service = None

        # Watch for Gnome15 starting and stopping
        try :
            self._connect()
        except dbus.exceptions.DBusException as e:
            logger.debug("Failed to connect to service.", exc_info = e)
            self._disconnect()
        self.session_bus.add_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')
        
        # Watch for new devices (if pyudev is installed)
        g15devices.device_added_listeners.append(self._devices_changed)
        g15devices.device_removed_listeners.append(self._devices_changed) 
        
    def run(self):
        ''' Set up everything and display the window
        '''
        if len(self.devices) > 1:
            self.main_window.set_size_request(800, 600)
        else:            
            self.main_window.set_size_request(640, 600)
        self.id = None
        while True:
            opt = self.main_window.run()
            logger.debug("Option %s", str(opt))
            if opt != 1 and opt != 2:
                break
            
        self.main_window.hide()
        g15profile.notifier.stop()
        
    '''
    Private
    '''
    def _devices_changed(self, device = None):
        self._load_devices()
        
    def _name_owner_changed(self, name, old_owner, new_owner):
        if name == "org.gnome15.Gnome15":
            if old_owner == "" and not self.connected:
                self._connect()
            elif old_owner != "" and self.connected:
                self._disconnect()
        
    def __del__(self):
        self._remove_notify_handles()
        
    def _remove_notify_handles(self):
        for h in self.notify_handles:
            self.conf_client.notify_remove(h)
        self.notify_handles = []
            
    def _stop_service(self, event = None):
        self.gnome15_service.Stop(reply_handler = self._general_dbus_reply, error_handler = self._general_dbus_error)
        
    def _general_dbus_reply(self, *args):
        logger.info("DBUS reply %s", str(args))

    def _general_dbus_error(self, *args):
        logger.error("DBUS error %s", str(args))

    def _starting(self):
        logger.debug("Got starting signal")
        self.state = STARTING
        self._status_change()
        
    def _started(self):
        logger.debug("Got started signal")
        self.state = STARTED
        self._status_change()
        
    def _stopping(self):
        logger.debug("Got stopping signal")
        self.state = STOPPING
        self._status_change()
        
    def _stopped(self):
        logger.debug("Got stopped signal")
        self.state = STOPPED
        self._status_change()
            
    def _disconnect(self):
        for sig in self._signal_handles:
            self.session_bus.remove_signal_receiver(sig)
        self._signal_handles = []
        self.screen_services = {}
        self.state = STOPPED
        self._do_status_change()
        self.connected = False
        
    def _connect(self):
        self.gnome15_service = self.session_bus.get_object('org.gnome15.Gnome15', '/org/gnome15/Service')
            
        # Set initial status
        logger.debug("Getting state")
        if self.gnome15_service.IsStarting():
            logger.debug("State is starting")
            self.state = STARTING
        elif self.gnome15_service.IsStopping():
            logger.debug("State is stopping")
            self.state = STOPPING
        else:
            logger.debug("State is started")
            self.state = STARTED
            for screen_name in self.gnome15_service.GetScreens():
                logger.debug("Screen added %s", screen_name)
                screen_service =  self.session_bus.get_object('org.gnome15.Gnome15', screen_name)
                self.screen_services[screen_name] = screen_service
        
        # Watch for changes
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._starting, dbus_interface="org.gnome15.Service", signal_name='Starting'))
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._started, dbus_interface="org.gnome15.Service", signal_name='Started'))
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._stopping, dbus_interface="org.gnome15.Service", signal_name='Stopping'))  
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._stopped, dbus_interface="org.gnome15.Service", signal_name='Stopped'))  
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._screen_added, dbus_interface="org.gnome15.Service", signal_name='ScreenAdded'))  
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._screen_removed, dbus_interface="org.gnome15.Service", signal_name='ScreenRemoved'))
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._status_change, dbus_interface="org.gnome15.Screen", signal_name='Connected'))
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._status_change, dbus_interface="org.gnome15.Screen", signal_name='ConnectionFailed'))    
        self._signal_handles.append(self.session_bus.add_signal_receiver(self._status_change, dbus_interface="org.gnome15.Screen", signal_name='Disconnected'))
        self.connected = True
        self._do_status_change()
        
    def _screen_added(self, screen_name):
        logger.debug("Screen added %s", screen_name)
        screen_service =  self.session_bus.get_object('org.gnome15.Gnome15', screen_name)
        self.screen_services[screen_name] = screen_service
        gobject.idle_add(self._do_status_change)
        
    def _screen_removed(self, screen_name):
        logger.debug("Screen removed %s", screen_name)
        if screen_name in self.screen_services:
            del self.screen_services[screen_name]
        self._do_status_change()
        
    def _status_change(self, arg1 = None, arg2 = None, arg3 = None):
        gobject.idle_add(self._do_status_change)
        
    def _do_status_change(self):
        if not self.gnome15_service or self.state == STOPPED:         
            self.stop_service_button.set_sensitive(False)
            logger.debug("Stopped")
            self._show_message(gtk.MESSAGE_WARNING, _("The Gnome15 desktop service is not running. It is recommended " + \
                                      "you add <b>g15-desktop-service</b> as a <i>Startup Application</i>."))
        elif self.state == STARTING:        
            logger.debug("Starting up")
            self.stop_service_button.set_sensitive(False)   
            self._show_message(gtk.MESSAGE_WARNING, _("The Gnome15 desktop service is starting up. Please wait"), False)
        elif self.state == STOPPING:        
            logger.debug("Stopping")                
            self.stop_service_button.set_sensitive(False)
            self._show_message(gtk.MESSAGE_WARNING, _("The Gnome15 desktop service is stopping."), False)
        else:        
            logger.debug("Started - Checking status")          
            connected = 0
            first_error = ""
            for screen in self.screen_services:
                try:
                    if self.screen_services[screen].IsConnected():
                        connected += 1
                    else:
                        first_error = self.screen_services[screen].GetLastError() 
                except dbus.DBusException as e:
                    logger.debug("D-Bus communication error", exc_info = e)
                    pass
            
            logger.debug("Found %d of %d connected", connected, len(self.screen_services))
            screen_count = len(self.screen_services)
            if connected != screen_count and first_error is not None and first_error != "":
                if len(self.screen_services) == 1:
                    self._show_message(gtk.MESSAGE_WARNING, _("The Gnome15 desktop service is running, but failed to connect " + \
                                      "to the keyboard driver. The error message given was <b>%s</b>") % first_error, False)
                else:
                    mesg = ("The Gnome15 desktop service is running, but only %d out of %d keyboards are connected. The first error message given was %s") % ( connected, screen_count, first_error )
                    self._show_message(gtk.MESSAGE_WARNING, mesg, False)
            else:
                self._hide_warning()
            self.stop_service_button.set_sensitive(True)
        
    def _hide_warning(self):
        self.warning_box_shown = False    
        self.infobar.hide_all()
        self.main_window.check_resize()
        
    def _start_service(self, widget):
        widget.set_sensitive(False)
        g15os.run_script("g15-desktop-service", ["-f"])
    
    def _show_message(self, type, text, start_service_button = True):
        self.infobar.set_message_type(type)
        if self.start_button != None:
            self.start_button.set_sensitive(True)
            self.start_button.set_visible(start_service_button)
        self.warning_label.set_text(text)
        self.warning_label.set_use_markup(True)

        if type == gtk.MESSAGE_WARNING:
            self.warning_image.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
#            self.warning_label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.Color(0, 0, 0))
        
        self.main_window.check_resize()        
        self.infobar.show_all()
        if self.start_button != None and not start_service_button:
            self.start_button.hide()
        self.warning_box_shown = True
        
    def _open_site(self, widget):
        subprocess.Popen(['xdg-open',widget.get_uri()])
        
    def _to_rgb(self, string_rgb):
        rgb = string_rgb.split(",")
        return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        
    def _to_color(self, rgb):
        return gtk.gdk.Color(rgb[0] <<8, rgb[1] <<8,rgb[2] <<8)
            
    def _color_chosen(self, widget, control):
        color = widget.color
        self.conf_client.set_string(self._get_full_key(control.id), "%d,%d,%d" % ( color[0],color[1],color[2]))
        
    def _control_changed(self, widget, control):
        if control.hint & g15driver.HINT_SWITCH != 0:
            val = 0
            if widget.get_active():
                val = 1
            self.conf_client.set_int(self._get_full_key(control.id), val)
        else:
            self.conf_client.set_int(self._get_full_key(control.id), int(widget.get_value()))
    
    def _show_preferences(self, widget):
        plugin = self._get_selected_plugin()
        plugin.show_preferences(self.main_window, self.driver, self.conf_client, self._get_full_key("plugins/%s" % plugin.id))
    
    def _show_about_plugin(self, widget):
        plugin = self._get_selected_plugin()
        dialog = self.widget_tree.get_object("AboutPluginDialog")
        dialog.set_title("About %s" % plugin.name)
        dialog.run()
        dialog.hide()
        
    def _load_macro_state(self):
        device_info = g15devices.get_device_info(self.driver.get_model_name()) if self.driver is not None else None
        self.macros_tab.set_visible(device_info is not None and device_info.macros)
        self.macros_tab_label.set_visible(device_info is not None and device_info.macros)
            
        # Hide memory bank if there are no M-Keys
        self.memory_bank.set_visible(self.driver != None and self.driver.has_memory_bank())
        
    def _load_plugins(self):
        """
        Loads what drivers and plugins are appropriate for the selected
        device
        """
        self.plugin_model.clear()
        if self.selected_device:
            # Plugins appropriate
            for mod in sorted(g15pluginmanager.imported_plugins, key=lambda key: key.name):
                key = self._get_full_key("plugins/%s/enabled" % mod.id )
                if self.driver and self.driver.get_model_name() in g15pluginmanager.get_supported_models(mod) and not g15pluginmanager.is_global_plugin(mod):
                    enabled = self.conf_client.get_bool(key)
                    self.plugin_model.append([enabled, mod.name, mod.id])
                    if mod.id == self.selected_id:
                        self.plugin_tree.get_selection().select_path(self.plugin_model.get_path(self.plugin_model.get_iter(len(self.plugin_model) - 1)))
            if len(self.plugin_model) > 0 and self._get_selected_plugin() == None:            
                self.plugin_tree.get_selection().select_path(self.plugin_model.get_path(self.plugin_model.get_iter(0)))
        
        self._select_plugin(None)
        self._set_tab_status()
        
    def _load_drivers(self):
        self.driver_model.clear()
        if self.selected_device:
            for driver_mod_key in list(g15drivermanager.imported_drivers):
                driver_mod = g15drivermanager.imported_drivers[driver_mod_key]
                try:
                    driver = driver_mod.Driver(self.selected_device)
                    if self.selected_device.model_id in driver.get_model_names():
                        self.driver_model.append((driver_mod.id, driver_mod.name))
                except Exception as e:
                    logger.info("Failed to load driver.", exc_info = e)
            
        self.driver_combo.set_sensitive(len(self.driver_model) > 1)
        self._set_driver_from_configuration()
        
    def _get_selected_plugin(self):
        (model, path) = self.plugin_tree.get_selection().get_selected()
        if path != None:
            return g15pluginmanager.get_module_for_id(model[path][2])
        
    def _toggle_enabled_profile_plugins(self, widget, path):
        row = self.enabled_profile_plugins_model[path]
        plugin_id = row[2]
        plugin = g15pluginmanager.get_module_for_id(plugin_id)
        if plugin != None:
            if plugin.id in self.selected_profile.selected_plugins:
                self.selected_profile.selected_plugins.remove(plugin.id)
            else:
                self.selected_profile.selected_plugins.append(plugin.id)
            self._load_enabled_profile_plugins()
            self._save_profile(self.selected_profile)
            
    def _toggle_plugin(self, widget, path):
        plugin = g15pluginmanager.get_module_for_id(self.plugin_model[path][2])
        if plugin != None:
            key = self._get_full_key("plugins/%s/enabled" % plugin.id )
            self.conf_client.set_bool(key, not self.conf_client.get_bool(key))
            
    def _select_plugin(self, widget):       
        plugin = self._get_selected_plugin()
        if plugin != None:
            self.selected_id = plugin.id
            self.widget_tree.get_object("PluginNameLabel").set_text(plugin.name)
            self.widget_tree.get_object("DescriptionLabel").set_text(plugin.description)
            self.widget_tree.get_object("DescriptionLabel").set_use_markup(True)
            self.widget_tree.get_object("AuthorLabel").set_text(plugin.author)
            self.widget_tree.get_object("SupportedLabel").set_text(", ".join(g15pluginmanager.get_supported_models(plugin)).upper())
            self.widget_tree.get_object("CopyrightLabel").set_text(plugin.copyright)
            self.widget_tree.get_object("SiteLabel").set_uri(plugin.site)
            self.widget_tree.get_object("SiteLabel").set_label(plugin.site)
            self.widget_tree.get_object("PreferencesButton").set_sensitive(plugin.has_preferences and self.driver is not None)
            self.widget_tree.get_object("PluginDetails").set_visible(True)
            
            themes = g15theme.get_themes(self.selected_device.model_id, plugin)
            self.theme_model.clear()
            if len(themes) > 1:
                key  = self._get_full_key("plugins/%s/theme" % plugin.id )
                plugin_theme = self.conf_client.get_string(key)
                if plugin_theme is None:
                    plugin_theme = "default"
                for i, t in enumerate(themes):
                    self.theme_model.append([t.theme_id,t.name])
                    if t.theme_id == plugin_theme:
                        self.theme_combo.set_active(i)
                self.theme_label.set_visible(True)
                self.theme_combo.set_visible(True)
            else:
                self.theme_label.set_visible(False)
                self.theme_combo.set_visible(False)
        else:
            self.widget_tree.get_object("PluginDetails").set_visible(False)
            
        # List the keys that are required for each action
        for c in self.key_table.get_children():
            self.key_table.remove(c)
        actions = g15pluginmanager.get_actions(plugin, self.selected_device)
        rows = len(actions) 
        if  rows > 0:
            self.key_table.set_property("n-rows", rows)         
        row = 0
        active_profile = g15profile.get_active_profile(self.driver.device) if self.driver is not None else None
        if active_profile is None:
            logger.warning("No active profile found. It's possible the profile no longer exists, or is supplied with a plugin that cannot be found.")
        else:
            bindings = []
            for action_id in actions:
                # First try the active profile to see if the action has been re-mapped
                action_binding = None
                for state in [ g15driver.KEY_STATE_UP, g15driver.KEY_STATE_HELD ]:
                    action_binding = active_profile.get_binding_for_action(state, action_id)
                    if action_binding is None:
                        # No other keys bound to action, try the device defaults
                        device_info = g15devices.get_device_info(self.driver.get_model_name())                
                        if action_id in device_info.action_keys:
                            action_binding = device_info.action_keys[action_id]
                            break
                    else:
                        break
                
                if action_binding is not None:
                    bindings.append(action_binding)
                else:
                    logger.warning("Plugin %s requires an action that is not available (%s)",
                                   plugin.id, action_id)
                    
            bindings = sorted(bindings)
                    
            for action_binding in bindings:
                # If hold
                label = gtk.Label("")
                label.set_size_request(40, -1)
                if action_binding.state == g15driver.KEY_STATE_HELD:
                    label.set_text(_("<b>Hold</b>"))
                    label.set_use_markup(True)
                label.set_alignment(0.0, 0.5)
                self.key_table.attach(label, 0, 1, row, row + 1,  xoptions = gtk.FILL, xpadding = 4, ypadding = 2);
                label.show()
                
                # Keys
                keys = gtk.HBox(spacing = 4)
                for k in action_binding.keys:
                    fname = os.path.abspath("%s/key-%s.png" % (g15globals.image_dir, k))
                    pixbuf = gtk.gdk.pixbuf_new_from_file(fname)
                    pixbuf = pixbuf.scale_simple(22, 14, gtk.gdk.INTERP_BILINEAR)
                    img = gtk.image_new_from_pixbuf(pixbuf)
                    img.show()
                    keys.add(img)
                keys.show()
                self.key_table.attach(keys, 1, 2, row, row + 1,  xoptions = gtk.FILL, xpadding = 4, ypadding = 2)
                
                # Text
                label = gtk.Label(actions[action_binding.action])
                label.set_alignment(0.0, 0.5)
                label.show()
                self.key_table.attach(label, 2, 3, row, row + 1,  xoptions = gtk.FILL, xpadding = 4, ypadding = 2)
                row += 1
                    
            
        if row > 0:
            self.key_frame.set_visible(True)
        else:   
            self.key_frame.set_visible(False)
            
    def _macro_profile_dropped(self, widget, context, x, y, selection, info, timestamp):       
#        print '\n'.join([str(t) for t in context.targets])
        return True     

    def _set_cycle_seconds_value_from_configuration(self):
        val = self.conf_client.get(self._get_full_key("cycle_seconds"))
        time = 10
        if val != None:
            time = val.get_int()
        if time != self.cycle_seconds.get_value():
            self.cycle_seconds.set_value(time)
            
    def _set_cycle_screens_value_from_configuration(self):
        val = g15gconf.get_bool_or_default(self.conf_client, self._get_full_key("cycle_screens"), True)
        self.cycle_seconds_widget.set_sensitive(val)
        if val != self.cycle_screens.get_active():
            self.cycle_screens.set_active(val)
            
    def _control_configuration_changed(self, client, connection_id, entry, args):
        widget = args[1]
        control = args[0]
        if isinstance(control.value, int):
            if control.hint & g15driver.HINT_SWITCH != 0:
                widget.set_active(entry.value.get_int() == 1)
            else:
                widget.set_value(entry.value.get_int())
        else:
            widget.set_color(self._to_rgb(entry.value.get_string()))

    def _cycle_screens_configuration_changed(self, client, connection_id, entry, args):
        self._set_cycle_screens_value_from_configuration()
        
    def _cycle_seconds_configuration_changed(self, client, connection_id, entry, args):
        self._set_cycle_seconds_value_from_configuration()
        
    def _plugins_changed(self, client, connection_id, entry, args):
        self._load_plugins()
        self._load_macro_state()
        self._load_drivers()
        self._load_enabled_profile_plugins()
        
    def _cycle_screens_changed(self, widget=None):
        self.conf_client.set_bool(self._get_full_key("cycle_screens"), self.cycle_screens.get_active())
        
    def _cycle_seconds_changed(self, widget):
        val = int(self.cycle_seconds.get_value())
        self.conf_client.set_int(self._get_full_key("cycle_seconds"), val)
        
    def _create_color_icon(self, color):
        draw = gtk.Image()
        pixmap = gtk.gdk.Pixmap(None, 16, 16, 24)
        cr = pixmap.cairo_create()
        cr.set_source_rgb(float(color[0]) / 255.0, float(color[1]) / 255.0, float(color[2]) / 255.0)
        cr.rectangle(0, 0, 16, 16)
        cr.fill()
        draw.set_from_pixmap(pixmap, None)
        return draw
    
    def _active_profile_changed(self, client, connection_id, entry, args):
        self._load_profile_list()
        
    def _send_delays_changed(self, widget=None):
        if not self.adjusting:
            self.selected_profile.send_delays = self.send_delays.get_active()
            self.selected_profile.fixed_delays = self.fixed_delays.get_active()
            self.selected_profile.press_delay = int(self.press_delay_adjustment.get_value() * 1000)
            self.selected_profile.release_delay = int(self.release_delay_adjustment.get_value() * 1000)
            self._save_profile(self.selected_profile)
            self._set_delay_state()
            
    def _set_delay_state(self):
        self.fixed_delays.set_sensitive(self.selected_profile.send_delays)
        self.press_delay.set_sensitive(self.selected_profile.fixed_delays and self.selected_profile.send_delays)
        self.release_delay.set_sensitive(self.selected_profile.fixed_delays and self.selected_profile.send_delays)
        
    def _activate_on_focus_changed(self, widget=None):
        if not self.adjusting:
            self.selected_profile.activate_on_focus = widget.get_active()   
            self._set_available_profile_actions()
            self._save_profile(self.selected_profile)
            
    def _parent_profile_changed(self, widget):
        if not self.adjusting:
            sel = self.parent_profile_combo.get_active()
            self.selected_profile.base_profile = self.parent_profile_model[sel][0] if sel > 0 else None 
            self._save_profile(self.selected_profile)
        
    def _window_name_changed(self, widget):
        if isinstance(widget, gtk.ComboBox):
            active = widget.get_active()
            if active >= 0:
                self.window_name.set_text(self.window_model[active][0])
        else:
            if widget.get_text() != self.selected_profile.window_name: 
                self.selected_profile.window_name = widget.get_text()
                if self.bamf_matcher != None:
                    for window in self.bamf_matcher.RunningApplications():
                        app = self.session_bus.get_object("org.ayatana.bamf", window)
                        view = dbus.Interface(app, 'org.ayatana.bamf.view')
                        if view.Name() == self.selected_profile.window_name:
                            icon = view.Icon()
                            if icon != None:
                                icon_path = g15icontools.get_icon_path(icon)
                                if icon_path != None:
                                    # We need to copy the icon as it may be temporary
                                    copy_path = os.path.join(icons_dir, os.path.basename(icon_path))
                                    shutil.copy(icon_path, copy_path)
                                    self.selected_profile.icon = copy_path
                                    self._set_image(self.profile_icon, copy_path)
                else:                    
                    import wnck           
                    for window in wnck.screen_get_default().get_windows():
                        if window.get_name() == self.selected_profile.window_name:
                            icon = window.get_icon()
                            if icon != None:
                                filename = os.path.join(icons_dir,"%d.png" % self.selected_profile.id)
                                icon.save(filename, "png")
                                self.selected_profile.icon = filename    
                                self._set_image(self.profile_icon, filename)
                            
                self._save_profile(self.selected_profile)
                
    def _driver_configuration_changed(self, *args):
        self._set_driver_from_configuration()
        self._load_plugins()
        self._add_controls()
        
    def _set_driver_from_configuration(self):        
        selected_driver = self.conf_client.get_string(self._get_full_key("driver"))
        i = 0
        sel = False
        for ( driver_id, driver_name ) in self.driver_model:
            if driver_id == selected_driver:
                self.driver_combo.set_active(i)
                sel = True
            i += 1
        if len(self.driver_model) > 0 and not sel:            
            self.conf_client.set_string(self._get_full_key("driver"), self.driver_model[0][0])
        else:
            driver_mod = g15drivermanager.get_driver_mod(selected_driver)
            
            # Show or hide the Keyboard / Plugins tab depending on if there is a driver that matches
            if not driver_mod:
                self.no_driver_available.set_label(_("There is no appropriate driver for the " + \
                                                     "device <b>%s</b>.\nDo you have all the " + \
                                                     "required packages installed?") \
                                                   % self.selected_device.model_fullname)
                self.tabs.set_visible(False)
                self.no_driver_available.set_visible(True)
            else:                
                self.driver_options.set_sensitive(driver_mod.has_preferences)
                self.tabs.set_visible(True)
                self.no_driver_available.set_visible(False)
                
    def _show_driver_options(self, widget):
        selected_driver = self.conf_client.get_string(self._get_full_key("driver"))
        driver_mod = g15drivermanager.get_driver_mod(selected_driver)
        driver_mod.show_preferences(self.selected_device,
                                    self.main_window,
                                    self.conf_client)

    def _set_tab_status(self):
        self.keyboard_tab.set_visible(self._controls_visible)
        self.plugins_tab.set_visible(len(self.plugin_model) > 0)
        self.profile_plugins_tab.set_visible(len(self.plugin_model) > 0)
            
    def _driver_options_changed(self):
        self._add_controls()
        self._load_plugins()
        self._load_macro_state()
        self._hide_warning()
            
    def _device_enabled_configuration_changed(self, client, connection_id, entry, args):
        self._set_enabled_value_from_configuration()
        
    def _set_enabled_value_from_configuration(self):        
        enabled = g15devices.is_enabled(self.conf_client, self.selected_device) if self.selected_device != None else False        
        self.device_enabled.set_active(enabled)
        self.device_enabled.set_sensitive(self.selected_device != None)
        self.tabs.set_sensitive(enabled)
                
    def _device_enabled_changed(self, widget = None):
        gobject.idle_add(self._set_device)
        
    def _theme_changed(self, widget = None):
        if not self.adjusting:
            sel = widget.get_active()
            if sel >= 0:
                key  = self._get_full_key("plugins/%s/theme" % self._get_selected_plugin().id )
                path = self.theme_model.get_iter(sel)
                self.conf_client.set_string(key, self.theme_model[path][0])
                
    def _driver_changed(self, widget = None):
        if len(self.driver_model) > 0:
            sel = self.driver_combo.get_active()
            if sel >= 0:
                row = self.driver_model[sel]
                current =  self.conf_client.get_string(self._get_full_key("driver"))
                if not current or row[0] != current:
                    self.conf_client.set_string(self._get_full_key("driver"), row[0])
        
    def _set_device(self):
        if self.selected_device:
            g15devices.set_enabled(self.conf_client, self.selected_device, self.device_enabled.get_active())
        
    def _memory_changed(self, widget):
        self._load_profile(self.selected_profile)
        
    def _device_selection_changed(self, widget):
        self._load_device()
        if self.selected_device:
            self.conf_client.set_string("/apps/gnome15/config_device_name", self.selected_device.uid)
            self.device_settings.set_visible(True)
            self.no_device_selected.set_visible(False)
        else:
            self.device_settings.set_visible(False)
            self.no_device_selected.set_visible(True)
    
    def _load_device(self):
        sel_items = self.device_view.get_selected_items()
        sel_idx = sel_items[0][0] if len(sel_items) > 0 else -1
        self.selected_device = self.devices[sel_idx] if sel_idx > -1 and sel_idx < len(self.devices) else None
        if self.selected_device:
            self._load_drivers()
        self._remove_notify_handles()
        self.device_title.set_text(self.selected_device.model_fullname if self.selected_device else "")
        self._set_enabled_value_from_configuration()
        if self.selected_device != None:            
            self.conf_client.add_dir(self._get_device_conf_key(), gconf.CLIENT_PRELOAD_NONE)   
            self.notify_handles.append(self.conf_client.notify_add(self._get_full_key("cycle_seconds"), self._cycle_seconds_configuration_changed));
            self.notify_handles.append(self.conf_client.notify_add(self._get_full_key("cycle_screens"), self._cycle_screens_configuration_changed));
            self.notify_handles.append(self.conf_client.notify_add(self._get_full_key("plugins"), self._plugins_changed))
            self.notify_handles.append(self.conf_client.notify_add(self._get_full_key("active_profile"), self._active_profile_changed))
            self.notify_handles.append(self.conf_client.notify_add(self._get_full_key("locked"), self._active_profile_changed))
            self.notify_handles.append(self.conf_client.notify_add(self._get_full_key("enabled"), self._device_enabled_configuration_changed))
            self.notify_handles.append(self.conf_client.notify_add(self._get_full_key("driver"), self._driver_configuration_changed))
            self.selected_profile = g15profile.get_active_profile(self.selected_device)  
            self._set_cycle_seconds_value_from_configuration()
            self._set_cycle_screens_value_from_configuration()
        self.selected_profile = None
        self._add_controls()
        self.main_window.show_all()
        self._load_profile_list()
        self._load_plugins()
        self._load_macro_state()
        self._load_windows()
        self._do_status_change()
        self._set_tab_status()
        
    def _get_device_conf_key(self):
        return "/apps/gnome15/%s" % self.selected_device.uid
    
    def _get_full_key(self, key):
        return "%s/%s" % (self._get_device_conf_key(), key)
        
    def _select_profile(self, widget):
        (model, path) = self.profiles_tree.get_selection().get_selected()
        self.selected_profile = g15profile.get_profile(self.selected_device, model[path][2])
        self._load_profile(self.selected_profile)
        
    def _select_macro(self, widget):
        self._set_available_actions()
        
    def _set_available_actions(self):
        (_, path) = self.macro_list.get_selection().get_selected()
        self.delete_macro_button.set_sensitive(path != None and not self.selected_profile.read_only)
        self.macro_properties_button.set_sensitive(path != None)
        
    def _set_available_profile_actions(self):
        sel = self.profile_plugins_mode.get_active()
        path = self.profile_plugins_mode_model.get_iter(sel)
        self.enabled_profile_plugins.set_sensitive(not self.selected_profile.read_only and self.profile_plugins_mode_model[path][0] == g15profile.SELECTED_PLUGINS) 
        self.window_name.set_sensitive(not self.selected_profile.read_only and self.selected_profile.activate_on_focus)        
        self.window_select.set_sensitive(not self.selected_profile.read_only and self.selected_profile.activate_on_focus)
        
    def _activate(self, widget):
        (model, path) = self.profiles_tree.get_selection().get_selected()
        self._make_active(g15profile.get_profile(self.selected_device,  model[path][2]))
        
    def _make_active(self, profile): 
        profile.make_active()
        self._load_profile_list()
    
    def _profile_plugins_mode_changed(self, widget = None):
        if not self.adjusting:
            sel = widget.get_active()
            path = self.profile_plugins_mode_model.get_iter(sel)
            self.selected_profile.plugins_mode = self.profile_plugins_mode_model[path][0] 
            self._set_available_profile_actions()
            self._save_profile(self.selected_profile)
        
    def _clear_icon(self, widget):
        if widget == self.clear_icon_button:
            self.selected_profile.icon = ""
            self._set_image(self.profile_icon, "")
        else:    
            self.selected_profile.background = ""
            self._set_image(self.background, "") 
        self._save_profile(self.selected_profile)
        
    def _add_macro_filters(self, dialog):
        macros_filter = gtk.FileFilter()
        macros_filter.set_name("Macro Archives")
        macros_filter.add_pattern("*.mzip")
        dialog.add_filter(macros_filter)
        all_filter = gtk.FileFilter()
        all_filter.set_name("All files")
        all_filter.add_pattern("*")
        dialog.add_filter(all_filter)
        
    def _import_profile(self, widget):
        dialog = gtk.FileChooserDialog("Import..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.main_window)
        self._add_macro_filters(dialog)
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:
            import_filename = dialog.get_filename()
            profile_dir = g15profile.get_profile_dir(self.selected_device)
            file = zipfile.ZipFile(import_filename, "r")
            
            profile_id = g15profile.generate_profile_id()
            
            try:
                everything_ok = False
                error = ""

                zip_contents = file.namelist();

                # Check if there is a macro file
                macro_filename = ""
                for filename in zip_contents:
                    if filename.endswith(".macros"):
                        everything_ok = True
                        macro_filename = filename
                        break
                else:
                    error = "Invalid archive (missing .macros file)"

                if everything_ok:
                    # Parse and handle the macro file
                    file_split = macro_filename.split(".", 1)
                        
                    dest_name = "%d.%s" % ( profile_id, file_split[1])
                    
                    # Read the profile so we can adjust for the new environment
                    profiles = g15profile.get_profiles(self.selected_device)
                    macro_file = file.open(macro_filename, 'r')
                    try:
                        imported_profile = g15profile.G15Profile(self.selected_device)
                        imported_profile.load(None, macro_file)
                        imported_profile.set_id(profile_id)
                    finally:
                        macro_file.close()

                    if self.selected_device.model_id not in imported_profile.models:
                        everything_ok = False
                        error = "The profile you imported was made for another device."

                    if everything_ok:
                        # Find the best new name for the profile
                        new_name = imported_profile.name
                        idx = 1
                        while True:
                            found = False
                            for p in profiles:
                                if new_name == p.name:
                                    found = True
                                    break
                            if found:
                                idx += 1
                                new_name = "%s (%d)" % (imported_profile.name, idx)
                            else:
                                break
                        imported_profile.name = new_name
                        
                        # Set the icons
                        if imported_profile.icon:
                            imported_profile.icon = "%s/%d.%s" % ( profile_dir, profile_id, imported_profile.icon.split(".", 1)[1] )
                        if imported_profile.background:
                            imported_profile.background = "%s/%d.%s" % ( profile_dir, profile_id, imported_profile.background.split(".", 1)[1] )
                            
                        # Actually save
                        g15profile.create_profile(imported_profile)

                        # Import the other files
                        for filename in zip_contents:
                            file_split = filename.split(".", 1)

                            dest_name = "%d.%s" % ( profile_id, file_split[1])

                            if not dest_name.endswith(".macros"):
                                # Just extract all other files
                                dest_dir = os.path.join(profile_dir, os.path.dirname(dest_name))
                                g15os.mkdir_p(dest_dir)
                                macro_file = file.open(filename, 'r')
                                try:
                                    out_file = open(os.path.join(dest_dir, os.path.basename(dest_name)), 'w')
                                    try:
                                        out_file.write(macro_file.read())
                                    finally:
                                        out_file.close()
                                finally:
                                    macro_file.close()

                # If there was an error when importing display an error message
                if not everything_ok:
                    import_profile_error_dialog = self.widget_tree.get_object("ImportProfileError")
                    import_profile_error_dialog.set_transient_for(self.main_window)
                    import_profile_error_dialog.format_secondary_text(error)
                    import_profile_error_dialog_close_button = self.widget_tree.get_object("ImportProfileErrorCloseButton")
                    import_profile_error_dialog_close_button.connect("clicked", lambda x: import_profile_error_dialog.hide())
                    import_profile_error_dialog.run()

            finally:
                file.close()
            
        dialog.destroy()
        
    def _lock_profile(self, widget):
        if g15profile.is_locked(self.selected_device):
            g15profile.set_locked(self.selected_device, False)
        if not self.selected_profile.is_active():
            self.selected_profile.make_active()
        g15profile.set_locked(self.selected_device, True)
        
    def _unlock_profile(self, widget):
        g15profile.set_locked(self.selected_device, False)
        
    def _export(self, widget):
        dialog = gtk.FileChooserDialog("Export..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_SAVE,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.main_window)
        dialog.set_filename(os.path.expanduser("~/%s.mzip" % self.selected_profile.name))
        self._add_macro_filters(dialog)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            export_file = dialog.get_filename()
            if not export_file.lower().endswith(".mzip"):
                export_file += ".mzip"
                
            self.selected_profile.export(export_file)
        dialog.destroy()
        
    def _browse_for_icon(self, widget):
        dialog = gtk.FileChooserDialog("Open..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.main_window)
        if widget == self.icon_browse_button:
            dialog.set_filename(self.selected_profile.icon)
        else:
            dialog.set_filename(self.selected_profile.background)
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        
        dialog.add_filter(filter)
        
        filter = gtk.FileFilter()
        filter.set_name("Images")
        filter.add_mime_type("image/png")
        filter.add_mime_type("image/jpeg")
        filter.add_mime_type("image/gif")
        filter.add_pattern("*.png")
        filter.add_pattern("*.jpg")
        filter.add_pattern("*.jpeg")
        filter.add_pattern("*.gif")
        dialog.add_filter(filter)
        
        response = dialog.run()
        
        if response == gtk.RESPONSE_OK:
            if widget == self.icon_browse_button:
                self.selected_profile.icon = dialog.get_filename()                
                self._set_image(self.profile_icon, self.selected_profile.icon) 
            else: 
                self.selected_profile.background = dialog.get_filename()          
                self._set_image(self.background, self.selected_profile.background)
            self._save_profile(self.selected_profile)
            
        dialog.destroy()
        
    def _remove_profile(self, widget):
        dialog = self.widget_tree.get_object("ConfirmRemoveProfileDialog")  
        dialog.set_transient_for(self.main_window)
        response = dialog.run()
        dialog.hide()
        if response == 1:
            active_profile = g15profile.get_active_profile(self.selected_device)
            if active_profile is not None and self.selected_profile.id == active_profile.id:
                if g15profile.is_locked(self.selected_device):
                    g15profile.set_locked(self.selected_device, False)
                self._make_active(g15profile.get_profile(self.selected_device, 0))
            self.selected_profile.delete()
            self.profiles.remove(self.selected_profile)
            if len(self.profiles) > 0:
                self.selected_profile = self.profiles[0]
            self._load_profile_list()
            
    def _profile_author_changed(self, widget):
        if not self.adjusting:
            self.selected_profile.author = widget.get_text()
            self._save_profile(self.selected_profile)
        
    def _new_macro(self, widget):
        memory = self._get_memory_number()
        
        # Find the next free G-Key
        use = None
        for row in self.driver.get_key_layout():
            if not use:
                for key in row:                
                    reserved = g15devices.are_keys_reserved(self.driver.get_model_name(), list(key))
                    in_use = self.selected_profile.are_keys_in_use(g15driver.KEY_STATE_UP, memory, [ key ])
                    if not in_use and not reserved:
                        use = key
                        break
                    
        if use:
            macro = self.selected_profile.create_macro(memory, [use], 
                                                       _("Macro %s") % " ".join(g15driver.get_key_names([use])),
                                                       g15profile.MACRO_SIMPLE, 
                                                       "", 
                                                       g15driver.KEY_STATE_UP)
            self._edit_macro(macro)
        else:
            logger.warning("No free keys")
        
    def _macro_properties(self, widget):
        self._edit_macro(self._get_selected_macro())
        
    def _get_selected_macro(self):        
        (model, path) = self.macro_list.get_selection().get_selected()
        if model and path:
            row = model[path]
            return self.selected_profile.get_macro(row[4], 
                                                   self._get_memory_number(), 
                                                   g15profile.get_keys_from_key(row[2]))
        
    def _select_window(self, widget):
        dialog = self.widget_tree.get_object("SelectWindowDialog")  
        dialog.set_transient_for(self.main_window)
        dialog.run()
        dialog.hide()
        
    def _edit_macro(self, macro):
        macro_editor = g15macroeditor.G15MacroEditor(self.main_window)
        macro_editor.set_driver(self.driver)
        macro_editor.set_macro(macro)
        macro_editor.run()
        
    def _remove_macro(self, widget):
        memory = self._get_memory_number()
        (model, path) = self.macro_list.get_selection().get_selected()
        key_list_key = model[path][2]
        activate_on = model[path][4]
        dialog = self.widget_tree.get_object("ConfirmRemoveMacroDialog") 
        dialog.set_transient_for(self.main_window)
        response = dialog.run()
        dialog.hide()
        if response == 1:
            keys = g15profile.get_keys_from_key(key_list_key)
            self.selected_profile.delete_macro(activate_on, memory, keys)
            self._load_profile_list()
            
    def _save_profile(self, profile):
        if not self.adjusting:
            if self.profile_save_timer is not None:
                self.profile_save_timer.cancel()
            self.profile_save_timer = g15scheduler.schedule("SaveProfile", 2, self._do_save_profile, profile)
            
    def _do_save_profile(self, profile):
        logger.info("Saving profile %s", profile.name)
        profile.save()
            
    global_config = None
    def _show_global_options(self, widget): 
        if self.global_config is None:
           self.global_config = G15GlobalConfig(self.main_window, self.widget_tree, self.conf_client)
        self.global_config.run()
        
    def _add_profile(self, widget):
        dialog = self.widget_tree.get_object("NewProfileDialog") 
        dialog.set_transient_for(self.main_window) 
        response = dialog.run()
        dialog.hide()
        if response == 1:
            new_profile_name = self.widget_tree.get_object("NewProfileName").get_text()
            new_profile = g15profile.G15Profile(self.selected_device, g15profile.generate_profile_id())
            new_profile.name = new_profile_name
            g15profile.create_profile(new_profile)
            self.selected_profile = g15profile.get_profile(self.selected_device, new_profile.id)
            self._load_profile_list()
        
    def _copy_profile(self, widget):
        dupe_profile = g15profile.get_profile(self.selected_device, self.selected_profile.id)
        dialog = self.widget_tree.get_object("CopyProfileDialog") 
        dialog.set_transient_for(self.main_window)
        
        # Choose a default name for the copy
        default_name = self.selected_profile.name
        last_cb = default_name.rfind(")")
        last_ob = default_name.rfind("(")
        i = 0
        if last_cb >=0 and last_ob >0:
            i = int(default_name[last_ob + 1:last_cb])
            default_name = default_name[:last_ob].strip()
        new_name = default_name
        while True:
            p = g15profile.get_profile_by_name(self.selected_device, new_name)
            if p is None:
                break
            i += 1
            new_name = "%s (%i)" % ( default_name, i )
         
        self.widget_tree.get_object("CopiedProfileName").set_text(new_name)
        response = dialog.run()
        dialog.hide()
        if response == 1:            
            dupe_profile.set_id(g15profile.generate_profile_id())
            dupe_profile.name = self.widget_tree.get_object("CopiedProfileName").get_text()
            dupe_profile.save()
            self.selected_profile = dupe_profile
            self._load_profile_list()
        
    def _get_memory_number(self):
        if self.m1.get_active():
            return 1
        elif self.m2.get_active():
            return 2
        elif self.m3.get_active():
            return 3
        
    def _load_devices(self):
        self.device_model.clear()
        self.selected_device = None
        self.devices = g15devices.find_all_devices()
        previous_sel_device_name = self._default_device_name  
        sel_device_name = None
        idx = 0
        for device in self.devices:
            if device.model_id == 'virtual':
                icon_file = g15icontools.get_icon_path(["preferences-system-window", "preferences-system-windows", "gnome-window-manager", "window_fullscreen"])
            else:
                icon_file = g15icontools.get_app_icon(self.conf_client,  device.model_id)
            pixb = gtk.gdk.pixbuf_new_from_file(icon_file)
            self.device_model.append([pixb.scale_simple(96, 96, gtk.gdk.INTERP_BILINEAR), device.model_fullname, 96, gtk.WRAP_WORD, pango.ALIGN_CENTER])
            if previous_sel_device_name is not None and device.uid == previous_sel_device_name:
                sel_device_name = device.uid
                self.device_view.select_path((idx,))
            idx += 1
        if sel_device_name is None and len(self.devices) > 0:
            sel_device_name = self.devices[0].uid
            self.device_view.select_path((0,))
            
        if idx != self._last_no_devices:
            if idx == 1:
                self.widget_tree.get_object("MainScrolledWindow").set_visible(False)
                self.widget_tree.get_object("DeviceDetails").set_visible(False)
            else:
                self.widget_tree.get_object("MainScrolledWindow").set_visible(True)
                self.widget_tree.get_object("DeviceDetails").set_visible(True)
        # Hide the device settings if no device is selected
        if sel_device_name is None:
            self.device_settings.set_visible(False)
            self.no_device_selected.set_visible(True)
        
    def _load_profile_list(self):
        current_selection = self.selected_profile
        self.profiles_model.clear()
        if self.selected_device != None:
            tree_selection = self.profiles_tree.get_selection()
            active = g15profile.get_active_profile(self.selected_device)
            active_id = ""
            if active != None:
                active_id = active.id
            self.selected_profile = None
            default_profile = g15profile.get_default_profile(self.selected_device)
            self.profiles = g15profile.get_profiles(self.selected_device)
            locked = g15profile.is_locked(self.selected_device)
            for profile in self.profiles: 
                weight = 400
                selected = profile.id == active_id
                if selected:
                    weight = 700
                lock_icon = gtk.gdk.pixbuf_new_from_file(os.path.join(g15globals.image_dir, "locked.png")) if locked and selected else None 
                self.profiles_model.append([profile.name, weight, profile.id, profile == default_profile, not profile.read_only, lock_icon ])
                if current_selection != None and profile.id == current_selection.id:
                    tree_selection.select_path(self.profiles_model.get_path(self.profiles_model.get_iter(len(self.profiles_model) - 1)))
                    self.selected_profile = profile         
            if self.selected_profile == None:                
                tree_selection.select_path(self.profiles_model.get_path(self.profiles_model.get_iter(0)))
                self.selected_profile = self.profiles[0]
            if self.selected_profile != None:                             
                self._load_profile(self.selected_profile)
                
    def _load_parent_profiles(self):
        self.parent_profile_model.clear()
        self.parent_profile_model.append([-1, "" ])
        if self.selected_device != None:
            for profile in self.profiles: 
                if profile.id != self.selected_profile.id:
                    self.parent_profile_model.append([profile.id, profile.name ])
        
    def _profiles_changed(self, device_uid, macro_profile_id):        
        gobject.idle_add(self._load_profile_list)
        
    def _profile_name_edited(self, widget, row, value):        
        profile = self.profiles[int(row)]
        if value != profile.name and not profile.read_only:
            profile.name = value
            self._save_profile(profile)
            
    def _macro_list_clicked(self, widget, event):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            self._macro_properties(event)
        
    def _macro_name_edited(self, widget, row, value):
        macro = self._get_sorted_list()[int(row)] 
        if value != macro.name:
            macro.name = value
            macro.save()
            self._load_profile(self.selected_profile)
        
    def _comparator(self, o1, o2):
        return o1.compare(o2)
        
    def _get_sorted_list(self):
        sm = list(self.selected_profile.get_sorted_macros(None, self._get_memory_number()))
        return sm
        
    def _load_profile(self, profile):
        self.adjusting = True
        try : 
            current_selection = self._get_selected_macro()        
            tree_selection = self.macro_list.get_selection()
            name = profile.window_name
            if name == None:
                name = ""            
            self.macros_model.clear()
            selected_macro = None
            macros = self._get_sorted_list()
            
            # Build the macro model and set the initial selection
            for macro in macros:
                if macro.activate_on == g15driver.KEY_STATE_HELD:
                    on_name = _("Hold")
                elif macro.activate_on == g15driver.KEY_STATE_DOWN:
                    on_name = _("Press")
                else:
                    on_name = _("Release")
                row = [", ".join(g15driver.get_key_names(macro.keys)),
                                          macro.name, 
                                          macro.key_list_key, 
                                          not profile.read_only, 
                                          macro.activate_on, 
                                          on_name  ]
                self.macros_model.append(row)
                if current_selection != None and macro.key_list_key == current_selection.key_list_key:
                    tree_selection.select_path(self.macros_model.get_path(self.macros_model.get_iter(len(self.macros_model) - 1)))
                    selected_macro = macro        
            if selected_macro == None and len(macros) > 0:            
                tree_selection.select_path(self.macros_model.get_path(self.macros_model.get_iter(0)))
                    
            
            # Various enabled / disabled and visible / invisible states are
            # adjusted depending on the selected profile
            self.new_macro_button.set_sensitive(not profile.read_only)
            self.delete_macro_button.set_sensitive(not profile.read_only)
            self.information_content.set_sensitive(not profile.read_only)
            self.delays_content.set_sensitive(not profile.read_only)
            self.activation_content.set_sensitive(not profile.read_only)
            self.profile_plugins_mode.set_sensitive(not profile.read_only)
            
            if profile.get_default():
                self.activate_on_focus.set_visible(False)
                self.launch_pattern_box.set_visible(False)
                self.activate_on_launch.set_visible(False)
                self.window_label.set_visible(False)
                self.window_select.set_visible(False)
                self.parent_profile_label.set_visible(False)
                self.parent_profile_box.set_visible(False)
                self.window_name.set_visible(False)
                self.activate_by_default.set_visible(True)
                self.context_remove_profile.set_sensitive(False)
            else:
                self._load_windows()
#                self.launch_pattern_box.set_visible(True)
#                self.activate_on_launch.set_visible(True)
                self.launch_pattern_box.set_visible(False)
                self.activate_on_launch.set_visible(False)
                
                self.window_name.set_visible(True)
                self.parent_profile_label.set_visible(True)
                self.parent_profile_box.set_visible(True)
                self.window_select.set_visible(True)
                self.activate_on_focus.set_visible(True)
                self.window_label.set_visible(True)
                self.activate_by_default.set_visible(False)
                self.context_remove_profile.set_sensitive(not profile.read_only)
                
            # Set actions available based on locked state
            locked = g15profile.is_locked(self.selected_device)
            self.context_activate_profile.set_sensitive(not locked and not profile.is_active())
            self.context_unlock_profile.set_sensitive(profile.is_active() and locked)
            self.context_lock_profile.set_sensitive(not profile.is_active() or ( profile.is_active() and not locked ) )
            self.activate_on_launch.set_active(profile.activate_on_launch)
            self.launch_pattern.set_sensitive(self.activate_on_launch.get_active())
            
            # Background button state             
            self.background_browse_button.set_visible(self.driver is not None and self.driver.get_bpp() > 1)
            self.background_label.set_visible(self.driver is not None and self.driver.get_bpp() > 1)
            self.clear_background_button.set_visible(self.driver is not None and self.driver.get_bpp() > 1)
            
            # Set the values of the widgets
            self.launch_pattern.set_text("" if profile.launch_pattern is None else profile.launch_pattern)
            self.profile_author.set_text(profile.author)
            self.activate_by_default.set_active(profile.activate_on_focus)
            if profile.window_name != None:
                self.window_name.set_text(profile.window_name)
            else:
                self.window_name.set_text("")
            self.send_delays.set_active(profile.send_delays)
            self.fixed_delays.set_active(profile.fixed_delays)
            self._set_delay_state()
            self.press_delay_adjustment.set_value(float(profile.press_delay) / 1000.0)
            self.release_delay_adjustment.set_value(float(profile.release_delay) / 1000.0)
            self._set_image(self.profile_icon, profile.get_profile_icon_path(48))            
            self._set_image(self.background, profile.get_resource_path(profile.background))
            self.activate_on_focus.set_active(profile.activate_on_focus)
            self.window_combo.set_sensitive(self.activate_on_focus.get_active())
            
            # Set up colors 
            if self.color_button != None:
                rgb = profile.get_mkey_color(self._get_memory_number())
                if rgb == None:
                    self.enable_color_for_m_key.set_active(False)
                    self.color_button.set_sensitive(False)
                    self.color_button.set_color(g15convert.to_color((255, 255, 255)))
                else:
                    self.color_button.set_sensitive(True and not profile.read_only)
                    self.color_button.set_color(g15convert.to_color(rgb))
                    self.enable_color_for_m_key.set_active(True)
                self.enable_color_for_m_key.set_sensitive(not profile.read_only)
                
            # Plugins
            self._load_enabled_profile_plugins()
                    
            # Parent profile
            self._load_parent_profiles()
            self.parent_profile_combo.set_active(0)
            for i in range(0, len(self.parent_profile_model)): 
                if ( profile.base_profile == None and i == 0 ) or \
                   ( i > 0 and profile.base_profile == self.parent_profile_model[i][0] ):
                    self.parent_profile_combo.set_active(i)
                
            # Inital state based on macro and profile selection
            self._set_available_actions()
            self._set_available_profile_actions()
        finally:
            self.adjusting = False
            
    def _load_enabled_profile_plugins(self):
        for i in range(0, len(self.profile_plugins_mode_model)):
            if self.selected_profile.plugins_mode == self.profile_plugins_mode_model[i][0]:
                self.profile_plugins_mode.set_active(i)
        self.enabled_profile_plugins_model.clear()
        if self.selected_device:
            for mod in sorted(g15pluginmanager.imported_plugins, key=lambda key: key.name):
                key = self._get_full_key("plugins/%s/enabled" % mod.id )
                if self.driver and self.driver.get_model_name() in g15pluginmanager.get_supported_models(mod) and not g15pluginmanager.is_global_plugin(mod):
                    enabled = self.conf_client.get_bool(key)
                    if enabled:
                        self.enabled_profile_plugins_model.append([mod.id in self.selected_profile.selected_plugins, mod.name, mod.id])
            
    def _set_image(self, widget, path):
        if path == None or path == "" or not os.path.exists(path):
            widget.set_from_stock(gtk.STOCK_MISSING_IMAGE, gtk.ICON_SIZE_DIALOG)
        else:
            widget.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(path, 48, 48))
            
    def _load_windows(self):
        self.window_model.clear()  
        window_name = self.window_name.get_text()
        i = 0
        if self.bamf_matcher != None:            
            for window in self.bamf_matcher.RunningApplications():
                app = self.session_bus.get_object("org.ayatana.bamf", window)
                view = dbus.Interface(app, 'org.ayatana.bamf.view')
                vn = view.Name()
                self.window_model.append([vn, window])                
                if window_name != None and vn == window_name:
                    self.window_combo.set_active(i)
                i += 1
        else:
            apps = {}
            for window in self.screen.get_windows():
                if not window.is_skip_pager():
                    app = window.get_application()                
                    if app and not app.get_name() in apps:
                        apps[app.get_name()] = app
            for app in apps:
                self.window_model.append([app, app])                
                if window_name != None and app == window_name:
                    self.window_combo.set_active(i)
                i += 1
        
    def _add_controls(self):
        
        self._controls_visible = False
                
        # Remove previous notify handles
        for nh in self.control_notify_handles:
            self.conf_client.notify_remove(nh)            
        
        driver_controls = None
        if self.selected_device != None:
            # Driver. We only need this to get the controls. Perhaps they should be moved out of the driver
            # class and the values stored separately
            try :
                self.driver = g15drivermanager.get_driver(self.conf_client, self.selected_device)
                self.driver.on_driver_options_change = self._driver_options_changed
                
                # Controls
                driver_controls = self.driver.get_controls()
                for control in driver_controls:
                    control.set_from_configuration(self.driver.device, self.conf_client)
                    
            except Exception as e:
                logger.error("Failed to load driver to query controls.", exc_info = e)
            
        if not driver_controls:
            driver_controls = []
        
        # Remove current components
        controls = self.widget_tree.get_object("ControlsBox")
        for c in controls.get_children():
            controls.remove(c)
        for c in self.memory_bank_vbox.get_children():
            self.memory_bank_vbox.remove(c)
        self.memory_bank_vbox.add(self.widget_tree.get_object("MemoryBanks"))
        
        # Slider and Color controls            
        table = gtk.Table(rows = max(1, len(driver_controls)), columns = 2)
        table.set_row_spacings(4)
        row = 0
        for control in driver_controls:
            val = control.value
            if isinstance(val, int):  
                if ( control.hint & g15driver.HINT_SWITCH ) == 0 and ( control.hint & g15driver.HINT_MKEYS ) == 0:
                    label = gtk.Label(control.name)
                    label.set_alignment(0.0, 0.5)
                    label.show()
                    table.attach(label, 0, 1, row, row + 1,  xoptions = gtk.FILL, xpadding = 8, ypadding = 4);
                    
                    hscale = gtk.HScale()
                    hscale.set_value_pos(gtk.POS_RIGHT)
                    hscale.set_digits(0)
                    hscale.set_range(control.lower,control.upper)
                    hscale.set_value(control.value)
                    hscale.connect("value-changed", self._control_changed, control)
                    hscale.show()
                    
                    halign = gtk.Alignment(0, 0, 1.0, 1.00)
                    halign.add(hscale)
                    
                    table.attach(halign, 1, 2, row, row + 1, xoptions = gtk.EXPAND | gtk.FILL)            
                    self.control_notify_handles.append(self.conf_client.notify_add(self._get_full_key(control.id), self._control_configuration_changed, [ control, hscale ]))
            else:  
                label = gtk.Label(control.name)
                label.set_alignment(0.0, 0.5)
                label.show()
                table.attach(label, 0, 1, row, row + 1,  xoptions = gtk.FILL, xpadding = 8, ypadding = 4);
                
                picker = colorpicker.ColorPicker(redblue = control.hint & g15driver.HINT_RED_BLUE_LED != 0)
                picker.set_color(control.value)    
                picker.connect("color-chosen", self._color_chosen, control)
                table.attach(picker, 1, 2, row, row + 1)
                
                self.control_notify_handles.append(self.conf_client.notify_add(self._get_full_key(control.id), self._control_configuration_changed, [ control, picker]));
                
            row += 1
        if row > 0:            
            self._controls_visible = True
        controls.add(table)
        controls.show_all()
          
        # Switch controls  
        controls = self.widget_tree.get_object("SwitchesBox")
        for c in controls.get_children():
            controls.remove(c)            
        table.set_row_spacings(4)
        row = 0
        for control in driver_controls:
            val = control.value
            if isinstance(val, int):  
                if control.hint & g15driver.HINT_SWITCH != 0:
                    check_button = gtk.CheckButton(control.name)
                    check_button.set_active(control.value == 1)
                    check_button.set_alignment(0.0, 0.0)
                    check_button.show()
                    controls.pack_start(check_button, False, False, 4)  
                    check_button.connect("toggled", self._control_changed, control)
                    self.notify_handles.append(self.conf_client.notify_add(self._get_full_key(control.id), self._control_configuration_changed, [ control, check_button ]));
                    row += 1
        if row > 0:
            self._controls_visible = True
            
        controls.show_all()
        self.widget_tree.get_object("SwitchesFrame").set_child_visible(row > 0)
        
        # Hide the cycle screens if the device has no screen
        if self.driver != None and self.driver.get_bpp() == 0:            
            self.cycle_screens.hide()
            self.cycle_screens_options.hide()
        else:            
            self._controls_visible = True
            self.cycle_screens.show()
            self.cycle_screens_options.show()
        
        # If the keyboard has a colour dimmer, allow colours to be assigned to memory banks
        control = self.driver.get_control_for_hint(g15driver.HINT_DIMMABLE) if self.driver != None else None
        if control != None and not isinstance(control.value, int):
            self._controls_visible = True
            hbox = gtk.HBox()
            self.enable_color_for_m_key = gtk.CheckButton(_("Set backlight colour"))
            self.enable_color_for_m_key.connect("toggled", self._color_for_mkey_enabled)
            hbox.pack_start(self.enable_color_for_m_key, True, False)            
            self.color_button = gtk.ColorButton()
            self.color_button.set_sensitive(False)                
            self.color_button.connect("color-set", self._profile_color_changed)
            hbox.pack_start(self.color_button, True, False)
            self.memory_bank_vbox.add(hbox)
            hbox.show_all()
        else:
            self.color_button = None
            self.enable_color_for_m_key = None
            
    def _profile_color_changed(self, widget):
        if not self.adjusting:
            self.selected_profile.set_mkey_color(self._get_memory_number(), 
                                                 g15convert.color_to_rgb(widget.get_color()) if self.enable_color_for_m_key.get_active() else None)
            self._save_profile(self.selected_profile)
    
    def _color_for_mkey_enabled(self, widget):
        self.color_button.set_sensitive(widget.get_active())        
        self._profile_color_changed(self.color_button)
        
    def _show_profile_list_context(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                self.profiles_context_menu.popup( None, None, None, event.button, time)
            return True