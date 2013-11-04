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

"""
Default actions

TODO MOVE THESE TO G15ACTIONS
"""
NEXT_SELECTION = "next-sel"
PREVIOUS_SELECTION = "prev-sel"
NEXT_PAGE = "next-page"
PREVIOUS_PAGE = "prev-page"
SELECT = "select"
VIEW = "view"
CLEAR = "clear"
MENU = "menu"
MEMORY_1 = "memory-1"
MEMORY_2 = "memory-2"
MEMORY_3 = "memory-3"

"""
Bitmask values for setting the M key LED lights. See set_mkey_lights()
"""
MKEY_LIGHT_1 = 1<<0
MKEY_LIGHT_2 = 1<<1
MKEY_LIGHT_3 = 1<<2
MKEY_LIGHT_MR = 1<<3

"""
Constants for key codes
"""
KEY_STATE_UP = 0
KEY_STATE_DOWN = 1
KEY_STATE_HELD = 2

"""
G keys

G15v1 - G1-G18
G15v1 - G1-G18
G13 - G1-22
G19 - G1-G12
"""
G_KEY_G1  = "g1"
G_KEY_G2  = "g2"
G_KEY_G3  = "g3"
G_KEY_G4  = "g4"
G_KEY_G5  = "g5"
G_KEY_G6  = "g6"
G_KEY_G7  = "g7"
G_KEY_G8  = "g8"
G_KEY_G9  = "g9"
G_KEY_G10 = "g10"
G_KEY_G11 = "g11"
G_KEY_G12 = "g12"
G_KEY_G13 = "g13"
G_KEY_G14 = "g14"
G_KEY_G15 = "g15"
G_KEY_G16 = "g16"
G_KEY_G17 = "g17"
G_KEY_G18 = "g18"
G_KEY_G19 = "g19"
G_KEY_G20 = "g20"
G_KEY_G21 = "g21"
G_KEY_G22 = "g22"

"""
Joystick (G13)
""" 
G_KEY_JOY_LEFT = "jl"
G_KEY_JOY_DOWN = "jd"
G_KEY_JOY_CENTER = "jc"
G_KEY_JOY = "js"


"""
Display keys
"""
G_KEY_BACK = "back"
G_KEY_DOWN = "down"
G_KEY_LEFT = "left"
G_KEY_MENU = "menu"
G_KEY_OK = "ok"
G_KEY_RIGHT = "right"
G_KEY_SETTINGS = "settings"
G_KEY_UP = "up"

"""
M keys. On all models
"""
G_KEY_M1  = "m1"
G_KEY_M2  = "m2"
G_KEY_M3  = "m3"
G_KEY_MR  = "mr"

"""
L-Keys. On g15v1, v2, g13 and g19. NOT on g110 
"""
G_KEY_L1  = "l1"
G_KEY_L2  = "l2"
G_KEY_L3  = "l3"
G_KEY_L4  = "l4"
G_KEY_L5  = "l5"
 
"""
Light key. On all models
"""
G_KEY_LIGHT = "light"

"""
Multimedia keys
"""
G_KEY_WINKEY_SWITCH = "win"
G_KEY_NEXT = "next"
G_KEY_PREV = "prev"
G_KEY_STOP = "stop"
G_KEY_PLAY = "play"
G_KEY_MUTE = "mute"
G_KEY_VOL_UP = "vol-up"
G_KEY_VOL_DOWN = "vol-down"

"""
G110 only
"""
G_KEY_MIC_MUTE = "mic-mute"
G_KEY_HEADPHONES_MUTE = "headphones-mute"

"""
Models
"""
MODEL_G15_V1 = "g15v1"
MODEL_G15_V2 = "g15v2"
MODEL_G11 = "g11"
MODEL_G13 = "g13"
MODEL_G19 = "g19"
MODEL_G930 = "g930"
MODEL_G35 = "g35"
MODEL_G510 = "g510"
MODEL_G110 = "g110"
MODEL_Z10 = "z10"
MODEL_MX5500 = "mx5500"
MODEL_GAMEPANEL = "gamepanel"

