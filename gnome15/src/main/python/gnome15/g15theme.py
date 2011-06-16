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
 
import os
import cairo
import rsvg
import math
import sys
import traceback
import pango
import pangocairo
import g15driver
import g15globals
import g15screen
import g15util
import xml.sax.saxutils as saxutils
import base64
import dbusmenu
import logging
import time
logger = logging.getLogger("theme")
from string import Template
from copy import deepcopy
from cStringIO import StringIO
from lxml import etree
from threading import RLock

BASE_PX=18.0

# The color in SVG theme files that by default gets replaced with the current 'highlight' color
DEFAULT_HIGHLIGHT_COLOR="#ff0000"
            
class Render():
    def __init__(self, document, properties, text_boxes, attributes, processing_result):
        self.document = document
        self.properties = properties
        self.text_boxes = text_boxes
        self.attributes = attributes
        self.processing_result = processing_result
        
class ScrollState():
    
    def __init__(self):
        self.range = (0.0, 0.0)
        self.adjust = 0.0
        self.reversed = True
        self.step = 1.0
        self.alignment = pango.ALIGN_LEFT
        self.val = 0
        self.original = 0
        
    def next(self):
        self.adjust += -self.step if self.reversed else self.step
        if self.adjust < self.range[0]:
            self.reversed = False
            self.adjust = self.range[0]
        elif self.adjust > self.range[1]:
            self.adjust = self.range[1]
            self.reversed = True
        self.val = self.adjust + self.original
        self.transform_elements()
            
class HorizontalScrollState(ScrollState):
    
    def __init__(self, element = None):
        ScrollState.__init__(self)
        self.element = element     
        self.other_elements = []
            
    def transform_elements(self):
        self.element.set("x", str(self.val))
        for e in self.other_elements:
            e.set("x", str(self.val))
                
class VerticalWrapScrollState(ScrollState):
    def __init__(self, text_box):
        ScrollState.__init__(self)
        self.text_box = text_box
            
    def transform_elements(self):
        self.text_box.base = self.val

class TextBox():
    def __init__(self):
        self.bounds = ( )
        self.text = "" 
        self.css = { }
        self.transforms = []
        self.base = 0
        
class LayoutManager():
    def __init__(self):
        pass
    
    def layout(self, parent):
        raise Exception("Not implemeted")
    
class GridLayoutManager(LayoutManager):

    def __init__(self, columns, rows = -1):
        self.rows = rows
        self.columns = columns 
    
    def layout(self, parent):
        x = 0
        y = 0
        col = 0
        row_height = 0
        for c in parent.get_children():
            bounds = c.view_bounds
            c.view_bounds = ( x, y, bounds[2], bounds[3])
            x += bounds[2]
            row_height = max(row_height, bounds[3])
            col += 1
            if col >= self.columns:
                x = 0
                y += row_height
                row_height = 0
                col = 0

        
class Component():
        
    def __init__(self, id):
        self.id = id
        self.theme = None
        self.children = []
        self.child_map = {}
        self.parent = None
        self.screen = None
        self.theme_properties = {}    
        self.theme_attributes = {}
        self.theme_properties_callback = None    
        self.theme_attributes_callback = None
        self.view_bounds = None
        self.view_element = None
        self.layout_manager = None
        self.base = 0
        self.focusable = False
        self._tree_lock = RLock()
        self.do_clip = False
        self.allow_scrolling = None
        
    def get_tree_lock(self):
