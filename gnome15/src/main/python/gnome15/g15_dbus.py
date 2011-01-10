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
import g15_globals as pglobals
import g15_theme as g15theme

BUS_NAME="org.gnome15.Gnome15"
NAME="/org/gnome15/Service"
IF_NAME="org.gnome15.Service"

class G15DBUSPage():
    
    def __init__(self):
        self.page = None
        self.timer = None
        self.theme = None
        self.properties = {}
        
    def paint(self, canvas):
        if self.theme != None:
            self.theme.draw(canvas, self.properties)

class G15DBUSService(dbus.service.Object):
    
    def __init__(self, service):
        bus = dbus.SessionBus()
        self.pages = {}
        self.service = service
        self.screen_id = 0
        bus_name = dbus.service.BusName(BUS_NAME, bus=bus, replace_existing=True, allow_replacement=True, do_not_queue=True)
        dbus.service.Object.__init__(self, bus_name, NAME)
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssss')
    def GetServerInformation(self):
        return ( pglobals.name, "Gnome15 Project", pglobals.version, "1.0" )
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssyyy')
    def GetDriverInformation(self):
        driver = self.service.driver
        return ( driver.get_name(), driver.get_model_name(), driver.get_size()[0], driver.get_size()[1], driver.get_bpp() ) if driver != None else None, 
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='b')
    def GetDriverConnected(self):
        return self.service.driver.is_connected() if self.service.driver != None else False
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='s')
    def GetLastError(self):
        return str(self.service.get_last_error())
    
    @dbus.service.method(IF_NAME, in_signature='s')
    def DestroyPage(self, id):
        print "Destroying page id =",id
        self.service.screen.del_page(self.pages[id].page)
        del self.pages[id]
    
    @dbus.service.method(IF_NAME, in_signature='s')
    def RaisePage(self, id):
        self.service.screen.raise_page(self.pages[id].page)
    
    @dbus.service.method(IF_NAME, in_signature='s')
    def CancelPageTimer(self, id):
        self.pages[id].timer.cancel()
    
    @dbus.service.method(IF_NAME, in_signature='s')
    def RedrawPage(self, id):
        print "Drawing page id =",id
        self.service.screen.redraw(self.pages[id].page)
    
    @dbus.service.method(IF_NAME, in_signature='sss')
    def LoadPageTheme(self, id, dir, variant):
        dbus_page = self.pages[id] 
        dbus_page.theme = g15theme.G15Theme(dir, self.service.screen, variant)
    
    @dbus.service.method(IF_NAME, in_signature='ss')
    def SetPageThemeSVG(self, id, svg_text):
        dbus_page = self.pages[id] 
        dbus_page.theme = g15theme.G15Theme(None, self.service.screen, None, svg_text = svg_text)
    
    @dbus.service.method(IF_NAME, in_signature='sss')
    def SetPageThemeProperty(self, id, name, value):
        dbus_page = self.pages[id] 
        dbus_page.properties[name] = value
    
    @dbus.service.method(IF_NAME, in_signature='sndd')
    def SetPagePriority(self, id, priority, revert_after, hide_after):
        print "Set priority of page id =",id,"to",priority,"hide_after =", hide_after," revert_after =", revert_after
        dbus_page = self.pages[id] 
        dbus_page.timer = self.service.screen.set_priority(dbus_page.page, priority, revert_after, hide_after)
    
    @dbus.service.method(IF_NAME, in_signature='ss')
    def CreatePage(self, id, title):
        print "Creating page id =",id,"title =",title
        dbus_page = G15DBUSPage()
        page = self.service.screen.new_page(dbus_page.paint, id="Clock", thumbnail_painter = None, panel_painter = None)
        dbus_page.page = page
        page.set_title(title)
        self.pages[id] = dbus_page