MODELS = [ MODEL_G15_V1, MODEL_G15_V2, MODEL_G11, MODEL_G13, MODEL_G19, MODEL_G510, MODEL_G110, MODEL_Z10, MODEL_MX5500, MODEL_GAMEPANEL, MODEL_G930, MODEL_G35 ]

"""
Control hints
"""
HINT_DIMMABLE = 1 << 0
HINT_SHADEABLE = 1 << 1
HINT_FOREGROUND = 1 << 2
HINT_BACKGROUND = 1 << 3
HINT_HIGHLIGHT = 1 << 4
HINT_SWITCH = 1 << 5
HINT_MKEYS = 1 << 6
HINT_VIRTUAL = 1 << 7
HINT_RED_BLUE_LED = 1 << 8

# 16bit 565
CAIRO_IMAGE_FORMAT=4

FX_QUEUE = "ControlEffects"

import util.g15scheduler as g15scheduler
import time
import colorsys
from threading import Lock
from threading import Event
import logging
logger = logging.getLogger(__name__)

seq_no = 0

def get_key_names(keys):
    """
    Get the string name of the key given it's code
    """
    key_names = []
    for key in keys:
        key_names.append((key[:1].upper() + key[1:].lower()).replace('-',' '))
    return key_names

def zeroize(val):
    """
    Zeroise a control value (will be used for the fully off value). The type
    returned will be the same as the type provided
    
    Keyword arguments:
    val        --    current value
    """
    if isinstance(val, int):
        return 0
    elif isinstance(val, tuple):
        return (0, 0, 0)
    else:
        return False

def get_mask_for_memory_bank(bank):
    """
    Get the M_KEY_LIGHT_* mask given the memory bank number (1,2 or 3)
    
    Keyword arguments:
    bank        --    memory bank
    """
    if bank == 1:
        return MKEY_LIGHT_1
    elif bank == 2:
        return MKEY_LIGHT_2
    elif bank == 3:
        return MKEY_LIGHT_3

def get_memory_bank_for_mask(val):
    """
    Get the memory bank that is activated given the M_KEY_LIGHT_* mask
    
    Keyword arguments:
    val        --    light key mask value
    """
    if val & MKEY_LIGHT_3 != 0:
        return 3
    elif val & MKEY_LIGHT_2 != 0:
        return 2
    elif val & MKEY_LIGHT_1 != 0:
        return 1
    return 0

class Control():
    """
    Represents a single "Control". Each control represents a feature of the
    device that may be adjusted. For example, the red, green and blue LEDs of
    the keyboard backlight on a G19.
    
    A control's value will be of different classes depending on the type of 
    control this instance represents.
    
    A On/Off or single value controls (such as brightness of a single LED is
    represented as as int).
    
    A colour control is a tuple consisting of R,G and B intensity values.
    
    Other controls are boolean (currently not used)    
    """
    
    def __init__(self, id, name, value = 0.0, lower = 0.0, upper = 255.0, hint = 0):
        """
        Constructor
        
        Keyword arguments:
        id            --    unique control ID
        name          --    an english name for the control
        value         --    the initial value (int,tuple or bool)
        lower         --    minimum value the control may be
        upper         --    maximum value the control may be
        hint          --    bitmask of HINT_ consants describing the control
        """
        self.id = id
        self.hint = hint
        self.name = name
        self.lower = lower
        self.upper = upper
        self.value = value
        self.default_value = value
        
    def set_from_configuration(self, device, conf_client):
        """
        Configure this control's value from it's gconf entry for the provided device 
        
        Keyword arguments:
        device         device the control is associated with
        conf_client    configuration client instance
        """
        entry = conf_client.get("/apps/gnome15/%s/%s" % ( device.uid, self.id ))
        if entry != None:
            if isinstance(self.default_value, int):
                self.value = entry.get_int()
            elif isinstance(self.default_value, tuple):
                rgb = entry.get_string().split(",")
                self.value = (int(rgb[0]),int(rgb[1]),int(rgb[2]))
            else:
                self.value = entry.get_bool()
        else:
            # Use the default value
            self.value = self.default_value
        
    def zeroize(self):
        """
        Set the control to it's OFF value e.g no power to any LED (R, G or B) 
        for an RGB control
        """
        self.value = zeroize(self.default_value)
        