#        if self.parent == None:
#            return self._tree_lock
#        else:
#            return self.parent.get_tree_lock()
        return self._tree_lock
        
    def is_focused(self):
        return self.get_root().focused == self
        
    def set_focused(self, focused):
        if not self.focusable:
            raise Exception("%s is not focusable" % self.id)
        self.get_root().set_focused_component(self)
        
    def set_theme(self, theme):
        self.theme = theme
        theme._set_component(self)
        self.view_bounds = theme.bounds
        
    def mark_dirty(self):
        if self.theme is not None:
            self.theme.mark_dirty()
        for c in self.get_children():
            c.mark_dirty()
        
    def get_allow_scrolling(self):
        c = self
        while c is not None:
            if c.allow_scrolling is not None:
                return c.allow_scrolling
            c = c.parent
        return True
    
    def do_scroll(self):
        for c in self.children:
            c.do_scroll()
        if self.theme and self.get_allow_scrolling():
            self.theme.do_scroll()
    
    def check_for_scroll(self):
        scroll = False
        for c in self.children:
            if c.check_for_scroll():
                scroll = True
        if self.theme and self.get_allow_scrolling() and self.theme.is_scroll_required():
            scroll = True
        return scroll
        
    def get_theme(self):
        c = self
        while c is not None:
            if c.theme:
                return c.theme
            c = c.parent
            
    def get_screen(self):
        c = self
        while c is not None:
            if c.screen:
                return c.screen
            c = c.parent
        
    def get_root(self):
        c = self
        r = None        
        while c is not None:
            r = c
            c = c.parent
        return r
    
    def index_of_child(self, child):
        return self.children.index(child)
        
    def get_child(self, index):
        return self.children[index]
        
    def contains_child(self, child):
        return child in self.children
        
    def get_child_count(self):
        return len(self.children)
        
    def set_children(self, children):
        self.get_tree_lock().acquire()
        try:
            self.remove_all_children()
            for c in children:
                self.add_child(c)
        finally:
            self.get_tree_lock().release()
        
    def get_children(self):
        return list(self.children)
        
    def add_child(self, child, index = -1):
        self.get_tree_lock().acquire()
        try:
            if child.parent:
                raise Exception("Child %s already has a parent. Remove it from it's last parent first before adding to %s." % (child.id, self.id))
            if child.id in self.child_map:
                raise Exception("Child with ID of %s already exists in component %s." % (child.id, self.id))
                
            self._check_has_parent()
            child.configure(self)
            self.child_map[child.id] = child
            if index == -1:
                self.children.append(child)
            else:
                self.children.insert(index, child)
            self.notify_add(child)
        finally:
            self.get_tree_lock().release()
        
    def remove_all_children(self):
        self.get_tree_lock().acquire()
        try:
            for c in list(self.children):
                self.remove_child(c)
        finally:
            self.get_tree_lock().release()
                    
    def remove_child(self, child):
        self.get_tree_lock().acquire()
        try:
            if not child in self.children:
                raise Exception("Not a child of this component.")
            if child.theme:
                child.theme._component_removed()
            child.parent = None
            del self.child_map[child.id]
            self.children.remove(child)
        finally:
            self.get_tree_lock().release()
        
    def remove_from_parent(self):
        if not self.parent:
            raise Exception("Not added to a parent.")
        self.parent.remove(self)
        
    def configure(self, parent):
        self.parent = parent        
        self.view_element = self.get_theme().get_element(self.id)
        self.view_bounds  = g15util.get_actual_bounds(self.view_element) if self.view_element is not None else None
        self.on_configure()
                
    def on_configure(self):
        pass
    
    def get_default_theme_dir(self):
        return os.path.join(g15globals.themes_dir, "default")
    
    def draw(self, element, theme):
        """
        Called by the theme for the component to adjust the SVG document ID if required
        """
        pass
    
    def paint_theme(self, canvas, properties, attributes):
        """
        Paint the theme. Do not call directly, instead call paint()
        """        
        self.theme.draw(canvas, properties, self.get_theme_attributes())
    
    def paint(self, canvas):
        self.get_tree_lock().acquire()
        try:
            canvas.save()    
            
            # Translate to the components bounds and clip to the size of the view     
            if self.view_bounds:
                canvas.translate(self.view_bounds[0], self.view_bounds[1])
                canvas.rectangle(0, 0, self.view_bounds[2], self.view_bounds[3])
                canvas.clip()
                
            # Translate against the base, this allows components to be scrolled within their viewport
            canvas.translate(0, -self.base)
                        
            # Draw any theme for this component
            if self.theme:
                canvas.save()   
                properties = self.get_theme_properties()
                if self.get_root().focused_component is not None:
                    properties['%s_focused' % self.get_root().focused_component.id ] = "true"
                self.paint_theme(canvas, properties, self.get_theme_attributes())
                canvas.restore()
                
            # Layout any children
            if self.layout_manager != None:
                self.layout_manager.layout(self)
                
            # Paint children
            for c in self.children:
                canvas.save()
                if not self.do_clip or c.view_bounds is None or self.overlaps(self.view_bounds, c.view_bounds):
                    c.paint(canvas)
    #            else:
    #                print "Skipping painting %s because it is not in view -  %s   - %s" % ( c.id, str(self.view_bounds), str(c.view_bounds))
                canvas.restore()
            
            canvas.restore()
        finally:
            self.get_tree_lock().release()
        
    def overlaps(self, bounds1, bounds2):
        return bounds2[1] >= ( self.base - bounds2[3] ) and bounds2[1] < ( self.base + bounds1[3] )
            
    def get_theme_properties(self):
        p = None
        if self.theme_properties_callback is not None:
            p = self.theme_properties_callback()
        if p is None:
            p = self.theme_properties
        return p
            
    def get_theme_attributes(self):
        p = None
        if self.theme_attributes_callback is not None:
            p = self.theme_attributes_callback()
        if p is None:
            p = self.theme_attributes
        return p
    
    def notify_add(self, component):
        if self.parent:
            self.parent.notify_add(component)        
    
    '''
    Private
    '''
    def _check_has_parent(self):
#        if not self.parent:
#            raise Exception("%s must be added to a parent before children can be added to it." % self.id)
        pass
        

class G15Page(Component):
    def __init__(self, id, screen, painter = None, priority = g15screen.PRI_NORMAL, on_shown=None, on_hidden=None, on_deleted=None, \
                 thumbnail_painter = None, panel_painter = None, theme_properties_callback = None, \
                 theme_attributes_callback = None, theme = None, title = None):
        Component.__init__(self, id)
        self.title = title if title else self.id
        self.time = time.time()
        self.thumbnail_painter = thumbnail_painter
        self.panel_painter = panel_painter
        self.on_shown = on_shown
        self.on_hidden = on_hidden
        self.on_deleted = on_deleted
        self.priority = priority
        self.value = self.priority * self.time
        self.painter = painter
        self.cairo = cairo
        self.theme_scroll_timer = None
        self.opacity = 0
        self.key_handlers = []
        self.properties = {}
        self.attributes = {}
        self.back_buffer = None
        self.buffer = None
        self.back_context = None
        self.font_size = 12.0
        self.font_family = "Sans"
        self.font_style = "normal"
        self.font_weight = "normal"
        self.on_shown_listeners = []
        self.on_hidden_listeners = []
        self.on_deleted_listeners = []
        self.theme_properties_callback = theme_properties_callback    
        self.theme_attributes_callback = theme_attributes_callback
        self.screen = screen
        self.focused_component = None
        if theme:
            self.set_theme(theme)
            
    def set_focused_component(self, focused_component, redraw = True):
        self.focused_component = focused_component
        if redraw:
            self.redraw()
    
    def notify_add(self, component):
        Component.notify_add(self, component)
        if not self.focused_component and component.focusable:
            self.next_focus(False)  
            
    def redraw(self):
        screen = self.get_screen()
        if screen:
            screen.redraw(self)
            
    def next_focus(self, redraw = True):
        focus_list = self._add_to_focus_list(self, [])
        if len(focus_list) == 0:
            self.focused_component = None
            return

        if self.focused_component and self.focused_component in focus_list:
            i = focus_list.index(self.focused)
            i += 1
            if i >= len(focus_list):
                i = 0
            self.focused_component = focus_list[i]
        else:
            self.focused_component = focus_list[0]
        self.mark_dirty()
        if redraw:
            self.redraw()   
        
    def _add_to_focus_list(self, component, focus_list = []):
        if component.focusable:
            focus_list.append(component)
        for c in component.get_children():
            self._add_to_focus_list(c, focus_list)
        return focus_list
            
    def is_visible(self):
        screen = self.get_screen()
        return screen and screen.get_visible_page() == self
        
    def set_title(self, title):
        self.title = title
        screen = self.get_screen()
        if screen and screen.get_page(self.id) is not None:
            for l in screen.screen_change_listeners:
                l.title_changed(self, title)
        
    def set_priority(self, priority):
        screen = self.get_screen()
        if not screen:
            raise Exception("Cannot set priority, not added to screen")
        screen.set_priority(self, priority)
        
    def set_time(self, time):
        self.time = time
        self.value = self.priority * self.time
        
    def get_val(self):
        return self.time * self.priority
    
    def new_surface(self):
        screen = self.get_screen()
        if not screen:
            raise Exception("Cannot create new surface, not added to screen")
        sw = screen.driver.get_size()[0]
        sh = screen.driver.get_size()[1]
        self.back_buffer = cairo.ImageSurface (cairo.FORMAT_ARGB32,sw, sh)
        self.back_context = cairo.Context(self.back_buffer)
        self.set_line_width(1.0)
        
        rgb = screen.driver.get_color(g15driver.HINT_FOREGROUND, ( 0, 0, 0 ))
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
        if self.painter != None:
            self.painter(canvas)
            
        Component.paint(self, canvas)
            
        # Paint the canvas
        if self.buffer != None:
            canvas.save()
            canvas.set_source_surface(self.buffer)
            canvas.paint()
            canvas.restore()
            
        # Check the theme tree to see if anything needs scrolling
        self.check_scroll_and_reschedule()
            
    def check_scroll_and_reschedule(self):
        scroll = self.check_for_scroll()
        if scroll and self.theme_scroll_timer == None:
            self.theme_scroll_timer = g15util.schedule("ScrollRedraw", self.screen.service.scroll_delay, self.scroll_and_reschedule)
        elif not scroll and self.theme_scroll_timer != None:
            self.theme_scroll_timer.cancel()
    
    def scroll_and_reschedule(self):
        self.do_scroll()
        self.theme_scroll_timer = None
        self.redraw()
            
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
        driver = self.get_screen().driver
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
        
    """
    Private
    """
        
    def _do_on_shown(self):
        for l in self.on_shown_listeners:
            l()
        if self.on_shown:
            self.on_shown()
        
    def _do_on_hidden(self):
        for l in self.on_hidden_listeners:
            l()
        if self.on_hidden:
            self.on_hidden()
        
    def _do_on_deleted(self):
        if self.theme:
            self.theme._component_removed()
        for l in self.on_deleted_listeners:
            l()
        if self.on_deleted:
            self.on_deleted()
        
    def _check_has_parent(self):
        # Theme is the root, needs no parent
        pass
        
    def _do_set_priority(self, priority):
        self.priority = priority
        self.value = self.priority * self.time

