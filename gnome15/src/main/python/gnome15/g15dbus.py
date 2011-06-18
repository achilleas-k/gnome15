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
import g15globals
import g15theme
import g15util
import g15driver
import g15devices
import gc
import objgraph
import gobject

from cStringIO import StringIO

BUS_NAME="org.gnome15.Gnome15"
NAME="/org/gnome15/Service"
DEBUG_NAME="/org/gnome15/Debug"
PAGE_NAME="/org/gnome15/Page"
SCREEN_NAME="/org/gnome15/Screen"
DEVICE_NAME="/org/gnome15/Device"
IF_NAME="org.gnome15.Service"
PAGE_IF_NAME="org.gnome15.Page"
SCREEN_IF_NAME="org.gnome15.Screen"
DEBUG_IF_NAME="org.gnome15.Debug"
DEVICE_IF_NAME="org.gnome15.Device"

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
    
class AbstractG15DBUSService(dbus.service.Object):
    
    def __init__(self, conn=None, object_path=None, bus_name=None):
        dbus.service.Object.__init__(self, conn, object_path, bus_name)
        self._reserved_keys = []
                    
    def handle_key(self, keys, state, post):
        if not post:
            p = []
            for k in keys:
                if k in self._reserved_keys:
                    p.append(k)
            if len(p) > 0:
                if state == g15driver.KEY_STATE_UP:
                    gobject.idle_add(self.KeysReleased,p)
                elif state == g15driver.KEY_STATE_DOWN:
                    gobject.idle_add(self.KeysPressed, p)
                return True
    
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
        
    @dbus.service.method(DEBUG_IF_NAME)
    def ShowGraph(self):
        objgraph.show_refs(self._service)
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def Referrers(self, typename):
        print "%d instances of type %s. Referrers :-" % ( objgraph.count(typename), typename)
        done = {}
        for r in objgraph.by_type(typename):
            for o in gc.get_referrers(r):
                name = type(o).__name__
                if name != "type" and name != typename and name != "frame" and not name in done:
                    done[name] = True
                    count = objgraph.count(name)
                    if count > 1:
                        print "   %s  (%d)" % ( name, count )
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def Refererents(self, typename):
        print "%d instances of  type %s. Referents :-" % ( objgraph.count(typename), typename)
        done = {}
        for r in objgraph.by_type(typename):
            for o in gc.get_referents(r):
                name = type(o).__name__
                if name != "type" and name != typename and not name in done:
                    done[name] = True
                    count = objgraph.count(name)
                    if count > 1:
                        print "   %s  (%d)" % ( name, count )
        
class G15DBUSDeviceService(AbstractG15DBUSService):
    
    def __init__(self, dbus_service, device):
        AbstractG15DBUSService.__init__(self, dbus_service._bus_name, "%s/%s" % ( DEVICE_NAME, device.uid ) )
        self._dbus_service = dbus_service
        self._service = dbus_service._service
        self._effect = None
        self._device = device
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='s')
    def GetScreen(self):
        for screen_path in self._dbus_service._dbus_screens:
            screen = self._dbus_service._dbus_screens[screen_path]
            if screen._screen.device.uid == self._device.uid:
                return "%s/%s" % ( SCREEN_NAME, self._device.uid)
        return ""
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='')
    def Disable(self):
        g15devices.set_enabled(self._service.conf_client, self._device, False)
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='')
    def Enable(self):
        g15devices.set_enabled(self._service.conf_client, self._device, True)
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='s')
    def GetModelFullName(self):
        return self._device.model_fullname
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='s')
    def GetUID(self):
        return self._device.uid
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='s')
    def GetUsbID(self):
        return "%s:%s" % ( hex(self._device.usb_id[0]), hex(self._device.usb_id[1]) )
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='u')
    def GetBPP(self):
        return self._device.bpp
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='uu')
    def GetSize(self):
        return self._device.size
        
