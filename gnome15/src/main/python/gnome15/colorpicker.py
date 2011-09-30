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
 

import gtk
import cairo
from gtk import gdk
import gobject


COLORS_REDBLUE = [(0, 0, 0, 1), (0, 0, 0, 1), (255, 0, 0, 1),  (255, 0, 0, 1), (255, 0, 255, 1), (255, 0, 255, 1), (0, 0, 255, 1),  (0, 0, 255, 1)  ]
COLORS_FULL = [(0, 0, 0, 1), (0, 0, 0, 1), (255, 0, 0, 1), (0, 255, 0, 1), (0, 0, 255, 1), (255, 255, 0, 1), (0, 255, 255, 1), (255, 0, 255, 1), (255, 255, 255, 1), (255, 255, 255, 1)  ]

CELL_HEIGHT = 16
CELL_WIDTH = 24 

class ColorPicker(gtk.DrawingArea):

    def __init__(self, colors = None):        
        self.__gobject_init__()
        self.colors = colors if colors is not None else COLORS_FULL
        super(ColorPicker, self).__init__()
        self.set_size_request(len(self.colors) * CELL_WIDTH, CELL_HEIGHT)
        self.connect("expose-event", self._expose)
        self.connect("button-press-event", self._button_press)
        self.connect("button-release-event", self._button_release)
        self.connect("motion-notify-event", self._mouse_motion)
        self.down = False
        self.add_events(gdk.BUTTON1_MOTION_MASK | gdk.BUTTON_PRESS_MASK | gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.color = (0, 0, 0)
        self.buffer = None
    
    def _mouse_motion(self, widget, event):
        if self.buffer is not None and self.down:
            self.color = self._get_color_at(event.x, event.y)
            self.emit("color-chosen")
            
    def _get_color_at(self, x, y):
        x = int(x)
        y = int(y)
        data = self.buffer.get_data()
        w = self.buffer.get_width()
        s = ( self.buffer.get_stride() / w ) * ( w  * y + x )
        s = max(0, min(s, len(data) - 3))
        b = ord(data[s])
        g = ord(data[s + 1])  
        r = ord(data[s + 2])
        return (r, g, b)
        
    def _button_press(self, widget, event):
        if self.buffer is not None:
            self.color = self._get_color_at(event.x, event.y)
            self.emit("color-chosen")
            self.down = True
    
    def _button_release(self, widget, event):
        self.down = False

    def _expose(self, widget, event):
        cr = widget.window.cairo_create()
        cr.set_line_width(1.0)
        size = self.size_request()
        cell_height = size[1]
        cell_width = size[0] / len(self.colors)
        
        # Draw to a back buffer so we can get the color at the point
        buffer = cairo.ImageSurface(cairo.FORMAT_ARGB32, size[0], size[1])
        ctx = cairo.Context(buffer)
        ctx.save()
        ctx.translate(1, 1)
        for i in range(1, len(self.colors)):
            c = self.colors[i]
            p = self.colors[i - 1] if i > 0 else c
            ctx.set_source_rgb(float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0)
            lg1 = cairo.LinearGradient(0.0, 0.0, cell_width, 0)
            lg1.add_color_stop_rgba(0.0, float(p[0]) / 255.0, float(p[1]) / 255.0, float(p[2]) / 255.0, float(p[3]))
            lg1.add_color_stop_rgba(0.6, float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0, float(c[3]))
            ctx.rectangle(0, 0, cell_width, cell_height)
            ctx.set_source(lg1)
            ctx.fill()
            ctx.translate(cell_width, 0)
        ctx.restore()
        
        self._rounded_rectangle(ctx, 0, 0, size[0] - 24, cell_height, 16)
        ctx.set_operator(cairo.OPERATOR_DEST_IN)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.set_source_rgb(0.5, 0.5, 0.5)
        self._rounded_rectangle(ctx, 0, 0, size[0] - 24, size[1], 16)
        ctx.set_line_width(1.0)
        ctx.stroke()
            
        # Paint
        cr.set_source_surface(buffer)
        cr.paint()
        self.buffer = buffer    
        
    def _rounded_rectangle(self, cr, x, y, w, h, r=20):
        cr.move_to(x+r,y)                      # Move to A
        cr.line_to(x+w-r,y)                    # Straight line to B
        cr.curve_to(x+w,y,x+w,y,x+w,y+r)       # Curve to C, Control points are both at Q
        cr.line_to(x+w,y+h-r)                  # Move to D
        cr.curve_to(x+w,y+h,x+w,y+h,x+w-r,y+h) # Curve to E
        cr.line_to(x+r,y+h)                    # Line to F
        cr.curve_to(x,y+h,x,y+h,x,y+h-r)       # Curve to G
        cr.line_to(x,y+r)                      # Line to H
        cr.curve_to(x,y,x,y,x+r,y)             # Curve to A
    


gobject.type_register(ColorPicker)
gobject.signal_new("color-chosen", ColorPicker, gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE, ())