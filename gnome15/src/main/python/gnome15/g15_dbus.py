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
import g15_util as g15util
import g15_driver as g15driver
import cairo
import pangocairo
import pango
import xml.sax.saxutils as saxutils
from cStringIO import StringIO

BUS_NAME="org.gnome15.Gnome15"
NAME="/org/gnome15/Service"
IF_NAME="org.gnome15.Service"

class G15DBUSPage():
    
    def __init__(self, plugin):
        self.page = None
        self.timer = None
        self.theme = None
        self.plugin = plugin
        self.properties = {}
        self.back_buffer = None
        self.buffer = None
        self.back_context = None
        self.font_size = 12.0
        self.font_family = "Sans"
        self.font_style = "normal"
        self.font_weight = "normal"
        
    def new_surface(self):
        sw = self.plugin.service.driver.get_size()[0]
        sh = self.plugin.service.driver.get_size()[1]
        self.back_buffer = cairo.ImageSurface (cairo.FORMAT_ARGB32,sw, sh)
        self.back_context = cairo.Context(self.back_buffer)
        self.set_line_width(1.0)
        
        rgb = self.plugin.service.driver.get_color(g15driver.HINT_FOREGROUND, ( 0, 0, 0 ))
        self.foreground(rgb[0],rgb[1],rgb[2], 255)
        
    def draw_surface(self):
        self.buffer = self.back_buffer
        
    def foreground(self, r, g, b, a = 255):
        self.foreground_rgb = (r, g, b, a)
        self.back_context.set_source_rgba(float(r) / 255.0, float(g) / 255.0, float(b) / 255.0, float(a) / 255.0)
        
    def save(self):
        self.back_context.save()
        
    def restore(self):
        self.back_context.restore()
        
    def set_line_width(self, line_width):
        self.back_context.set_line_width(line_width)
        
    def arc(self, x, y, radius, angle1, angle2, fill = False):
        self.back_context.arc(x, y, radius, g15util.degrees_to_radians(angle1), g15util.degrees_to_radians(angle2))
        if fill:
            self.back_context.fill()
        else:
            self.back_context.stroke()
        
    def line(self, x1, y1, x2, y2):
        self.back_context.line_to(x1, y1)
        self.back_context.line_to(x2, y2)
        self.back_context.stroke()
        
    def image(self, image, x, y):
        self.back_context.translate(x, y)
        self.back_context.set_source_surface(image)
        self.back_context.paint()
        self.back_context.translate(-x, -y)
        
    def rectangle(self, x, y, width, height, fill = False):
        self.back_context.rectangle(x, y, width, height)
        if fill:
            self.back_context.fill()
        else:
            self.back_context.stroke()
        
    def paint(self, canvas):
        # Paint the theme
        if self.theme != None:
            canvas.save()
            self.theme.draw(canvas, self.properties)
            canvas.restore()
            
        # Paint the canvas
        if self.buffer != None:
            canvas.save()
            canvas.set_source_surface(self.buffer)
            canvas.paint()
            canvas.restore()
            
    def set_font(self, font_size = None, font_family = None, font_style = None, font_weight = None):
        if font_size:
            self.font_size = font_size
        if font_family:
            self.font_family = font_family
        if font_style:
            self.font_style = font_style
        if font_weight:
            self.font_weight = font_weight
            
    def text(self, text, x, y, width, height, text_align = "left"):
        driver = self.plugin.service.driver
        pango_context = pangocairo.CairoContext(self.back_context)
        pango_context.set_antialias(driver.get_antialias()) 
        fo = cairo.FontOptions()
        fo.set_antialias(driver.get_antialias())
        if driver.get_antialias() == cairo.ANTIALIAS_NONE:
            fo.set_hint_style(cairo.HINT_STYLE_NONE)
            fo.set_hint_metrics(cairo.HINT_METRICS_OFF)
        
        buf = "<span"
        if self.font_size != None:
            buf += " size=\"%d\"" % ( int(self.font_size * 1000) ) 
        if self.font_style != None:
            buf += " style=\"%s\"" % self.font_style
        if self.font_weight != None:
            buf += " weight=\"%s\"" % self.font_weight
        if self.font_family != None:
            buf += " font_family=\"%s\"" % self.font_family                
        if self.foreground_rgb != None:
            buf += " foreground=\"%s\"" % g15util.rgb_to_hex(self.foreground_rgb[0:3])
            
        buf += ">%s</span>" % saxutils.escape(text)
        attr_list = pango.parse_markup(buf)
        
        # Create the layout
        layout = pango_context.create_layout()
        
        pangocairo.context_set_font_options(layout.get_context(), fo)      
        layout.set_attributes(attr_list[0])
        layout.set_width(int(pango.SCALE * width))
        layout.set_wrap(pango.WRAP_WORD_CHAR)      
        layout.set_text(text)
        spacing = 0
        layout.set_spacing(spacing)
        
        # Alignment
        if text_align == "right":
            layout.set_alignment(pango.ALIGN_RIGHT)
        elif text_align == "center":
            layout.set_alignment(pango.ALIGN_CENTER)
        else:
            layout.set_alignment(pango.ALIGN_LEFT)
        
        # Draw text to canvas
        self.back_context.set_source_rgb(self.foreground_rgb[0], self.foreground_rgb[1], self.foreground_rgb[2])
        pango_context.save()
        pango_context.rectangle(x, y, width, height)
        pango_context.clip()  
                  
        pango_context.move_to(x, y)    
        pango_context.update_layout(layout)
        pango_context.show_layout(layout)        
        pango_context.restore()

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
    
    @dbus.service.method(IF_NAME, in_signature='', out_signature='ssnnn')
    def GetDriverInformation(self):
        driver = self.service.driver
        return ( driver.get_name(), driver.get_model_name(), driver.get_size()[0], driver.get_size()[1], driver.get_bpp() ) if driver != None else None 
    
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
    def NewSurface(self, id):
        self.pages[id].new_surface()
    
    @dbus.service.method(IF_NAME, in_signature='s')
    def Save(self, id):
        self.pages[id].save()
    
    @dbus.service.method(IF_NAME, in_signature='s')
    def Restore(self, id):
        self.pages[id].restore()
    
    @dbus.service.method(IF_NAME, in_signature='s')
    def DrawSurface(self, id):
        self.pages[id].draw_surface()
    
    @dbus.service.method(IF_NAME, in_signature='sd')
    def SetLineWidth(self, id, line_width):
        self.pages[id].set_line_width(line_width)
    
    @dbus.service.method(IF_NAME, in_signature='sdddd')
    def Line(self, id, x1, y1, x2, y2):
        self.pages[id].line(x1, y1, x2, y2)
    
    @dbus.service.method(IF_NAME, in_signature='sddddb')
    def Rectangle(self, id, x, y, width, height, fill):
        self.pages[id].rectangle(x, y, width, height, fill)
    
    @dbus.service.method(IF_NAME, in_signature='sdddb')
    def Circle(self, id, x, y, radius, fill):
        self.pages[id].arc(x, y, radius, 0, 360, fill)
    
    @dbus.service.method(IF_NAME, in_signature='sdddddb')
    def Arc(self, id, x, y, radius, startAngle, endAngle, fill):
        self.pages[id].arc(x, y, radius, startAngle, endAngle, fill)
    
    @dbus.service.method(IF_NAME, in_signature='snnnn')
    def Foreground(self, id, r, g, b, a):
        self.pages[id].foreground(r, g, b, a)
    
    @dbus.service.method(IF_NAME, in_signature='sdsss')
    def SetFont(self, id, font_size = 12.0, font_family = "Sans", font_style = "normal", font_weight = "normal"):
        self.pages[id].set_font(font_size, font_family, font_style, font_weight)
    
    @dbus.service.method(IF_NAME, in_signature='ssdddds')
    def Text(self, id, text, x, y, width, height, text_align = "left"):
        self.pages[id].text(text, x, y, width, height, text_align)
    
    @dbus.service.method(IF_NAME, in_signature='ssdddd')
    def Image(self, id, path, x, y, width, height):
        if not "/" in path:
            path = g15util.get_icon_path(path, width if width != 0 else 128)
            
        size = None if width == 0 or height == 0 else (width, height)
        
        img_surface = g15util.load_surface_from_file(path, size)
        self.pages[id].image(img_surface, x, y)
        
    @dbus.service.method(IF_NAME, in_signature='saydd')
    def ImageData(self, id, image_data, x, y):
        print "Got image data of",len(image_data),"bytes"        
        file_str = StringIO(str(image_data))
        img_surface = g15util.load_surface_from_file(file_str, None)
        file_str.close()
        self.pages[id].image(img_surface, x, y)
    
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
        dbus_page = G15DBUSPage(self)
        page = self.service.screen.new_page(dbus_page.paint, id=id, thumbnail_painter = None, panel_painter = None)
        dbus_page.page = page
        page.set_title(title)
        self.pages[id] = dbus_page