class G15DBUSScreenService(AbstractG15DBUSService):
    
    def __init__(self, dbus_service, screen):
        AbstractG15DBUSService.__init__(self, dbus_service._bus_name, "%s/%s" % ( SCREEN_NAME, screen.device.uid ) )
        self._dbus_service = dbus_service
        self._service = dbus_service._service
        self._effect = None
        self._screen = screen
        self._screen.add_screen_change_listener(self)
        self._screen.key_handlers.append(self)
        self._dbus_pages = {}
        
    '''
    screen change listener
    '''
        
    def memory_bank_changed(self, new_memory_bank):
        logger.debug("Sending memory bank changed signel (%d)" % new_memory_bank)
        gobject.idle_add(self.MemoryBankChanged, self._get_screen_path(), new_memory_bank)
        
    def attention_cleared(self):
        logger.debug("Sending attention cleared signal")
        gobject.idle_add(self.AttentionCleared,self._get_screen_path())
        logger.debug("Sent attention cleared signal")
            
    def attention_requested(self, message):
        logger.debug("Sending attention requested signal")
        gobject.idle_add(self.AttentionRequested, self._get_screen_path(), message if message != None else "")
        logger.debug("Sent attention requested signal")
            
    def driver_connected(self, driver):
        logger.debug("Sending driver connected signal")
        gobject.idle_add(self.Connected, self._get_screen_path(), driver.get_name())
        logger.debug("Sent driver connected signal")
            
    def driver_disconnected(self, driver):
        logger.debug("Sending driver disconnected signal")
        gobject.idle_add(self.Disconnected, self._get_screen_path(), driver.get_name())
        logger.debug("Sent driver disconnected signal")
        
    def page_changed(self, page):
        logger.debug("Sending page changed signal for %s" % page.id)
        dbus_page = self._dbus_pages[page.id]
        self.PageChanged(self._get_screen_path(), dbus_page._sequence_number)
        logger.debug("Sent page changed signal for %s" % page.id)
        
    def new_page(self, page): 
        logger.debug("Sending new page signal for %s" % page.id)
        if page.id in self._dbus_pages:
            raise Exception("Page %s already in DBUS service." % page.id)
        dbus_page = G15DBUSPageService(self, page, self._dbus_service._page_sequence_number)
        self._dbus_pages[page.id] = dbus_page
        gobject.idle_add(self.PageCreated, self._get_screen_path(), self._dbus_service._page_sequence_number, page.title)
        self._dbus_service._page_sequence_number += 1
        logger.debug("Sent new page signal for %s" % page.id)
        
    def title_changed(self, page, title):
        logger.debug("Sending title changed signal for %s" % page.id)
        dbus_page = self._dbus_pages[page.id]
        gobject.idle_add(self.PageTitleChanged, self._get_screen_path(), dbus_page._sequence_number, title)
        logger.debug("Sent title changed signal for %s" % page.id)
    
    def deleting_page(self, page):
        logger.debug("Sending page deleted signal for %s" % page.id)
        if page.id in self._dbus_pages:
            dbus_page = self._dbus_pages[page.id]
            if dbus_page in page.key_handlers: 
                page.key_handlers.remove(dbus_page)
            gobject.idle_add(self.PageDeleting, self._get_screen_path(), dbus_page._sequence_number, )
        else:
            logger.warning("DBUS Page %s is deleting, but it never existed. Huh? %s" % ( page.id, str(self._dbus_pages) ))
        logger.debug("Sent page deleting signal for %s" % page.id)
            
    def deleted_page(self, page):
        logger.debug("Sending page deleted signal for %s" % page.id)
        if page.id in self._dbus_pages:
            dbus_page = self._dbus_pages[page.id]
            gobject.idle_add(self.PageDeleted, self._get_screen_path(), dbus_page._sequence_number)
            dbus_page.remove_from_connection()
            del self._dbus_pages[page.id]
        else:
            logger.warning("DBUS Page %s was deleted, but it never existed. Huh? %s" % ( page.id, str(self._dbus_pages) ))
        logger.debug("Sent page deleted signal for %s" % page.id)
            
    """
    DBUS Functions
    """
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='s')
    def GetMessage(self):
        return self._screen.attention_message
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='')
    def ClearAttention(self):
        return self._screen.clear_attention()
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='s', out_signature='')
    def RequestAttention(self, message):
        self._screen.request_attention(message)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='ssn', out_signature='t')
    def CreatePage(self, id, title, priority):
        page = self._screen.new_page(None, priority = priority, id = id, thumbnail_painter = None, panel_painter = None)
        page.set_title(title)
        return self.GetPageSequenceNumber(id)
            
    @dbus.service.method(SCREEN_IF_NAME, in_signature='s')
    def ReserveKey(self, key_name):
        if key_name in self._reserved_keys:
            raise Exception("Already reserved")
        self._reserved_keys.add(key_name)
            
    @dbus.service.method(SCREEN_IF_NAME, in_signature='s')
    def UnreserveKey(self, key_name):
        if not key_name in self._reserved_keys:
            raise Exception("Not reserved")
        self._reserved_keys.remove(key_name)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='ssss')
    def GetDeviceInformation(self):
        device = self._screen.device
        return ( device.uid, device.model_id, "%s:%s" % ( hex(device.usb_id[0]),hex(device.usb_id[1]) ), device.model_fullname )
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='ssnnn')
    def GetDriverInformation(self):
        driver = self._screen.driver
        return ( driver.get_name(), driver.get_model_name(), driver.get_size()[0], driver.get_size()[1], driver.get_bpp() ) if driver != None else None 
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='s')
    def GetDeviceUID(self):
        return self._screen.device.uid
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='as')
    def GetControlIds(self):
        c = []
        for control in self._screen.driver.get_controls():
            c.append(control.id)
        return c
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='s', out_signature='s')
    def GetControlValue(self, id):
        control = self._screen.driver.get_control(id)
        if isinstance(control.value, int):
            if control.hint & g15driver.HINT_SWITCH != 0:
                return "true" if control.value else "false"
            else:
                return str(control.value)
        else:
            return "%d,%d,%d" % control.value
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='s', out_signature='t')
    def GetControlHint(self, id):
        return self._screen.driver.get_control(id).hint
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='ss', out_signature='')
    def SetControlValue(self, id, value):
        control = self._screen.driver.get_control(id)
        if isinstance(control.value, int):
            if control.hint & g15driver.HINT_SWITCH != 0:
                control.value = 1 if value == "true" else 0
            else:
                control.value = int(value)
        else:
            sp = value.split(",")
            control.value = (int(sp[0]), int(sp[1]), int(sp[2]))
        self._screen.driver.update_control(control)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='b')
    def IsConnected(self):
        return self._screen.driver.is_connected() if self._screen.driver != None else False
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='n')
    def CycleKeyboard(self, value):
        self.CancelBlink()
        for c in self._get_dimmable_controls():
            if isinstance(c.value, int):
                self._screen.cycle_level(value, c)
            else:
                self._screen.cycle_color(value, c)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='ddan')
    def BlinkKeyboard(self, blink_delay, duration, levels):
        self.CancelBlink()
        self._effect = Blinker(blink_delay, duration, levels, self._screen.driver, self._get_dimmable_control_values())
        
    @dbus.service.method(SCREEN_IF_NAME)
    def CancelBlink(self):
        if self._effect != None:
            self._effect.cancel()
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='s', out_signature='u')
    def GetPageSequenceNumber(self, id):
        for page in self._dbus_pages.values():
            if page._page.id == id:
                return page._sequence_number
        return 0
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='u')
    def GetVisiblePageSequenceNumber(self):
        return self.GetPageSequenceNumber(self._screen.get_visible_page().id)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='n', out_signature='au')
    def GetPageSequenceNumbers(self, priority):
        l = []
        for page in self._dbus_pages.values():
            if page._page.priority >= priority:
                l.append(page._sequence_number)
        return l
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='s')
    def GetLastError(self):
        return str(self._screen.get_last_error())
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='')
    def ClearPopup(self):
        return self._screen.clear_popup()
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='n', out_signature='')
    def Cycle(self, cycle):
        return self._screen.cycle(cycle)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='b')
    def IsAttentionRequested(self):
        return self._screen.attention
    
    """
    DBUS Signals
    """
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='ss')
    def Disconnected(self, screen_path, driver_name):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='ss')
    def Connected(self, screen_path, driver_name):
        pass
            
    @dbus.service.signal(SCREEN_IF_NAME, signature='su')
    def MemoryBankChanged(self, screen_path, new_memory_bank):
        pass 
            
    @dbus.service.signal(SCREEN_IF_NAME, signature='st')
    def PageChanged(self, screen_path, page_sequence):
        pass 
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='sts')
    def PageCreated(self, screen_path, page_sequence, title):
        pass 
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='sts')
    def PageTitleChanged(self, screen_path, page_sequence, new_title):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='st')
    def PageDeleted(self, screen_path, page_sequence):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='st')
    def PageDeleting(self, screen_path, page_sequence):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='ss')
    def AttentionRequested(self, screen_path, message):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def AttentionCleared(self, screen_path):
        pass  
                    
    @dbus.service.signal(SCREEN_IF_NAME, signature='sas')
    def KeysPressed(self, screen_path, keys):
        pass 
                    
    @dbus.service.signal(SCREEN_IF_NAME, signature='sas')
    def KeysReleased(self, screen_path, keys):
        pass
    
    """
    Private
    """
    
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
    
    def _get_screen_path(self):
        return "%s/%s" % ( SCREEN_NAME, self._screen.device.uid )

