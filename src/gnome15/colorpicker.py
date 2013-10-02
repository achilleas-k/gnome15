#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2011 Brett Smith <tanktarta@blueyonder.co.uk>
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

import gtk
import cairo
from gtk import gdk
import gobject
import g15globals
import util.g15convert as g15convert
import os

COLORS_REDBLUE = [(0, 0, 0, 1), (255, 0, 0, 1), (255, 0, 255, 1), (0, 0, 255, 1)  ]
COLORS_FULL = [(0, 0, 0, 1), (255, 0, 0, 1), (0, 255, 0, 1), (0, 0, 255, 1), (255, 255, 0, 1), (0, 255, 255, 1), (255, 0, 255, 1), (255, 255, 255, 1)  ]
COLORS_NAMES = ["Black", "Red", "Green", "Blue", "Yellow", "Cyan", "Indigo", "White" ]

CELL_HEIGHT = 12
CELL_WIDTH = 24
            
def _get_color_at( buffer, x, y):
    x = int(x)
    y = int(y)
    data = buffer.get_data()
    w = buffer.get_width()
    s = ( buffer.get_stride() / w ) * ( w  * y + x )
    s = max(0, min(s, len(data) - 3))
    b = ord(data[s])
    g = ord(data[s + 1])  
    r = ord(data[s + 2])
    return (r, g, b)
        
def _rounded_rectangle(cr, x, y, w, h, r=20):
    cr.move_to(x+r,y)                      # Move to A
    cr.line_to(x+w-r,y)                    # Straight line to B
    cr.curve_to(x+w,y,x+w,y,x+w,y+r)       # Curve to C, Control points are both at Q
    cr.line_to(x+w,y+h-r)                  # Move to D
    cr.curve_to(x+w,y+h,x+w,y+h,x+w-r,y+h) # Curve to E
    cr.line_to(x+r,y+h)                    # Line to F
    cr.curve_to(x,y+h,x,y+h,x,y+h-r)       # Curve to G
    cr.line_to(x,y+r)                      # Line to H
    cr.curve_to(x,y,x,y,x+r,y)             # Curve to A

class ColorPreview(gtk.DrawingArea):

    def __init__(self, picker):              
        self.__gobject_init__()
        self.picker = picker
        super(ColorPreview, self).__init__()
        self.set_size_request(CELL_WIDTH, CELL_HEIGHT)
        self.connect("expose-event", self._expose)
        self.connect("button-press-event", self._button_press)
        self.down = False
        self.add_events(gdk.BUTTON1_MOTION_MASK | gdk.BUTTON_PRESS_MASK)
            
    def _show_redblue_picker(self, widget_tree):
        main_window = widget_tree.get_object("RBPicker")
        c_widget = widget_tree.get_object("RBImageEvents")
        img_surface = cairo.ImageSurface.create_from_png(os.path.join(g15globals.ui_dir, 'redblue.png'))
        
        r_adjustment = widget_tree.get_object("RAdjustment")
        r_adjustment.set_value(self.picker.color[0])
        b_adjustment = widget_tree.get_object("BAdjustment")
        b_adjustment.set_value(self.picker.color[2])
        self.adjusting_rb = False
        self.picker_down = False
        
        def _update_adj(c):
            self.picker._select_color((int(r_adjustment.get_value()), \
                                       0, int(b_adjustment.get_value())))
        
        def _set_color(c):
            r_adjustment.set_value(c[0])
            b_adjustment.set_value(c[2])
            
        def _button_release(widget, event):
            self.picker_down  = False
        
        def _button_press( widget, event):
            _set_color(_get_color_at(img_surface, event.x, event.y))
            self.picker_down  = True
    
        def _mouse_motion(widget, event):
            if self.picker_down:
                _set_color(_get_color_at(img_surface, event.x, event.y))
            
        r_adjustment.connect("value-changed", _update_adj)
        b_adjustment.connect("value-changed", _update_adj)
        c_widget.connect("button-press-event", _button_press)
        c_widget.connect("button-release-event", _button_release)
        c_widget.connect("motion-notify-event", _mouse_motion)
        c_widget.add_events(gdk.BUTTON1_MOTION_MASK | gdk.BUTTON_PRESS_MASK | gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK)
        
        main_window.set_transient_for(self.get_toplevel())
        main_window.run()            
        main_window.hide()
            
    def _show_picker(self, widget_tree):
        main_window = widget_tree.get_object("RGBPicker")
        c_widget = widget_tree.get_object("RGBColour")
        c_widget.set_current_color(g15convert.to_color(self.picker.color))
        def colour_picked(arg):
            self.picker._select_color(g15convert.color_to_rgb(c_widget.get_current_color()))
        c_widget.connect("color-changed", colour_picked)
        main_window.set_transient_for(self.get_toplevel())
        main_window.run()            
        main_window.hide()
        
    def _button_press(self, widget, event):
        widget_tree = gtk.Builder()
        widget_tree.set_translation_domain("colorpicker")
        widget_tree.add_from_file(os.path.join(g15globals.ui_dir, 'colorpicker.ui'))
        if self.picker.redblue:
            self._show_redblue_picker(widget_tree)
        else:
            self._show_picker(widget_tree)

    def _expose(self, widget, event):
        size = self.size_request()
        cell_height = self.allocation[3]
        cell_width = self.allocation[2]

        ctx = widget.window.cairo_create()
        ctx.set_line_width(1.0)
        
        # Draw to a back buffer so we can get the color at the point
        ctx.set_source_rgb(float(self.picker.color[0]) / 255.0, float(self.picker.color[1]) / 255.0, float(self.picker.color[2]) / 255.0)
        _rounded_rectangle(ctx, 0, 0, cell_width, cell_height, 16)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.set_source_rgb(0.5, 0.5, 0.5)        
        _rounded_rectangle(ctx, 0, 0, cell_width, cell_height, 16)
        ctx.stroke()     

class ColorBar(gtk.DrawingArea):

    def __init__(self, picker):        
        self.__gobject_init__()
        super(ColorBar, self).__init__()
        self.picker = picker
        self.set_size_request(len(self.picker.colors) * CELL_WIDTH, CELL_HEIGHT)
        self.connect("expose-event", self._expose)
        self.connect("button-press-event", self._button_press)
        self.connect("button-release-event", self._button_release)
        self.connect("motion-notify-event", self._mouse_motion)
        self.down = False
        self.add_events(gdk.BUTTON1_MOTION_MASK | gdk.BUTTON_PRESS_MASK | gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.picker_image_surface = None
    
    def _mouse_motion(self, widget, event):
        if self.picker_image_surface is not None and self.down:
            self.picker._select_color(_get_color_at(self.picker_image_surface, event.x, event.y))
        
    def _button_press(self, widget, event):
        if self.picker_image_surface is not None:
            self.picker._select_color(_get_color_at(self.picker_image_surface, event.x, event.y))
            self.down = True
    
    def _button_release(self, widget, event):
        self.down = False
        
    def _do_small_bar(self, ctx, cell_height, cell_width, c):
        ctx.set_source_rgb(float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0)
        ctx.rectangle(0, 0, cell_width, cell_height)
        ctx.fill()
        ctx.translate(cell_width, 0)
        
    def _do_bar(self, ctx, cell_height, cell_width, p, c):
        ctx.set_source_rgb(float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0)
        lg1 = cairo.LinearGradient(0.0, 0.0, cell_width, 0)
        lg1.add_color_stop_rgba(0.0, float(p[0]) / 255.0, float(p[1]) / 255.0, float(p[2]) / 255.0, float(p[3]))
        lg1.add_color_stop_rgba(0.5, float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0, float(c[3]))
        ctx.rectangle(0, 0, cell_width, cell_height)
        ctx.set_source(lg1)
        ctx.fill()
        ctx.translate(cell_width, 0)

    def _expose(self, widget, event):
        cr = widget.window.cairo_create()
        cr.set_line_width(1.0)
        size = (self.allocation[2],self.allocation[3])
        cell_height = size[1]
        tc = len(self.picker.colors)
        cell_width = size[0] / tc
        main_width = cell_width * tc 
        
        # Draw to a back buffer so we can get the color at the point
        picker_image_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size[0], size[1])
        ctx = cairo.Context(picker_image_surface)
        ctx.save()
        ctx.translate(1, 1)
        colors = self.picker.colors
        lc = colors[0]
        self._do_small_bar(ctx, cell_height, cell_width, lc)  
        for i in range(0, len(colors) - 1):
            c = colors[i]
            self._do_bar(ctx, cell_height, cell_width, c, colors[i + 1])
        self._do_small_bar(ctx, cell_height, cell_width / 2, lc)  
        ctx.restore()
        _rounded_rectangle(ctx, 0, 0, main_width, cell_height, 16)
        ctx.set_operator(cairo.OPERATOR_DEST_IN)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.set_source_rgb(0.5, 0.5, 0.5)        
        _rounded_rectangle(ctx, 0, 0, main_width, cell_height, 16)
        ctx.stroke()
            
        # Paint
        cr.set_source_surface(picker_image_surface)
        cr.paint()
        self.picker_image_surface = picker_image_surface
    
class ColorPicker(gtk.HBox):

    def __init__(self, colors = None, redblue = False):
        self.__gobject_init__()
        gtk.HBox.__init__(self, spacing = 8)
        self.colors = colors if colors is not None else ( COLORS_REDBLUE if redblue else COLORS_FULL )
        self.redblue = redblue
        self.color = (0,0,0)
        super(ColorPicker, self).__init__()
        
        bar = ColorBar(self)
        preview = ColorPreview(self)
        
        self.pack_start(bar, True, True)
        self.pack_start(preview, False, True)
        
    def set_color(self, color):
        self.color = color
        self.queue_draw()
        
    def _select_color(self, color):
        self.color = color
        self.queue_draw()
        self.emit("color-chosen")

gobject.type_register(ColorPicker)
gobject.type_register(ColorBar)
gobject.type_register(ColorPreview)
gobject.signal_new("color-chosen", ColorPicker, gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, ())