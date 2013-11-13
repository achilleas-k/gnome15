#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2013 Nuno Aruajo <nuno.araujo@russo79.com>
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
Pommodoro timer plugin for Gnome15.
This plugin allows a user to apply the Pommodoro Technique to manage their time.
"""

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("pommodoro", modfile = __file__).ugettext

import gnome15.g15screen as g15screen
import gnome15.g15theme as g15theme
import gnome15.util.g15scheduler as g15scheduler
import gnome15.util.g15pythonlang as g15pythonlang
import gnome15.util.g15gconf as g15gconf
import gnome15.util.g15uigconf as g15uigconf
import gnome15.g15driver as g15driver
import gnome15.g15globals as g15globals
import gnome15.g15text as g15text
import gnome15.g15plugin as g15plugin
import gnome15.util.g15cairo as g15cairo
import gnome15.util.g15scheduler as g15scheduler
import datetime
import gtk
import pango
import os
import locale

import logging
logger = logging.getLogger(__name__)

# Plugin details - All of these must be provided
id="pommodoro"
name=_("Pommodoro Timer")
description=_("A Pommodoro Timer.\n" \
              "The <a href=\"http://www.pomodorotechnique.com/\">Pomodoro Technique</a> is an " \
              "amazing way to get the most out of your work day - breaking up your time into " \
              "manageable sections lets you focus more on the task, and accomplish more!")
author="Nuno Araujo <nuno.araujo@russo79.com>"
copyright=_("Copyright (C) 2013 Nuno Araujo")
site="http://www.russo79.com/gnome15"
has_preferences=True
unsupported_models = [g15driver.MODEL_G110,
                      g15driver.MODEL_G11,
                      g15driver.MODEL_G930,
                      g15driver.MODEL_G35]
actions={
         g15driver.SELECT : _("Start / Stop Pommodoro"),
         g15driver.CLEAR : _("Reset finished pommodoro counter"),
         g15driver.VIEW : _("Cancel Pommodoro")
         }
actions_g19={
         g15driver.SELECT : _("Start / Stop Pommodoro"),
         g15driver.CLEAR : _("Reset finished pommodoro counter"),
         g15driver.VIEW : _("Cancel Pommodoro")
         }


DEFAULT_WORK_DURATION       = 25 # [min]
DEFAULT_SHORTBREAK_DURATION =  5 # [min]
DEFAULT_LONGBREAK_DURATION  = 15 # [min]

def create(gconf_key, gconf_client, screen):
    return G15PommodoroPlugin(gconf_key, gconf_client, screen)

def show_preferences(parent, driver, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "pommodoro.ui"))

    dialog = widget_tree.get_object("PommodoroPreferencesDialog")
    dialog.set_transient_for(parent)

    g15uigconf.configure_adjustment_from_gconf(gconf_client,
                                            "{0}/work_duration".format(gconf_key),
                                            "WorkDuration",
                                            DEFAULT_WORK_DURATION,
                                            widget_tree)
    g15uigconf.configure_adjustment_from_gconf(gconf_client,
                                            "{0}/shortbreak_duration".format(gconf_key),
                                            "ShortBreakDuration",
                                            DEFAULT_SHORTBREAK_DURATION,
                                            widget_tree)
    g15uigconf.configure_adjustment_from_gconf(gconf_client,
                                            "{0}/longbreak_duration".format(gconf_key),
                                            "LongBreakDuration",
                                            DEFAULT_LONGBREAK_DURATION,
                                            widget_tree)
    dialog.run()
    dialog.hide()


class PommodoroTimer:
    '''
    PommodoroTimer is a state machine with three main states:
        STOPPED : No activity is taking place
        RUNNING : An activity is taking place
        WAITING : The time allocate to the activity is finished and the timer is waiting for a
                  command either to start the next activity or to stop.

    When in RUNNING state, three different activities are timed:
        WORKING       : The user is currently running a pommodoro
        SHORT_PAUSING : The pommodoro is over and the user is taking a short break
        LONG_PAUSING  : The user is taking a long break each 4 finished pommodoros
    The duration of these activities are configured by three parameters (work_duration,
    shortbreak_duration and longbreak_duration).

    Switching to RUNNING and STOPPED states is made by calling respecively the start and stop
    methods.

    Switching from the WAITING state to the RUNNING state is made by calling the go_on method.

    Switching from the RUNNING state to the WAITING state happens automatically when a activity
    finishes. This is managed by a g15scheduler queue timer.

    If setup, the method assigned to on_state_change method is called each time the state of
    PommodoroTimer changes.

    PommodoroTimer also counts the number of times the WORKING activity was finished in a counter.
    '''

    # States
    STOPPED = 0
    RUNNING = 1
    WAITING = 2

    #Activities
    WORKING       = 1
    SHORT_PAUSING = 2
    LONG_PAUSING  = 3

    NUMBER_OF_POMMODOROS_BEFORE_LONG_PAUSE = 4

    def __init__(self):
        self.work_duration = DEFAULT_WORK_DURATION
        self.shortbreak_duration = DEFAULT_SHORTBREAK_DURATION
        self.longbreak_duration = DEFAULT_LONGBREAK_DURATION

        self._count = 0

        self._state = PommodoroTimer.STOPPED
        self._activity = PommodoroTimer.WORKING

        self._state_change_timer = None
        self._started_at = None
        self._timer_value = self._minutes_to_timedelta(self.work_duration)

        self.on_state_change = None
        self.on_count_change = None

    def start(self):
        '''
        Start the timer
        '''
        if self._state == PommodoroTimer.STOPPED:
            self._state_next()

    def stop(self):
        '''
        Stop the timer
        '''
        if self._state in [PommodoroTimer.WAITING, PommodoroTimer.RUNNING]:
            self._destroy_state_change_timer()
            self._timer_value = self._minutes_to_timedelta(self.work_duration)
            self._state = PommodoroTimer.STOPPED
            self._activity = PommodoroTimer.WORKING
            self._signal_state_change()
            self._log_pommodoro_state()

    def go_on(self):
        '''
        Continue the timer when in WAITING state
        '''
        if self._state == PommodoroTimer.WAITING:
            self._state_next()

    def init_count_at(self, value):
        self._count = value
        self._signal_count_change()

    def count_reset(self):
        '''
        Resets the finished pommodoros counter
        '''
        self._count = 0
        self._signal_count_change()

    def recalculate(self):
        '''
        Recalculate the timer schedulers.
        This method should be called when changes are made to any of the fields managing the
        the activity durations (work_duration, shortbreak_duration or longbreak_duration)
        '''

        # Update the _timer_value to a new value depending on the activity.
        if self._state in [PommodoroTimer.RUNNING, PommodoroTimer.STOPPED]:
            # We don't set the new values if the timer is finished (WAITING).
            if self._activity == PommodoroTimer.WORKING:
                self._timer_value = self._minutes_to_timedelta(self.work_duration)
            elif self._activity == PommodoroTimer.SHORT_PAUSING:
                self._timer_value = self._minutes_to_timedelta(self.shortbreak_duration)
            elif self._activity == PommodoroTimer.LONG_PAUSING:
                self._timer_value = self._minutes_to_timedelta(self.longbreak_duration)

        # If the timer is running, reschedule the state change timer
        if self._state == PommodoroTimer.RUNNING:
            next_schedule = max(0, (self._timer_value - self._elapsed_time()).total_seconds())
            self._schedule_next_state(next_schedule)
            logger.info("Scheduled next state change in %s", str(next_schedule))

    @property
    def state(self):
        '''
        Returns the current state of the pommodoro timer
        '''
        return self._state

    @property
    def activity(self):
        '''
        Returns the current activity
        '''
        return self._activity

    @property
    def timer_value(self):
        '''
        Returns the current timer maximum value
        '''
        return self._timer_value

    @property
    def value(self):
        '''
        Returns the current timer remaining time.
        Note, this value can be less than 0 if the timer has elapsed.
        '''
        if self._state == PommodoroTimer.STOPPED:
            return self._timer_value
        else:
            return self._timer_value + self._started_at - datetime.datetime.now()

    @property
    def started_at(self):
        '''
        Returns the time at which the last activity started
        '''
        return self._started_at

    @property
    def count(self):
        '''
        Returns the number of finished pommodoros
        '''
        return self._count

    '''
    Private methods
    '''
    def _elapsed_time(self):
        return datetime.datetime.now() - self._started_at

    def _state_next(self):
        '''
        Switch to next state within 'normal' workflow
        '''
        logger.debug("Switching to next state")
        if self._state == PommodoroTimer.STOPPED:
            # Start pommodoro timer
            self._schedule_next_state(self._timer_value.total_seconds())
            self._started_at = datetime.datetime.now()
            self._state = PommodoroTimer.RUNNING
            self._activity = PommodoroTimer.WORKING

        elif self._state == PommodoroTimer.RUNNING:
            # Timer over, go to waiting state
            self._destroy_state_change_timer()
            if self._activity == PommodoroTimer.WORKING:
                self._count_increase()
            self._state = PommodoroTimer.WAITING

        elif self._state == PommodoroTimer.WAITING:
            # User accepted to continue, cycle activity and go to RUNNING state
            if self._activity == PommodoroTimer.WORKING:
                # Start pause if we were working
                if self._count % PommodoroTimer.NUMBER_OF_POMMODOROS_BEFORE_LONG_PAUSE == 0:
                    # If 4 pommodoros were completed, start long pause
                    self._timer_value = self._minutes_to_timedelta(self.longbreak_duration)
                    self._activity = PommodoroTimer.LONG_PAUSING
                else:
                    # Start short pause
                    self._timer_value = self._minutes_to_timedelta(self.shortbreak_duration)
                    self._activity = PommodoroTimer.SHORT_PAUSING
            else:
                # Start working if we were in pause
                self._timer_value = self._minutes_to_timedelta(self.work_duration)
                self._activity = PommodoroTimer.WORKING
            self._schedule_next_state(self._timer_value.total_seconds())
            self._started_at = datetime.datetime.now()
            self._state = PommodoroTimer.RUNNING
        self._signal_state_change()
        self._log_pommodoro_state()

    def _signal_state_change(self):
        if self.on_state_change is not None:
            self.on_state_change()

    def _log_pommodoro_state(self):
        logger.info("Switched to state {0} - {1}".format(self._state, self._activity))

    def _schedule_next_state(self, when):
        self._destroy_state_change_timer()
        self._state_change_timer = g15scheduler.schedule("PommodoroTimerStateChange",
                                                        when,
                                                        self._state_next)

    def _destroy_state_change_timer(self):
        if self._state_change_timer is not None:
            self._state_change_timer.cancel()
            self._state_change_timer = None

    def _minutes_to_timedelta(self, minutes):
        return datetime.timedelta(0, 0, 0, 0, minutes)

    def _count_increase(self):
        self._count += 1
        self._signal_count_change()

    def _signal_count_change(self):
        if self.on_count_change is not None:
            self.on_count_change()


class G15PommodoroPlugin(g15plugin.G15RefreshingPlugin):

    def __init__(self, gconf_key, gconf_client, screen):
        g15plugin.G15RefreshingPlugin.__init__(self,
                                               gconf_client,
                                               gconf_key,
                                               screen,
                                               self._get_icon_path("Machovka_tomato.png"),
                                               id,
                                               name)
        self.waiting_image = \
                g15cairo.load_surface_from_file(self._get_icon_path("Machovka_tomato.png"))
        self.running_image = \
                g15cairo.load_surface_from_file(self._get_icon_path("Machovka_tomato_green.png"))
        self.waiting_image_1bpp = \
                g15cairo.load_surface_from_file(self._get_icon_path("tomato_empty_1bpp.png"))
        self.running_image_1bpp = \
                g15cairo.load_surface_from_file(self._get_icon_path("tomato_1bpp.png"))

        self.pommodoro_timer = PommodoroTimer()
        self.pommodoro_timer.on_state_change = self.timer_state_changed
        self.pommodoro_timer.on_count_change = self.pommodoro_count_save
        self._load_configuration()

    def activate(self):
        self._load_configuration()
        self.pommodoro_timer.stop()
        g15plugin.G15RefreshingPlugin.activate(self)
        self.screen.key_handler.action_listeners.append(self)
        self.watch([self._get_configuration_key("work_duration"),
                    self._get_configuration_key("shortbreak_duration"),
                    self._get_configuration_key("longbreak_duration")], self._config_changed)

    def deactivate(self):
        self.pommodoro_timer.stop()
        self.screen.key_handler.action_listeners.remove(self)
        g15plugin.G15RefreshingPlugin.deactivate(self)

    def action_performed(self, binding):
        if not (self.page and self.page.is_visible()):
            # Return if we are not displayed on screen
            return

        if binding.action == g15driver.SELECT:
            if self.pommodoro_timer.state == PommodoroTimer.STOPPED:
                self.pommodoro_timer.start()
            elif self.pommodoro_timer.state == PommodoroTimer.WAITING:
                self.pommodoro_timer.go_on()
            else:
                self.pommodoro_timer.stop()
        elif binding.action == g15driver.VIEW:
            if self.pommodoro_timer.state == PommodoroTimer.WAITING:
                self.pommodoro_timer.stop()
        elif binding.action == g15driver.CLEAR:
                self.pommodoro_timer.count_reset()

    def _paint_panel(self, canvas, allocated_size, horizontal):
        # Nothing to paint if the timer is stopped
        if self.pommodoro_timer.state == PommodoroTimer.STOPPED:
            return

        # Nothing to paint if the page is visible
        if not self.page or (self.page and self.page.is_visible()):
            return

        if self.screen.driver.get_bpp() == 1:
            if self.pommodoro_timer.state == PommodoroTimer.WAITING:
                size = g15cairo.paint_thumbnail_image(allocated_size,
                                                      self.waiting_image_1bpp,
                                                      canvas)
            elif self.pommodoro_timer.state == PommodoroTimer.RUNNING:
                size = g15cairo.paint_thumbnail_image(allocated_size,
                                                      self.running_image_1bpp,
                                                      canvas)
        else:
            if self.pommodoro_timer.state == PommodoroTimer.WAITING:
                size = g15cairo.paint_thumbnail_image(allocated_size, self.waiting_image, canvas)
            elif self.pommodoro_timer.state == PommodoroTimer.RUNNING:
                size = g15cairo.paint_thumbnail_image(allocated_size, self.running_image, canvas)

        return size

    def get_theme_properties(self):
        properties = { }

        properties["timer"] = self._format_timer_value_for_display()

        properties["pommodoro_timer"] = self._get_progress_in_percent()

        if self.pommodoro_timer.activity == PommodoroTimer.WORKING:
            properties["action"] = "Work"
        elif self.pommodoro_timer.activity == PommodoroTimer.SHORT_PAUSING:
            properties["action"] = "Small break"
        elif self.pommodoro_timer.activity == PommodoroTimer.LONG_PAUSING:
            properties["action"] = "Long break"

        properties["count"] = str(self.pommodoro_timer.count)

        if self.pommodoro_timer.state == PommodoroTimer.WAITING:
            if self.pommodoro_timer.activity == PommodoroTimer.WORKING:
                properties["message"] = "Time for a break"
            else:
                properties["message"] = "Break's over!"
        else:
            properties["message"] = ""

        return properties

    def timer_state_changed(self):
        self._reload_theme()
        # Raise the page for 10 seconds if a activity has just finished (state went to WAITING)
        if self.pommodoro_timer.state == PommodoroTimer.WAITING \
           and self.page is not None \
           and self.page.theme is not None:
            self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 10.0)


    def pommodoro_count_save(self):
        pommodoro_count_conf_key = self._get_configuration_key("pommodoro_count")
        self.gconf_client.set_int(pommodoro_count_conf_key, self.pommodoro_timer.count)

    def _format_timer_value_for_display(self):
        total_seconds = int(self.pommodoro_timer.value.total_seconds())
        if total_seconds > 0:
            return str(datetime.timedelta(0, total_seconds))
        else:
            x = int((datetime.datetime.now() \
                    - self.pommodoro_timer.started_at \
                    - self.pommodoro_timer.timer_value).total_seconds())
            return "- {0}".format(str(datetime.timedelta(0, x)))

    def _get_progress_in_percent(self):
        return 100 - int(self.pommodoro_timer.value.total_seconds() \
                         / self.pommodoro_timer.timer_value.total_seconds() \
                         * 100)

    def _config_changed(self, client, connection_id, entry, args):
        self._load_configuration()
        self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)

    def _load_configuration(self):
        work_duration_conf_key = self._get_configuration_key("work_duration")
        self.pommodoro_timer.work_duration = g15gconf.get_int_or_default(self.gconf_client,
                                                                        work_duration_conf_key,
                                                                        DEFAULT_WORK_DURATION)

        shortbreak_conf_key = self._get_configuration_key("shortbreak_duration")
        self.pommodoro_timer.shortbreak_duration = \
                g15gconf.get_int_or_default(self.gconf_client,
                                            shortbreak_conf_key,
                                            DEFAULT_SHORTBREAK_DURATION)

        longbreak_conf_key = self._get_configuration_key("longbreak_duration")
        self.pommodoro_timer.longbreak_duration = \
                g15gconf.get_int_or_default(self.gconf_client,
                                            longbreak_conf_key,
                                            DEFAULT_LONGBREAK_DURATION)

        pommodoro_count_conf_key = self._get_configuration_key("pommodoro_count")
        self.pommodoro_timer.init_count_at(g15gconf.get_int_or_default(self.gconf_client,
                                                                       pommodoro_count_conf_key,
                                                                       0))
        self.pommodoro_timer.recalculate()

    def _get_configuration_key(self, key_name):
        '''
        Returns the full gconf key name for the relative key_name passed as parameter
        '''
        return "{0}/{1}".format(self.gconf_key, key_name)

    def _reload_theme(self):
        variant = None
        if self.pommodoro_timer.state == PommodoroTimer.WAITING:
            variant = "timerover"
        if self.page is not None and self.page.theme is not None:
            self.page.theme.set_variant(variant)

    def _get_icon_path(self, name):
        return os.path.join(os.path.dirname(__file__), name)