class G15DBUSPageService(AbstractG15DBUSService):
    
    def __init__(self, screen_service, page, sequence_number):
        AbstractG15DBUSService.__init__(self, screen_service._dbus_service._bus_name, "%s%s" % ( PAGE_NAME , str( sequence_number ) ) )
        
        self._screen_service = screen_service
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
    def Delete(self):
        self._screen_service._screen.del_page(self._page)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def Raise(self):
        self._screen_service._screen.raise_page(self._page)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='', out_signature='')
    def CycleTo(self):
        self._screen_service._screen.cycle_to(self._page)
    
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
        self._screen_service._screen.redraw(self._page)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ss')
    def LoadTheme(self, dir, variant):
        self._page.add_theme(g15theme.G15Theme(dir, self._screen_service._screen, variant))
        
    @dbus.service.method(PAGE_IF_NAME, in_signature='s')
    def SetThemeSVG(self, svg_text):
        self._page.add_theme(g15theme.G15Theme(None, self._screen_service._screen, None, svg_text = svg_text))
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ss')
    def SetThemeProperty(self, name, value):
        self._page.properties[name] = value
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='a{ss}')
    def SetThemeProperties(self, properties):
        self._page.properties = properties
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ndd')
    def SetPriority(self, priority, revert_after, delete_after):
        self._timer = self._screen_service._screen.set_priority(self._page, priority, revert_after, delete_after)
                    
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
        self._debug_service = G15DBUSDebugService(self)
        self._service.service_listeners.append(self)
        logger.debug("DBUS service ready")
        self._dbus_screens = {}
        self._dbus_devices = []
        for device in g15devices.find_all_devices():
            dbus_device = G15DBUSDeviceService(self, device)
            self._dbus_devices.append(dbus_device)
        
    def stop(self):   
        for dbus_device in self._dbus_devices:
            self._silently_remove_from_connector(dbus_device)
        for screen in self._dbus_screens:
            self._silently_remove_from_connector(self._dbus_screens[screen])               
        self._silently_remove_from_connector(self._debug_service)               
        self._silently_remove_from_connector(self)
        
    def _silently_remove_from_connector(self, object):
        try:
            object.remove_from_connection()
        except Exception:
            pass
            
    '''
    service listener
    '''
    def screen_added(self, screen):
        logger.debug("Screen added for %s" % screen.device.model_id)        
        screen_service = G15DBUSScreenService(self, screen)
        self._dbus_screens[screen.device.uid] = screen_service
        gobject.idle_add(self.ScreenAdded, "%s/%s" % ( SCREEN_NAME, screen.device.uid ))
        
    def screen_removed(self, screen):
        logger.debug("Screen removed for %s" % screen.device.model_id)
        screen_service = self._dbus_screens[screen.device.uid]
        screen_service.remove_from_connection()  
        del self._dbus_screens[screen.device.uid]
        gobject.idle_add(self.ScreenRemoved, "%s/%s" % ( SCREEN_NAME, screen.device.uid ))
        
    def service_stopping(self):
        logger.debug("Sending stopping down signal")
        gobject.idle_add(self.Stopping)
        
    def service_stopped(self):
        logger.debug("Sending stopped down signal")
        gobject.idle_add(self.Stopped)
        
    def service_starting_up(self):
        logger.debug("Sending starting up signal")
        gobject.idle_add(self.Starting)
        
    def service_started_up(self):
        logger.debug("Sending started up signal")
        gobject.idle_add(self.Started)
       
    '''
    DBUS Signals
    ''' 
    
    @dbus.service.signal(IF_NAME)
    def Stopping(self):
        pass
      
    @dbus.service.signal(IF_NAME)
    def Stopped(self):
        pass
    
    @dbus.service.signal(IF_NAME)
    def Starting(self):
        pass 
    
    @dbus.service.signal(IF_NAME)
    def Started(self):
        pass
    
    @dbus.service.signal(IF_NAME)
    def ScreenAdded(self, screen_name):
        pass
    
    @dbus.service.signal(IF_NAME)
    def ScreenRemoved(self, screen_name):
        pass
    
    '''
    DBUS methods
    ''' 
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ( g15globals.name, "Gnome15 Project", g15globals.version, "1.1" )
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='')
    def Stop(self):
        self._service.shutdown()
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsStarting(self):
        return self._service.starting_up
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsStarted(self):
        return not self._service.starting_up and not not self._service.shutting_down 
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsStopping(self):
        return self._service.shutting_down
    
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='ssss')
    def GetDeviceInformation(self):
        device = self._screen.device
        return ( device.uid, device.model_id, "%s:%s" % ( hex(device.usb_id[0]),hex(device.usb_id[1]) ), device.model_fullname )

    @dbus.service.method(IF_NAME, out_signature='as')
    def GetDevices(self):
        l = []
        for device in self._dbus_devices:
            l.append("%s/%s" % (DEVICE_NAME, device._device.uid ) )
        return l


    @dbus.service.method(IF_NAME, out_signature='as')
    def GetScreens(self):
        l = []
        for screen in self._dbus_screens:
            l.append("%s/%s" % (SCREEN_NAME, screen ) )
        return l