class AbstractControlAcquisition(object):
    
    def __init__(self, driver):
        self.driver = driver
        self.val = None
        self.on_released = None
        self.reset_timer = None
        self.fade_timer = None
        self.on = False
        self._released = False
        self._waiting = False
        self._condition = Event()
        
    def wait(self):
        if self._waiting:
            raise Exception("Already waiting")
        self._waiting = True
        self._condition.wait()   
        self._waiting = False
        
    def fade(self, percentage = 100.0, duration = 1.0, release = False, step = 1):
        target_val = self.get_target_value(self.val, percentage)
        if self.val != target_val:
            self.fade_cancelled = False
            self._reduce( ( duration / float( self.val - target_val ) ) * step, target_val, release, step)
        elif release:
            self.driver.release_control(self)
        
    def get_target_value(self, val, percentage):
        return val - int ( ( float(val) / 100.0 ) * percentage )
        
        
    def blink(self, off_val = 0, delay = 0.5, duration = None, blink_started = None):
        if blink_started == None:
            blink_started = time.time()
        self.cancel_fade()
        self.cancel_reset()
        if self.on:
            self.adjust(self.val)
        else:
            self.adjust(off_val if isinstance(off_val, int) or isinstance(off_val, tuple) else off_val())
        self.on = not self.on
        if duration == None or time.time() < blink_started + duration:
            self.reset_timer = g15scheduler.queue(FX_QUEUE, "Blink", delay, self.blink, off_val, delay, duration, blink_started)
        return self.reset_timer
    
    def is_active(self):
        raise Exception("Not implemented")
    
    def adjust(self, val):
        raise Exception("Not implemented")
        
    def set_value(self, val, reset_after = None):
        old_val = val
        if self.val is None or val != self.val or reset_after is not None:
            if self.val is None:
                logger.debug("Initial value of control is %s", str(val))
                self.reset_val = val
            
            self.val = val
            self.on = True
            self.cancel_fade()
            self.adjust(val)
            self.cancel_reset()
            
            logger.debug("Set value of control to %s", str(val))
                    
            if reset_after:
                self.reset_val = old_val
                self.reset_timer = g15scheduler.queue(FX_QUEUE, "LEDReset", reset_after, self.reset)
                return self.reset_timer
            
    def reset(self):
        self.set_value(self.reset_val)
            
    def cancel_reset(self):
        if self.reset_timer:            
            self.reset_timer.cancel()
            self.reset_timer = None
        
    def get_value(self):
        return self.val
    
    def cancel_fade(self):
        if self.fade_timer is not None:
            self.fade_cancelled = True
    
    def _cleanup(self):
        self.cancel_reset()
        self.cancel_fade()
    
    """
    Private
    """
    def _reduce(self, interval, target_val, release, step):
        if not self.fade_cancelled:
            if self.val > target_val:
                self.set_value(self.val - step)
            if self.val == target_val:
                if release:
                    self.driver.release_control(self)
            else:                
                self.fade_timer = g15scheduler.queue(FX_QUEUE, "Fade", interval, self._reduce, interval, target_val, release, step)
                
    def _notify_released(self):
        if self._released:
            raise Exception("Already released")  
        if self.on_released:
            self.on_released()
        self._released = True        
        self._condition.set()
    
class ControlAcquisition(AbstractControlAcquisition):
    
    def __init__(self, driver, control):
        self.control = control
        AbstractControlAcquisition.__init__(self, driver)
        
    def is_active(self):
        if self.control.id in self.driver.acquired_controls:
            ctrls = self.driver.acquired_controls[self.control.id]
            return len(ctrls) > 0 and self in ctrls and ctrls.index(self) == len(ctrls) - 1
    
    def blink(self, off_val = None, delay = 0.5, duration = None, blink_started = None):
        AbstractControlAcquisition.blink(self, ( (0,0,0) if isinstance(self.control.value, tuple) else 0 ) if off_val is None else off_val , delay, duration, blink_started)
            
    def release(self):
        self.driver.release_control(self)
        
    def adjust(self, val):
        if self.is_active():
            self.control.value = val
            self.driver.update_control(self.control)
        
    def fade(self, percentage = 100.0, duration = 1.0, release = False, step = 1):
        if isinstance(self.val, int):
            AbstractControlAcquisition.fade(self, percentage, duration, release)
        else:
            self.fade_cancelled = False
            target_val = self.get_target_value(self.val, percentage)
            h, s, v = self.rgb_to_hsv(self.val)
            t_h, t_s, t_v = self.rgb_to_hsv(target_val)
            diff = float( v - t_v )
            if diff > 0:
                self._reduce( ( duration / diff ) * step, target_val, release, step)
            elif release:
                self.driver.release_control(self)
        
    def get_target_value(self, val, percentage):
        if isinstance(self.val, int):
            return AbstractControlAcquisition.get_target_value(self, val, percentage)
        else:
            h, s, v = self.rgb_to_hsv(val)
            return self.hsv_to_rgb(( h, s, AbstractControlAcquisition.get_target_value(self, v, percentage) ))
            
    def rgb_to_hsv(self, val):        
        r, g, b = val
        h, s, v = colorsys.rgb_to_hsv(float(r) / 255.0, float(g) / 255.0, float(b) / 255.0)
        return ( int(h * 255.0), int(s * 255.0), int(v * 255.0 ))
            
    def hsv_to_rgb(self, val):        
        h, s, v = val
        r, g, b = colorsys.hsv_to_rgb(float(h) / 255.0, float(s) / 255.0, float(v) / 255.0)
        return ( int(r * 255.0), int(g * 255.0), int(b * 255.0 ))
    
    """
    Private
    """
    def _reduce(self, interval, target_val, release, step):
        if not self.fade_cancelled:
            if isinstance(self.val, int):
                AbstractControlAcquisition._reduce(self, interval, target_val, release, step)
            else:
                if self.val > target_val:
                    h, s, v = self.rgb_to_hsv(self.val)
                    v = max(0, v - step)
                    new_rgb = self.hsv_to_rgb((h, s, v))
                    if new_rgb == self.val:
                        new_rgb = target_val
                    self.set_value(new_rgb)
                if self.val <= target_val:
                    if release and not self._released:
                        self.driver.release_control(self)
                else:
                    g15scheduler.queue(FX_QUEUE, "Fade", interval, self._reduce, interval, target_val, release, step)
        
