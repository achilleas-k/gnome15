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
This module deals with handling raw key presses from the driver, and turning them
into Macros or actions. The different types of macro are handled accordingly, as well
as the repetition functions.

All key events are handled on a queue (one per instance of a key handler). 

"""

import gnome15.g15locale as g15locale
_ = g15locale.get_translation("gnome15").ugettext

import g15profile
import g15util
import g15driver
import g15actions
import g15uinput

import logging
logger = logging.getLogger("keyboard")
   
class KeyState():
    """
    Holds the current state of a single macro key
    """
    def __init__(self, key):
        self.key = key
        self.state_id = None
        self.timer = None
        self.consumed = False
        self.defeat_release = False
        self.consume_until_release = False
        
    def is_consumed(self):
        return self.consumed or self.consume_until_release
        
    def cancel_timer(self):
        """
        Cancel the HELD timer if one exists.
        """
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
            
    def __repr__(self):
        return "%s = %s [consumed = %s]" % (self.key, g15profile.to_key_state_name(self.state_id), str(self.consumed) )      
    
class G15KeyHandler():
    """
    Main class for handling key events. There should be one instance of this
    per active G15Screen. 
    """
    
    def __init__(self, screen):
        # Public        
        self.queue_name = "MacroQueue-%s" % screen.device.uid
        
        """
        List of callbacks invoked when an action is activated by it's key combination
        """
        self.action_listeners = []
        
        """
        List of callbacks invoked for raw key handling. Normally plugins shouldn't
        use this, use actions instead
        """
        self.key_handlers = []
        
        # Private
        self.__screen = screen
        self.__conf_client = self.__screen.conf_client
        self.__repeat_macros = []
        self.__macro_repeat_timer = None
        self.__uinput_macros = []
        self.__normal_macros = []
        self.__normal_held_macros = []
        self.__notify_handles = []
        self.__key_states = {}
        
    def get_key_states(self):
        # Get the current state of the keys
        return self.__key_states
        
    def start(self):
        """
        Start handling keys
        """
        screen_key = "/apps/gnome15/%s" % self.__screen.device.uid
        logger.info("Starting %s's key handler." % self.__screen.device.uid)
        g15profile.profile_listeners.append(self._profile_changed)
        self.__screen.screen_change_listeners.append(self)
        self.__notify_handles.append(self.__conf_client.notify_add("%s/active_profile" % screen_key, self._active_profile_changed))
        logger.info("Starting of %s's key handler is complete." % self.__screen.device.uid)
        self._reload_active_macros()
        
    def stop(self):
        """
        Stop handling keys
        """  
        logger.info("Stopping key handler for %s" % self.__screen.device.uid)
        g15util.stop_queue(self.queue_name)
        self.__screen.screen_change_listeners.remove(self)
        if self._profile_changed in g15profile.profile_listeners:
            g15profile.profile_listeners.remove(self._profile_changed)
        for h in self.__notify_handles:
            self.__conf_client.notify_remove(h)
        self.__notify_handles = [] 
        logger.info("Stopped key handler for %s" % self.__screen.device.uid)
        
    def key_received(self, keys, state_id):
        """
        This function starts processing of the provided keys, turning them
        into macros, actions and handling repetition. The key event will be
        placed on the queue, leaving this function to return immediately
        
        Keyword arguments:
        keys            --    list of keys to process
        state_id           -- key state ID (g15driver.KEY_STATE_UP, _DOWN and _HELD)
        """
        g15util.queue(self.queue_name, "KeyReceived", 0, self._do_key_received, keys, state_id)
            
    def memory_bank_changed(self, bank):
        self._reload_active_macros()
        
    """
    Callbacks
    """
            
    def _active_profile_changed(self, client, connection_id, entry, args):
        self._reload_active_macros()
        return 1

    def _profile_changed(self, profile_id, device_uid):
        self._reload_active_macros()
    
    """
    Private
    """
        
    def _reload_active_macros(self):
        self.__normal_held_macros = []
        self.__normal_macros = []
        self.__uinput_macros = []
        self._build_macros()
        
    def _do_key_received(self, keys, state_id):
        """
        Actual handling of key events.
        
        Keyword arguments:
        keys        --    list of keys
        state_id    --    key state (g15driver.KEY_STATE_UP, _DOWN and _HELD)
        """
               
        """
        See if the screen itself, or the plugins, want to handle the key. This
        is the legacy method of key handling, the preferred method now is
        actions which is handled below. However, this is still useful for plugins
        that want to take over key handling, such as screensaver which 
        disables all keys while it is active.
        """ 
        try:
            if self._handle_key(keys, state_id, post=False):
                return  
            
            """
            Deal with each key separately, this keeps it simpler
            """
            for key in keys:
            
                """
                Now set up the macro key state. This is where we decide what macros
                and actions to activate.
                """
                if self._configure_key_state(key, state_id):
                            
                    """
                    Do uinput macros first. These are treated slightly differently, because
                    a press of the Macro key equals a "press" of the virtual key,
                    a release of the Macro key equals a "release" of the virtual key etc.  
                    """
                    self._handle_uinput_macros()
                    
                    """
                    Now the ordinary macros, processed on key_up
                    """
                    self._handle_normal_macros()
                    
                    """
                    Now the actions
                    """
                    self._handle_actions()
                
            """
            Now do the legacy 'post' handling.
            """
            if not self._handle_key(keys, state_id, post=True):
                pass
                    
            """
            When ALL keys are UP, clear out the state 
            """
            up = 0
            for k, v in self.__key_states.items():
                if v.state_id == g15driver.KEY_STATE_UP:
                    up += 1
            if up > 0 and up == len(self.__key_states):
                self.__key_states = {}
        finally:
            """
            Always redraw the current page on key presses
            """
            page = self.__screen.get_visible_page()
            if page:
                page.mark_dirty()
                page.redraw()
            
    def _handle_actions(self):
        """
        This handles the default action bindings. The actions may have
        already re-mapped as a macro, in which case they will be ignored 
        here.
        """
        action_keys = self.__screen.driver.get_action_keys()
        if action_keys:
            for action in action_keys:
                binding = action_keys[action]
                f = 0
                for k in binding.keys:
                    if k in self.__key_states and \
                            binding.state == self.__key_states[k].state_id and \
                            not self.__key_states[k].is_consumed():
                        f += 1
                if f == len(binding.keys):
                    self._action_performed(binding)
                    for k in binding.keys:
                        self.__key_states[k].consume_until_release = True
        
    def _handle_normal_macros(self):
        """
        First check for any KEY_STATE_HELD macros. We do these first so KEY_STATE_UP
        macros don't consume the key states
        """        
        for m in self.__normal_held_macros:
            held = []
            for k in m.keys:
                if k in self.__key_states:
                    key_state = self.__key_states[k]
                    if not key_state.is_consumed() and key_state.state_id == g15driver.KEY_STATE_HELD:
                        held.append(key_state)
                        
            if len(held) == len(m.keys):
                self._handle_macro(m, g15driver.KEY_STATE_HELD, held)
        
        
        """
        Search for all the non-uinput macros that would be activated by the
        current key state. In this case, KEY_STATE_UP macros are looked for
        """
        for m in self.__normal_macros:
            up = []
            held = []
            for k in m.keys:
                if k in self.__key_states:
                    key_state = self.__key_states[k]
                    if not key_state.is_consumed() and key_state.state_id == g15driver.KEY_STATE_UP and not key_state.defeat_release:
                        up.append(key_state)
                    if not key_state.is_consumed() and key_state.state_id == g15driver.KEY_STATE_HELD:
                        held.append(key_state)
                        
            if len(up) == len(m.keys):
                self._handle_macro(m, g15driver.KEY_STATE_UP, up)
            if len(held) == len(m.keys):
                self._handle_macro(m, g15driver.KEY_STATE_HELD, held)
                
            
    def _handle_uinput_macros(self):
        """
        Search for all the uinput macros that would be activated by the
        current key state, and emit events of the same type.
        """
        uinput_repeat = False
        for m in self.__uinput_macros:
            down = []
            up = []
            held = []
            for k in m.keys:
                if k in self.__key_states:
                    key_state = self.__key_states[k]
                    if not key_state.is_consumed():
                        if key_state.state_id == g15driver.KEY_STATE_UP and not key_state.defeat_release:
                            up.append(key_state)
                        if key_state.state_id == g15driver.KEY_STATE_DOWN:
                            down.append(key_state)
                        if key_state.state_id == g15driver.KEY_STATE_HELD:
                            held.append(key_state)
                        
            if len(down) == len(m.keys):
                self._handle_uinput_macro(m, g15driver.KEY_STATE_DOWN, down)
            if len(up) == len(m.keys):
                self._handle_uinput_macro(m, g15driver.KEY_STATE_UP, up)
            if len(held) == len(m.keys):
                self._handle_uinput_macro(m, g15driver.KEY_STATE_HELD, held)
                uinput_repeat = True
                                
        """
        Simulate a uinput repeat by just handling an empty key list.
        No keys have changed state, so we should just keep hitting this
        reschedule until they do
        """
        if uinput_repeat:
            g15util.queue(self.queue_name, "RepeatUinput", \
                              0.1, \
                              self._handle_uinput_macros)
                
    def _configure_key_state(self, key, state_id):
        
        """
        Maintains the "key state" table, which holds what state each key
        is currently in.
        
        This function will return the number of state changes, so this key
        event may be ignored if it is no longer appropriate (i.e. a hold
        timer event for keys that are now released)
        
        Keyword arguments:
        key        -- single key
        state_id   -- state_id (g15driver.KEY_STATE_UP, _DOWN or _HELD)
        """
        if state_id == g15driver.KEY_STATE_HELD and not key in self.__key_states:
            """
            All keys were released before the HOLD timer kicked in, so we
            totally ignore this key
            """
            pass
        else:
            if not key in self.__key_states:
                self.__key_states[key] = KeyState(key)
            key_state = self.__key_states[key]
            
            # This is a new key press, so reset this key's consumed state
            key_state.consumed = False
            
            # Check the sanity of the key press
            self._check_key_state(state_id, key_state)            
            key_state.state_id = state_id
            
            if state_id == g15driver.KEY_STATE_DOWN:
                """
                Key is now down, let's set up a timer to produce a held event
                """
                key_state.timer = g15util.queue(self.queue_name,
                                                "HoldKey%s" % str(key), \
                                                self.__screen.service.key_hold_duration, \
                                                self._do_key_received, [ key ], \
                                                g15driver.KEY_STATE_HELD)
            elif state_id == g15driver.KEY_STATE_UP:
                """
                Now the key is up, cancel the HELD timer if one exists. 
                """                
                key_state.cancel_timer()
            
            return True
                
    def _get_all_macros(self, profile = None, macro_list = None, macro_keys = None, mapped_to_key = False, state = None):
        """
        Get all macros, including those in parent profiles. By default, the
        "root" is the active profile
        
        Keyword argumentsL
        profile        -- root profile or None for active profile
        macro_list     -- list to append macros to.
        mapped_to_key  -- boolean indicator whether to only find UINPUT type macros
        """
        if profile is None:
            profile = g15profile.get_active_profile(self.__screen.device)
        if macro_list is None:
            macro_list = []
        if macro_keys is None:
            macro_keys = []
            
        if state == None:
            state = g15driver.KEY_STATE_UP
             
        bank = self.__screen.get_memory_bank()
        for m in profile.macros[state][bank - 1]:
            if not m.key_list_key in macro_keys:
                if ( not mapped_to_key and not m.is_uinput() ) or \
                    ( mapped_to_key and m.is_uinput() ):
                    macro_list.append(m)
                    macro_keys.append(m.key_list_key)
        if profile.base_profile is not None:
            profile = g15profile.get_profile(self.__screen.device, profile.base_profile)
            if profile is not None:
                self._get_all_macros(profile, macro_list, macro_keys, mapped_to_key, state)
        return macro_list
    
    def _build_macros(self, profile = None, macro_keys = None, held_macro_keys = None):
        if profile is None:
            profile = g15profile.get_active_profile(self.__screen.device)
        if macro_keys is None:
            macro_keys = []
        if held_macro_keys is None:
            held_macro_keys = []
            
        bank = self.__screen.get_memory_bank()
        for m in profile.macros[g15driver.KEY_STATE_UP][bank - 1]:
            if not m.key_list_key in macro_keys:
                if m.is_uinput():
                    self.__uinput_macros.append(m)
                else:
                    self.__normal_macros.append(m)
                macro_keys.append(m.key_list_key)
                
        for m in profile.macros[g15driver.KEY_STATE_HELD][bank - 1]:
            if not m.key_list_key in held_macro_keys:
                if not m.is_uinput():
                    self.__normal_held_macros.append(m)
                held_macro_keys.append(m.key_list_key)
                
        if profile.base_profile is not None:
            profile = g15profile.get_profile(self.__screen.device, profile.base_profile)
            if profile is not None:
                self._build_macros(profile, macro_keys, held_macro_keys)
                
    def _check_key_state(self, new_state_id, key_state):
        """
        Sanity check
        
        Keyword arguments:
        new_state_id        --    new state ID
        key_state           --    key state object
        """
        if new_state_id == g15driver.KEY_STATE_UP and \
            key_state.state_id not in [ g15driver.KEY_STATE_DOWN, g15driver.KEY_STATE_HELD ]:
            logger.warning("Received key up state before receiving key down, indicates defeated key press.")
            return False
#        if new_state_id == g15driver.KEY_STATE_DOWN and \
#            key_state.state_id is not None:
#            logger.warning("Received unexpected key down (key was in state %s)." % g15profile.to_key_state_name(key_state.state_id))
#            return False
        if new_state_id == g15driver.KEY_STATE_HELD and \
            key_state.state_id in [ g15driver.KEY_STATE_UP, None ]:
            logger.warning("Received key held state before receiving key down.")
            return False
        
        return True
        
    def _send_uinput_keypress(self, macro, uc, uinput_repeat = False):
        g15uinput.locks[macro.type].acquire()
        try:
            if uinput_repeat:
                g15uinput.emit(macro.type, uc, 2)
            else:
                g15uinput.emit(macro.type, uc, 1)
                g15uinput.emit(macro.type, uc, 0)                            
        finally:
            g15uinput.locks[macro.type].release()
            
    def _repeat_uinput(self, macro, uc, uinput_repeat = False):
        if macro in self.__repeat_macros:
            self._send_uinput_keypress(macro, uc, uinput_repeat)
        if macro in self.__repeat_macros:
            self.__macro_repeat_timer = g15util.queue(self.queue_name, "MacroRepeat", macro.repeat_delay, self._repeat_uinput, self.__reload_macro_instance(macro), uc, uinput_repeat)
        
    def _handle_uinput_macro(self, macro, state, key_states):
        uc = macro.get_uinput_code()
        self._consume_keys(key_states)
        if state == g15driver.KEY_STATE_UP:  
            if macro in self.__repeat_macros and macro.repeat_mode == g15profile.REPEAT_WHILE_HELD:
                self.__repeat_macros.remove(macro)
            g15uinput.emit(macro.type, uc, 0)
        elif state == g15driver.KEY_STATE_DOWN:
            if macro in self.__repeat_macros:
                if macro.repeat_mode == g15profile.REPEAT_TOGGLE and macro.repeat_delay != -1:
                    """
                    For REPEAT_TOGGLE mode with custom repeat rate, we now cancel
                    the repeat timer and defeat the key release.
                    """                   
                    self.__repeat_macros.remove(macro)                 
                else:
                    """
                    For REPEAT_TOGGLE mode with default repeat rate, we will send a release if this 
                    is the second press. We also defeat the 2nd release.
                    """
                    g15uinput.emit(macro.type, uc, 0)
                    self.__repeat_macros.remove(macro)
                    self._defeat_release(key_states)
            else:
                if macro.repeat_mode == g15profile.REPEAT_TOGGLE:
                    """
                    Start repeating
                    """
                    if not macro in self.__repeat_macros:
                        self._defeat_release(key_states)   
                        self.__repeat_macros.append(macro)                        
                        if macro.repeat_delay != -1:
                            """
                            For the default delay, just let the OS handle the repeat
                            """
                            self._repeat_uinput(macro, uc)
                        else:
                            """
                            For the custom delay, send the key press now. We send
                            the first when it is actually released, then start
                            sending further repeats on a timer
                            """
                            g15uinput.emit(macro.type, uc, 1)
                            self._defeat_release(key_states)
                elif macro.repeat_mode == g15profile.NO_REPEAT:
                    """
                    For NO_REPEAT macros we send the release now, and defeat the
                    actual key release that will come later.
                    """
                    self._send_uinput_keypress(macro, uc)
                elif macro.repeat_mode == g15profile.REPEAT_WHILE_HELD and macro.repeat_delay != -1:
                    self._send_uinput_keypress(macro, uc)
                else:
                    g15uinput.emit(macro.type, uc, 1)
                            
        elif state == g15driver.KEY_STATE_HELD:
            if macro.repeat_mode == g15profile.REPEAT_WHILE_HELD:
                if macro.repeat_delay != -1:
                    self.__repeat_macros.append(macro)
                    self._repeat_uinput(macro, uc, False)
                
    def _defeat_release(self, key_states):
        for k in key_states:
            k.defeat_release = True
            k.cancel_timer()
            
    def _consume_keys(self, key_states):
        """
        Mark as consumed so they don't get activated again if other key's are
        pressed or released while this macro is active
        
        Keyword arguments:
        key_states        -- list of KeyState objects to mark as consumed
        """
        for k in key_states:
            k.consumed = True         
            
    def _process_macro(self, macro, state, key_states): 
        if macro.type == g15profile.MACRO_ACTION:
            binding = g15actions.ActionBinding(macro.macro, macro.keys, state)
            if not self._action_performed(binding):
                # Send it to the service for handling
                self.__screen.service.handle_macro(macro)
            else:
                for k in key_states:
                    k.consume_until_released = True
        else:
            # Send it to the service for handling
            self.__screen.service.handle_macro(macro)
                
    def _handle_macro(self, macro, state, key_states, repetition = False):
        self._consume_keys(key_states)                
        delay = macro.repeat_delay if macro.repeat_delay != -1 else 0.1
        if macro.repeat_mode == g15profile.REPEAT_TOGGLE and not state == g15driver.KEY_STATE_HELD:
            if macro in self.__repeat_macros and not repetition:
                # Key pressed again, so stop repeating
                self.__cancel_macro_repeat_timer()
                self.__repeat_macros.remove(macro)
            else:
                if not macro in self.__repeat_macros and not repetition:
                    self.__repeat_macros.append(macro)
                else:
                    self._process_macro(macro, state, key_states)
                    
                # We test again because a toggle might have stopped the repeat
                if macro in self.__repeat_macros:
                    self.__macro_repeat_timer = g15util.queue(self.queue_name, "RepeatMacro", delay, self._handle_macro, macro, state, key_states, True)
        elif macro.repeat_mode == g15profile.REPEAT_WHILE_HELD:
            if state == g15driver.KEY_STATE_UP and macro in self.__repeat_macros and not repetition:
                # Key released again, so stop repeating
                self.__cancel_macro_repeat_timer()
                self.__repeat_macros.remove(macro)
            else:
                if state == g15driver.KEY_STATE_HELD and not macro in self.__repeat_macros and not repetition:
                    self.__repeat_macros.append(macro)
                self._process_macro(macro, state, key_states)
                    
                # We test again because a toggle might have stopped the repeat
                if macro in self.__repeat_macros:
                    self.__macro_repeat_timer = g15util.queue(self.queue_name, "RepeatMacro", delay, self._handle_macro, macro, g15driver.KEY_STATE_HELD, key_states, True)
        elif state == g15driver.KEY_STATE_UP and macro.activate_on == g15driver.KEY_STATE_UP:
            self._process_macro(macro, state, key_states)
        elif state == g15driver.KEY_STATE_HELD and macro.activate_on == g15driver.KEY_STATE_HELD:
            self._process_macro(macro, state, key_states)
            
            # Also defeat the key release so any normal KEY_STATE_UP macros don't get activated as well
            self._defeat_release(key_states)
                    
    def __cancel_macro_repeat_timer(self):
        """
        Cancel the currently pending macro repeat
        """
        if self.__macro_repeat_timer is not None:
            self.__macro_repeat_timer.cancel()
            self.__macro_repeat_timer = None
                    
    def _handle_key(self, keys, state_id, post=False):
        """
        Send the key press to various handlers. This is for plugins and other
        code that needs to completely take over the macro keys, for general
        key handling "Actions" should be used instead. 
        """
        
        # Event first goes to this objects key handlers
        for h in self.key_handlers:
            if h.handle_key(keys, state_id, post):
                return True
                
        return False
    
    def _action_performed(self, binding):
        logger.info("Invoking action '%s'" % binding.action)
        for l in self.action_listeners:  
            if l.action_performed(binding):
                return True