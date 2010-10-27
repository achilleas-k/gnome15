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

import pygtk
pygtk.require('2.0')
import gtk
import os
import g15_globals as pglobals
import g15_profile as g15profile
import gconf
import g15_driver_manager as g15drivermanager
import g15_driver as g15driver
import g15_util as g15util
import dbus
import shutil
import wnck

# Store the temporary profile icons here (for when the icon comes from a window, the filename is not known
icons_dir = os.path.join(os.path.join(os.path.expanduser("~"),".gnome15"),"profile-icons")
if not os.path.exists(icons_dir):
    os.makedirs(icons_dir)

'''
Dialog that allows editing of Macros
'''

class G15Macros:
    
    adjusting = False
    
    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        
        # How many macro keys are there?
        self.keys = 18
        
        # Load main Glade file
        glade = os.path.join(pglobals.glade_dir, 'g15-macros.glade')        
        self.widget_tree = gtk.Builder()
        self.widget_tree.add_from_file(glade)
        
        # Monitor gconf
        self.conf_client = gconf.client_get_default()
        self.conf_client.add_dir("/apps/gnome15", gconf.CLIENT_PRELOAD_NONE)
        self.conf_client.notify_add("/apps/gnome15/active_profile", self.active_profile_changed);
        self.conf_client.notify_add("/apps/gnome15/profiles", self.profiles_changed);
        
        # Driver
        self.driver = g15drivermanager.get_driver(self.conf_client)

        # Widgets
        self.main_window = self.widget_tree.get_object("MainWindow")
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
        self.remove_button = self.widget_tree.get_object("RemoveButton")
        self.activate_on_focus = self.widget_tree.get_object("ActivateProfileOnFocusCheckbox")
        self.macro_name_renderer = self.widget_tree.get_object("MacroNameRenderer")
        self.window_label = self.widget_tree.get_object("WindowLabel")
        self.activate_by_default = self.widget_tree.get_object("ActivateByDefaultCheckbox")
        self.send_delays = self.widget_tree.get_object("SendDelaysCheckbox")
        self.profile_icon = self.widget_tree.get_object("ProfileIcon")
        self.icon_browse_button = self.widget_tree.get_object("BrowseForIcon")
        self.clear_icon_button = self.widget_tree.get_object("ClearIcon")
        self.macro_properties_button = self.widget_tree.get_object("MacroPropertiesButton")
        self.delete_macro_button = self.widget_tree.get_object("DeleteMacroButton")
        self.memory_bank_label = self.widget_tree.get_object("MemoryBankLabel")
        self.macro_keys_label = self.widget_tree.get_object("MacroKeysLabel")
        self.macro_name_field = self.widget_tree.get_object("MacroNameField")
        self.script_model = self.widget_tree.get_object("ScriptModel")
        self.script_label = self.widget_tree.get_object("ScriptLabel")
        self.memory_bank_vbox = self.widget_tree.get_object("MemoryBankVBox")
        
        # Window 
        self.main_window.set_transient_for(self.parent_window)
        self.main_window.set_icon_from_file(g15util.get_app_icon(self.conf_client, "gnome15"))
        
        # Models        
        self.macrosModel = self.widget_tree.get_object("MacroModel")
        self.profiles_model = self.widget_tree.get_object("ProfileModel")
        
        self.selected_profile = g15profile.get_active_profile()
            
        # Configure widgets
        self.profiles_tree.get_selection().set_mode(gtk.SELECTION_SINGLE)        
        self.macro_list.get_selection().set_mode(gtk.SELECTION_SINGLE)
        
        # Bind to events
        self.widget_tree.get_object("AddButton").connect("clicked", self.add_profile)
        self.widget_tree.get_object("ActivateButton").connect("clicked", self.activate)
        self.activate_on_focus.connect("toggled", self.activate_on_focus_changed)
        self.activate_by_default.connect("toggled", self.activate_on_focus_changed)
        self.clear_icon_button.connect("clicked", self.clear_icon)
        self.delete_macro_button.connect("clicked", self.remove_macro)
        self.icon_browse_button.connect("clicked", self.browse_for_icon)
        self.macro_properties_button.connect("clicked", self.macro_properties)
        self.macro_list.connect("cursor-changed", self.select_macro)
        self.macro_name_renderer.connect("edited", self.macro_name_edited)
        self.m1.connect("toggled", self.memory_changed)
        self.m2.connect("toggled", self.memory_changed)
        self.m3.connect("toggled", self.memory_changed)
        self.profiles_tree.connect("cursor-changed", self.select_profile)
        self.remove_button.connect("clicked", self.remove_profile)
        self.send_delays.connect("toggled", self.send_delays_changed)
        self.window_combo.child.connect("changed", self.window_name_changed)
        self.window_combo.connect("changed", self.window_name_changed)
        
        # If the keyboard has a colour dimmer, allow colours to be assigned to memory banks
        control = self.driver.get_control_for_hint(g15driver.HINT_DIMMABLE)
        if control != None and not isinstance(control.value, int):
            hbox = gtk.HBox()
            self.enable_color_for_m_key = gtk.CheckButton("Set backlight colour")
            self.enable_color_for_m_key.connect("toggled", self._color_for_mkey_enabled)
            hbox.pack_start(self.enable_color_for_m_key, True, False)            
            self.color_button = gtk.ColorButton()
            self.color_button.set_sensitive(False)                
            self.color_button.connect("color-set", self._color_changed)
#            color_button.set_color(self.to_color(control.value))
            hbox.pack_start(self.color_button, True, False)
            self.memory_bank_vbox.add(hbox)
            hbox.show_all()
        else:
            self.color_button = None
            self.enable_color_for_m_key = None
              
        
        # Connection to BAMF for running applications list
        try :
            self.session_bus = dbus.SessionBus()
            self.bamf_matcher = self.session_bus.get_object("org.ayatana.bamf", '/org/ayatana/bamf/matcher')
        except:
            print "WARNING: BAMF not available, falling back to WNCK"
            self.bamf_matcher = None

    def active_profile_changed(self, client, connection_id, entry, args):
        self.load_configurations()
        
    def send_delays_changed(self, widget=None):
        self.selected_profile.send_delays = self.send_delays.get_active()
        self.selected_profile.save()
        
    def activate_on_focus_changed(self, widget=None):
        self.selected_profile.activate_on_focus = widget.get_active()        
        self.window_combo.set_sensitive(self.selected_profile.activate_on_focus)
        self.selected_profile.save()
        
    def window_name_changed(self, widget):
        if isinstance(widget, gtk.ComboBoxEntry):
            active = widget.get_active()
            if active >= 0:
                self.window_combo.child.set_text(self.window_model[active][0])
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
                                icon_path = g15util.get_icon_path(self.conf_client, icon)
                                if icon_path != None:
                                    # We need to copy the icon as it may be temporary
                                    copy_path = os.path.join(icons_dir, os.path.basename(icon_path))
                                    shutil.copy(icon_path, copy_path)
                                    self.selected_profile.icon = copy_path
                else:                               
                    for window in wnck.screen_get_default().get_windows():
                        if window.get_name() == self.selected_profile.window_name:
                            icon = window.get_icon()
                            if icon != None:
                                filename = os.path.join(icons_dir,"%d.png" % self.selected_profile.id)
                                icon.save(filename, "png")
                                self.selected_profile.icon = filename    
                            
                self.selected_profile.save()
        
    def memory_changed(self, widget):
        self.load_configuration(self.selected_profile)
        
    def select_profile(self, widget):
        (model, path) = self.profiles_tree.get_selection().get_selected()
        self.selected_profile = g15profile.get_profile(model[path][2])
        self.load_configuration(self.selected_profile)
        
    def select_macro(self, widget):
        self.set_available_actions()
        
    def set_available_actions(self):
        (model, path) = self.macro_list.get_selection().get_selected()
        self.delete_macro_button.set_sensitive(path != None)
        self.macro_properties_button.set_sensitive(path != None)
        
    def activate(self, widget):
        (model, path) = self.profiles_tree.get_selection().get_selected()
        self.make_active(g15profile.get_profile(model[path][2]))
        
    def make_active(self, profile): 
        profile.make_active()
        self.load_configurations()
        
    def clear_icon(self, widget):
        self.selected_profile.icon = ""            
        self.selected_profile.save()
        
    def browse_for_icon(self, widget):
        dialog = gtk.FileChooserDialog("Open..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.main_window)
        dialog.set_filename(self.selected_profile.icon)
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
            self.selected_profile.icon = dialog.get_filename()            
            self.selected_profile.save()
            
        dialog.destroy()
        
    def remove_profile(self, widget):
        dialog = self.widget_tree.get_object("ConfirmRemoveProfileDialog")  
        dialog.set_transient_for(self.main_window)
        response = dialog.run()
        dialog.hide()
        if response == 1:
            active_profile = g15profile.get_active_profile()
            if self.selected_profile.id == active_profile.id:
                self.make_active(g15profile.get_profile(0))
            self.selected_profile.delete()
            self.load_configurations()
        
    def macro_properties(self, widget):
        memory = self.get_memory_number()
        (model, path) = self.macro_list.get_selection().get_selected()
        key_list_key = model[path][2]
        macro = self.selected_profile.get_macro(memory, g15profile.get_keys_from_key(key_list_key))
        dialog = self.widget_tree.get_object("EditMacroDialog")  
        dialog.set_transient_for(self.main_window)        
        self.memory_bank_label.set_text("M%d" % memory)
        self.macro_keys_label.set_text(",".join(g15util.get_key_names(macro.keys)))
        self.macro_name_field.set_text(macro.name)
        self.script_model.clear()
        script_text = ""
        last = ""
        for line in macro.macro.split("\n"):
            args = line.split()
            self.script_model.append(args)
            if args[0] == "Release":
                if len(args[1]) == 1:
                    if len(last) > 1:
                        script_text += " "
                    script_text += args[1]
                else:
                    if not script_text.endswith(" "):
                        script_text += " "
                    script_text += args[1]
                last = args[1]
        self.script_label.set_text(script_text)
                        
        dialog.run()
        dialog.hide()
        macro.name = self.macro_name_field.get_text()
        self.load_configurations()
        
    def remove_macro(self, widget):
        memory = self.get_memory_number()
        (model, path) = self.macro_list.get_selection().get_selected()
        key_list_key = model[path][2]
        dialog = self.widget_tree.get_object("ConfirmRemoveMacroDialog") 
        dialog.set_transient_for(self.main_window)
        response = dialog.run()
        dialog.hide()
        if response == 1:
            keys = g15profile.get_keys_from_key(key_list_key)
            self.selected_profile.delete_macro(memory, keys)
            self.load_configurations()
        
    def add_profile(self, widget):
        dialog = self.widget_tree.get_object("AddProfileDialog") 
        dialog.set_transient_for(self.main_window) 
        response = dialog.run()
        dialog.hide()
        if response == 1:
            new_profile_name = self.widget_tree.get_object("NewProfileName").get_text()
            new_profile = g15profile.G15Profile(new_profile_name, "")
            g15profile.create_profile(new_profile)
            self.selected_profile = new_profile
            self.load_configurations()
        
    def get_memory_number(self):
        if self.m1.get_active():
            return 1
        elif self.m2.get_active():
            return 2
        elif self.m3.get_active():
            return 3
        
    def load_configurations(self):
        self.profiles_model.clear()
        tree_selection = self.profiles_tree.get_selection()
        active = g15profile.get_active_profile()
        active_id = -1
        if active != None:
            active_id = active.id
        current_selection = self.selected_profile
        self.selected_profile = None
        self.profiles = g15profile.get_profiles()
        for profile in self.profiles: 
            weight = 400
            if profile.id == active_id:
                weight = 700
            self.profiles_model.append([profile.name, weight, profile.id])
            if current_selection != None and profile.id == current_selection.id:
                tree_selection.select_path(self.profiles_model.get_path(self.profiles_model.get_iter(len(self.profiles_model) - 1)))
                self.selected_profile = profile
        if self.selected_profile != None:                             
            self.load_configuration(self.selected_profile)             
        elif len(self.profiles) > 0:            
            tree_selection.select_path(self.profiles_model.get_path(self.profiles_model.get_iter(0)))
        else:
            default_profile = g15profile.G15Profile("Default")
            g15profile.create_profile(default_profile)
            self.load_configurations()
            
        
    def profiles_changed(self, client, connection_id, entry, args):
        self.load_configurations()
        
    def macro_name_edited(self, widget, row, value):
        macro = self.get_sorted_list()[int(row)] 
        if value != macro.name:
            macro.name = value
            macro.save()
            self.load_configuration(self.selected_profile)
        
    def get_sorted_list(self):
        return sorted(self.selected_profile.macros[self.get_memory_number() - 1], key=lambda key: key.key_list_key)
        
    def load_configuration(self, profile): 
        name = profile.window_name
        if name == None:
            name = ""            
        self.macrosModel.clear()
        for macro in self.get_sorted_list():
            self.macrosModel.append([", ".join(g15util.get_key_names(macro.keys)), macro.name, macro.key_list_key, True])
        self.activate_on_focus.set_active(profile.activate_on_focus)
        self.activate_by_default.set_active(profile.activate_on_focus)
        if profile.window_name != None:
            self.window_combo.child.set_text(profile.window_name)
        else:
            self.window_combo.child.set_text("")
        self.send_delays.set_active(profile.send_delays)
        self.window_combo.set_sensitive(self.activate_on_focus.get_active())
        
        if profile.icon == None or profile.icon == "":
            self.profile_icon.set_from_stock(gtk.STOCK_MISSING_IMAGE, gtk.ICON_SIZE_DIALOG)
        else:
            self.profile_icon.set_from_pixbuf(gtk.gdk.pixbuf_new_from_file_at_size(profile.icon, 48, 48))
        
        if profile.get_default():
            self.window_combo.set_visible(False)
            self.activate_on_focus.set_visible(False)
            self.window_label.set_visible(False)
            self.activate_by_default.set_visible(True)
            self.remove_button.set_sensitive(False)
        else:
            self.window_combo.set_visible(True)
            self.activate_on_focus.set_visible(True)
            self.window_label.set_visible(True)
            self.activate_by_default.set_visible(False)
            self.remove_button.set_sensitive(True)
            
        if self.color_button != None:
            rgb = profile.get_mkey_color(self.get_memory_number() - 1)
            if rgb == None:
                self.enable_color_for_m_key.set_active(False)
                self.color_button.set_sensitive(False)
                self.color_button.set_color(g15util.to_color((255, 255, 255)))
            else:
                self.color_button.set_sensitive(True)
                self.color_button.set_color(g15util.to_color(rgb))
                self.enable_color_for_m_key.set_active(True)
            
        self.load_windows()
        self.set_available_actions()
            
    def load_windows(self):        
        self.window_model.clear()
        if self.bamf_matcher != None:            
            for window in self.bamf_matcher.RunningApplications():
                app = self.session_bus.get_object("org.ayatana.bamf", window)
                view = dbus.Interface(app, 'org.ayatana.bamf.view')
                self.window_model.append([view.Name(), window])
        else:
            for window in wnck.screen_get_default().get_windows():
                self.window_model.append([window.get_name(), window.get_name()])

    def run(self):
        ''' Set up device list and start main window app.
        '''
        self.id = None                
        self.load_configurations()
        self.update_children()
        self.main_window.run()
        self.main_window.hide()
        

    def update_children(self):
        ''' Update the child widgets to reflect current settings.
        '''
        self.adjusting = True
        self.adjusting = False
        
    def _color_changed(self, widget):
        self.selected_profile.set_mkey_color(self.get_memory_number() - 1, 
                                             g15util.color_to_rgb(widget.get_color()) if self.enable_color_for_m_key.get_active() else None)
        self.selected_profile.save()
    
    def _color_for_mkey_enabled(self, widget):
        self.color_button.set_sensitive(widget.get_active())        
        self._color_changed(self.color_button)