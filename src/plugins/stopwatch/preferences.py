#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2011 Nuno Araujo <nuno.araujo@russo79.com>
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

import gnome15.util.g15uigconf as g15uigconf
import gtk
import os

class G15StopwatchPreferences():

    def __init__(self, parent, driver, gconf_client, gconf_key):
        widget_tree = gtk.Builder()
        widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "stopwatch.ui"))

        self.dialog = widget_tree.get_object("StopwatchDialog")
        self.dialog.set_transient_for(parent)

        # Timer 1 settings
        g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/timer1_enabled",  "cb_timer1_enabled", False, widget_tree, True)

        timer1_label = widget_tree.get_object("e_timer1_label")
        timer1_label.set_text(gconf_client.get_string(gconf_key + "/timer1_label") or "")
        timer1_label.connect("changed", self._label_changed, gconf_key + "/timer1_label", gconf_client)

        g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/timer1_mode_stopwatch", "rb_timer1_stopwatch_mode", True, widget_tree, True)
        rb_timer1_stopwatch = widget_tree.get_object("rb_timer1_stopwatch_mode")
        rb_timer1_stopwatch.connect("clicked", self._timer_timer_mode, widget_tree, "1", False)
        g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/timer1_mode_countdown", "rb_timer1_countdown_mode", False, widget_tree, True)
        rb_timer1_countdown = widget_tree.get_object("rb_timer1_countdown_mode")
        rb_timer1_countdown.connect("clicked", self._timer_timer_mode, widget_tree, "1", True)

        g15uigconf.configure_spinner_from_gconf(gconf_client, gconf_key + "/timer1_hours", "sb_timer1_hours", 0, widget_tree, False)
        g15uigconf.configure_spinner_from_gconf(gconf_client, gconf_key + "/timer1_minutes", "sb_timer1_minutes", 5, widget_tree, False)
        g15uigconf.configure_spinner_from_gconf(gconf_client, gconf_key + "/timer1_seconds", "sb_timer1_seconds", 0, widget_tree, False)

        g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/timer1_loop", "cb_timer1_loop", False, widget_tree, True)

        # Timer 2 settings
        g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/timer2_enabled", "cb_timer2_enabled", False, widget_tree, True)

        timer2_label = widget_tree.get_object("e_timer2_label")
        timer2_label.set_text(gconf_client.get_string(gconf_key + "/timer2_label") or "")
        timer2_label.connect("changed", self._label_changed, gconf_key + "/timer2_label", gconf_client)

        g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/timer2_mode_stopwatch", "rb_timer2_stopwatch_mode", True, widget_tree, True)
        rb_timer2_stopwatch = widget_tree.get_object("rb_timer2_stopwatch_mode")
        rb_timer2_stopwatch.connect("clicked", self._timer_timer_mode, widget_tree, "2", False)

        g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/timer2_mode_countdown", "rb_timer2_countdown_mode", False, widget_tree, True)
        rb_timer2_countdown = widget_tree.get_object("rb_timer2_countdown_mode")
        rb_timer2_countdown.connect("clicked", self._timer_timer_mode, widget_tree, "2", True)

        g15uigconf.configure_spinner_from_gconf(gconf_client, gconf_key + "/timer2_hours", "sb_timer2_hours", 0, widget_tree, False)
        g15uigconf.configure_spinner_from_gconf(gconf_client, gconf_key + "/timer2_minutes", "sb_timer2_minutes", 5, widget_tree, False)
        g15uigconf.configure_spinner_from_gconf(gconf_client, gconf_key + "/timer2_seconds", "sb_timer2_seconds", 0, widget_tree, False)

        g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/timer2_loop", "cb_timer2_loop", False, widget_tree, True)
        g15uigconf.configure_checkbox_from_gconf(gconf_client, gconf_key + "/keep_page_visible", "cb_keep_page_visible", True, widget_tree, True)

        # Refresh UI state
        self._timer_timer_mode(None, widget_tree, "1", rb_timer1_countdown.get_active())
        self._timer_timer_mode(None, widget_tree, "2", rb_timer2_countdown.get_active())

        
    def _label_changed(self, widget, gconf_key, gconf_client):
        gconf_client.set_string(gconf_key, widget.get_text())

    '''
    Set the UI sensivity according to the selected mode
    '''
    def _timer_timer_mode(self, widget, widget_tree, timer_no, mode = False):
        sb_timer_hours = widget_tree.get_object("sb_timer" + timer_no + "_hours")
        sb_timer_hours.set_sensitive(mode)
        sb_timer_minutes = widget_tree.get_object("sb_timer" + timer_no + "_minutes")
        sb_timer_minutes.set_sensitive(mode)
        sb_timer_seconds = widget_tree.get_object("sb_timer" + timer_no + "_seconds")
        sb_timer_seconds.set_sensitive(mode)
        cb_timer_loop = widget_tree.get_object("cb_timer" + timer_no + "_loop")
        cb_timer_loop.set_sensitive(mode)

    def run(self):
        self.dialog.run()
        self.dialog.hide()

# vim:set ts=4 sw=4 et:
