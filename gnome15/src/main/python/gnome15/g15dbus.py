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
 
import dbus.service
import g15globals as pglobals
import g15theme as g15theme
import g15util as g15util
import g15driver as g15driver
import time
import gc
import objgraph

from cStringIO import StringIO
from threading import Thread

BUS_NAME="org.gnome15.Gnome15"
NAME="/org/gnome15/Service"
DEBUG_NAME="/org/gnome15/Debug"
PAGE_NAME="/org/gnome15/Page"
DRIVER_NAME="/org/gnome15/Driver"
IF_NAME="org.gnome15.Service"
PAGE_IF_NAME="org.gnome15.Page"
DRIVER_IF_NAME="org.gnome15.Driver"
DEBUG_IF_NAME="org.gnome15.Debug"

# Logging
import logging
logger = logging.getLogger("dbus")

'''
Blinks keyboard backlight at configured rate
'''
class Blinker():
    def __init__(self, blink_delay, duration, levels, driver, control_values):
        self._driver = driver
        self._levels = levels
        self._cancelled = False
        self._control_values = control_values
        self._blink_delay = blink_delay
        self._duration = duration
        self._controls = []
        self._active = True
        self._toggles = 0
        self._timer = None
        for c in self._driver.get_controls():
            if c.hint & g15driver.HINT_DIMMABLE != 0:
                self._controls.append(c)
                
                
        if self._blink_delay == 0:
            self._on()
            if self._duration != 0:
                self._timer = g15util.schedule("resetKeyboardLights", self._duration, self._reset)
        else:
            self._toggles = int(self._duration / self._blink_delay)
            self._toggle()
            
    def _toggle(self):
        if self._active:
            self._off()
        else:
            self._on()
        self._toggles -= 1
        if not self._cancelled:
            if self._toggles > 0:
                self._timer = g15util.schedule("toggleLights", self._blink_delay, self._toggle)
            else: 
                self._reset()
    
    def cancel(self):
        self._cancelled = True
        if self._timer != None:
            self._timer.cancel()
        self._reset()
        
    def _off(self):
        for c in self._controls:
            if isinstance(c.value,int):
                c.value = c.lower
            else:
                c.value = (0, 0, 0)
            self._driver.update_control(c)
            
        self._active = False
        
    def _on(self):
        for c in self._controls:
            if self._cancelled:
                break
            
            if isinstance(c.value,int):
                if len(self._levels) > 0:
                    c.value = self._levels[0]
                else:
                    c.value = c.upper
            else:
                if len(self._levels) > 0:
                    c.value = (self._levels[0], self._levels[1], self._levels[2])
                else:
                    c.value = (255, 255, 255)
                    
            self._driver.update_control(c)
        
        self._active = True
            
    def _reset(self):                
        # Reset to original            
        i = 0
        for c in self._controls:
            c.value = self._control_values[i]
            self._driver.update_control(c)
            i += 1
    
class G15DBUSDebugService(dbus.service.Object):
    
    def __init__(self, dbus_service):
        dbus.service.Object.__init__(self, dbus_service._bus_name, DEBUG_NAME)
        self._service = dbus_service._service
        
    @dbus.service.method(DEBUG_IF_NAME)
    def GC(self):
        logger.info("Collecting garbage")
        gc.collect()
        logger.info("Collected garbage")
        
    @dbus.service.method(DEBUG_IF_NAME)
    def MostCommonTypes(self):
        objgraph.show_most_common_types(limit=200)
        
class G15DBUSDriverService(dbus.service.Object):
    
    def __init__(self, dbus_service):
        dbus.service.Object.__init__(self, dbus_service._bus_name, DRIVER_NAME)
        self._service = dbus_service._service
        self._effect = None
    
    @dbus.service.signal(DRIVER_IF_NAME, signature='s')
    def Disconnected(self, driver_name):
        pass
    
    @dbus.service.signal(DRIVER_IF_NAME, signature='s')
    def Connected(self, driver_name):
        pass
    
    @dbus.service.signal(DRIVER_IF_NAME)
    def AttentionRequested(self, signature='s'):
        pass
    
    @dbus.service.method(DRIVER_IF_NAME, in_signature='', out_signature='ssnnn')
    def GetInformation(self):
        driver = self._service.driver
        return ( driver.get_name(), driver.get_model_name(), driver.get_size()[0], driver.get_size()[1], driver.get_bpp() ) if driver != None else None 
    
    @dbus.service.method(DRIVER_IF_NAME, in_signature='', out_signature='as')
    def GetControlIds(self):
        c = []
        for control in self._service.driver.get_controls():
            c.append(control.id)
        return c
    
    @dbus.service.method(DRIVER_IF_NAME, in_signature='s', out_signature='s')
    def GetControlValue(self, id):
        control = self._service.driver.get_control(id)
        if isinstance(control.value, int):
            if control.hint & g15driver.HINT_SWITCH != 0:
                return "true" if control.value else "false"
            else:
                return str(control.value)
        else:
            return "%d,%d,%d" % control.value
    
    @dbus.service.method(DRIVER_IF_NAME, in_signature='s', out_signature='t')
    def GetControlHint(self, id):
        return self._service.driver.get_control(id).hint
    
    @dbus.service.method(DRIVER_IF_NAME, in_signature='ss', out_signature='')
    def SetControlValue(self, id, value):
        control = self._service.driver.get_control(id)
        if isinstance(control.value, int):
            if control.hint & g15driver.HINT_SWITCH != 0:
                control.value = 1 if value == "true" else 0
            else:
                control.value = int(value)
        else:
            sp = value.split(",")
            control.value = (int(sp[0]), int(sp[1]), int(sp[2]))
        self._service.driver.update_control(control)
    
    @dbus.service.method(DRIVER_IF_NAME, in_signature='', out_signature='b')
    def IsConnected(self):
        return self._service.driver.is_connected() if self._service.driver != None else False
    
    @dbus.service.method(DRIVER_IF_NAME, in_signature='n')
    def CycleKeyboard(self, value):
        self.CancelBlink()
        for c in self._get_dimmable_controls():
            if isinstance(c.value, int):
                self._service.cycle_level(value, c)
            else:
                self._service.cycle_color(value, c)
    
    @dbus.service.method(DRIVER_IF_NAME, in_signature='ddan')
    def BlinkKeyboard(self, blink_delay, duration, levels):
        self.CancelBlink()
        self._effect = Blinker(blink_delay, duration, levels, self._service.driver, self._get_dimmable_control_values())
        
    @dbus.service.method(DRIVER_IF_NAME)
    def CancelBlink(self):
        if self._effect != None:
            self._effect.cancel()
        
    def _get_dimmable_controls(self):
        controls = []
        for c in self._service.driver.get_controls():
            if c.hint & g15driver.HINT_DIMMABLE != 0:
                controls.append(c)
        return controls
        
    def _get_dimmable_control_values(self):
        values = []
        for c in self._get_dimmable_controls():
            values.append(c.value)
        return values
    
class AbstractG15DBUSService(dbus.service.Object):
    
    def __init__(self):
        self._reserved_keys = []
                    
    def handle_key(self, keys, state, post):
        if not post:
            p = []
            for k in keys:
                if k in self._reserved_keys:
                    p.append(k)
            if len(p) > 0:
                if state == g15driver.KEY_STATE_UP:
                    self.KeysReleased(p)
                elif state == g15driver.KEY_STATE_DOWN:
                    self.KeysPressed(p)
                return True

class G15DBUSPageService(AbstractG15DBUSService):
    
    def __init__(self, plugin, page, sequence_number):
        AbstractG15DBUSService.__init__(self)
        dbus.service.Object.__init__(self, plugin._bus_name, "%s%s" % ( PAGE_NAME , str( sequence_number ) ) ) 
        
        self._plugin = plugin
        self._sequence_number = sequence_number
        self._page = page
        self._timer = None
        
        self._page.key_handlers.append(self)
    
    @dbus.service.method(PAGE_IF_NAME, out_signature='n')
    def GetPriority(self):
        return self._page.priority
    
    @dbus.service.method(PAGE_IF_NAME, out_signature='u')
    def GetSequenceNumber(self):
        return self._sequence_number
    
    @dbus.service.method(PAGE_IF_NAME, out_signature='s')
    def GetTitle(self):
        return self._page.title
    
    @dbus.service.method(PAGE_IF_NAME, out_signature='s')
    def GetId(self):
        return self._page.id
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def Destroy(self):
        self._plugin._service.screen.del_page(self._page)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def Raise(self):
        self._plugin._service.screen.raise_page(self._page)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='', out_signature='')
    def CycleTo(self):
        self._plugin._service.screen.cycle_to(self._page)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def NewSurface(self):
        self._page.new_surface()
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def Save(self):
        self._page.save()
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def Restore(self):
        self._page.restore()
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def DrawSurface(self):
        self._page.draw_surface()
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='d')
    def SetLineWidth(self, line_width):
        self._page.set_line_width(line_width)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='dddd')
    def Line(self, x1, y1, x2, y2):
        self._page.line(x1, y1, x2, y2)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ddddb')
    def Rectangle(self, x, y, width, height, fill):
        self._page.rectangle(x, y, width, height, fill)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='dddb')
    def Circle(self, x, y, radius, fill):
        self._page.arc(x, y, radius, 0, 360, fill)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='dddddb')
    def Arc(self, x, y, radius, startAngle, endAngle, fill):
        self._page.arc(x, y, radius, startAngle, endAngle, fill)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='nnnn')
    def Foreground(self, r, g, b, a):
        self._page.foreground(r, g, b, a)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='dsss')
    def SetFont(self, font_size = 12.0, font_family = "Sans", font_style = "normal", font_weight = "normal"):
        self._page.set_font(font_size, font_family, font_style, font_weight)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='sdddds')
    def Text(self, text, x, y, width, height, text_align = "left"):
        self._page.text(text, x, y, width, height, text_align)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='sdddd')
    def Image(self, path, x, y, width, height):
        if not "/" in path:
            path = g15util.get_icon_path(path, width if width != 0 else 128)
            
        size = None if width == 0 or height == 0 else (width, height)
        
        img_surface = g15util.load_surface_from_file(path, size)
        self._page.image(img_surface, x, y)
        
    @dbus.service.method(PAGE_IF_NAME, in_signature='aydd')
    def ImageData(self, image_data, x, y):
        file_str = StringIO(str(image_data))
        img_surface = g15util.load_surface_from_file(file_str, None)
        file_str.close()
        self._page.image(img_surface, x, y)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def CancelTimer(self):
        self._timer.cancel()
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def Redraw(self):
        self._plugin._service.screen.redraw(self._page)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ss')
    def LoadTheme(self, dir, variant):
        self._page.theme = g15theme.G15Theme(dir, self._plugin._service.screen, variant)
        
    @dbus.service.method(PAGE_IF_NAME, in_signature='s')
    def SetThemeSVG(self, svg_text):
        self._page.theme = g15theme.G15Theme(None, self._plugin._service.screen, None, svg_text = svg_text)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ss')
    def SetThemeProperty(self, name, value):
        self._page.properties[name] = value
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='a{ss}')
    def SetThemeProperties(self, properties):
        self._page.properties = properties
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ndd')
    def SetPriority(self, priority, revert_after, delete_after):
        self._timer = self._service.screen.set_priority(self._page, priority, revert_after, delete_after)
                    
    @dbus.service.signal(PAGE_IF_NAME, signature='as')
    def KeysPressed(self, keys):
        pass 
                    
    @dbus.service.signal(PAGE_IF_NAME, signature='as')
    def KeysReleased(self, keys):
        pass
            
    @dbus.service.method(PAGE_IF_NAME, in_signature='s')
    def ReserveKey(self, key_name):
        if key_name in self._reserved_keys:
            raise Exception("Already reserved")
        self._reserved_keys.add(key_name)
            
    @dbus.service.method(PAGE_IF_NAME, in_signature='s')
    def UnreserveKey(self, key_name):
        if not key_name in self._reserved_keys:
            raise Exception("Not reserved")
        self._reserved_keys.remove(key_name)

