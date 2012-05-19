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
import sys
import traceback

from cStringIO import StringIO

BUS_NAME="org.gnome15.Gnome15"
NAME="/org/gnome15/Service"
DEBUG_NAME="/org/gnome15/Debug"
PAGE_NAME="/org/gnome15/Page"
CONTROL_ACQUISITION_NAME="/org/gnome15/Control"
SCREEN_NAME="/org/gnome15/Screen"
DEVICE_NAME="/org/gnome15/Device"
IF_NAME="org.gnome15.Service"
PAGE_IF_NAME="org.gnome15.Page"
CONTROL_ACQUISITION_IF_NAME="org.gnome15.Control"
SCREEN_IF_NAME="org.gnome15.Screen"
DEBUG_IF_NAME="org.gnome15.Debug"
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
            
    @dbus.service.method(SCREEN_IF_NAME, in_signature='b')
    def set_receive_actions(self, enabled):
        if enabled and self in self._screen.key_handler.action_listeners:
            raise Exception("Already receiving actions")
        elif not enabled and not self in self._screen.key_handler.action_listeners:
            raise Exception("Not receiving actions")
        if enabled:
            self._screen.key_handler.action_listeners.append(self)
        else:
            self._screen.key_handler.action_listeners.remove(self)
    
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
        print "Most used objects"
        print "-----------------"
        print
        objgraph.show_most_common_types(limit=200)
        print "Job Queues"
        print "----------"
        print
        g15util.scheduler.print_all_jobs()
        print "Threads"
        print "-------"
        for threadId, stack in sys._current_frames().items():
            print "ThreadID: %s" % threadId
            for filename, lineno, name, line in traceback.extract_stack(stack):
                print '    File: "%s", line %d, in %s' % (filename, lineno, name)
        
    @dbus.service.method(DEBUG_IF_NAME)
    def ShowGraph(self):
        objgraph.show_refs(self._service)
        
    @dbus.service.method(DEBUG_IF_NAME, in_signature='s')
    def Objects(self, typename):
        print "%d instances of type %s. Referrers :-" % ( objgraph.count(typename), typename)
        done = {}
        for r in objgraph.by_type(typename):
            if isinstance(r, list):
                print "%s" % str(r[:min(20, len(r))])
            else:
                print "%s" % str(r)
        
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
    def Referents(self, typename):
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
        self._device = device    
        
    @dbus.service.method(DEVICE_IF_NAME, in_signature='b')
    def SetReceiveActions(self, enabled):
        self.set_receive_actions(enabled)
        
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
        self._dbus_pages = {}
        self._clients = {}
        
    '''
    screen change listener and action listener
    '''
        
    def memory_bank_changed(self, new_memory_bank):
        logger.debug("Sending memory bank changed signel (%d)" % new_memory_bank)
        gobject.idle_add(self.MemoryBankChanged, new_memory_bank)
        
    def attention_cleared(self):
        logger.debug("Sending attention cleared signal")
        gobject.idle_add(self.AttentionCleared)
        logger.debug("Sent attention cleared signal")
            
    def attention_requested(self, message):
        logger.debug("Sending attention requested signal")
        gobject.idle_add(self.AttentionRequested, message if message != None else "")
        logger.debug("Sent attention requested signal")
            
    def driver_connected(self, driver):
        logger.debug("Sending driver connected signal")
        gobject.idle_add(self.Connected, driver.get_name())
        logger.debug("Sent driver connected signal")
            
    def driver_disconnected(self, driver):
        logger.debug("Sending driver disconnected signal")
        gobject.idle_add(self.Disconnected, driver.get_name())
        logger.debug("Sent driver disconnected signal")
        
    def page_changed(self, page):
        logger.debug("Sending page changed signal for %s" % page.id)
        dbus_page = self._dbus_pages[page.id]
        self.PageChanged(dbus_page._bus_name)
        logger.debug("Sent page changed signal for %s" % page.id)
        
    def new_page(self, page): 
        logger.debug("Sending new page signal for %s" % page.id)
        if page.id in self._dbus_pages:
            raise Exception("Page %s already in DBUS service." % page.id)
        dbus_page = G15DBUSPageService(self, page, self._dbus_service._page_sequence_number)
        self._dbus_pages[page.id] = dbus_page
        gobject.idle_add(self.PageCreated, dbus_page._bus_name, page.title)
        self._dbus_service._page_sequence_number += 1
        logger.debug("Sent new page signal for %s" % page.id)
        
    def title_changed(self, page, title):
        logger.debug("Sending title changed signal for %s" % page.id)
        dbus_page = self._dbus_pages[page.id]
        gobject.idle_add(self.PageTitleChanged, dbus_page._bus_name, title)
        logger.debug("Sent title changed signal for %s" % page.id)
    
    def deleting_page(self, page):
        logger.debug("Sending page deleted signal for %s" % page.id)
        
        for client_bus_name in self._clients:
            client = self._clients[client_bus_name]
            if page in client.pages:
                client.pages.remove(page)
        
        if page.id in self._dbus_pages:
            dbus_page = self._dbus_pages[page.id]
            if dbus_page in page.key_handlers: 
                page.key_handlers.remove(dbus_page)
            gobject.idle_add(self.PageDeleting, dbus_page._bus_name, )
        else:
            logger.warning("DBUS Page %s is deleting, but it never existed. Huh? %s" % ( page.id, str(self._dbus_pages) ))
        logger.debug("Sent page deleting signal for %s" % page.id)
            
    def deleted_page(self, page):
        logger.debug("Sending page deleted signal for %s" % page.id)
        if page.id in self._dbus_pages:
            dbus_page = self._dbus_pages[page.id]
            gobject.idle_add(self.PageDeleted, dbus_page._bus_name)
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
    def GetPageForID(self, id):
        return self._dbus_pages[id]._bus_name
    
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
        l = []
        for page in self._dbus_pages.values():
            if page._page.priority >= priority:
                l.append(page._bus_name)
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
        
    @dbus.service.method(SCREEN_IF_NAME, in_signature='b')
    def SetReceiveActions(self, enabled):
        self.set_receive_actions(enabled)
    
    """
    DBUS Signals
    """
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def Disconnected(self, driver_name):
        pass
    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
    def Connected(self, driver_name):
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
    
    """
    Private
    """
    
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
            
    @dbus.service.method(SCREEN_IF_NAME, in_signature='b')
    def SetReceiveActions(self, enabled):
        if enabled and self in self._screen_service._screen.action_listeners:
            raise Exception("Already receiving actions")
        elif not enabled and not self in self._screen_service._screen.action_listeners:
            raise Exception("Not receiving actions")
        if enabled:
            self._screen_service._screen.action_listeners.append(self)
        else:
            self._screen_service._screen.action_listeners.remove(self)
            
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='b')
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
            
    @dbus.service.method(SCREEN_IF_NAME, in_signature='', out_signature='b')
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
        self._page.set_theme(g15theme.G15Theme(dir, variant))
        
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
                    
    @dbus.service.signal(SCREEN_IF_NAME, signature='s')
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
        self._debug_service = G15DBUSDebugService(self)
        self._service.service_listeners.append(self)
        logger.debug("DBUS service ready")
        self._dbus_screens = {}
        self._dbus_devices = []
        for device in g15devices.find_all_devices():
            dbus_device = G15DBUSDeviceService(self, device)
            self._dbus_devices.append(dbus_device)
            
        self._bus.add_signal_receiver(self._name_owner_changed,
                                     dbus_interface='org.freedesktop.DBus',
                                     signal_name='NameOwnerChanged')  
        
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
        return ( g15globals.name, "Gnome15 Project", g15globals.version, "2.1" )
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='')
    def Stop(self):
        g15util.queue("serviceQueue", "dbusShutdown", 0, self._service.shutdown)
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsStarting(self):
        return self._service.starting_up
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def IsStarted(self):
        return not self._service.starting_up and not not self._service.shutting_down 
    
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
            
