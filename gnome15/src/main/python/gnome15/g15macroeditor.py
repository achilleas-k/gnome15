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

"""
Manages the UI for editing a single macro. 
"""

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("gnome15").ugettext


import g15globals
import g15profile
import g15util
import g15uinput
import g15devices
import g15driver
import g15keyio
import g15actions
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import os
import pango
import gconf

import logging
logger = logging.getLogger("config")

# Key validation constants
IN_USE = "in-use"
RESERVED_FOR_ACTION = "reserved"
NO_KEYS = "no-keys"
OK = "ok"

class G15MacroEditor():
    
    def __init__(self, parent=None):
        """
        Constructor. Create a new macro editor. You must call set_driver() 
        and set_macro() after constructions to populate the macro key buttons
        and the other fields.
        """
        self.__gconf_client = gconf.client_get_default()
        self.__widget_tree = gtk.Builder()
        self.__widget_tree.set_translation_domain("g15-macroeditor")
        self.__widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "macro-editor.glade"))
        self.__window = self.__widget_tree.get_object("EditMacroDialog")
        if self.__window is not None and parent is not None:            
            self.__window.set_transient_for(parent)
         
        self.adjusting = False
        self.editing_macro = None
        self.selected_profile = None
        self.memory_number = 1
        self.close_button = None
        
        # Private
        self.__text_buffer = None
        self.__rows = None
        self.__driver = None
        self.__key_buttons = None
        self.__load_objects()
        self.__load_actions()
        self.__create_macro_info_bar()
        self.__macro_save_timer = None
        
        # Connect signal handlers
        self.__widget_tree.connect_signals(self)
        
    def run(self):
        self.__window.run()
        self.__window.hide()
        
    def set_driver(self, driver):
        """
        Set the driver to use for this macro. This allows the full set of
        available keys (and other capabilities) to determined.
        
        Keyword arguments:
        driver        --    driver
        """
        self.__driver = driver
        
    def set_macro(self, macro):
        """
        Set the macro to edit. Note, set_driver must have been called first
        so it knows which macro keys are available for use for the model
        in question.
        
        Keyword arguments:
        macro        --    macro to edit
        """
        if self.__driver is None:
            raise Exception("No driver set. Cannot set macro")
        
        self.adjusting = True
        try:
            self.editing_macro = macro
            self.selected_profile = macro.profile
            self.memory_number = macro.memory
            self.__widget_tree.get_object("KeyBox").set_sensitive(not self.selected_profile.read_only)
            keys_frame = self.__widget_tree.get_object("KeysFrame")
            self.__allow_combination.set_active(len(self.editing_macro.keys) > 1)
            
            # Build the G-Key selection widget
            if self.__rows:
                keys_frame.remove(self.__rows)
            self.__rows = gtk.VBox()
            self.__rows.set_spacing(4)
            self.__key_buttons = []
            for row in self.__driver.get_key_layout():
                hbox = gtk.HBox()
                hbox.set_spacing(4)
                for key in row:
                    key_name = g15util.get_key_names([ key ])
                    g_button = gtk.ToggleButton(" ".join(key_name))
                    g_button.key = key
                    key_active = key in self.editing_macro.keys
                    g_button.set_active(key_active)
                    self.__set_button_style(g_button)
                    g_button.connect("toggled", self._toggle_key, key, self.editing_macro)
                    self.__key_buttons.append(g_button)
                    hbox.pack_start(g_button, True, True)
                self.__rows.pack_start(hbox, False, False)
            keys_frame.add(self.__rows)     
            keys_frame.show_all()
            
            # Set the activation mode
            for index, (activate_on_id, activate_on_name) in enumerate(self.__activate_on_combo.get_model()):
                if activate_on_id == self.editing_macro.activate_on:
                    self.__activate_on_combo.set_active(index)
                        
            # Set the repeat mode
            for index, (repeat_mode_id, repeat_mode_name) in enumerate(self.__repeat_mode_combo.get_model()):
                if repeat_mode_id == self.editing_macro.repeat_mode:
                    self.__repeat_mode_combo.set_active(index)
            
            # Set the type of macro
            for index, (macro_type, macro_type_name) in enumerate(self.__map_type_model):
                if macro_type == self.editing_macro.type:
                    self.__mapped_key_type_combo.set_active(index) 
            self.__set_available_options()
                
            # Set the other details 
            for index, row in enumerate(self.__map_type_model):
                if row[0] == self.editing_macro.type:                
                    self.__mapped_key_type_combo.set_active(index)
                    break
            self.__load_keys()
            if self.editing_macro.type in [ g15profile.MACRO_MOUSE, g15profile.MACRO_JOYSTICK, g15profile.MACRO_DIGITAL_JOYSTICK, g15profile.MACRO_KEYBOARD ]:
                for index, row in enumerate(self.__mapped_key_model):
                    if self.__mapped_key_model[index][0] == self.editing_macro.macro: 
                        self.__select_tree_row(self.__uinput_tree, index)
                        break
            elif self.editing_macro.type == g15profile.MACRO_ACTION:
                for index, row in enumerate(self.__action_model):
                    if self.__action_model[index][0] == self.editing_macro.macro: 
                        self.__select_tree_row(self.__action_tree, index)
                        break
                
            self.__text_buffer = gtk.TextBuffer()        
            self.__text_buffer.connect("changed", self._macro_script_changed)    
            self.__macro_script.set_buffer(self.__text_buffer)
                
            self.__turbo_rate.get_adjustment().set_value(self.editing_macro.repeat_delay)
            self.__memory_bank_label.set_text("M%d" % self.memory_number)
            self.__macro_name_field.set_text(self.editing_macro.name)
            self.__override_default_repeat.set_active(self.editing_macro.repeat_delay != -1)
            
            if self.editing_macro.type == g15profile.MACRO_SIMPLE:
                self.__simple_macro.set_text(self.editing_macro.macro)
            else:
                self.__simple_macro.set_text("")
            if self.editing_macro.type == g15profile.MACRO_COMMAND:
                cmd = self.editing_macro.macro
                background = False
                if cmd.endswith("&"):
                    cmd = cmd[:-1]
                    background = True
                elif cmd == "":
                    background = True
                self.__command.set_text(cmd)
                self.__run_in_background.set_active(background)
            else:
                self.__run_in_background.set_active(False)
                self.__command.set_text("")
            if self.editing_macro.type == g15profile.MACRO_SCRIPT:
                self.__text_buffer.set_text(self.editing_macro.macro)
            else:            
                self.__text_buffer.set_text("")
                
            self.__check_macro(self.editing_macro.keys)
            self.__macro_name_field.grab_focus()
            
        finally:
            self.adjusting = False
        self.editing_macro.name = self.__macro_name_field.get_text()
        self.__set_available_options()
        
    """
    Event handlers    
    """
    def _override_default_repeat_changed(self, widget):
        if not self.adjusting:
            sel = widget.get_active()
            if sel:
                self.editing_macro.repeat_delay = 0.1
                self.__turbo_rate.get_adjustment().set_value(0.1)
                self.__save_macro(self.editing_macro)
                self.__set_available_options()
            else:
                self.editing_macro.repeat_delay = -1.0
                self.__set_available_options()
                self.__save_macro(self.editing_macro)
        
    def _macro_script_changed(self, text_buffer):
        self.editing_macro.macro = text_buffer.get_text(text_buffer.get_start_iter(), text_buffer.get_end_iter())
        self.__save_macro(self.editing_macro)
        
    def _show_script_editor(self, widget):
        editor = G15MacroScriptEditor(self.__gconf_client, self.__driver, self.editing_macro, self.__window)
        if editor.run():
            self.__text_buffer.set_text(self.editing_macro.macro)
            self.__save_macro(self.editing_macro)
    
    def _turbo_changed(self, widget):
        if not self.adjusting:
            self.editing_macro.repeat_delay = widget.get_value() 
            self.__save_macro(self.editing_macro)
    
    def _repeat_mode_selected(self, widget):
        if not self.adjusting:
            self.editing_macro.repeat_mode = widget.get_model()[widget.get_active()][0]
            self.__save_macro(self.editing_macro)
            self.__set_available_options()
    
    def _mapped_key_type_changed(self, widget):
        if not self.adjusting:
            key = self.__map_type_model[widget.get_active()][0]
            self.editing_macro.type = key
            self.editing_macro.macro = ""
            self.adjusting = True
            try:
                self.__load_keys()
            finally:
                self.adjusting = False
            self.__select_tree_row(self.__uinput_tree, 0)
            self.set_macro(self.editing_macro)
            self.__set_available_options()
    
    def _clear_filter(self, widget):
        self.__filter.set_text("")
    
    def _filter_changed(self, widget):
        try:
            self.adjusting  = True
            self.__load_keys()
        finally:
            self.adjusting = False
        self._key_selected(None)
    
    def _simple_macro_changed(self, widget):
        self.editing_macro.macro = widget.get_text()
        self.__save_macro(self.editing_macro)
        
    def _command_changed(self, widget):
        self.__save_command()
        
    def _browse_for_command(self, widget):
        dialog = gtk.FileChooserDialog(_("Open.."),
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        file_filter = gtk.FileFilter()
        file_filter.set_name(_("All files"))
        file_filter.add_pattern("*")
        dialog.add_filter(file_filter)
        response = dialog.run()
        while gtk.events_pending():
            gtk.main_iteration(False) 
        if response == gtk.RESPONSE_OK:
            self.__command.set_text(dialog.get_filename())
        dialog.destroy()
        return False
        
    def _run_in_background_changed(self, widget):
        if not self.adjusting:
            self.__save_command()
        
    def _allow_combination_changed(self, widget):
        if not self.adjusting and not self.__allow_combination.get_active():
            for button in self.__key_buttons:
                if len(self.editing_macro.keys) > 1:
                    button.set_active(False)
            self.__check_macro(self.editing_macro.keys)
            
    def _macro_name_changed(self, widget):
        self.editing_macro.name = widget.get_text()
        self.__save_macro(self.editing_macro)
            
    def _toggle_key(self, widget, key, macro):
        """
        Event handler invoked when one of the macro key buttons is pressed.
        """
        keys = list(macro.keys) 
                
        if key in keys:
            keys.remove(key)
        else:            
            if not self.adjusting and not self.__allow_combination.get_active():
                for button in self.__key_buttons:
                    if button != widget:
                        self.adjusting = True
                        try :
                            button.set_active(False)
                        finally:
                            self.adjusting = False
                for ikey in keys:
                    if ikey != key:
                        keys.remove(ikey)
            keys.append(key)
            
        if not self.selected_profile.are_keys_in_use(self.editing_macro.activate_on, 
                                                     self.memory_number, keys, 
                                                     exclude=[self.editing_macro]):
            if self.__macro_name_field.get_text() == "" or self.__macro_name_field.get_text().startswith("Macro "):
                new_name = " ".join(g15util.get_key_names(keys))
                self.editing_macro.name = _("Macro %s") % new_name
                self.__macro_name_field.set_text(self.editing_macro.name)
            macro.set_keys(keys)
            
        self.__set_button_style(widget)
        
        if not self.adjusting:
            self.__check_macro(keys)
            self.__save_macro(self.editing_macro)
            
    def _key_selected(self, widget):
        if not self.adjusting:
            (model, path) = self.__uinput_tree.get_selection().get_selected()
            if path is not None:
                key = model[path][0]
                self.editing_macro.macro = key
                self.__save_macro(self.editing_macro)
            
    def _action_selected(self, widget):
        if not self.adjusting:
            (model, path) = self.__action_tree.get_selection().get_selected()
            if path:
                key = model[path][0]
                self.editing_macro.macro = key
                self.__save_macro(self.editing_macro)
    
    def _activate_on_changed(self, widget):
        if not self.adjusting:
            self.editing_macro.set_activate_on(widget.get_model()[widget.get_active()][0])
            self.__save_macro(self.editing_macro)
            if self.editing_macro.activate_on == g15driver.KEY_STATE_HELD:
                self.__repeat_mode_combo.set_active(0)
            self.__set_available_options()            
            self.__check_macro(list(self.editing_macro.keys)) 
        
    """
    Private
    """
            
    def __save_command(self):
        macrotext = self.__command.get_text()
        if self.__run_in_background.get_active():
            macrotext += "&"
        self.editing_macro.macro = macrotext
        self.__save_macro(self.editing_macro)
        
    def __select_tree_row(self, tree, row):
        tree_iter = tree.get_model().iter_nth_child(None, row)
        if tree_iter:
            tree_path = tree.get_model().get_path(tree_iter) 
            tree.get_selection().select_path(tree_path)
            tree.scroll_to_cell(tree_path)
            
    def __save_macro(self, macro):
        """
        Schedule saving of the macro in 2 seconds. This may be called again 
        before the 2 seconds are up, in which case the timer will reset.
        
        Keyword arguments:
        macro        -- macro to save
        """
        if not self.adjusting:
            if self.__macro_save_timer is not None:
                self.__macro_save_timer.cancel()
            self.__macro_save_timer = g15util.schedule("SaveMacro", 2, self.__do_save_macro, macro)            
            
    def __do_save_macro(self, macro):
        """
        Actually save the macro. This should not be called directly
        
        Keyword arguments:
        macro        -- macro to save
        """
        if self.__validate_macro(macro.keys) in [ OK, RESERVED_FOR_ACTION ] :
            logger.info("Saving macro %s" % macro.name)
            macro.save()
            
    def __load_actions(self):
        self.__action_model.clear()
        for action in g15actions.actions:
            self.__action_model.append([action, action])
            
    def __load_objects(self):
        """
        Load references to the various components contain in the Glade file
        """
        self.__macro_script = self.__widget_tree.get_object("MacroScript")
        self.__map_type_model = self.__widget_tree.get_object("MapTypeModel")
        self.__mapped_key_model = self.__widget_tree.get_object("MappedKeyModel")
        self.__mapped_key_type_combo = self.__widget_tree.get_object("MappedKeyTypeCombo")
        self.__map_type_model = self.__widget_tree.get_object("MapTypeModel")
        self.__simple_macro = self.__widget_tree.get_object("SimpleMacro")
        self.__command = self.__widget_tree.get_object("Command")
        self.__run_in_background = self.__widget_tree.get_object("RunInBackground")
        self.__browse_for_command = self.__widget_tree.get_object("BrowseForCommand")
        self.__allow_combination = self.__widget_tree.get_object("AllowCombination")
        self.__macro_name_field = self.__widget_tree.get_object("MacroNameField")
        self.__macro_warning_box = self.__widget_tree.get_object("MacroWarningBox")
        self.__memory_bank_label = self.__widget_tree.get_object("MemoryBankLabel")
        self.__uinput_box = self.__widget_tree.get_object("UinputBox")
        self.__command_box = self.__widget_tree.get_object("CommandBox")
        self.__script_box = self.__widget_tree.get_object("ScriptBox")
        self.__simple_box = self.__widget_tree.get_object("SimpleBox")
        self.__action_box = self.__widget_tree.get_object("ActionBox")
        self.__uinput_tree = self.__widget_tree.get_object("UinputTree")
        self.__action_tree = self.__widget_tree.get_object("ActionTree")
        self.__action_model = self.__widget_tree.get_object("ActionModel")
        self.__repeat_mode_combo = self.__widget_tree.get_object("RepeatModeCombo")
        self.__repetition_frame = self.__widget_tree.get_object("RepetitionFrame")
        self.__turbo_rate = self.__widget_tree.get_object("TurboRate")
        self.__turbo_box = self.__widget_tree.get_object("TurboBox")
        self.__filter = self.__widget_tree.get_object("Filter")
        self.__override_default_repeat = self.__widget_tree.get_object("OverrideDefaultRepeat")
        self.__activate_on_combo = self.__widget_tree.get_object("ActivateOnCombo")
        self.__show_script_editor = self.__widget_tree.get_object("ShowScriptEditor")
        
    def __load_keys(self):
        """
        Load the available keys for the selected macro type
        """
        sel_type = self.__get_selected_type()
        filter_text = self.__filter.get_text().strip().lower()
        if g15profile.is_uinput_type(sel_type):
            (model, path) = self.__uinput_tree.get_selection().get_selected()
            sel = None
            if path:
                sel = model[path][0]
            model.clear()
            found = False
            for n, v in g15uinput.get_buttons(sel_type):
                if len(filter_text) == 0 or filter_text in n.lower(): 
                    model.append([n, v])
                    if n == sel:
                        self.__select_tree_row(self.__uinput_tree, len(model))
                        found  = True
            (model, path) = self.__uinput_tree.get_selection().get_selected()
            if not found and len(model) > 0:
                self.__select_tree_row(self.__uinput_tree, 0)
            
    def __get_selected_type(self):
        """
        Get the selected macro type
        """
        return self.__map_type_model[self.__mapped_key_type_combo.get_active()][0]
        
    def __set_available_options(self):
        """
        Set the sensitive state of various components based on the current
        selection of other components. 
        """
        
        sel_type = self.__get_selected_type();
        uinput_type = g15profile.is_uinput_type(sel_type)
        opposite_state = g15driver.KEY_STATE_UP if \
                               self.editing_macro.activate_on == \
                               g15driver.KEY_STATE_HELD else \
                               g15driver.KEY_STATE_HELD
        key_conflict = self.selected_profile.get_macro(opposite_state, \
                                           self.editing_macro.memory,
                                           self.editing_macro.keys) is not None
        
        self.__uinput_tree.set_sensitive(uinput_type)
        self.__run_in_background.set_sensitive(sel_type == g15profile.MACRO_COMMAND)
        self.__command.set_sensitive(sel_type == g15profile.MACRO_COMMAND)
        self.__browse_for_command.set_sensitive(sel_type == g15profile.MACRO_COMMAND)
        self.__simple_macro.set_sensitive(sel_type == g15profile.MACRO_SIMPLE)
        self.__macro_script.set_sensitive(sel_type == g15profile.MACRO_SCRIPT)
        self.__action_tree.set_sensitive(sel_type == g15profile.MACRO_ACTION)
        self.__activate_on_combo.set_sensitive(not uinput_type and not key_conflict)
        self.__repeat_mode_combo.set_sensitive(self.__activate_on_combo.get_active() != 2)
        self.__override_default_repeat.set_sensitive(self.editing_macro.repeat_mode != g15profile.NO_REPEAT)
        self.__turbo_box.set_sensitive(self.editing_macro.repeat_mode != g15profile.NO_REPEAT and self.__override_default_repeat.get_active())
        
        self.__simple_box.set_visible(sel_type == g15profile.MACRO_SIMPLE)
        self.__command_box.set_visible(sel_type == g15profile.MACRO_COMMAND)
        self.__action_box.set_visible(sel_type == g15profile.MACRO_ACTION)
        self.__script_box.set_visible(sel_type == g15profile.MACRO_SCRIPT)
        self.__show_script_editor.set_visible(sel_type == g15profile.MACRO_SCRIPT)
        self.__uinput_box.set_visible(uinput_type)
        
    def __validate_macro(self, keys):
        """
        Validate the list of keys, checking if they are in use, reserved
        for an action, and that some have actually been supplier
        
        Keyword arguments:
        keys        -- list of keys to validate
        """
        if len(keys) > 0:
            reserved = g15devices.are_keys_reserved(self.__driver.get_model_name(), keys)
            
            in_use = self.selected_profile.are_keys_in_use(self.editing_macro.activate_on, 
                                                           self.memory_number, 
                                                           keys, 
                                                           exclude=[self.editing_macro])
            if in_use:
                return IN_USE       
            elif reserved:
                return RESERVED_FOR_ACTION
            else:
                return OK
        else:     
            return NO_KEYS
        
    def __check_macro(self, keys):
        """
        Check with the keys provided are valid for the current state, e.g.
        check if another macro or action is using them. Note, this still
        allows the change to happen, it will just show a warning and prevent
        the window from being closed if 
        """
        val = self.__validate_macro(keys)
        if val == IN_USE:
            self.__macro_infobar.set_message_type(gtk.MESSAGE_ERROR)
            self.__macro_warning_label.set_text(_("This key combination is already in use with " + \
                                              "another macro. Please choose a different key or combination of keys"))
            self.__macro_infobar.set_visible(True)
            self.__macro_infobar.show_all()
            
            if self.close_button is not None:
                self.close_button.set_sensitive(False)
        elif val == RESERVED_FOR_ACTION:
            self.__macro_infobar.set_message_type(gtk.MESSAGE_WARNING)
            self.__macro_warning_label.set_text(_("This key combination is reserved for use with an action. You " + \
                                              "may use it, but the results are undefined."))
            self.__macro_infobar.set_visible(True)
            self.__macro_infobar.show_all()
            if self.close_button is not None:
                self.close_button.set_sensitive(True)      
        elif val == NO_KEYS:     
            self.__macro_infobar.set_message_type(gtk.MESSAGE_WARNING)
            self.__macro_warning_label.set_text(_("You have not chosen a macro key to assign the action to."))
            self.__macro_infobar.set_visible(True)
            self.__macro_infobar.show_all()
            if self.close_button is not None:
                self.close_button.set_sensitive(False)
        else:
            self.__macro_infobar.set_visible(False)
            if self.close_button is not None:
                self.close_button.set_sensitive(True)
        
    def __create_macro_info_bar(self):
        """
        Creates a component for display information about the current 
        macro, such as conflicts. The component is added to a placeholder in
        the Glade file
        """
        self.__macro_infobar = gtk.InfoBar()    
        self.__macro_infobar.set_size_request(-1, -1)   
        self.__macro_warning_label = gtk.Label()
        self.__macro_warning_label.set_line_wrap(True)
        self.__macro_warning_label.set_width_chars(60)
        content = self.__macro_infobar.get_content_area()
        content.pack_start(self.__macro_warning_label, True, True)
        
        self.__macro_warning_box.pack_start(self.__macro_infobar, True, True)
        self.__macro_infobar.set_visible(False)
            
    def __set_button_style(self, button):
        """
        Alter the button style based on whether it is active or not
        
        Keyword arguments:
        button        -- button widget
        """
        font = pango.FontDescription("Sans 10")
        if button.get_use_stock():
            label = button.child.get_children()[1]
        elif isinstance(button.child, gtk.Label):
            label = button.child
        else:
            raise ValueError("button does not have a label")
        if button.get_active():
            font.set_weight(pango.WEIGHT_HEAVY)
        else:
            font.set_weight(pango.WEIGHT_MEDIUM)
        label.modify_font(font)
        
OP_ICONS = { 'delay' : 'gtk-media-pause',
            'press' : 'gtk-go-down',
            'upress' : 'gtk-go-down',
            'release' : 'gtk-go-up',
            'urelease' : 'gtk-go-up',
            'execute' : 'gtk-execute',
            'label' : 'gtk-underline',
            'wait'  : 'gtk-stop',
            'goto' : [ 'stock_media-prev','media-skip-backward','gtk-media-previous' ] }
        
class G15MacroScriptEditor():
    
    def __init__(self, gconf_client, driver, editing_macro, parent = None):
        
        self.__gconf_client = gconf_client
        self.__driver = driver
        self.__clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        
        self.__recorder = g15keyio.G15KeyRecorder(self.__driver)
        self.__recorder.on_stop = self._on_stop_record
        self.__recorder.on_add = self._on_record_add
        
        self.__widget_tree = gtk.Builder()
        self.__widget_tree.set_translation_domain("g15-macroeditor")
        self.__widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "script-editor.glade"))
        self._load_objects()
        if parent is not None:
            self.__window.set_transient_for(parent)
        self._load_key_presses()
        self._configure_widgets()
        self._add_info_box()
        self.set_macro(editing_macro)
        self._set_available()
        
        # Connect signal handlers
        self.__widget_tree.connect_signals(self)
        
        # Configure defaults
        self.__output_delays.set_active(g15util.get_bool_or_default(self.__gconf_client, "/apps/gnome15/script_editor/record_delays", True))
        self.__emit_uinput.set_active(g15util.get_bool_or_default(self.__gconf_client, "/apps/gnome15/script_editor/emit_uinput", False))
        self.__recorder.output_delays = self.__output_delays.get_active()
        self.__recorder.emit_uinput = self.__emit_uinput.get_active()
        
    def set_macro(self, macro):
        self.__editing_macro = macro
        self.__macros = self.__editing_macro.macro.split("\n")
        self.__recorder.clear()
        self._rebuild_model()
        self._set_available()
        
    def _rebuild_model(self):
        self.__script_model.clear()
        for macro_text in self.__macros:
            split = macro_text.split(" ")
            op = split[0].lower()
            if len(split) > 1:
                val = " ".join(split[1:])                
                if op in OP_ICONS:
                    icon = OP_ICONS[op]
                    icon_path = g15util.get_icon_path(icon, 24)
                    self.__script_model.append([gtk.gdk.pixbuf_new_from_file(icon_path), val, op, True])
                    
        self._validate_script()

    def _validate_script(self):
        msg =  self._do_validate_script()
        if msg:
            self._show_message(gtk.MESSAGE_ERROR, msg)
            self.__save_button.set_sensitive(False)
        else:
            self.__infobar.hide_all()
            self.__save_button.set_sensitive(True)
                            
    def _do_validate_script(self):
        labels = []
        for _,val,op,_ in self.__script_model:
            if op == "label":
                if val in labels:
                    return "Label <b>%s</b> is defined more than once" % val
                labels.append(val)
        
        pressed = {}
        for _,val,op,_ in self.__script_model:
            if op == "press" or op == "upress":
                if val in pressed:
                    return "More than one key press of <b>%s</b> before a release" % val
                pressed[val] = True
            elif op == "release" or op == "urelease":
                if not val in pressed:
                    return "Release of <b>%s</b> before it was pressed" % val
                del pressed[val]
            elif op == "goto":
                if not val in labels:
                    return "Goto <b>%s</b> uses a label that doesn't exist" % val
                
        if len(pressed) > 0:
            return "The script leaves <b>%s</b> pressed on completion" % ",".join(pressed.keys())
        
        return None
        
    def run(self):
        response = self.__window.run()
        self.__window.hide()
        if response == gtk.RESPONSE_OK:
            buf = ""
            for p in self.__macros:
                if not buf == "":
                    buf += "\n"
                buf += p
            self.__editing_macro.macro = buf
            return True
        
    def _add_info_box(self):
        self.__infobar = gtk.InfoBar()    
        self.__infobar.set_size_request(-1, 32)   
        self.__warning_label = gtk.Label()
        self.__warning_label.set_size_request(400, -1)
        self.__warning_label.set_line_wrap(True)
        self.__warning_label.set_alignment(0.0, 0.0)
        self.__warning_image = gtk.Image()  
        content = self.__infobar.get_content_area()
        content.pack_start(self.__warning_image, False, False)
        content.pack_start(self.__warning_label, True, True)
        self.__info_box_area.pack_start(self.__infobar, False, False)
        self.__infobar.hide_all() 
        
    def _show_message(self, message_type, text):
        print "Showing message",text
        self.__infobar.set_message_type(message_type)
        self.__warning_label.set_text(text)
        self.__warning_label.set_use_markup(True)

        if type == gtk.MESSAGE_WARNING:
            self.__warning_image.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
        
#        self.main_window.check_resize()        
        self.__infobar.show_all()
        
    def _load_objects(self):
        self.__window = self.__widget_tree.get_object("EditScriptDialog")
        self.__script_model = self.__widget_tree.get_object("ScriptModel")
        self.__script_tree = self.__widget_tree.get_object("ScriptTree")
        self.__set_value_dialog = self.__widget_tree.get_object("SetValueDialog")
        self.__set_value = self.__widget_tree.get_object("SetValue")
        self.__edit_selected_values = self.__widget_tree.get_object("EditSelectedValues")
        self.__delay_adjustment = self.__widget_tree.get_object("DelayAdjustment")
        self.__command = self.__widget_tree.get_object("Command")
        self.__label = self.__widget_tree.get_object("Label")
        self.__goto_label_model = self.__widget_tree.get_object("GotoLabelModel")
        self.__goto_label = self.__widget_tree.get_object("GotoLabel")
        self.__key_press_model = self.__widget_tree.get_object("KeyPressModel")
        self.__record_key = self.__widget_tree.get_object("RecordKey")
        self.__emit_uinput = self.__widget_tree.get_object("EmitUInput")
        self.__output_delays = self.__widget_tree.get_object("OutputDelays")
        self.__record_button = self.__widget_tree.get_object("RecordButton")
        self.__stop_button = self.__widget_tree.get_object("StopButton")
        self.__record_status = self.__widget_tree.get_object("RecordStatus")
        self.__scrip_editor_popup = self.__widget_tree.get_object("ScriptEditorPopup")
        self.__info_box_area =  self.__widget_tree.get_object("InfoBoxArea")
        self.__save_button =  self.__widget_tree.get_object("SaveButton")
        self.__wait_combo =  self.__widget_tree.get_object("WaitCombo")
        self.__wait_model =  self.__widget_tree.get_object("WaitModel")
        
    def _load_key_presses(self):
        self.__key_press_model.clear()
        if self.__emit_uinput.get_active():
            for n, v in g15uinput.get_buttons(g15uinput.KEYBOARD):
                self.__key_press_model.append([n])
        else:
            for n in g15keyio.get_keysyms():
                self.__key_press_model.append([n])
        
    def _configure_widgets(self):
        self.__script_tree.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        tree_selection = self.__script_tree.get_selection()
        tree_selection.connect("changed", self._on_selection_changed)
        
    def _on_tree_button_press(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            tree_selection = self.__script_tree.get_selection()
            if tree_selection.count_selected_rows() < 2:
                pthinfo = treeview.get_path_at_pos(x, y)
                if pthinfo is not None:
                    path, col, _, _ = pthinfo
                    treeview.grab_focus()
                    treeview.set_cursor( path, col, 0)
            self.__scrip_editor_popup.popup( None, None, None, event.button, time)
            return True

    def _on_cut(self, widget):
        self._on_copy(widget)
        tree_selection = self.__script_tree.get_selection()
        _, selected_paths = tree_selection.get_selected_rows()
        for p in reversed(selected_paths):
            del self.__macros[p[0]]
        self._rebuild_model()
        
    def _on_copy(self, widget):
        tree_selection = self.__script_tree.get_selection()
        model, selected_paths = tree_selection.get_selected_rows()
        buf = ""
        for p in selected_paths:
            if not buf == "":
                buf += "\n"
            buf += self._format_row(model[p])
        self.__clipboard.set_text(buf)
        
    def _on_paste(self, widget):
        self.__clipboard.request_text(self._clipboard_text_received)
        
    def _clipboard_text_received(self, clipboard, text, data):
        i = self._get_insert_index()
        if text:
            for macro_text in text.split("\n"):
                split = macro_text.split(" ")
                op = split[0].lower()
                if len(split) > 1:
                    val = split[1]
                    if op in OP_ICONS:
                        self.__macros.insert(i, macro_text)
                        i += 1 
            self._rebuild_model()   
        
    def _on_record_add(self, pr, key):
        gobject.idle_add(self._set_available)
        
    def _on_selection_changed(self, widget):
        self.__edit_selected_values.set_sensitive(self._unique_selected_types() == 1)
        
    def  _unique_selected_types(self):
        tree_selection = self.__script_tree.get_selection()
        model, selected_paths = tree_selection.get_selected_rows()
        t = {}
        for p in selected_paths:
            op = model[p][2]
            t[op] = ( t[op] if op in t else 0 ) + 1
                        
        return len(t)
    
    def _on_emit_uinput_toggled(self, widget):
        self.__recorder.emit_uinput = widget.get_active()
        self.__gconf_client.set_bool("/apps/gnome15/script_editor/emit_uinput", widget.get_active())
    
    def _on_deselect_all(self, widget):
        self.__script_tree.get_selection().unselect_all()
        
    def _on_edit_selected_values_activate(self, widget):
        self.__set_value_dialog.set_transient_for(self.__window)
        response = self.__set_value_dialog.run()
        self.__set_value_dialog.hide()
        if response == gtk.RESPONSE_OK:
            tree_selection = self.__script_tree.get_selection()
            model, selected_paths = tree_selection.get_selected_rows()
            for p in selected_paths:
                self.__macros[p[0]] = self._format_row(model[p], self.__set_value.get_text())
            self._rebuild_model()
                
    def _format_row(self, row, value = None):
        return "%s %s" % (self._format_op(row[2]),value if value is not None else row[1])
    
    def _format_op(self, op):
        return op[:1].upper() + op[1:]
    
    def _on_browse_command(self, widget):
        dialog = gtk.FileChooserDialog("Choose Command..",
                               None,
                               gtk.FILE_CHOOSER_ACTION_OPEN,
                               (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.__window)
        dialog.set_filename(self.__command.get_text())
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:
            self.__command.set_text(dialog.get_filename())
    
    def _on_new_goto(self, widget):
        self.__goto_label_model.clear()
        for _,val,op,_ in self.__script_model:
            if op == "label":
                self.__goto_label_model.append([val])
        if not self.__goto_label.get_active() >= 0 and len(self.__goto_label_model) > 0:
            self.__goto_label.set_active(0)
        
        dialog = self.__widget_tree.get_object("AddGotoDialog")  
        dialog.set_transient_for(self.__window)
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:            
            self._insert_macro("%s %s" % ( self._format_op("goto"), self.__goto_label_model[self.__goto_label.get_active()][0]))
    
    def _on_new_label(self, widget):
        dialog = self.__widget_tree.get_object("AddLabelDialog")  
        dialog.set_transient_for(self.__window)
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:            
            self._insert_macro("%s %s" % ( self._format_op("label"), self.__label.get_text()))
    
    def _on_new_execute(self, widget):
        dialog = self.__widget_tree.get_object("AddExecuteDialog")  
        dialog.set_transient_for(self.__window)
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:            
            self._insert_macro("%s %s" % ( self._format_op("execute"), self.__command.get_text()))
            
    
    def _on_new_wait(self, widget):        
        dialog = self.__widget_tree.get_object("AddWaitDialog")  
        dialog.set_transient_for(self.__window)
        if not self.__wait_combo.get_active() >= 0 and len(self.__wait_model) > 0:
            self.__wait_combo.set_active(0)
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:
            self._insert_macro("%s %s" % ( self._format_op("wait"), self.__wait_model[self.__wait_combo.get_active()][0])) 
    
    def _on_add_delay(self, widget):        
        dialog = self.__widget_tree.get_object("AddDelayDialog")  
        dialog.set_transient_for(self.__window)
        response = dialog.run()
        dialog.hide()
        self._stop_recorder()
        if response == gtk.RESPONSE_OK:
            self._insert_macro("%s %s" % ( self._format_op("delay"), int(self.__delay_adjustment.get_value())) )
            
    def _on_rows_reordered(self, model, path, iter, new_order):
        print "reorder"
        # The model will have been updated, so update our text base list from that
        for index,row in enumerate(self._script.model):
            x = self._format_row(row)
            print x
            self.__macros[index] = x
        self._rebuild_model()
            
    def _get_insert_index(self):   
        tree_selection = self.__script_tree.get_selection()
        _, selected_paths = tree_selection.get_selected_rows()
        return len(self.__script_model) if len(selected_paths) == 0 else selected_paths[0][0] + 1
    
    def _on_start_record_button(self, widget):
        self.__recorder.start_record()
        self._set_available()
        
    def _set_available(self):
        self.__record_button.set_sensitive(not self.__recorder.is_recording())
        self.__stop_button.set_sensitive(self.__recorder.is_recording())
        ops = len(self.__recorder.script)
        self.__record_status.set_text(_("Now recording (%d) operations" % ops) if self.__recorder.is_recording() else (_("Will insert %d operations" % ops) if ops > 0 else ""))
        
    def _on_stop_record_button(self, widget):
        self.__recorder.stop_record()
        
    def _on_stop_record(self, recorder): 
        gobject.idle_add(self._set_available)
        
    def _stop_recorder(self):
        if self.__recorder.is_recording():
            self.__recorder.stop_record()
    
    def _on_output_delays_changed(self, widget):
        self.__recorder.output_delays = widget.get_active()
        self.__gconf_client.set_bool("/apps/gnome15/script_editor/record_delays", self.__recorder.output_delays)
        
    def _on_record(self, widget):
        self.__recorder.clear()
        self._set_available()
        dialog = self.__widget_tree.get_object("RecordDialog")  
        dialog.set_transient_for(self.__window)
        response = dialog.run()
        dialog.hide()
        if self.__recorder.is_recording():
            self.__recorder.stop_record()
        if response == gtk.RESPONSE_OK:
            i = self._get_insert_index()
            for op, value in self.__recorder.script:
                if len(self.__recorder.script) > 0:
                    macro_text = "%s %s" % ( self._format_op(op), value) 
                    self.__macros.insert(i, macro_text)
                    i += 1 
            self._rebuild_model()
            
    def _insert_macro(self, macro_text):
        i = self._get_insert_index() 
        self.__macros.insert(i, macro_text) 
        self._rebuild_model()
        
    def _on_remove_macro_operations(self, widget):        
        dialog = self.__widget_tree.get_object("RemoveMacroOperationsDialog")  
        dialog.set_transient_for(self.__window)
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_OK:
            tree_selection = self.__script_tree.get_selection()
            _, selected_paths = tree_selection.get_selected_rows()
            for p in reversed(selected_paths):
                del self.__macros[p[0]]
            self._rebuild_model()
    
    def _on_value_edited(self, widget, path, value):
        self.__macros[int(path)] = self._format_row(self.__script_model[int(path)], value)
        self._rebuild_model()
        
    def _on_select_all_key_operations(self, widget):
        self._select_by_op([ "press", "release", "upress", "urelease" ]) 
        
    def _on_select_all_key_presses(self, widget):
        self._select_by_op(["press", "upress" ])
        
    def _on_select_all_key_releases(self, widget):
        self._select_by_op(["release", "urelease"])
        
    def _on_select_all_commands(self, widget):
        self._select_by_op("execute")
        
    def _on_select_all(self, widget):
        self.__script_tree.get_selection().select_all()
        
    def _on_select_all_delays(self, widget):
        self._select_by_op("delay") 
        
    def _on_macro_operation_cursor_changed(self, widget):
        pass
            
#        tree_selection = self.__script_tree.get_selection()
#        _, selected_path = tree_selection.get_selected_rows()
#        if len(selected_path) == 1:
#            selected_index = selected_path[0][0]
#            _,val,op,_ = self.__script_model[selected_index]
#            print op,val
#            
#            if op == "press":
#                for i in range(selected_index + 1, len(self.__macros)):
#                    _,row_val,row_op,_ = self.__script_model[i]
#                    if row_op == "delay":
#                        self._select_row(i)
#                    elif row_op == "release" and val == row_val:
#                        self._select_row(i)
#                        
#                        if i + 1 < len(self.__script_model) and \
#                            self.__script_model[i + 1][2] == "delay":
#                            self._select_row(i + 1)
#                        
#                        break 
#            elif op == "release":
#                if selected_index + 1 < len(self.__script_model) and \
#                    self.__script_model[selected_index + 1][2] == "delay":
#                    self._select_row(selected_index + 1)
#                    
#                for i in range(selected_index - 1, 0, -1):
#                    _,row_val,row_op,_ = self.__script_model[i]
#                    if row_op == "delay":
#                        self._select_row(i)
#                    elif row_op == "press" and val == row_val:
#                        self._select_row(i)
#                        break
        
                
    def _select_by_op(self, show_ops):
        tree_selection = self.__script_tree.get_selection()
        tree_selection.unselect_all()
        for idx, row in enumerate(self.__script_model):
            _,_,op,_ = row
            if isinstance(show_ops, list) and op in show_ops or op == show_ops:
                tree_selection.select_path(self.__script_model.get_path(self.__script_model.get_iter_from_string("%d" % idx)))
                
    def _select_row(self, row):
        self.__script_tree.get_selection().select_path(self.__script_model.get_path(self.__script_model.get_iter_from_string("%d" % row)))

if __name__ == "__main__":
    me = G15MacroEditor()
    if (me.window):
        me.window.connect("destroy", gtk.main_quit)
        me.window.run()
        me.window.hide()
