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
 
import dbus.service
import g15globals
import g15theme
import util.g15scheduler as g15scheduler
import util.g15gconf as g15gconf
import util.g15cairo as g15cairo
import util.g15icontools as g15icontools
import g15driver
import g15devices
import gobject


from cStringIO import StringIO

BUS_NAME="org.gnome15.Gnome15"
NAME="/org/gnome15/Service"
PAGE_NAME="/org/gnome15/Page"
CONTROL_ACQUISITION_NAME="/org/gnome15/Control"
SCREEN_NAME="/org/gnome15/Screen"
DEVICE_NAME="/org/gnome15/Device"
IF_NAME="org.gnome15.Service"
PAGE_IF_NAME="org.gnome15.Page"
CONTROL_ACQUISITION_IF_NAME="org.gnome15.Control"
SCREEN_IF_NAME="org.gnome15.Screen"
DEVICE_IF_NAME="org.gnome15.Device"

# Logging
import logging
logger = logging.getLogger("dbus")
    
class AbstractG15DBUSService(dbus.service.Object):
    
    def __init__(self, conn=None, object_path=None, bus_name=None):
        dbus.service.Object.__init__(self, conn, object_path, bus_name)
        self._reserved_keys = []
        
    def action_performed(self, binding):
        self.Action(binding.action)
                    
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
            
    def _set_receive_actions(self, enabled):
        if enabled and self in self._screen.key_handler.action_listeners:
            raise Exception("Already receiving actions")
        elif not enabled and not self in self._screen.key_handler.action_listeners:
            raise Exception("Not receiving actions")
        if enabled:
            self._screen.key_handler.action_listeners.append(self)
        else:
            self._screen.key_handler.action_listeners.remove(self)
        
class G15DBUSDeviceService(AbstractG15DBUSService):
    
    def __init__(self, dbus_service, device):
        AbstractG15DBUSService.__init__(self, dbus_service._bus_name, "%s/%s" % ( DEVICE_NAME, device.uid ) )
        self._dbus_service = dbus_service
        self._service = dbus_service._service
        self._device = device  
    
    @dbus.service.signal(DEVICE_IF_NAME, signature='s')
    def ScreenAdded(self, screen_name):
        pass
    
    @dbus.service.signal(DEVICE_IF_NAME, signature='s')
    def ScreenRemoved(self, screen_name):
        pass  
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='b')
    def SetReceiveActions(self, enabled):
        self._set_receive_actions(enabled)
        
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
    def GetModelId(self):
        return self._device.model_id
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='s')
    def GetUID(self):
        return self._device.uid
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='s')
    def GetUsbID(self):
        return "%s:%s" % ( hex(self._device.controls_usb_id[0]), hex(self._device.controls_usb_id[1]) )
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='u')
    def GetBPP(self):
        return self._device.bpp
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='', out_signature='uu')
    def GetSize(self):
        return self._device.size
    
class G15DBUSClient():
    
    def __init__(self, bus_name):
        self.bus_name = bus_name
        self.pages = []
        self.acquisitions = []
        
    def cleanup(self):
        for p in list(self.pages):
            p.delete()
        for a in list(self.acquisitions):
            a.release()
        
class G15DBUSScreenService(AbstractG15DBUSService):
    
    def __init__(self, dbus_service, screen):
        self._bus_name = "%s/%s" % ( SCREEN_NAME, screen.device.uid )
        AbstractG15DBUSService.__init__(self, dbus_service._bus_name, self._bus_name )
        self._dbus_service = dbus_service
        self._service = dbus_service._service
        self._screen = screen
        self._screen.add_screen_change_listener(self)
        self._screen.key_handler.key_handlers.append(self)
        self._notify_handles = []
        self._dbus_pages = {}
        self._clients = {}
        
        self._notify_handles.append(self._screen.conf_client.notify_add("/apps/gnome15/%s/cycle_screens" % self._screen.device.uid, self._cycle_screens_option_changed))
        
    '''
    screen change listener and action listener
    '''
        
    def memory_bank_changed(self, new_memory_bank):
        if g15scheduler.run_on_gobject(self.memory_bank_changed, new_memory_bank):
            return
        logger.debug("Sending memory bank changed signel (%d)" % new_memory_bank)
        self.MemoryBankChanged(new_memory_bank)
        
    def attention_cleared(self):
        if g15scheduler.run_on_gobject(self.attention_cleared):
            return
        logger.debug("Sending attention cleared signal")
        self.AttentionCleared()
        logger.debug("Sent attention cleared signal")
            
    def attention_requested(self, message):
        if g15scheduler.run_on_gobject(self.attention_requested, message):
            return
        logger.debug("Sending attention requested signal")
        self.AttentionRequested(message if message != None else "")
        logger.debug("Sent attention requested signal")
            
    def driver_connected(self, driver):
        if g15scheduler.run_on_gobject(self.driver_connected, driver):
            return
        logger.debug("Sending driver connected signal")
        self.Connected(driver.get_name())
        logger.debug("Sent driver connected signal")
            
    def driver_connection_failed(self, driver, exception):
        if g15scheduler.run_on_gobject(self.driver_connection_failed, driver, exception):
            return
        logger.debug("Sending driver connection failed signal")
        self.ConnectionFailed(driver.get_name(), str(exception))
        logger.debug("Sent driver connection failed signal")
            
    def driver_disconnected(self, driver):
        if g15scheduler.run_on_gobject(self.driver_disconnected, driver):
            return
        logger.debug("Sending driver disconnected signal")
        self.Disconnected(driver.get_name())
        logger.debug("Sent driver disconnected signal")
        
    def page_changed(self, page):
        if g15scheduler.run_on_gobject(self.page_changed, page):
            return
        logger.debug("Sending page changed signal for %s" % page.id)
        if page.id in self._dbus_pages:
            dbus_page = self._dbus_pages[page.id]
            self.PageChanged(dbus_page._bus_name)
            logger.debug("Sent page changed signal for %s" % page.id)
        else:
            logger.warn("Got page_changed event when no such page (%s) exists" % page.id)
        
    def new_page(self, page): 
        if g15scheduler.run_on_gobject(self.new_page, page):
            return
        logger.debug("Sending new page signal for %s" % page.id)
        if page.id in self._dbus_pages:
            raise Exception("Page %s already in DBUS service." % page.id)
        dbus_page = G15DBUSPageService(self, page, self._dbus_service._page_sequence_number)
        self._dbus_pages[page.id] = dbus_page
        self.PageCreated(dbus_page._bus_name, page.title)
        self._dbus_service._page_sequence_number += 1
        logger.debug("Sent new page signal for %s" % page.id)
        
    def title_changed(self, page, title): 
        if g15scheduler.run_on_gobject(self.title_changed, page, title):
            return
        logger.debug("Sending title changed signal for %s" % page.id)
        dbus_page = self._dbus_pages[page.id]
        self.PageTitleChanged(dbus_page._bus_name, title)
        logger.debug("Sent title changed signal for %s" % page.id)
    
    def deleting_page(self, page):
        if g15scheduler.run_on_gobject(self.deleting_page, page):
            return
        logger.debug("Sending page deleting signal for %s" % page.id)
        
        for client_bus_name in self._clients:
            client = self._clients[client_bus_name]
            if page in client.pages:
                client.pages.remove(page)
        
        if page.id in self._dbus_pages:
            dbus_page = self._dbus_pages[page.id]
            if dbus_page in page.key_handlers: 
                page.key_handlers.remove(dbus_page)
            self.PageDeleting(dbus_page._bus_name, )
        else:
            logger.warning("DBUS Page %s is deleting, but it never existed. Huh? %s" % ( page.id, str(self._dbus_pages) ))
        logger.debug("Sent page deleting signal for %s" % page.id)
            
    def deleted_page(self, page):
        if g15scheduler.run_on_gobject(self.deleted_page, page):
            return
        logger.debug("Sending page deleted signal for %s" % page.id)
        if page.id in self._dbus_pages:
            dbus_page = self._dbus_pages[page.id]
            self.PageDeleted(dbus_page._bus_name)
            dbus_page.remove_from_connection()
            del self._dbus_pages[page.id]
        else:
            logger.warning("DBUS Page %s was deleted, but it never existed. Huh? %s" % ( page.id, str(self._dbus_pages) ))
        logger.debug("Sent page deleted signal for %s" % page.id)
            
    """
    DBUS Functions
    """
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='sds', out_signature='s', sender_keyword = "sender")
    def AcquireControl(self, control_id, release_after, value, sender = None):        
        control = self._screen.driver.get_control(control_id)
        if control is None:
            raise Exception("No control with ID of %s" % control_id)
        if value == "":
            initial_value = None
        elif isinstance(control.value, int):
            if control.hint & g15driver.HINT_SWITCH != 0:
                initial_value = 1 if value == "true" else 0
            else:
                initial_value = int(value)
        else:
            sp = value.split(",")
            initial_value = (int(sp[0]), int(sp[1]), int(sp[2]))
        control_acquisition = self._screen.driver.acquire_control(control, None if release_after == 0 else release_after, initial_value)
        dbus_control_acquisition = G15DBUSControlAcquisition(self, control_acquisition, self._dbus_service._acquire_sequence_number)
        self._get_client(sender).acquisitions.append(control_acquisition)
        control_acquisition.on_release = dbus_control_acquisition._notify_release 
        self._dbus_service._acquire_sequence_number += 1
        return dbus_control_acquisition._bus_name
        
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='s')
    def GetMessage(self):
        return self._screen.attention_message
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='')
    def ClearAttention(self):
        return self._screen.clear_attention()
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='s', out_signature='')
    def RequestAttention(self, message):
        self._screen.request_attention(message)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='ssn', out_signature='s', sender_keyword = 'sender')
    def CreatePage(self, page_id, title, priority, sender = None):
        page = g15theme.G15Page(page_id, self._screen, priority = priority)
        self._screen.add_page(page)
        page.set_title(title)
        self._get_client(sender).pages.append(page)
        return self.GetPageForID(page_id)
            
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='b')
    def IsCyclingEnabled(self):
        return g15gconf.get_bool_or_default(self._service.conf_client, "/apps/gnome15/%s/cycle_screens" % self._screen.device.uid, True);
            
    @dbus.service.method(SCREEN_IF_NAME, in_signature='b', out_signature='')
    def SetCyclingEnabled(self, enabled):
        self._service.conf_client.set_bool("/apps/gnome15/%s/cycle_screens" % self._screen.device.uid, enabled);
            
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='b')
    def IsReceiveActions(self):
        return self in self._screen.key_handler.action_listeners
            
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
        return ( device.uid, device.model_id, "%s:%s" % ( hex(device.controls_usb_id[0]),hex(device.controls_usb_id[1]) ), device.model_fullname )
    
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
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='b')
    def IsConnected(self):
        return self._screen.driver.is_connected() if self._screen.driver != None else False
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='n')
    def CycleKeyboard(self, value):
        for c in self._get_dimmable_controls():
            if isinstance(c.value, int):
                self._screen.cycle_level(value, c)
            else:
                self._screen.cycle_color(value, c)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='s', out_signature='s')
    def GetPageForID(self, page_id):
        return self._dbus_pages[page_id]._bus_name
    
    @dbus.service.method(SCREEN_IF_NAME, out_signature='s')
    def GetVisiblePage(self):
        return self.GetPageForID(self._screen.get_visible_page().id)
    
    @dbus.service.method(SCREEN_IF_NAME, out_signature='as')
    def GetPages(self):
        l = []
        for page in self._dbus_pages.values():
            l.append(page._bus_name)
        return l
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='n', out_signature='as')
    def GetPagesBelowPriority(self, priority):
        logger.warning("The GetPagesBelowPriority is deprecated. Use GetPages instead.")
        l = []
        for page in self._dbus_pages.values():
            if page._page.priority >= priority:
                l.append(page._bus_name)
        return l
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='s')
    def GetLastError(self):
        err = self._screen.get_last_error()
        if err is None:
            return ""
        return str(err)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='')
    def ClearPopup(self):
        return self._screen.clear_popup()
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='n', out_signature='')
    def Cycle(self, cycle):
        return self._screen.cycle(cycle)
    
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='b')
    def IsAttentionRequested(self):
        return self._screen.attention
        
    @dbus.service.method(SCREEN_IF_NAME, in_signature='b')
    def SetReceiveActions(self, enabled):
        self._set_receive_actions(enabled)
    
    """
    DBUS Signals
    """
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def Disconnected(self, driver_name):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def Connected(self, driver_name):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='ss')
    def ConnectionFailed(self, driver_name, exception_text):
        pass
            
    @dbus.service.signal(SCREEN_IF_NAME, signature='u')
    def MemoryBankChanged(self, new_memory_bank):
        pass 
            
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def PageChanged(self, page_path):
        pass 
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='ss')
    def PageCreated(self, page_path, title):
        pass 
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='ss')
    def PageTitleChanged(self, page_path, new_title):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def PageDeleted(self, page_path):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def PageDeleting(self, page_path):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def AttentionRequested(self, message):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='')
    def AttentionCleared(self):
        pass  
                    
    @dbus.service.signal(SCREEN_IF_NAME, signature='as')
    def KeysPressed(self, keys):
        pass  
                    
    @dbus.service.signal(SCREEN_IF_NAME, signature='as')
    def KeysReleased(self, keys):
        pass
                    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def Action(self, binding):
        pass   
                    
    @dbus.service.signal(SCREEN_IF_NAME, signature='b')
    def CyclingChanged(self, cycle):
        pass    
    
    """
    Private
    """
    def _removing(self):
        for h in self._notify_handles:
            self._service.conf_client.notify_remove(h)
        
    def _cycle_screens_option_changed(self, client, connection_id, entry, args):
        self.CyclingChanged(entry.value.get_bool())
    
    def _get_dimmable_controls(self):
        controls = []
        for c in self._screen.driver.get_controls():
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
    
    def _get_client(self, sender):
        if sender in self._clients:
            return self._clients[sender]
        else:
            c = G15DBUSClient(sender)
            self._clients[sender] = c
            return c
    
class G15DBUSControlAcquisition(AbstractG15DBUSService):
    
    def __init__(self, screen_service, acquisition, sequence_number):
        self._bus_name = "%s%s" % ( CONTROL_ACQUISITION_NAME , str( sequence_number ) )        
        AbstractG15DBUSService.__init__(self, screen_service._dbus_service._bus_name, self._bus_name )
        self._screen_service = screen_service
        self._sequence_number = sequence_number
        self._acquisition = acquisition        
    
    @dbus.service.method(CONTROL_ACQUISITION_IF_NAME, out_signature='s')
    def GetValue(self):
        control = self._acquisition.control
        value = self._acquisition.val
        if isinstance(value, int):
            if control.hint & g15driver.HINT_SWITCH != 0:
                return "true" if value else "false"
            else:
                return str(value)
        else:
            return "%d,%d,%d" % value
    
    @dbus.service.method(CONTROL_ACQUISITION_IF_NAME, out_signature='t')
    def GetHint(self):
        return self._acquisition.control.hint
    
    @dbus.service.method(CONTROL_ACQUISITION_IF_NAME, in_signature='sd', out_signature='')
    def SetValue(self, value, reset_after):
        control = self._acquisition.control
        reset_after = None if reset_after == 0.0 else reset_after
        if isinstance(control.value, int):
            if control.hint & g15driver.HINT_SWITCH != 0:
                self._acquisition.set_value(1 if value == "true" else 0, reset_after)
            else:
                self._acquisition.set_value(int(value), reset_after)
        else:
            sp = value.split(",")
            self._acquisition.set_value((int(sp[0]), int(sp[1]), int(sp[2])), reset_after)
               
    @dbus.service.method(CONTROL_ACQUISITION_IF_NAME, in_signature='ddb', out_signature='')
    def Fade(self, percentage, duration, release):
        self._acquisition.fade(percentage, duration, release)
            
    @dbus.service.method(CONTROL_ACQUISITION_IF_NAME, in_signature='ddd', out_signature='')
    def Blink(self, off_val, delay, duration):
        self._acquisition.blink(off_val, delay, None if duration == 0 else duration)
            
    @dbus.service.method(CONTROL_ACQUISITION_IF_NAME)
    def Reset(self):
        self._acquisition.reset()
            
    @dbus.service.method(CONTROL_ACQUISITION_IF_NAME)
    def CancelReset(self):
        self._acquisition.cancel_reset()
            
    @dbus.service.method(CONTROL_ACQUISITION_IF_NAME)
    def Release(self):
        self._screen_service._screen.driver.release_control(self._acquisition)
        
    """
    Private
    """
    def _notify_release(self):
        logger.info("Release acquisition of control %s" % self._acquisition.control.id)
        for client_bus_name in self._screen_service._clients:
            client = self._screen_service._clients[client_bus_name]
            if self._acquisition in client.acquisitions:
                client.acquisitions.remove(self._acquisition)            
        self.remove_from_connection()

class G15DBUSPageService(AbstractG15DBUSService):
    
    def __init__(self, screen_service, page, sequence_number):
        self._bus_name = "%s%s" % ( PAGE_NAME , str( sequence_number ) )        
        AbstractG15DBUSService.__init__(self, screen_service._dbus_service._bus_name, self._bus_name )        
        self._screen_service = screen_service
        self._screen = self._screen_service._screen
        self._sequence_number = sequence_number
        self._page = page
        self._timer = None        
        self._page.key_handlers.append(self)
            
    @dbus.service.method(PAGE_IF_NAME, in_signature='b')
    def SetReceiveActions(self, enabled):
        if enabled and self in self._screen_service._screen.action_listeners:
            raise Exception("Already receiving actions")
        elif not enabled and not self in self._screen_service._screen.action_listeners:
            raise Exception("Not receiving actions")
        if enabled:
            self._screen_service._screen.action_listeners.append(self)
        else:
            self._screen_service._screen.action_listeners.remove(self)
            
    @dbus.service.method(PAGE_IF_NAME, in_signature='', out_signature='b')
    def GetReceiveActions(self):
        return self in self._screen_service._screen.action_listeners
    
    @dbus.service.method(PAGE_IF_NAME, out_signature='n')
    def GetPriority(self):
        return self._page.priority
    
    @dbus.service.method(PAGE_IF_NAME, out_signature='s')
    def GetTitle(self):
        return self._page.title
    
    @dbus.service.method(PAGE_IF_NAME, out_signature='s')
    def GetId(self):
        return self._page.id
    
    @dbus.service.method(PAGE_IF_NAME, out_signature='b')
    def IsVisible(self):
        return self._page.is_visible()
            
    @dbus.service.method(PAGE_IF_NAME, in_signature='', out_signature='b')
    def IsReceiveActions(self):
        return self in self._screen.key_handler.action_listeners
    
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
    def Text(self, text, x, y, width, height, contraints = "left"):
        self._page.text(text, x, y, width, height, contraints)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='sdddd')
    def Image(self, path, x, y, width, height):
        if not "/" in path:
            path = g15icontools.get_icon_path(path, width if width != 0 else 128)
            
        size = None if width == 0 or height == 0 else (width, height)
        
        img_surface = g15cairo.load_surface_from_file(path, size)
        self._page.image(img_surface, x, y)
        
    @dbus.service.method(PAGE_IF_NAME, in_signature='aydd')
    def ImageData(self, image_data, x, y):
        file_str = StringIO(str(image_data))
        img_surface = g15cairo.load_surface_from_file(file_str, None)
        file_str.close()
        self._page.image(img_surface, x, y)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def CancelTimer(self):
        self._timer.cancel()
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='')
    def Redraw(self):
        self._screen_service._screen.redraw(self._page)
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ss')
    def LoadTheme(self, theme_dir, variant):
        self._page.set_theme(g15theme.G15Theme(theme_dir, variant))
        
    @dbus.service.method(PAGE_IF_NAME, in_signature='s')
    def SetThemeSVG(self, svg_text):
        self._page.set_theme(g15theme.G15Theme(None, None, svg_text = svg_text))
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ss')
    def SetThemeProperty(self, name, value):
        self._page.theme_properties[name] = value
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='a{ss}')
    def SetThemeProperties(self, properties):
        self._page.theme_properties = properties
    
    @dbus.service.method(PAGE_IF_NAME, in_signature='ndd')
    def SetPriority(self, priority, revert_after, delete_after):
        self._timer = self._screen_service._screen.set_priority(self._page, priority, revert_after, delete_after)
                    
    @dbus.service.signal(PAGE_IF_NAME, signature='as')
    def KeysPressed(self, keys):
        pass 
                    
    @dbus.service.signal(PAGE_IF_NAME, signature='as')
    def KeysReleased(self, keys):
        pass
                    
    @dbus.service.signal(PAGE_IF_NAME, signature='s')
    def Action(self, binding):
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
        
    """
    Callbacks
    """
    def action_performed(self, binding):
        if self.IsVisible():
            AbstractG15DBUSService.action_performed(self, binding)

class G15DBUSService(AbstractG15DBUSService):
    
    def __init__(self, service):        
        AbstractG15DBUSService.__init__(self)
        self._service = service
        logger.debug("Getting Session DBUS")
        self._bus = dbus.SessionBus()
        self._page_sequence_number = 1
        self._acquire_sequence_number = 1
        logger.debug("Exposing service")
        self._bus_name = dbus.service.BusName(BUS_NAME, bus=self._bus, replace_existing=False, allow_replacement=False, do_not_queue=True)
        dbus.service.Object.__init__(self, self._bus_name, NAME)
        self._service.service_listeners.append(self)
        logger.debug("DBUS service ready")
        self._dbus_screens = {}
        self._dbus_devices = []
        self._dbus_device_map = {}
        for device in g15devices.find_all_devices():
            dbus_device = G15DBUSDeviceService(self, device)
            self._dbus_devices.append(dbus_device)
            self._dbus_device_map[device.uid] = dbus_device
        g15devices.device_added_listeners.append(self._device_added)
        g15devices.device_removed_listeners.append(self._device_removed)
            
        self._bus.add_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')
        
    def _device_removed(self, device):
        if device.uid in self._dbus_device_map:
            dbus_device = self._dbus_device_map[device.uid]
            self._dbus_devices.remove(dbus_device)
            del self._dbus_device_map[device.uid]
            logger.info("Removed DBUS device %s/%s" % ( DEVICE_NAME, device.uid ))
            self.DeviceRemoved("%s/%s" % ( DEVICE_NAME, device.uid ))
            self._silently_remove_from_connector(dbus_device)
        else:
            logger.warn("DBUS service did not know about a device for some reason (%s)" % device.uid)
        
    def _device_added(self, device):
        dbus_device = G15DBUSDeviceService(self, device)
        self._dbus_devices.append(dbus_device)
        self._dbus_device_map[device.uid] = dbus_device
        logger.info("Added DBUS device %s/%s" % ( DEVICE_NAME, device.uid ))
        self.DeviceAdded("%s/%s" % ( DEVICE_NAME, device.uid ))
        
    def stop(self):   
        g15devices.device_added_listeners.remove(self._device_added)
        g15devices.device_removed_listeners.remove(self._device_removed)
        for dbus_device in self._dbus_devices:
            self._silently_remove_from_connector(dbus_device)
        for screen in self._dbus_screens:
            self._silently_remove_from_connector(self._dbus_screens[screen])    
        self._silently_remove_from_connector(self)
        
    def _silently_remove_from_connector(self, obj):
        try:
            obj.remove_from_connection()
        except Exception as e:
            logger.debug("Error silently removing obj from connection.", exc_info = e)
            pass
            
    '''
    service listener
    '''
    def screen_added(self, screen):
        if g15scheduler.run_on_gobject(self.screen_added, screen):
            return
        logger.debug("Screen added for %s" % screen.device.model_id)        
        screen_service = G15DBUSScreenService(self, screen)
        self._dbus_screens[screen.device.uid] = screen_service
        self.ScreenAdded("%s/%s" % ( SCREEN_NAME, screen.device.uid ))
        dbus_device = self._dbus_device_map[screen.device.uid]
        dbus_device.ScreenAdded("%s/%s" % ( SCREEN_NAME, screen.device.uid ))
        
    def screen_removed(self, screen):
        if g15scheduler.run_on_gobject(self.screen_removed, screen):
            return
        logger.debug("Screen removed for %s" % screen.device.model_id)
        self.ScreenRemoved("%s/%s" % ( SCREEN_NAME, screen.device.uid ))
        if screen.device.uid in self._dbus_device_map:
            dbus_device = self._dbus_device_map[screen.device.uid]
            dbus_device.ScreenRemoved("%s/%s" % ( SCREEN_NAME, screen.device.uid ))
        try:
            screen_service = self._dbus_screens[screen.device.uid]
            screen_service._removing()
            screen_service.remove_from_connection()
        except Exception as e:
            logger.debug("Error removing screen object.", exc_info = e)
            # May happen on shutdown
            pass  
        del self._dbus_screens[screen.device.uid]
        
    def service_stopping(self):
        if g15scheduler.run_on_gobject(self.service_stopping):
            return
        logger.debug("Sending stopping down signal")
        self.Stopping()
        
    def service_stopped(self):
        if g15scheduler.run_on_gobject(self.service_stopped):
            return
        logger.debug("Sending stopped down signal")
        self.Stopped()
        
    def service_starting_up(self):
        if g15scheduler.run_on_gobject(self.service_starting_up):
            return
        logger.debug("Sending starting up signal")
        self.Starting()
        
    def service_started_up(self):
        if g15scheduler.run_on_gobject(self.service_started_up):
            return
        logger.debug("Sending started up signal")
        self.Started()
       
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
    
    @dbus.service.signal(IF_NAME, signature='s')
    def ScreenAdded(self, screen_name):
        pass
    
    @dbus.service.signal(IF_NAME, signature='s')
    def ScreenRemoved(self, screen_name):
        pass
    
    @dbus.service.signal(IF_NAME, signature='s')
    def DeviceAdded(self, device_name):
        pass
    
    @dbus.service.signal(IF_NAME, signature='s')
    def DeviceRemoved(self, device_name):
        pass
    
    '''
    DBUS methods
    ''' 
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ( g15globals.name, "Gnome15 Project", g15globals.version, "2.1" )
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='')
    def Stop(self):
        g15scheduler.queue("serviceQueue", "dbusShutdown", 0, self._service.shutdown)
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsStarting(self):
        return self._service.starting_up
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsStarted(self):
        started = not self._service.starting_up and not self._service.shutting_down
        return started 
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsStopping(self):
        return self._service.shutting_down

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

    @dbus.service.method(IF_NAME, in_signature='ssas')
    def Launch(self, profile_name, screen_id, args):
        logger.info("Launch under profile %s, screen %s, args = %s" % (profile_name, screen_id, str(args)))
    
    """
    Private
    """
    def _name_owner_changed(self, name, old_owner, new_owner):
        for screen in self._dbus_screens.values():
            if name in screen._clients and old_owner and not new_owner:
                logger.info("Cleaning up DBUS client %s" % name)
                client = screen._clients[name]
                client.cleanup()
                del screen._clients[name]
            
