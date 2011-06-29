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
 
import pango
import pangocairo
import cairo

# Shared pango context
pango_context = pangocairo.cairo_font_map_get_default().create_context()
 
"""
Handles drawing and measuring of text on a screen. 
"""


def new_text(screen = None):
    """
    Create a new text handler. This should be used rather than directly constructing
    the G15PangoText
    """
    if screen:
        return G15PangoText(screen.driver.get_antialias())
    else:
        return G15PangoText(True)

class G15Text():
    
    def __init__(self, antialias):
        self.antialias = antialias
        
    def set_attributes(self, text, bounds = None, wrap = None, align = None, width = None, spacing = None, \
            font_desc = None, font_absolute_size = None):
        self.text = text
        self.bounds = bounds
        
    def measure(self):
        raise Exception("Not implemented")
        
    def draw(self, x, y, clip = None):
        raise Exception("Not implemented")
    
    def set_canvas(self, canvas):
        self.canvas = canvas
    
    """
    Private
    """
    def _create_font_options(self):        
        fo = cairo.FontOptions()
        fo.set_antialias(self.antialias)
        if self.antialias == cairo.ANTIALIAS_NONE:
            fo.set_hint_style(cairo.HINT_STYLE_NONE)
            fo.set_hint_metrics(cairo.HINT_METRICS_OFF)            
    
class G15PangoText(G15Text):
    
    def __init__(self, antialias):
        G15Text.__init__(self, antialias)
        pangocairo.context_set_font_options(pango_context, self._create_font_options())   
        self.pango_cairo_context = None
        self.layout = None
        
    def set_canvas(self, canvas):           
        G15Text.set_canvas(self, canvas)
        
        self.pango_cairo_context = pangocairo.CairoContext(self.canvas)
        self.layout = pango.Layout(pango_context)
        
    def set_attributes(self, text, bounds = None, wrap = None, align = pango.ALIGN_LEFT, width = None, spacing = None, \
            font_desc = None, font_absolute_size = None, attributes = None,
            weight = None, style = None, font_pt_size = None):
        G15Text.set_attributes(self, text, bounds, wrap, align, width, spacing, font_desc, font_absolute_size)  
            
        font_desc_name = "Sans" if font_desc == None else font_desc
        if weight:
            font_desc_name += " %s" % weight
        if style:
            font_desc_name += " %s" % style
        if font_pt_size:
            font_desc_name += " " + str(font_pt_size)
        font_desc = pango.FontDescription(font_desc_name)
        print "Setting font to %s" % font_desc
        if font_absolute_size is not None:
            font_desc.set_absolute_size(font_absolute_size)
        self.layout.set_font_description(font_desc)        
        
        if align != None:
            self.layout.set_alignment(align)
        if spacing != None:
            self.layout.set_spacing(spacing)
        if width != None:
            self.layout.set_width(width)
        if wrap:
            self.layout.set_wrap(wrap)
        if attributes:
            self.layout.set_attributes(attributes)
            
        self.layout.set_text(text)
        self.metrics = pango_context.get_metrics(self.layout.get_font_description())
        
    def measure(self):
        text_extents = self.layout.get_extents()[1]
        return text_extents[0] / pango.SCALE, text_extents[1] / pango.SCALE, text_extents[2] / pango.SCALE, text_extents[3] / pango.SCALE
    
    def draw(self, x, y):
        self.pango_cairo_context.save()
        if self.bounds:
            self.pango_cairo_context.rectangle(self.bounds[0] - 1, self.bounds[1] - 1, self.bounds[2] + 2, self.bounds[3] + 2)
            self.pango_cairo_context.clip()
            
        
        # Can only align text when they are bounds within which to align it
        if self.bounds is not None:
            y = y - ( self.metrics.get_ascent()  / 1000.0 )
            if self.layout.get_alignment() == pango.ALIGN_CENTER:
                x = x - ( self.bounds[2] / 2 )
            elif self.layout.get_alignment() == pango.ALIGN_RIGHT:
                x = x - ( self.bounds[2] )
        
        self.pango_cairo_context.move_to(x, y)
        self.pango_cairo_context.show_layout(self.layout)
        self.pango_cairo_context.restore()