class G15DBUSService(AbstractG15DBUSService):
    
    def __init__(self, service):        
        AbstractG15DBUSService.__init__(self)
        self._service = service
        logger.debug("Getting Session DBUS")
        self._bus = dbus.SessionBus()
        self._page_sequence_number = 1
        logger.debug("Exposing service")
        self._bus_name = dbus.service.BusName(BUS_NAME, bus=self._bus, replace_existing=False, allow_replacement=False, do_not_queue=True)
        dbus.service.Object.__init__(self, self._bus_name, NAME)
        self._service.screen.add_screen_change_listener(self)
        self._dbus_pages = {}
        self._driver_service = G15DBUSDriverService(self)
        self._debug_service = G15DBUSDebugService(self)
        self._service.service_listeners.append(self)
        self._service.screen.key_handlers.append(self)
        logger.debug("DBUS service ready")
        
    def stop(self):
        self._driver_service.remove_from_connection()        
        self._debug_service.remove_from_connection()
        self.remove_from_connection()
            
    '''
    service listener
    '''
    def shutting_down(self):
        logger.debug("Sending shutting down signal")
        self.ShuttingDown()
        
    def starting_up(self):
        logger.debug("Sending starting up signal")
        self.StartingUp()
        
    def started_up(self):
        logger.debug("Sending started up signal")
        self.StartedUp()
        
    def attention_cleared(self):
        logger.debug("Sending attention cleared signal")
        self.AttentionCleared()
            
    def attention_requested(self, message):
        logger.debug("Sending attention requested signal")
        self.AttentionRequested(message if message != None else "")
            
    def driver_connected(self, driver):
        logger.debug("Sending driver connected signal")
        self._driver_service.Connected(driver.get_name())
            
    def driver_disconnected(self, driver):
        logger.debug("Sending driver disconnected signal")
        self._driver_service.Disconnected(driver.get_name())
        
    '''
    screen change listener
    '''
    def page_changed(self, page):
        logger.debug("Sending page changed signal for %s" % page.id)
        dbus_page = self._dbus_pages[page.id]
        self.PageChanged(dbus_page._sequence_number)
        
    def new_page(self, page): 
        logger.debug("Sending new page signal for %s" % page.id)
        dbus_page = G15DBUSPageService(self, page, self._page_sequence_number)
        self._dbus_pages[page.id] = dbus_page
        self.PageCreated(self._page_sequence_number, page.title)
        self._page_sequence_number += 1
        
    def title_changed(self, page, title):
        logger.debug("Sending title changed signal for %s" % page.id)
        dbus_page = self._dbus_pages[page.id]
        self.PageTitleChanged(dbus_page._sequence_number, title)
    
    def del_page(self, page):
        logger.debug("Sending page deleted signal for %s" % page.id)
        if page.id in self._dbus_pages:
            dbus_page = self._dbus_pages[page.id]
            page.key_handlers.remove(dbus_page)
            self.PageDestroyed(dbus_page._sequence_number)
            del self._dbus_pages[page.id]
            dbus_page.remove_from_connection()
            
        else:
            logger.warning("DBUS Page %s was deleted, but it never existed. Huh?" % ( page.id ))
       
    '''
    DBUS Signals
    ''' 
    @dbus.service.signal(IF_NAME, signature='t')
    def PageChanged(self, page_sequence):
        pass 
    
    @dbus.service.signal(IF_NAME, signature='ts')
    def PageCreated(self, page_sequence, title):
        pass 
    
    @dbus.service.signal(IF_NAME, signature='ts')
    def PageTitleChanged(self, page_sequence, new_title):
        pass
    
    @dbus.service.signal(IF_NAME, signature='t')
    def PageDestroyed(self, page_sequence):
        pass
    
    @dbus.service.signal(IF_NAME)
    def AttentionRequested(self, signature='s'):
        pass
    
    @dbus.service.signal(IF_NAME)
    def AttentionCleared(self):
        pass  
    
    @dbus.service.signal(IF_NAME)
    def ShuttingDown(self):
        pass  
    
    @dbus.service.signal(IF_NAME)
    def StartingUp(self):
        pass 
    
    @dbus.service.signal(IF_NAME)
    def StartedUp(self):
        pass
                    
    @dbus.service.signal(IF_NAME, signature='as')
    def KeysPressed(self, keys):
        pass 
                    
    @dbus.service.signal(IF_NAME, signature='as')
    def KeysReleased(self, keys):
        pass
    
    '''
    DBUS methods
    ''' 
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ( pglobals.name, "Gnome15 Project", pglobals.version, "1.0" )
    
    
    
    @dbus.service.method(IF_NAME, in_signature='s', out_signature='u')
    def GetPageSequenceNumber(self, id):
        for page in self._dbus_pages.values():
            if page._page.id == id:
                return page._sequence_number
        return 0
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='u')
    def GetVisiblePageSequenceNumber(self):
        return self.GetPageSequenceNumber(self._service.screen.get_visible_page().id)
    
    @dbus.service.method(IF_NAME, in_signature='n', out_signature='au')
    def GetPageSequenceNumbers(self, priority):
        l = []
        for page in self._dbus_pages.values():
            if page._page.priority >= priority:
                l.append(page._sequence_number)
        return l
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='s')
    def GetLastError(self):
        return str(self._service.get_last_error())
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='')
    def Shutdown(self):
        self._service.shutdown()
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='')
    def ClearPopup(self):
        return self._service.screen.clear_popup()
    
    @dbus.service.method(IF_NAME, in_signature='n', out_signature='')
    def Cycle(self, cycle):
        return self._service.screen.cycle(cycle)
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsAttentionRequested(self):
        return self._service.attention
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsStartingUp(self):
        return self._service.starting_up
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsShuttingDown(self):
        return self._service.shutting_down
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='s')
    def GetMessage(self):
        return self._service.attention_message
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='')
    def ClearAttention(self):
        return self._service.clear_attention()
    
    @dbus.service.method(IF_NAME, in_signature='s', out_signature='')
    def RequestAttention(self, message):
        self._service.request_attention(message)
    
    @dbus.service.method(IF_NAME, in_signature='ssn', out_signature='t')
    def CreatePage(self, id, title, priority):
        page = self._service.screen.new_page(None, priority = priority, id = id, thumbnail_painter = None, panel_painter = None)
        page.set_title(title)
        return self.GetPageSequenceNumber(id)
            
    @dbus.service.method(IF_NAME, in_signature='s')
    def ReserveKey(self, key_name):
        if key_name in self._reserved_keys:
            raise Exception("Already reserved")
        self._reserved_keys.add(key_name)
            
    @dbus.service.method(IF_NAME, in_signature='s')
    def UnreserveKey(self, key_name):
        if not key_name in self._reserved_keys:
            raise Exception("Not reserved")
        self._reserved_keys.remove(key_name)