class Scrollbar(Component):
    
    def __init__(self, id, values_callback):
        Component.__init__(self, id)
        self.values_callback = values_callback
        
    def on_configure(self):
        pass
        
    def draw(self, theme, element):
        max_s, view_size, position = self.values_callback()
        knob = element.xpath('//svg:*[@class=\'knob\']',namespaces=theme.nsmap)[0]
        track = element.xpath('//svg:*[@class=\'track\']',namespaces=theme.nsmap)[0]
        track_bounds = g15util.get_bounds(track)
        knob_bounds = g15util.get_bounds(knob)
        scale = max(1.0, max_s / view_size)
        knob.set("y", str( int( knob_bounds[1] + ( position / max(scale, 0.01) ) ) ) )
        knob.set("height", str(int(track_bounds[3] / max(scale, 0.01) )))
        
class Menu(Component):
    def __init__(self, id):
        Component.__init__(self, id)
        self.selected = None
        self.on_selected = None
        self.on_move = None
        self.i = 0
        self.do_clip = True
        self.layout_manager = GridLayoutManager(1)
        self.scroll_timer = None
        
    def add_separator(self):
        self.add_child(MenuSeparator())
        
    def sort(self):
        pass
        
    def on_configure(self):    
        if self.view_element == None:
            raise Exception("No element in SVG with ID of %s. Required for Menu component" % self.id)    
        menu_theme = self.load_theme()
        if menu_theme:
            self.set_theme(menu_theme)
          
    def load_theme(self):
        pass
        
    def get_scroll_values(self):
        max_val = 0
        for item in self.get_children():
            max_val += self.get_item_height(item, True)
        return max(max_val, self.view_bounds[3]), self.view_bounds[3], self.base
        
    def get_item_height(self, item, group = False):
        return item.theme.bounds[3]
    
    def paint(self, canvas):   
        self.get_tree_lock().acquire()
        try:    
            self.select_first()                 
            
            # Get the Y position of the selected item
            y = 0 
            selected_y = -1
            for item in self.get_children():
                ih = self.get_item_height(item, True)
                if item == self.selected:
                    selected_y = y
                y += ih
                    
            new_base = self.base
                    
            # How much vertical space there is
            v_space = self.view_bounds[3]
                
            # If the position of the selected item is offscreen below, change the offset so it is just visible
            if self.selected != None:
                ih = self.get_item_height(self.selected, True)
                if selected_y >= new_base + v_space - ih:
                    new_base = ( selected_y + ih ) - v_space
                # If the position of the selected item is offscreen above base, change the offset so it is just visible
                elif selected_y < new_base:
                    new_base = selected_y
                    
            if new_base != self.base:
                # Stop all of the children from scrolling horizontally while we scroll vertically
                if new_base < self.base:
                    self.base -= max(1, int(( self.base - new_base ) / 3))
                else:
                    self.base += max(1, int(( new_base - self.base ) / 3))
                self.get_root().mark_dirty()
                if self.scroll_timer is not None:
                    self.scroll_timer.cancel()
                self.scroll_timer = g15util.schedule("ScrollTo", self.get_screen().service.animation_delay, self.get_root().redraw)
            
            Component.paint(self, canvas)
        finally:
            self.get_tree_lock().release()
        
    def get_items_per_page(self):
        self.get_tree_lock().acquire()
        try:
            total_size = 0
            for item in self.get_children():
                total_size += self.get_item_height(item, True)            
            avg_size = total_size / self.get_child_count()
            return int(self.view_bounds[3] / avg_size)
        finally:
            self.get_tree_lock().release()
        
    def handle_key(self, keys, state, post):   
        self.select_first()   
        if not post and state == g15driver.KEY_STATE_DOWN:                
            if g15driver.G_KEY_UP in keys:
                self._move_up(1)
                return True
            elif g15driver.G_KEY_DOWN in keys or g15driver.G_KEY_L4 in keys:
                self._move_down(1)
                return True                              
            elif g15driver.G_KEY_RIGHT in keys:
                self._move_down(self.get_items_per_page())
                return True        
            elif g15driver.G_KEY_LEFT in keys:
                self._move_up(self.get_items_per_page())
                return True        
            elif g15driver.G_KEY_OK in keys or g15driver.G_KEY_L5 in keys:
                if self.selected and self.selected.activate():
                    return True
    
                
        return False
        
    def select_first(self):
        self.get_tree_lock().acquire()
        try:
            if not self.selected == None and not self.contains_child(self.selected):
                self.selected = None
            if self.selected == None:
                if self.get_child_count():
                    self.selected  = self.get_child(0)
                else:
                    self.selected = None
        finally:
            self.get_tree_lock().release()
    
    '''
    Private
    '''
    
    def _check_selected(self):
        self.get_tree_lock().acquire()
        try:
            if not self.selected in self.get_children():
                if self.i >= self.get_child_count():
                    return
                self.selected = self.get_child(self.i)
        finally:
            self.get_tree_lock().release()
            
    
    def _do_selected(self):
        old_selected = self.selected
        self.selected = self.get_child(self.i)
        if self.on_selected:
            self.on_selected()
        self.selected.mark_dirty()
        if old_selected:
            old_selected.mark_dirty()
        self.get_root().redraw()
        
    def _move_up(self, amount = 1):
        self.get_tree_lock().acquire()
        try:
            if self.get_child_count() == 0:
                return
            if self.on_move:
                self.on_move()
            self._check_selected()
            if not self.selected in self.get_children():
                self.i = 0
            else:
                self.i = self.index_of_child(self.selected)
                
            items = self.get_child_count()
            try:
                if self.i == 0:
                    self.i = items - 1
                    return    
                for a in range(0, abs(amount), 1):
                    while True:
                        self.i -= 1 
                        if self.i < 0:
                            if a == 0:
                                self.i = items - 1
                            else:
                                self.i = 0
                                return
                        if not isinstance(self.get_child(self.i), MenuSeparator):
                            break
            finally:
                self._do_selected()
        finally:
            self.get_tree_lock().release()
            
    def _move_down(self, amount = 1):
        self.get_tree_lock().acquire()
        try:
            if self.get_child_count() == 0:
                return
            if self.on_move:
                self.on_move()
            self._check_selected()
            if not self.selected in self.get_children():
                self.i = 0
            else:
                self.i = self.index_of_child(self.selected)
                
            items = self.get_child_count()
            try:
                if self.i == items - 1:
                    self.i = 0
                    return            
                for a in range(0, abs(amount), 1):
                    while True:
                        self.i += 1
                        if self.i == items:
                            if a == 0:
                                self.i = 0
                            else:
                                self.i = items - 1
                                return
                        if not isinstance(self.get_child(self.i), MenuSeparator):
                            break
            finally:
                self._do_selected()
        finally:
            self.get_tree_lock().release()
        
