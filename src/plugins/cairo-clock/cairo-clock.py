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
 
import gnome15.g15_screen as g15screen 
import gnome15.g15_theme as g15theme 
import gnome15.g15_util as g15util 
import gnome15.g15_driver as g15driver
import datetime
from threading import Timer
import time
import gtk
import os
import sys
import cairo
import rsvg

# Plugin details - All of these must be provided
id="cairo-clock"
name="Cairo Clock"
description="Port of MacSlow's SVG clock to Gnome15\n" \
    + "Requires cairo-clock to be installed (at least the themes). " \
    + "Note, only works on the G19."
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.tanktarta.pwp.blueyonder.co.uk/gnome15/"
has_preferences=True

def create(gconf_key, gconf_client, screen):
    return G15CairoClock(gconf_key, gconf_client, screen)

def show_preferences(parent, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "cairo-clock.glade"))
    
    dialog = widget_tree.get_object("ClockDialog")
    dialog.set_transient_for(parent)
    
    display_seconds = widget_tree.get_object("DisplaySecondsCheckbox")
    display_seconds.set_active(gconf_client.get_bool(gconf_key + "/display_seconds"))
    display_seconds.connect("toggled", changed, gconf_key + "/display_seconds", gconf_client)
    
    display_date = widget_tree.get_object("DisplayDateCheckbox")
    display_date.set_active(gconf_client.get_bool(gconf_key + "/display_date"))
    display_date.connect("toggled", changed, gconf_key + "/display_date", gconf_client)
    
    twenty_four_hour = widget_tree.get_object("TwentyFourHourCheckbox")
    twenty_four_hour.set_active(gconf_client.get_bool(gconf_key + "/twenty_four_hour"))
    twenty_four_hour.connect("toggled", changed, gconf_key + "/twenty_four_hour", gconf_client)

    e = gconf_client.get(gconf_key + "/theme")
    theme_name = "default"
    if e != None:
        theme_name = e.get_string()
    theme_model = widget_tree.get_object("ThemeModel")
    theme = widget_tree.get_object("ThemeCombo")
    theme.connect("changed", theme_changed, gconf_key + "/theme", [ gconf_client, theme_model])
    
    theme_dir = get_theme_dir(gconf_key, gconf_client)
    if os.path.exists(theme_dir):
        for fname in os.listdir(theme_dir):
            if os.path.isdir(os.path.join(theme_dir, fname)):
                theme_model.append([fname])
                if fname == theme_name:
                    theme.set_active(len(theme_model) - 1) 
    
    dialog.run()
    dialog.hide()

def changed(widget, key, gconf_client):
    gconf_client.set_bool(key, widget.get_active())
    
def theme_changed(widget, key, args):
    gconf_client = args[0]
    model = args[1]
    gconf_client.set_string(key, model[widget.get_active()][0])
    
def get_theme_dir(gconf_key, gconf_client):    
    theme_dir = gconf_client.get(gconf_key + "/theme_dir")
    if theme_dir != None:
        return theme_dir.get_string()
    else:  
        return "/usr/share/cairo-clock/themes"

class G15CairoClock():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.page = None
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.revert_timer = None
        self.timer = None
    
    def activate(self): 
        if self.screen.driver.get_bpp() == 1:
            raise Exception("Cairo clock not supported on low-res LCD")       
        self.notify_handler = self.gconf_client.notify_add(self.gconf_key, self.config_changed);   
        self.load_surfaces()         
        self.page = self.screen.new_page(self.paint, priority=g15screen.PRI_NORMAL, 
                                        on_shown=self.on_shown,on_hidden=self.on_hidden,id="Clock",
                                        thumbnail_painter = self.paint_thumbnail)
        self.page.set_title("Cairo Clock")
    
    def on_shown(self):
        self.cancel_refresh()
        self.refresh()
            
    def on_hidden(self):
        self.cancel_refresh()
        self.schedule_refresh()
        
    def cancel_refresh(self):
        if self.timer != None:
            self.timer.cancel()
            self.timer = None
        
    def load_surfaces(self):
        
        self.svg_size = None
        self.width = self.screen.width
        self.height = self.screen.height
        
        theme = self.gconf_client.get_string(self.gconf_key + "/theme")
        if theme == None:
            theme = "default"
            
        self.clock_theme_dir = get_theme_dir(self.gconf_key, self.gconf_client) + "/" + theme          
        self.behind_hands = self.load_surface_list(["clock-drop-shadow", "clock-face", "clock-marks"])
        self.hour_surfaces = self.load_surface_list(["clock-hour-hand-shadow", "clock-hour-hand"])
        self.minute_surfaces = self.load_surface_list(["clock-minute-hand-shadow", "clock-minute-hand"])
        self.second_surfaces = self.load_surface_list(["clock-secondhand-shadow", "clock-second-hand"])
        self.above_hands = self.load_surface_list([ "clock-face-shadow", "clock-glass", "clock-frame" ])
            
    def load_surface_list(self, names):
        list = []        
        for i in names:
            path = self.clock_theme_dir + "/" + i + ".svg"
            if os.path.exists(path):  
                svg = rsvg.Handle(path)   
                if self.svg_size == None:
                    self.svg_size = svg.get_dimension_data()[2:4]
                    print "Will use SVG canvas size of",self.svg_size
                    
                svg_size = self.svg_size
                     
                sx = self.width / svg_size[0]
                sy = self.height / svg_size[1]
                scale = min(sx, sy)                      
                surface = cairo.SVGSurface(None, svg_size[0] * scale * 2,svg_size[1] * scale * 2)  
                context = cairo.Context(surface)
                context.scale(scale, scale)
                context.translate(svg_size[0], svg_size[1])
                svg.render_cairo(context)
                context.translate(-svg_size[0], -svg_size[1])
                list.append(((svg_size[0] * scale, svg_size[1] * scale), surface))
        return list
        
    def schedule_refresh(self):
        if self.page == None:
            return
        
        now = datetime.datetime.now()
        display_seconds = self.gconf_client.get_bool(self.gconf_key + "/display_seconds")
        
        if self.screen.is_visible(self.page):
            if display_seconds:
                next_tick = now + datetime.timedelta(0, 1.0)
                next_tick = datetime.datetime(next_tick.year,next_tick.month,next_tick.day,next_tick.hour, next_tick.minute, int(next_tick.second))
            else:
                next_tick = now + datetime.timedelta(0, 60.0)
                next_tick = datetime.datetime(next_tick.year,next_tick.month,next_tick.day,next_tick.hour, next_tick.minute, 0)
            delay = g15util.total_seconds( next_tick - now )        
            self.timer = g15util.schedule("CairoRefresh", delay, self.refresh)
    
    def deactivate(self):
        self.cancel_refresh()
        self.gconf_client.notify_remove(self.notify_handler);
        self.screen.del_page(self.page)
        self.page = None
        
    def config_changed(self, client, connection_id, entry, args):
        self.load_surfaces()
        self.screen.set_priority(self.page, g15screen.PRI_HIGH, revert_after = 3.0)
        self.cancel_refresh()
        self.schedule_refresh()
        
    def destroy(self):
        pass
    
    def refresh(self):
        self.screen.redraw(self.page)
        self.schedule_refresh()
        
    def paint_thumbnail(self, canvas, allocated_size, horizontal):
        scale = allocated_size / self.height
        canvas.scale(scale, scale)
        self._do_paint(canvas, self.width, self.height, False)
        canvas.scale(1 / scale, 1 / scale)
        return allocated_size 
        
    def paint(self, canvas, draw_date = True):
            
        width = float(self.screen.width)
        height = float(self.screen.height)
            
        self._do_paint(canvas, width, height, draw_date)
        
    def _do_paint(self, canvas, width, height, draw_date = True):
        now = datetime.datetime.now()
        properties = { }
        
        time_format = "%H:%M"
        display_seconds = self.gconf_client.get_bool(self.gconf_key + "/display_seconds")
        if display_seconds:
            time_format = "%H:%M:%S"
            
        clock_width = min(width, height)
        clock_height = min(width, height)
            
        time = datetime.datetime.now().strftime(time_format)
        
        drawing_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, clock_width, clock_height)
        drawing_context = cairo.Context(drawing_surface)
        
        # Below hands          
        for svg_size, surface in self.behind_hands:
            drawing_context.save()
            drawing_context.translate(-svg_size[0], -svg_size[1])
            drawing_context.set_source_surface(surface)
            drawing_context.paint()
            drawing_context.restore()
            
        # Date
        if draw_date and self.gconf_client.get_bool(self.gconf_key + "/display_date"):
            drawing_context.save()
            date_text = datetime.datetime.now().strftime("%d/%m")
            drawing_context.select_font_face("Liberation Sans",
                        cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            drawing_context.set_font_size(27.0)
            x_bearing, y_bearing, text_width, text_height = drawing_context.text_extents(date_text)[:4]
            rgb = self.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 ))
            drawing_context.set_source_rgb(rgb[0],rgb[1],rgb[2])            
            tx = ( ( clock_width - text_width ) / 2 ) - x_bearing
            ty = clock_height * 0.665
            drawing_context.move_to( tx, ty )

            drawing_context.show_text(date_text)
            drawing_context.restore()
            
        # The hand
        s_deg = now.second * 6
        m_deg = now.minute * 6 + ( now.second * ( 6.0 / 60.0 ) )
        
        if self.gconf_client.get_bool(self.gconf_key + "/twenty_four_hour"):
            h_deg = float(now.hour) * 15.0 + (  float ( now.minute * 0.25 ) )
        else:
            h_deg = float( now.hour % 12 ) * 30.0 + (  float ( now.minute * 0.5 ) )
            
        self.draw_hand(drawing_context, self.hour_surfaces, clock_width, clock_height, h_deg)
        self.draw_hand(drawing_context, self.minute_surfaces, clock_width, clock_height, m_deg)
        if display_seconds:
            self.draw_hand(drawing_context, self.second_surfaces, clock_width, clock_height, s_deg)
            
        # Above hands          
        for svg_size, surface in self.above_hands:
            drawing_context.save()
            drawing_context.translate(-svg_size[0], -svg_size[1])
            drawing_context.set_source_surface(surface)
            drawing_context.paint()
            drawing_context.restore()
        
        # Paint to clock, centering it on the screen
        canvas.translate( ( width - height)  / 2, 0)
        canvas.set_source_surface(drawing_surface)
        canvas.paint()
        
        
    def draw_hand(self, drawing_context, hand_surfaces, width, height, deg):
        for svg_size, surface in hand_surfaces:
            drawing_context.save()
            drawing_context.translate(svg_size[0] / 2.0, svg_size[1] / 2.0)
            g15util.rotate(drawing_context, -90)
            g15util.rotate(drawing_context, deg)
            drawing_context.translate(-svg_size[0], -svg_size[1])
            drawing_context.set_source_surface(surface)
            drawing_context.paint()
            drawing_context.restore()