class AbstractDriver(object):
    
    def __init__(self, id):
        self.id = id
        global seq_no
        self.on_driver_options_change = None
        seq_no += 1
        self.seq = seq_no
        self.disconnecting = False
        self.connecting = False
        self.all_off_on_disconnect = True
        self.allow_multiple = True
        self._reset_state()
        
    def has_memory_bank(self):
        for l in self.get_key_layout():
            if G_KEY_M1 in l or G_KEY_M2 in l or G_KEY_M3 in l:
                return True
        return False
        
    def release_all_acquisitions(self):
        self.acquired_controls = {}
        values = dict(self.initial_acquired_control_values)
        for k in values:
            c = self.get_control(k)
            if c:
                if k in self.acquired_controls:
                    self.acquired_controls[k]._cleanup()
                c.value = values[k]
                self.update_control(c)
                    
    def zeroize_all_controls(self):
        for c in self.get_controls():
            c.zeroize()
        
    def acquire_control(self, control, release_after = None, val = None, on_release = None):
        control_acquisitions = self.acquired_controls[control.id] if control.id in self.acquired_controls else []
        self.acquired_controls[control.id] = control_acquisitions
        if len(control_acquisitions) == 0:
            self.initial_acquired_control_values[control.id] = control.value
            
        control_acquisition = ControlAcquisition(self, control)
        control_acquisition.on_release = on_release
        control_acquisitions.append(control_acquisition)
        
        # Only set the value when active (i.e. in the control_acquisitions list)
        control_acquisition.set_value(val if val is not None else control.value)
        
        if release_after:
            g15scheduler.queue(FX_QUEUE, "ReleaseControl", release_after, self._release_control, control_acquisition)
        return control_acquisition
        
    def acquire_control_with_hint(self, hint, release_after = None, val = None):
        control = self.get_control_for_hint(hint)
        if control:
            return self.acquire_control(control, release_after, val)
    
    def release_control(self, control_acquisition):
        logger.info("Releasing %s", control_acquisition.control.id)
        if control_acquisition.control.id in self.acquired_controls:
            control_acquisitions = self.acquired_controls[control_acquisition.control.id]
            control_acquisition._notify_released()
            control_acquisition.cancel_reset()
            control_acquisition.cancel_fade()
            control_acquisitions.remove(control_acquisition)
            ctrls = len(control_acquisitions)
            if ctrls > 0:
                control_acquisition.control.value = control_acquisitions[ctrls - 1].val
                self.update_control(control_acquisition.control)
            else:
                control_acquisition.control.value = self.initial_acquired_control_values[control_acquisition.control.id]
                self.update_control(control_acquisition.control)
    
    def release_mkey_lights(self, control_acquisition):
        logger.warning("DEPRECATED call to release_mkey_lights, use release_control")
        self.release_control(control_acquisition)
            
    def disconnect(self):
        """
        Disconnect the driver. Callers should use this, and s
        subclasses should override on_disconnect.
        """
        try:
            self.disconnecting = True
            logger.info("Disconnecting driver")
            if self.all_off_on_disconnect:
                for c in self.initial_acquired_control_values:
                    self.initial_acquired_control_values[c] = zeroize(self.initial_acquired_control_values[c])
            self.release_all_acquisitions()
            if self.all_off_on_disconnect:
                for c in self.get_controls():
                    if isinstance(c.value, int):
                        c.value = 0
                    elif isinstance(c.value, tuple):
                        c.value = (0, 0, 0)
                    self.update_control(c)
            self._on_disconnect()
        finally:
            self.disconnecting = False
            self._reset_state()
    
    def _on_disconnect(self):
        """
        For subclasses to implemented disconnection logic
        """
        raise NotImplementedError( "Not implemented" )
    
    def connect(self):
        """
        Start the driver
        """
        if self.is_connected():
            raise Exception("Already connected")
        logger.info("Connecting driver %s", self.get_name())
        self.connecting = True
        try:
            self._on_connect()
        finally:
            self.connecting = False
            
    def _on_connect(self):
        raise NotImplementedError( "Not implemented" )
    
    def is_connected(self):
        """
        Get if driver is connected
        """
        raise NotImplementedError( "Not implemented" )
        
    def reconnect(self):
        """
        Disconnected (if connected), then reconnect
        """
        if self.is_connected():
            self.disconnect()
        self.connect()
    

    def get_name(self):
        """
        Get the name of the driver
        """
        raise NotImplementedError( "Not implemented" )
    
    
    def get_model_names(self):
        """
        Get a list of the model names this driver supports
        """
        raise NotImplementedError( "Not implemented" )
    
    
    def get_model_name(self):
        """
        Get the model name that this driver is connected to
        """
        raise NotImplementedError( "Not implemented" )
        
    
    def get_size(self):
        """
        Get the size of the screen. Returns a tuple of (width, height)
        """
        raise NotImplementedError( "Not implemented" )
    
    def get_key_layout(self):
        """
        Get the grid the extra keys available on this keyboard. This is currently only a hint for the Gtk driver
        """
        raise NotImplementedError( "Not implemented" )
    

    def get_bpp(self):
        """
        Get the bits per pixel. 1 would be monochrome
        """
        raise NotImplementedError( "Not implemented")
    
    
    def get_controls(self):
        """
        Get the all of the controls available. This would include things such as LCD contrast, LCD brightness,
        keyboard colour, keyboard backlight etc
        """
        raise NotImplementedError( "Not implemented")
    
    
    def paint(self, image):
        """
        Repaint the screen. 
        """
        raise NotImplementedError( "Not implemented" )
    
    
    def update_control(self, control):
        """
        Synchronize a control with the keyboard. For example, if the control was for the
        keyboard colour, the keyboard colour would actually change when this function
        is invoked
        
        Subclasses should not override this function, instead they should implement
        on_update_control()
        
        Keyword arguments:
        control        -- control to update
        """
        if self.check_control(control):
            for l in self.control_update_listeners:
                l.control_updated(control)
            self.on_update_control(control)

    def check_control(self, control):
        if isinstance(control.value, int):
            if control.value > control.upper:
                control.value = control.upper
            elif control.value < control.lower:
                control.value = control.lower
        return True
    
    def on_update_control(self, control):
        raise NotImplementedError( "Not implemented" )
                
        
        
    def grab_keyboard(self, callback):
        """
        Start receiving events when the additional keys (G keys, L keys and M keys)
        are pressed and released. The provided callback will be invoked with two
        arguments, the first being the key code (see the constants G_KEY_xx)
        and the second being the key state (KEY_STATE_DOWN or KEY_STATE_UP).
        
        Keyword arguments:
        callback    --    invoked when keys are pressed
        """
        raise NotImplementedError( "Not implemented" )
    
    
    def process_svg(self, document):
        """
        Give the driver a chance to alter a theme's SVG. This has been introduced to work
        around a problem of Inkscape (the recommended 'IDE' for designing themes),
        does not saving bitmap font names
        """
        raise NotImplementedError( "Not implemented" )
    
    def get_mkey_lights(self):
        return self.lights 
        
    def get_control(self, control_id):
        controls = self.get_controls()
        if controls:
            for control in self.get_controls():
                if control_id == control.id:
                    return control
            
    def get_control_for_hint(self, hint):
        controls = self.get_controls()
        if controls:
            for control in self.get_controls():
                if ( hint & control.hint ) == hint:
                    return control
                
    def update_controls(self):
        for control in self.get_controls():
            if control.hint & HINT_VIRTUAL == 0:
                self.update_control(control)
    
    def get_color_as_ratios(self, hint, default):
        fg_control = self.get_control_for_hint(hint)
        fg_rgb = default
        if fg_control != None:
            fg_rgb = fg_control.value
        return ( float(fg_rgb[0]) / 255.0,float(fg_rgb[1]) / 255.0,float(fg_rgb[2]) / 255.0 )
    
    def get_color_as_hexrgb(self, hint, default):
        fg_control = self.get_control_for_hint(hint)
        fg_rgb = default
        if fg_control != None:
            fg_rgb = fg_control.value
        return rgb_to_hex(fg_rgb)
    
    def get_color(self, hint, default):
        fg_control = self.get_control_for_hint(hint)
        fg_rgb = default
        if fg_control != None:
            fg_rgb = fg_control.value
        return fg_rgb
    
    """
    Private
    """
    
    def _release_control(self, control_acquisition):
        if control_acquisition.is_active():
            self.release_control(control_acquisition)
    
    def _reset_state(self):
        self.lights = 0
        self.control_update_listeners = []
        self.acquired_controls = {}
        self.initial_acquired_control_values = {}

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb
