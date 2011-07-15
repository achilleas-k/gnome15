#!/usr/bin/python
# -*- coding: utf-8 -*-

# ZetCode PyGTK tutorial 
#
# This example creates a burning
# custom widget
#
# author: Jan Bodnar
# website: zetcode.com 
# last edited: April 2011


import gtk
import cairo
from gtk import gdk
import g15util
import gobject

COLORS = [(0, 0, 0, 1), (0, 0, 0, 1), (255, 0, 0, 1), (0, 255, 0, 1), (0, 0, 255, 1), (255, 255, 0, 1), (0, 255, 255, 1), (255, 0, 255, 1), (255, 255, 255, 1), (255, 255, 255, 1)  ]
CELL_HEIGHT = 16
CELL_WIDTH = 24

class ColorPicker(gtk.DrawingArea):

    def __init__(self):        
        self.__gobject_init__()
        super(ColorPicker, self).__init__()
        self.set_size_request(len(COLORS) * CELL_WIDTH, CELL_HEIGHT)
        self.connect("expose-event", self.expose)
        self.connect("button-press-event", self._button_press)
        self.connect("button-release-event", self._button_release)
        self.connect("motion-notify-event", self._mouse_motion)
        self.pixbuf = None
        self.down = False
        self.add_events(gdk.BUTTON1_MOTION_MASK | gdk.BUTTON_PRESS_MASK | gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.color = (0, 0, 0)
    
    def _mouse_motion(self, widget, event):
        if self.pixbuf is not None and self.down:
            r,g,b,a = self.pixbuf.subpixbuf(int(event.x), int(event.y), 1, 1).get_pixels_array()[0][0]
            self.color = (r, g, b)
            self.emit("color-chosen")
        
    def _button_press(self, widget, event):
        if self.pixbuf is not None:
            r,g,b,a = self.pixbuf.subpixbuf(int(event.x), int(event.y), 1, 1).get_pixels_array()[0][0]
            self.color = (r, g, b)
            self.emit("color-chosen")
            self.down = True
    
    def _button_release(self, widget, event):
        print "Release"
        self.down = False

    def expose(self, widget, event):
        cr = widget.window.cairo_create()
        cr.set_line_width(1.0)
        size = self.size_request()
        cell_height = size[1]
        cell_width = size[0] / len(COLORS)
        
        # Draw to a back buffer so we can get the color at the point
        buffer = cairo.ImageSurface(cairo.FORMAT_ARGB32, size[0], size[1])
        ctx = cairo.Context(buffer)
        ctx.save()
        ctx.translate(1, 1)
        for i in range(1, len(COLORS)):
            c = COLORS[i]
            p = COLORS[i - 1] if i > 0 else c
            ctx.set_source_rgb(float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0)
            lg1 = cairo.LinearGradient(0.0, 0.0, cell_width, 0)
            lg1.add_color_stop_rgba(0.0, float(p[0]) / 255.0, float(p[1]) / 255.0, float(p[2]) / 255.0, float(p[3]))
            lg1.add_color_stop_rgba(0.6, float(c[0]) / 255.0, float(c[1]) / 255.0, float(c[2]) / 255.0, float(c[3]))
            ctx.rectangle(0, 0, cell_width, cell_height)
            ctx.set_source(lg1)
            ctx.fill()
            ctx.translate(cell_width, 0)
        ctx.restore()
        
        self.rounded_rectangle(ctx, 0, 0, size[0] - 24, cell_height, 16)
        ctx.set_operator(cairo.OPERATOR_DEST_IN)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.set_source_rgb(0.5, 0.5, 0.5)
        self.rounded_rectangle(ctx, 0, 0, size[0] - 24, size[1], 16)
        ctx.set_line_width(1.0)
        ctx.stroke()
            
        # Paint and get the pixbuf
        cr.set_source_surface(buffer)
        cr.paint()
        self.pixbuf = g15util.surface_to_pixbuf(buffer)    
        
    def rounded_rectangle(self, cr, x, y, w, h, r=20):
        # This is just one of the samples from 
        # http://www.cairographics.org/cookbook/roundedrectangles/
        #   A****BQ
        #  H      C
        #  *      *
        #  G      D
        #   F****E
    
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