class MenuItem(Component):
    def __init__(self, id="menu-entry", group = True):
        Component.__init__(self, id)
        self.group = group
        
    def on_configure(self):
        self.set_theme(G15Theme(self.parent.get_theme().dir, "menu-entry" if self.group else "menu-child-entry"))
        
    def get_theme_properties(self):     
        return {
            "item_selected" : self.parent is not None and self == self.parent.selected
                           }
        
    def get_allow_scrolling(self):
        self.get_tree_lock().acquire()
        try:
            return self.parent is not None and self == self.parent.selected
        finally:
            self.get_tree_lock().release()
        
    def activate(self):
        return False
        
class MenuSeparator(MenuItem):
    def __init__(self, id = "menu-separator"):
        MenuItem.__init__(self, id)
        
    def on_configure(self):
        self.set_theme(G15Theme(self.parent.get_theme().dir, "menu-separator"))
    
class DBusMenuItem(MenuItem):
    def __init__(self, id, dbus_menu_entry):
        MenuItem.__init__(self, id)
        self.dbus_menu_entry = dbus_menu_entry
        
    def activate(self):
        self.dbus_menu_entry.activate()
        
    def get_theme_properties(self):
        properties = MenuItem.get_theme_properties(self)
        properties["item_name"] = self.dbus_menu_entry.get_label() 
        properties["item_type"] = self.dbus_menu_entry.type
        properties["item_alt"] = self.dbus_menu_entry.get_alt_label()
        icon_name = self.dbus_menu_entry.get_icon_name()
        if icon_name != None:
            properties["item_icon"] = g15util.load_surface_from_file(g15util.get_icon_path(icon_name), self.theme.bounds[3])
        else:
            properties["item_icon"] = self.dbus_menu_entry.get_icon()
        return properties 

class DBusMenu(Menu):
    def __init__(self, dbus_menu):
        Menu.__init__(self, "menu")
        self.dbus_menu = dbus_menu
        
    def on_configure(self):
        Menu.on_configure(self)
        self.populate()
        
    def menu_changed(self, menu = None, property = None, value = None):
        current_ids = []
        for item in self.get_children():
            current_ids.append(item.id)
            
        self.populate()
        
        was_selected = self.selected
        
        # Scroll to item if it is newly visible
        if menu != None:
            if property != None and property == dbusmenu.VISIBLE and value and menu.get_type() != "separator":
                self.selected = menu
        else:
            # Layout change
            
            # See if the selected item is still there
            if self.selected != None:
                sel = self.selected
                self.selected = None
                for i in self.get_children():
                    if i.id == sel.id:
                        self.selected = i
            
            # See if there are new items, make them selected
            for item in self.get_children():
                if not item.id in current_ids:
                    self.selected = item
                    break
        
    def populate(self):
        self.remove_all_children()
        i = 0
        for item in self.dbus_menu.root_item.children:
            if item.is_visible():
                if item.type == dbusmenu.TYPE_SEPARATOR:
                    self.add_child(MenuSeparator("dbus-menu-separator-%d" % i))
                else:
                    self.add_child(DBusMenuItem("dbus-menu-item-%d" % i, item))
                i += 1   
    
class ConfirmationScreen(G15Page):
    
    def __init__(self, screen, title, text, icon, callback, arg):
        self.page = G15Page.__init__(self, title, screen, priority = g15screen.PRI_HIGH, \
                                     theme = G15Theme(os.path.join(g15globals.themes_dir, "default"), "confirmation-screen"))
        self.theme_properties = { 
                           "title": title,
                           "text": text,
                           "icon": icon
                      }
        self.arg = arg
        self.callback = callback               
        self.screen.add_page(self)
        self.redraw()           
        self.key_handlers.append(self)
        
    def handle_key(self, keys, state, post):
        if not post and state == g15driver.KEY_STATE_UP:             
            if g15driver.G_KEY_RIGHT in keys or g15driver.G_KEY_L4 in keys:
                self.screen.del_page(self)
            elif g15driver.G_KEY_LEFT in keys or g15driver.G_KEY_L2 in keys:
                self.callback(self.arg)  
                self.screen.del_page(self)
                
class G15Theme():    
    def __init__(self, dir, variant = None, svg_text = None, prefix = None, auto_dirty = True):
        if isinstance(dir, str):
            self.dir = dir
        else:
            self.dir = os.path.join(os.path.dirname(sys.modules[dir.__module__].__file__), "default")        
        self.variant = variant
        self.page = None
        self.instance = None
        self.svg_processor = None
        self.svg_text = svg_text
        self.prefix = prefix
        self.offscreen_windows = []
        self.render_lock = RLock()
        self.scroll_timer = None
        self.dirty = False
        self.component = None
        self.auto_dirty = auto_dirty
        self.render = None
        self.scroll_state = {}
        self.nsmap = {
            'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
            'cc': 'http://web.resource.org/cc/',
            'svg': 'http://www.w3.org/2000/svg',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'xlink': 'http://www.w3.org/1999/xlink',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'inkscape': 'http://www.inkscape.org/namespaces/inkscape'
            }
        
    def _set_component(self, component):
        self.component = component
        page = component.get_root()
        if self.page is not None:
            self.page.on_shown_listeners.remove(self._page_visibility_changed)
            self.page.on_hidden_listeners.remove(self._page_visibility_changed)
        self.page = page
        if self.page is not None:
            self.page.on_shown_listeners.append(self._page_visibility_changed)
            self.page.on_hidden_listeners.append(self._page_visibility_changed)
            
        self.screen = self.page.get_screen()
        self.driver = self.screen.driver
        if self.dir != None:
            self.theme_name = os.path.basename(self.dir)
            prefix_path = self.prefix if self.prefix != None else os.path.basename(os.path.dirname(self.dir)).replace("-", "_")+ "_" + self.theme_name + "_"
            module_name = self.get_path_for_variant(self.dir, self.variant, "py", fatal = False, prefix = prefix_path)
            module = None
            if module_name != None:
                if not dir in sys.path:
                    sys.path.insert(0, self.dir)
                module = __import__(os.path.basename(module_name)[:-3])
                self.instance = module.Theme(self.screen, self)
            path = self.get_path_for_variant(self.dir, self.variant, "svg")
            self.document = etree.parse(path)
        elif self.svg_text != None:
            self.document = etree.ElementTree(etree.fromstring(self.svg_text))
        else:
            raise Exception("Must either supply theme directory or SVG text")
            
        self.driver.process_svg(self.document)
        self.bounds = g15util.get_bounds(self.document.getroot())

    def get_path_for_variant(self, dir, variant, extension, fatal = True, prefix = ""):
        if variant == None:
            variant = ""
        elif variant != "":
            variant = "-" + variant
            
        # First try the provided path (i.e the plugin directory)
        path = os.path.join(dir, prefix + self.driver.get_model_name() + variant + "." + extension )
        if not os.path.exists(path):
            # Next try the theme directory
            path = os.path.join(dir, g15globals.themes_dir, "default", self.driver.get_model_name() + variant + "." + extension)
            if not os.path.exists(path):
                # Now look for a default theme file in the provided path (i.e the plugin directory)
                path = os.path.join(dir, prefix + "default" + variant + "." + extension)
                if not os.path.exists(path):
                    # Finally look for a default theme file in the theme directory
                    path = os.path.join(dir, g15globals.themes_dir, "default", "default" + variant + "." + extension)
                    if not os.path.exists(path):
                        if fatal:
                            raise Exception("Missing %s. No .%s file for model %s in %s for variant %s" % ( path, extension, self.driver.get_model_name(), dir, variant ))
                        else:
                            return None
        return path
    
    def convert_css_size(self, css_size):
        em = 1.0
        if css_size.endswith("px"):
            # Get EM based on size of 10px (the default cairo context is 10 so this should be right?)
            px = float(css_size[:len(css_size) - 2])          
            em = px / BASE_PX
        elif css_size.endswith("pt"):      
            # Convert to px first, then use same algorithm
            pt = float(css_size[:len(css_size) - 2])
            px = ( pt * 96.0 ) / 72.0          
            em = px / BASE_PX
        elif css_size.endswith("%"):
            em = float(css_size[:len(css_size) - 1]) / 100.0
        elif css_size.endswith("em"):
            em = float(css_size)
        else:
            raise Exception("Unknown font size")
        return em
        
    def get_string_width(self, text, canvas, css):        
        # Font family
        font_family = css.get("font-family")
        
        # Font size (translate to 'em')
        font_size_text = css.get("font-size")
        em = self.convert_css_size(font_size_text)
        
        # Font weight
        font_weight = cairo.FONT_WEIGHT_NORMAL
        if css.get("font-weight") == "bold":
            font_weight = cairo.FONT_WEIGHT_BOLD
        
        # Font style
        font_slant = cairo.FONT_SLANT_NORMAL
        if css.get("font-style") == "italic":
            font_slant = cairo.FONT_SLANT_ITALIC
        elif css.get("font-style") == "oblique":
            font_slant = cairo.FONT_SLANT_OBLIQUE
        
        try :
            canvas.save()
            canvas.select_font_face(font_family, font_slant, font_weight)
            canvas.set_font_size(em * 10.0 * ( 4 / 3) )  
            return canvas.text_extents(text)[:4]
        finally:            
            canvas.restore()
            
    def parse_css(self, styles_text):        
        # Parse CSS styles            
        styles = { }
        for style in styles_text.split(";") :
            style_args = style.lstrip().rstrip().split(":")
            if len(style_args) > 1:
                styles[style_args[0].rstrip()] = style_args[1].lstrip().rstrip()
        return styles
    
    def format_styles(self, styles):
        buf = ""
        for style in styles:
            buf += style + ":" + styles[style] + ";"
        return buf.rstrip(';')

    def add_window(self, id, page):
        # Get the bounds of the GTK element and remove it from the SVG
        element = self.document.getroot().xpath('//svg:*[@id=\'%s\']' % id,namespaces=self.nsmap)[0]
        offscreen_bounds = g15util.get_actual_bounds(element)
        element.getparent().remove(element)
        import g15gtk as g15gtk
        window = g15gtk.G15Window(self.get_screen(), page, offscreen_bounds[0], offscreen_bounds[1], offscreen_bounds[2], offscreen_bounds[3])
        self.offscreen_windows.append((window, offscreen_bounds))
        return window
    
    def get_element(self, id, root = None):
        if root == None:
            root = self.document.getroot()
        els = root.xpath('//svg:*[@id=\'%s\']' % str(id),namespaces=self.nsmap)
        return els[0] if len(els) > 0 else None
    
    def mark_dirty(self):
        self.dirty = True
            
    def draw(self, canvas, properties = {}, attributes = {}):
        if self.render != None and self.auto_dirty:
            if self.render.properties != properties or self.render.attributes != attributes or \
               self.render.properties.values() != properties.values() or self.render.attributes.values() != attributes.values():
                self.dirty = True
        
        if self.render == None or self.dirty:
            self.render_lock.acquire()
            try:
                document = deepcopy(self.document)
                processing_result = None
                
                # Give the python portion of the theme chance to draw stuff under the SVG
                if self.instance != None:            
                    try :
                        getattr(self.instance, "paint_background")
                        try :
                            self.instance.paint_background(properties, attributes)
                        except:
                            traceback.print_exc(file=sys.stderr)
                    except AttributeError:                
                        # Doesn't exist
                        pass
                    
                root = document.getroot()  
                pango_context = pangocairo.CairoContext(canvas)
                    
                # Remove all elements that are dependent on properties having non blank values
                for element in root.xpath('//svg:*[@title]',namespaces=self.nsmap):
                    title = element.get("title")
                    if title != None:
                        args = title.split(" ")
                        if args[0] == "del":
                            var = args[1]
                            set = True
                            if var.startswith("!"):
                                var = var[1:]
                                set = False
                            if ( set and var in properties and properties[var] != "" and properties[var] != False ) or \
                                ( not set and ( not var in properties or properties[var] == "" or properties[var] == False ) ):
                                element.getparent().remove(element)
                    
                # Process any components
                if self.component:
                    for component_id in self.component.child_map.keys():
                        component_elements = root.xpath('//svg:*[@id=\'%s\']' % component_id,namespaces=self.nsmap)
                        if len(component_elements) > 0:
                            self.component.child_map[component_id].draw(self, component_elements[0])
                        else:
                            logger.warning("Cannot find SVG element for component %s" % component_id)
                          
                # Set any progress bars (always measure in percentage). Progress bars have
                # their width attribute altered 
                for element in root.xpath('//svg:rect[@class=\'progress\']',namespaces=self.nsmap):
                    bounds = g15util.get_bounds(element)
                    id = element.get("id")
                    if id.endswith("_progress"):
                        property_key = id[:-9]
                        if property_key in properties:
                            value = float(properties[property_key])
                            if value == 0:
                                value = 0.1
                            element.set("width", str(int((bounds[2] / 100.0) * value)))
                        else:
                            logger.warning("Found progress element with an ID that doesn't exist in " + \
                                           "theme properties. Theme directory is %s, variant is %s." % (self.dir, self.variant ))
                    else:
                        logger.warning("Found progress element with an ID that doesn't end in _progress")
                        
                # Populate any embedded images
                 
        #        for element in root.xpath('//svg:image[@class=\'embedded_image\']',namespaces=self.nsmap):
                for element in root.xpath('//svg:image',namespaces=self.nsmap):
                    id = element.get("title")
                    if id != None and id in properties and properties[id] != None:
                        file_str = StringIO()
                        val = properties[id]
                        if isinstance(val, str) and str(val).startswith("file:"):
                            file_str.write(val[5:])
                        elif isinstance(val, str) and str(val).startswith("/"):
                            file_str.write(val)
                        else:
                            file_str.write("data:image/png;base64,")
                            img_data = StringIO()
                            if isinstance(val, cairo.Surface):
                                val.write_to_png(img_data)
                                file_str.write(base64.b64encode(img_data.getvalue()))
                            else: 
                                file_str.write(val)
                        element.set("{http://www.w3.org/1999/xlink}href", file_str.getvalue())
                        
                        
                self._do_shadow("shadow", self.screen.driver.get_color_as_hexrgb(g15driver.HINT_BACKGROUND, (255, 255,255)), root)
                self._do_shadow("reverseshadow", self.screen.driver.get_color_as_hexrgb(g15driver.HINT_FOREGROUND, (0, 0, 0)), root)
                
                text_boxes = []
                
                highlight_control = self.screen.driver.get_control_for_hint(g15driver.HINT_HIGHLIGHT)
                if highlight_control:  
                    for element in root.xpath('//svg:*[@style]',namespaces=self.nsmap):
                        element.set("style", element.get("style").replace(DEFAULT_HIGHLIGHT_COLOR, self.screen.driver.get_color_as_hexrgb(g15driver.HINT_HIGHLIGHT, (255, 0, 0 ))))
                
                # Look for text elements that have a clip path. If the rendered text is wider than
                # the clip path, then this element may be scrolled. This clipped text can also
                # be used to wrap and scroll vertical text, replacing the old 'text box' mechanism  
                for element in root.xpath('//svg:text[@clip-path]',namespaces=self.nsmap):
                    clip_val = element.get("clip-path")
                    vertical_wrap = "vertical-wrap" == element.get("title")
                    if len(clip_val) > 0 and clip_val != "none":
                        id = clip_val[5:-1] 
                        clip_path_node = root.xpath('//svg:clipPath[@id=\'' + id + '\']',namespaces=self.nsmap)
                        if len(clip_path_node) == 0:
                            raise Exception("Text node had clip path (%s), but no clip path element with matching ID of %s could be found" % ( id, element.get("clip-path") ) )
                        clip_path_node = clip_path_node[0]
                        
                        t_span_node = element.find("svg:tspan", namespaces=self.nsmap)
                        t_span_text = element.findtext("svg:tspan", namespaces=self.nsmap)
                        if not t_span_text:
                            raise Exception("Text node had clip path, but no tspan->text could be found")
                        
                        clip_path_rect_node = clip_path_node.find("svg:rect", namespaces=self.nsmap)
                        clip_path_bounds = self._get_actual_element_bounds(clip_path_rect_node, element)
                        
                        text_box = TextBox()            
                        text_box.text = Template(t_span_text).safe_substitute(properties) 
                        text_box.css = self.parse_css(element.get("style"))
                        text_box.bounds = clip_path_bounds
                        
                        layout = self._create_pango_layout(text_box, pango_context, vertical_wrap)
                        text_width, text_height = layout.get_pixel_size()
                        text_width, text_height = self._get_actual_size(element, text_width, text_height)
            
                        if vertical_wrap:
                            text_boxes.append(text_box)
                            if text_height > clip_path_bounds[3]:
                                if id in self.scroll_state:
                                    scroll_item = self.scroll_state[id]
                                    scroll_item.text_box = text_box
                                    text_box.base = scroll_item.val
                                else:
                                    scroll_item = VerticalWrapScrollState(text_box)
                                    scroll_item.vertical = True
                                    scroll_item.step = self.screen.service.scroll_amount
                                    self.scroll_state[id] = scroll_item
                                    diff = text_height - clip_path_bounds[3]
                                    scroll_item.range = ( 0, diff)                                
                                scroll_item.transform_elements()
                            elif id in self.scroll_state:
                                del self.scroll_state[id]
                                
                            element.getparent().remove(element)
                        else:
                            # Enable or disable scrolling            
                            if text_width > clip_path_bounds[2]:
                                if id in self.scroll_state:
                                    scroll_item = self.scroll_state[id]
                                    scroll_item.element = element
                                else:
                                    scroll_item = HorizontalScrollState(element)
                                    scroll_item.step = self.screen.service.scroll_amount
                                    self.scroll_state[id] = scroll_item
                                    diff = text_width - clip_path_bounds[2]
                                    scroll_item.alignment = layout.get_alignment()
                                    scroll_item.original = float(element.get("x"))
                                    if scroll_item.alignment == pango.ALIGN_CENTER:
                                        scroll_item.range = ( -(diff / 2), (diff / 2))
                                        scroll_item.adjust = diff / 2
                                    elif scroll_item.alignment == pango.ALIGN_LEFT:
                                        scroll_item.range = ( -diff, 0)
                                    elif scroll_item.alignment == pango.ALIGN_RIGHT:
                                        scroll_item.range = ( 0, diff)
                                    if self.screen.driver.get_bpp() > 1:
                                        self.screen.step = 3
                                    
                                scroll_item.other_elements = [t_span_node]
                                scroll_item.transform_elements()
                            elif id in self.scroll_state:
                                del self.scroll_state[id]
        
                # Find all of the  text boxes. This is a hack to get around rsvg not supporting
                # flowText completely. The SVG must contain two elements. The first must have
                # a class attribute of 'textbox' and the ID must be the property key that it 
                # will contain. The next should be the text element (which defines style etc)
                # and must have an id attribute of <propertyKey>_text. The text layer is
                # then rendered by after the SVG using Pango.
                for element in root.xpath('//svg:rect[@class=\'textbox\']',namespaces=self.nsmap):
                    id = element.get("id")
                    text_node = root.xpath('//*[@id=\'' + id + '_text\']',namespaces=self.nsmap)[0]
                    if text_node != None:            
                        styles = self.parse_css(text_node.get("style"))                
        
                        # Store the text box
                        text_box = TextBox()            
                        text_box.text = properties[id]
                        text_box.css = styles
                        text_boxes.append(text_box)
                        text_box.bounds = self._get_actual_element_bounds(element)
                        
                        # Remove the textnod SVG element
                        text_node.getparent().remove(text_node)
                        element.getparent().remove(element)
        
                    
                # Pass the SVG document to the SVG processor if there is one
                if self.svg_processor != None:
                    self.svg_processor(self, properties, attributes)
                
                # Pass the SVG document to the theme's python code to manipulate the document if required
                if self.instance != None:
                    try :
                        getattr(self.instance, "process_svg")
                        try :                
                            processing_result = self.instance.process_svg(self.driver, root, properties, self.nsmap)
                        except:
                            traceback.print_exc(file=sys.stderr)
                    except AttributeError:                
                        # Doesn't exist
                        pass
                
                # Set the default fill color to be the default foreground. If elements don't specify their
                # own colour, they will inherit this
                
                root_style = root.get("style")
                fg_c = self.screen.driver.get_control_for_hint(g15driver.HINT_FOREGROUND)
                fg_h = None
                if fg_c != None:
                    val = fg_c.value
                    fg_h = "#%02x%02x%02x" % ( val[0],val[1],val[2] )
                    if root_style != None:
                        root_styles = self.parse_css(root_style)
                    else:
                        root_styles = { }
                    root_styles["fill"] = fg_h
                    root.set("style", self.format_styles(root_styles))
                    
                self.render = Render(document, properties, text_boxes, attributes, processing_result)
                self.dirty = False
            finally:
                self.render_lock.release()
            
                        
        self._render_document(canvas, self.render)
        return self.render.document
    
    def _component_removed(self):
        self.scroll_state = {}
        pass
    
    def _page_visibility_changed(self):
        pass
            
    def _render_document(self, canvas, render):
            
        encoded_properties = {}
        # Encode entities in all the property values
        for key in render.properties.keys():
            encoded_properties[key] = saxutils.escape(str(render.properties[key]))
                
        xml = etree.tostring(render.document)
        t = Template(xml)
        xml = t.safe_substitute(encoded_properties)       
        svg = rsvg.Handle()
#        print "------------------------------"
#        print xml
#        print "------------------------------"
#            print "XML size %d" % len(xml)
        try :
            svg.write(xml)
        except:
            traceback.print_exc(file=sys.stderr)
        
        svg.close()
        svg.render_cairo(canvas)
         
        if len(render.text_boxes) > 0:
            rgb = self.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 ))
            for text_box in render.text_boxes:                
                pango_context = pangocairo.CairoContext(canvas)
                layout = self._create_pango_layout(text_box, pango_context, wrap = True)
                
                # Draw text to canvas                
                canvas.set_source_rgb(rgb[0], rgb[1], rgb[2])
                pango_context.save()
                pango_context.rectangle(text_box.bounds[0], text_box.bounds[1], text_box.bounds[2], text_box.bounds[3])
                pango_context.clip()
                pango_context.move_to(text_box.bounds[0], text_box.bounds[1]  - text_box.base)    
                pango_context.update_layout(layout)
                pango_context.show_layout(layout)
                pango_context.restore()
                
        # Paint all GTK components that may have been added
        for offscreen_window, offscreen_bounds in self.offscreen_windows:
            pixbuf = offscreen_window.get_as_pixbuf()
            if pixbuf != None:
                image = g15util.pixbuf_to_surface(pixbuf)
                canvas.save()
                canvas.translate(offscreen_bounds[0], offscreen_bounds[1])
                canvas.set_source_surface(image)
                canvas.paint()
                canvas.restore()
        
        # Give the python portion of the theme chance to draw stuff over the SVG
        if self.instance != None:
            try :
                getattr(self.instance, "paint_foreground")
                try :
                    self.instance.paint_foreground(canvas, render.properties, render.attributes, render.processing_result)
                except:
                    traceback.print_exc(file=sys.stderr)
            except AttributeError:                
                # Doesn't exist
                pass
            
    def is_scroll_required(self):
        return len(self.scroll_state) > 0
            
    def do_scroll(self):
        try:
            self.render_lock.acquire()
            if len(self.scroll_state) > 0:
                for key in self.scroll_state:
                    self.scroll_state[key].next()
                return True
        finally:
            self.render_lock.release()
            
    def _get_actual_size(self, element, width, height):
        list_transforms = [ cairo.Matrix(width, 0.0, 0.0, height, float(element.get("x")), float(element.get("y"))) ]
        el = element
        while el != None:
            list_transforms += g15util.get_transforms(el)
            el = el.getparent()
        list_transforms.reverse()
        t = list_transforms[0]
        for i in range(1, len(list_transforms)):
            t = t.multiply(list_transforms[i])
        xx, yx, xy, yy, x0, y0 = t
        return ( xx, yy )
    
    def _get_actual_element_bounds(self, element, clipped_node = None):
        # Traverse the parents to the root to get any tranlations to apply so the box gets placed at
        # the correct position
        el = element
        list_transforms = [ cairo.Matrix(1.0, 0.0, 0.0, 1.0, float(element.get("x")), float(element.get("y"))) ]
        
        # If the element is a clip path and the associated clipped_node is provided, the work out the transforms from 
        # the parent of the clipped_node, not the clip itself
        if clipped_node is not None:
            el = clipped_node.getparent() 
        
        while el != None:
            list_transforms += g15util.get_transforms(el)
            el = el.getparent()
        list_transforms.reverse()
        t = list_transforms[0]
        for i in range(1, len(list_transforms)):
            t = t.multiply(list_transforms[i])
                    
        xx, yx, xy, yy, x0, y0 = t
        width = element.get("width")
        if not width:
            width = 0
        height = element.get("height")
        if not height:
            height = 0
        return ( x0, y0, float(width), float(height))
    
    def _create_pango_layout(self, text_box, pango_context, wrap = False):
        fo = pango_context.get_font_options()
        attr_list, text_align = self._create_pango_for_text_box(text_box)
        layout = pango_context.create_layout()                
        pangocairo.context_set_font_options(layout.get_context(), fo)      
        layout.set_attributes(attr_list[0])
        if wrap:
            layout.set_width(int(pango.SCALE * text_box.bounds[2]))
            layout.set_wrap(pango.WRAP_WORD_CHAR)
        else:      
            layout.set_width(-1)
        layout.set_text(text_box.text)
        spacing = 0
        layout.set_spacing(spacing)
        
        # Alignment
        if text_align == "right":
            layout.set_alignment(pango.ALIGN_RIGHT)
        elif text_align == "center":
            layout.set_alignment(pango.ALIGN_CENTER)
        else:
            layout.set_alignment(pango.ALIGN_LEFT)
            
        return layout
    
    def _create_pango_for_text_box(self, text_box):
        """
        Turns a TextBox into pango attributes that may be rendered using
        cairo. A 2 element tuple is returned contain the pango attribute
        list and a text alignment.
        
        Keyword arguments:
        text_box        --    text_box
        """        
        css = text_box.css
         
        # Workout font size
        font_size_css = css["font-size"]
        font_size = None
        if font_size_css:
            nw = "".join(font_size_css.split()).lower()            
            if nw.endswith("px"):   
                fs = float(font_size_css[:-2])
                font_size = int(g15util.approx_px_to_pt(fs) * 1000.0)
            elif nw.endswith("pt"):   
                fs = float(font_size_css[:-2])
                font_size = int(fs * 1000.0)

        # TODO The size of the text produced by this code does not exactly match what size would be produce
        # when rendered by RSVG. Find out why this is
        if font_size:
            font_size *= 1.08              
        
        
        font_family = css["font-family"]
        font_weight = css["font-weight"]
        font_style = css["font-style"]
        if "text-align" in css:
            text_align = css["text-align"]
        else:
            text_align = "start"
#                line_height = "80%"
#                if "line-height" in css:
#                    line_height = css["line-height"]
        if "fill" in css:
            foreground = css["fill"]
        else:
            foreground = None
        
        buf = "<span"
        if font_size != None:
            buf += " size=\"%d\"" % font_size 
        if font_style != None:
            buf += " style=\"%s\"" % font_style
        if font_weight != None:
            buf += " weight=\"%s\"" % font_weight
        if font_family != None:
            buf += " font_family=\"%s\"" % font_family                
        if foreground != None and foreground != "none":
            buf += " foreground=\"%s\"" % foreground
            
        buf += ">%s</span>" % saxutils.escape(text_box.text)
        
        attr_list = pango.parse_markup(buf)
        return attr_list, text_align
    
    def _do_shadow(self, id, color, root):
        """
        Shadow is a special text effect useful on the G15. It will take 8 copies of a text element, make
        them the same color as the background, and render them under the original text element at x-1/y-1,
        xy-1,x+1/y,x-1/y etc. This makes the text legible if it overlaps other text or an image (
        at the expense of losing some detail of whatever is underneath)
        
        Keyword arguments:
        id            --    id of element to shadow
        color         --    3 element tuple for RGB values of colour to use for shadow
        root          --    SVG document root
        """
        idx = 1
        for element in root.xpath('//svg:*[@class=\'%s\']' % id,namespaces=self.nsmap):
            for x in range(-1, 2):
                for y in range(-1, 2):
                    if x != 0 or y != 0:
                        shadowed = deepcopy(element)
                        shadowed.set("id", shadowed.get("id") + "_" + str(idx))
                        for bound_element in shadowed.iter():
                            bounds = g15util.get_bounds(bound_element)
                            bound_element.set("x", str(bounds[0] + x))
                            bound_element.set("y", str(bounds[1] + y))                        
                        styles = self.parse_css(shadowed.get("style"))
                        if styles == None:
                            styles = {}
                        styles["fill"] = color
                        shadowed.set("style", self.format_styles(styles))
                        element.addprevious(shadowed)
                        idx += 1