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
 
 
"""
This module contains all the classes required for the Gnome15 component and themeing 
system.

The basis of this is a component hierarchy that starts with a G15Page (actually, the
'screen' is kind of the root component, but that anomaly will be fixed). 

All components may contain children. Whether or not they are rendered is down to 
the individual parent component. There is currently a limited set of container type
components, including Component itself, Page and Menu. Menu's children must be MenuItem
objects (or a subclass of MenuItem). Page's may contain any type of child.

Each component has a 'Theme' associated with it. This is an SVG file that is rendered
at painting time. A Page's theme will take up all available space and be rendered at
0,0, where as child components will be rendered at and within bounds defined in the
parent's theme file (by using an svg:rect with an ID that links the two), or at a
place calculated by the component itself (for example, MenuItem children).

The Theme is also responsible for handling automatic text scrolling, as well as processing
the SVG by doing string replacements and other manipulations such as those required
for progress bars, scroll bars.
"""

import os
import cairo
import rsvg
import sys
import traceback
import pango
import g15driver
import g15globals
import g15screen
import g15util
import g15text
import g15locale
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
        
    def reset(self):
        self.adjust = 0.0
        self.do_transform()
        
    def next(self):
        self.adjust += -self.step if self.reversed else self.step
        if self.adjust < self.range[0] and self.reversed:
            self.reversed = False
            self.adjust = self.range[0]
        elif self.adjust > self.range[1] and not self.reversed:
            self.adjust = self.range[1]
            self.reversed = True
        self.do_transform()
            
    def do_transform(self):
        self.val = self.adjust + self.original
        self.transform_elements()
            
class HorizontalScrollState(ScrollState):
    
    def __init__(self, element = None):
        ScrollState.__init__(self)
        self.element = element     
        self.other_elements = []
            
    def transform_elements(self):
        self.element.set("x", str(int(self.val)))
        for e in self.other_elements:
            e.set("x", str(int(self.val)))
            
    def next(self):
        ScrollState.next(self)
                
class VerticalWrapScrollState(ScrollState):
    def __init__(self, text_box):
        ScrollState.__init__(self)
        self.text_box = text_box
            
    def transform_elements(self):
        self.text_box.base = self.val

class TextBox():
    def __init__(self):
        self.bounds = ( )
        self.clip = ()
        self.align = "start"
        self.text = "" 
        self.wrap = False
        self.css = { }
        self.normal_shadow = False
        self.reverse_shadow = False
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
        self._children = []
        self.child_map = {}
        self.parent = None
        self.screen = None
        self.enabled = True
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
        
    def is_enabled(self):
        return self.enabled
        
    def get_tree_lock(self):
#        if self.parent == None:
#            return self._tree_lock
#        else:
#            return self.parent.get_tree_lock()
        return self._tree_lock
    
    def clear_scroll(self):
        if self.theme:
            self.theme.clear_scroll()
        
    def is_focused(self):
        return self.get_root().focused_component == self
    
    def set_focused_component(self, component):
        self.focused_component = component
        
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
        for c in self._children:
            c.do_scroll()
        if self.theme and self.get_allow_scrolling():
            self.theme.do_scroll()
    
    def check_for_scroll(self):
        scroll = False
        for c in self._children:
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
        return self._children.index(child)
        
    def get_child(self, index):
        return self._children[index]
        
    def get_child_by_id(self, id):
        return self.child_map[id] if id in self.child_map else None
        
    def contains_child(self, child):
        return child in self._children
        
    def get_child_count(self):
        return len(self._children)
        
        
#    def set_children(self, children):
#        self.get_tree_lock().acquire()
#        try:
#            to_remove = list(set(self._children) - set(children))
#            to_add = list(set(children) - set(self._children))
#            for c in to_add:
#                c.configure(self)
#                self.notify_add(c)
#            for c in to_remove:
#                c.notify_remove()
#                if c.theme:
#                    c.theme._component_removed()
#            self._children = children
#            self.child_map = {}
#            for c in self._children:
#                self.child_map[c.id] = c
#        finally:
#            self.get_tree_lock().release()
            
    def set_children(self, children):
        g15screen.check_on_redraw()
        self.get_tree_lock().acquire()
        try:
            # Remove any children that we currently have, but are not in the new list
            for c in list(set(self._children) - set(children)):
                self.remove_child(c)
                
            # Add any new children
            for c in list(set(children) - set(self._children)):
                self.add_child(c)
                
            # Now just change out child list to the new one so the order is correct
            self._children = children
        finally:
            self.get_tree_lock().release()
        
    def get_children(self):
        return list(self._children)
        
    def add_child(self, child, index = -1):
        g15screen.check_on_redraw()
        self.get_tree_lock().acquire()
        try:
            if child.parent:
                raise Exception("Child %s already has a parent. Remove it from it's last parent first before adding to %s." % (child.id, self.id))
            if child.id in self.child_map:
                raise Exception("Child with ID of %s already exists in component %s. Trying to add %s, but %s exists" % (child.id, self.id, str(child), str(self.child_map[child.id])))
            self._check_has_parent()
            child.configure(self)
            self.child_map[child.id] = child
            if index == -1:
                self._children.append(child)
            else:
                self._children.insert(index, child)
            self.notify_add(child)
        finally:
            self.get_tree_lock().release()
        
    def remove_all_children(self):
        g15screen.check_on_redraw()
        self.get_tree_lock().acquire()
        try:
            for c in list(self._children):
                self.remove_child(c)
        finally:
            self.get_tree_lock().release()
                    
    def remove_child(self, child):
        g15screen.check_on_redraw()
        self.get_tree_lock().acquire()
        try:
            if not child in self._children:
                raise Exception("Not a child of this component.")
            child.notify_remove()
            if child.theme:
                child.theme._component_removed()
            child.parent = None
            del self.child_map[child.id]
            self._children.remove(child)
        finally:
            self.get_tree_lock().release()
                    
    def remove_child_at(self, index):
        g15screen.check_on_redraw()
        self.get_tree_lock().acquire()
        try:
            self.remove_child(self._children[index])
        finally:
            self.get_tree_lock().release()
        
    def remove_from_parent(self):
        g15screen.check_on_redraw()
        if not self.parent:
            raise Exception("Not added to a parent.")
        self.parent.remove(self)
        
    def configure(self, parent):
        self.parent = parent
        theme = self.get_theme()
        if theme == None:
            logger.warning("No theme for component with ID of %s" % self.id)
        else: 
            self.view_element = self.get_theme().get_element(self.id)
            self.view_bounds  = g15util.get_actual_bounds(self.view_element) if self.view_element is not None else None
        self.on_configure()
        
    def is_visible(self):
        return self.parent != None and self.parent.is_visible()
                
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
        g15screen.check_on_redraw()
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
            for c in self._children:
                canvas.save()
                if not self.do_clip or c.view_bounds is None or self.overlaps(self.view_bounds, c.view_bounds):
                    c.paint(canvas)
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
           
    def notify_remove(self):
        self.remove_all_children()
    
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
        self.scroll_lock = RLock()
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
            i = focus_list.index(self.focused_component)
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
        self.text_handler = g15text.new_text(screen)
        screen.configure_canvas(self.back_context)
        self.text_handler.set_canvas(self.back_context)
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
        
    def delete(self):
        self.screen.del_page(self)
        
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
        self.scroll_lock.acquire()
        try:
            scroll = self.check_for_scroll()
            if scroll and self.theme_scroll_timer == None:
                self.theme_scroll_timer = g15util.schedule("ScrollRedraw", self.screen.service.scroll_delay, self.scroll_and_reschedule)
            elif not scroll and self.theme_scroll_timer != None:
                self.theme_scroll_timer.cancel()
                self.theme_scroll_timer = None
        finally:
            self.scroll_lock.release()
    
    def scroll_and_reschedule(self):
        self.scroll_lock.acquire()
        try:
            self.do_scroll()
            self.theme_scroll_timer = None
            self.redraw()
        finally:
            self.scroll_lock.release()
            
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
        bounds = None
        if width > 0 and height > 0:
            bounds = (x, y, width, height)
        if text_align == "center":
            align = pango.ALIGN_CENTER
        elif text_align == "right":
            align = pango.ALIGN_RIGHT
        else:
            align = pango.ALIGN_LEFT
        self.text_handler.set_attributes(text, bounds = bounds, align = align, font_desc = self.font_family, font_pt_size = self.font_size, \
                                 style = self.font_style, weight = self.font_weight)
        self.text_handler.draw(x, y)
        
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
        
    def select_last_item(self):
        c = self.get_child_count()
        if c > 0:
            self.set_selected_item(self.get_children()[c - 1])
        
    def set_selected_item(self, item):
        i = self.index_of_child(item)
        if i >= 0:
            self.i = i
            self._do_selected()
        
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
        self._recalc_scroll_values()
        self.get_screen().action_listeners.append(self)
        
    def notify_remove(self):
        Component.notify_remove(self)
        self.get_screen().action_listeners.remove(self)
          
    def load_theme(self):
        pass
    
    def add_child(self, child, index = -1):
        Component.add_child(self, child, index)
        self.select_first()
        self._recalc_scroll_values()
        self.centre_on_selected()
    
    def remove_child(self, child):
        Component.remove_child(self, child)
        self.select_first()
        self._recalc_scroll_values()
        self.centre_on_selected()
    
    def set_children(self, children):
        was_selected = self.selected
        Component.set_children(self, children)
        if was_selected in self.get_children():
            self.selected = was_selected
        else:
            self.select_first()
        self.centre_on_selected()
            
    def centre_on_selected(self):
        y = 0
        c = self.get_children()
        for r in range(0, self._get_selected_index()):
            y += self.get_item_height(c[r], True)
        self.base = max(0, y - ( self.view_bounds[3] / 2 ))
        self._recalc_scroll_values()
        self.get_root().redraw()
        
    def get_scroll_values(self):
        return self.scroll_values
        
    def get_item_height(self, item, group = False):
        if item.theme is None:
            logger.warn("Component %s has no theme and so no height" % item.id)
            return 10
        else:            
            return item.theme.bounds[3]
    
    def paint(self, canvas):   
        g15screen.check_on_redraw()
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
                self._recalc_scroll_values()
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
            
    def action_performed(self, binding):
        if self.is_visible():
            if binding.action == g15driver.NEXT_SELECTION:
                self.get_screen().resched_cycle()
                self._move_down(1)
                return True
            elif binding.action == g15driver.PREVIOUS_SELECTION:
                self.get_screen().resched_cycle()
                self._move_up(1)
                return True
            if binding.action == g15driver.NEXT_PAGE:
                self.get_screen().resched_cycle()
                self._move_down(10)
                return True
            elif binding.action == g15driver.PREVIOUS_PAGE:
                self.get_screen().resched_cycle()
                self._move_up(10)
                return True
            elif binding.action == g15driver.SELECT:
                self.get_screen().resched_cycle()
                if self.selected:
                    self.selected.activate()
                return True
        
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
                cc = self.get_child_count()
                if cc > 0:
                    for i in range(0, cc):
                        s = self.get_child(i)
                        if s.is_enabled() and not isinstance(s, MenuSeparator) :
                            self.selected  = s
                            break
                else:
                    self.selected = None
        finally:
            self.get_tree_lock().release()
    
    '''
    Private
    '''
    
    def _recalc_scroll_values(self):
        max_val = 0
        for item in self.get_children():
            max_val += self.get_item_height(item, True)
        self.scroll_values = max(max_val, self.view_bounds[3]), self.view_bounds[3], self.base
    
    def _check_selected(self):
        if not self.selected in self.get_children():
            if self.i >= self.get_child_count():
                return
            self.selected = self.get_child(self.i)
    
    def _do_selected(self):
        self.selected = self.get_child(self.i)
        if self.on_selected:
            self.on_selected()
        self._recalc_scroll_values()
        self.clear_scroll()
        self.mark_dirty()
        self.get_root().redraw()
        
    def _get_selected_index(self):
        c = self.get_children()
        if not self.selected in c:
            return 0 if len(c) > 0 else -1
        else:
            return self.index_of_child(self.selected)
        
    def _move_up(self, amount = 1):
        self.get_tree_lock().acquire()
        try:
            if self.get_child_count() == 0:
                return
            if self.on_move:
                self.on_move()
            self._check_selected()
            self.i = self._get_selected_index()
            items = self.get_child_count()
            try:
                if self.i == 0:
                    self.i = items - 1
                    return
                
                first_enabled = self._get_first_enabled()
                if first_enabled > -1:
                    for a in range(0, abs(amount), 1):
                        while True:
                            self.i -= 1 
                            if self.i < first_enabled:
                                if a == 0:
                                    self.i = self._get_last_enabled()
                                    return
                                else:
                                    self.i = first_enabled
                            c = self.get_child(self.i)
                            if not isinstance(c, MenuSeparator) and c.is_enabled():
                                break
            finally:
                self._do_selected()
        finally:
            self.get_tree_lock().release()
            
    def _get_first_enabled(self):
        for ci in range(0, self.get_child_count()):
            c = self.get_child(ci)
            if not isinstance(c, MenuSeparator) and c.is_enabled():
                return ci
        return -1
            
    def _get_last_enabled(self):
        for ci in range(self.get_child_count() - 1, 0, -1):
            c = self.get_child(ci)
            if not isinstance(c, MenuSeparator) and c.is_enabled():
                return ci
        return -1
                
            
    def _move_down(self, amount = 1):
        self.get_tree_lock().acquire()
        try:
            if self.get_child_count() == 0:
                return
            if self.on_move:
                self.on_move()
            self._check_selected()
            self.i = self._get_selected_index()
                
            items = self.get_child_count()
            try:
                if self.i == items - 1:
                    self.i = 0
                    return
                    
                first_enabled = self._get_first_enabled()
                         
                if first_enabled > -1:
                    for a in range(0, abs(amount), 1):       
                        while True:
                            self.i += 1
                            if self.i == items:
                                if a == 0:
                                    self.i = first_enabled
                                    return
                                else:
                                    self.i = self._get_last_enabled()
                            c = self.get_child(self.i)
                            if not isinstance(c, MenuSeparator) and c.is_enabled():
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
        
    def is_enabled(self):
        return self.dbus_menu_entry.enabled
        
    def get_theme_properties(self):
        properties = MenuItem.get_theme_properties(self)
        properties["item_name"] = self.dbus_menu_entry.get_label() 
        properties["item_type"] = self.dbus_menu_entry.type 
        properties["item_enabled"] = self.dbus_menu_entry.enabled
        properties["item_radio"] = self.dbus_menu_entry.toggle_type == dbusmenu.TOGGLE_TYPE_RADIO
        properties["item_radio_selected"] = self.dbus_menu_entry.toggle_state == 1
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
        
        # Scroll to item if it is newly visible
        if menu != None:
            if property != None and property == dbusmenu.VISIBLE and value and menu.type != "separator":
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
        
        self.select_first()
        
    def populate(self):
        self.get_tree_lock().acquire()
        try:
            self.remove_all_children()
            i = 0
            for item in self.dbus_menu.root_item.children:
                if item.is_visible():
                    if item.type == dbusmenu.TYPE_SEPARATOR:
                        self.add_child(MenuSeparator("dbus-menu-separator-%d" % i))
                    else:
                        self.add_child(DBusMenuItem("dbus-menu-item-%d" % i, item))
                    i += 1   
        finally:
            self.get_tree_lock().release()
    
class ErrorScreen(G15Page):
    
    def __init__(self, screen, title, text, icon = "dialog-error"):
        self.page = G15Page.__init__(self, title, screen, priority = g15screen.PRI_HIGH, \
                                     theme = G15Theme(os.path.join(g15globals.themes_dir, "default"), "error-screen"))
        self.theme_properties = { 
                           "title": title,
                           "text": text,
                           "icon": g15util.get_icon_path(icon)
                      }               
        self.screen.add_page(self)
        self.redraw()
        self.screen.action_listeners.append(self)
        
    def action_performed(self, binding):             
        if binding.action == g15driver.SELECT:
            self.screen.del_page(self)
            self.screen.action_listeners.remove(self)  
    
class ConfirmationScreen(G15Page):
    
    def __init__(self, screen, title, text, icon, callback, arg, cancel_callback = None):
        G15Page.__init__(self, title, screen, priority = g15screen.PRI_HIGH, \
                                     theme = G15Theme(os.path.join(g15globals.themes_dir, "default"), "confirmation-screen"))
        self.theme_properties = { 
                           "title": title,
                           "text": text,
                           "icon": icon
                      }
        self.arg = arg
        self.callback = callback               
        self.cancel_callback = cancel_callback
        self.screen.add_page(self)
        self.redraw()
        self.screen.action_listeners.append(self)
        
    def action_performed(self, binding):             
        if binding.action == g15driver.PREVIOUS_SELECTION:
            self.screen.del_page(self)
            self.screen.action_listeners.remove(self)
            if self.cancel_callback is not None:
                self.cancel_callback(self.arg)
        elif binding.action == g15driver.NEXT_SELECTION:
            self.screen.del_page(self)
            self.screen.action_listeners.remove(self)
            self.callback(self.arg)  
                
class G15Theme():    
    def __init__(self, dir, variant = None, svg_text = None, prefix = None, auto_dirty = True, translation = None):
        if isinstance(dir, str):
            self.dir = dir
        else:
            self.dir = os.path.join(os.path.dirname(sys.modules[dir.__module__].__file__), "default")
        self.document = None       
        self.variant = variant
        self.page = None
        self.instance = None
        self.svg_processor = None
        self.svg_text = svg_text
        self.prefix = prefix
        self.render_lock = RLock()
        self.scroll_timer = None
        self.dirty = False
        self.component = None
        self.auto_dirty = auto_dirty
        self.render = None
        self.scroll_state = {}
        self.translation = translation
        self.nsmap = {
            'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
            'cc': 'http://web.resource.org/cc/',
            'svg': 'http://www.w3.org/2000/svg',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'xlink': 'http://www.w3.org/1999/xlink',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'inkscape': 'http://www.inkscape.org/namespaces/inkscape',
            }
        
    def clear_scroll(self):
        for s in self.scroll_state:
            self.scroll_state[s].reset()
        
    def _set_component(self, component):
        self.render_lock.acquire()
        try:
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
            self.text = g15text.new_text(self.screen)       
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
                
            self.process_svg()
            self.bounds = g15util.get_bounds(self.document.getroot())
        finally:
            self.render_lock.release()
        
    def process_svg(self):        
        self.driver.process_svg(self.document)
        root = self.document.getroot()
        
        # Remove glow effects
        if self.screen.service.disable_svg_glow:
            for element in root.xpath('//svg:filter[@inkscape:label="Glow"]',namespaces=self.nsmap):
                element.getparent().remove(element)
                
        # Remove sodipodi attributes
        self.del_namespace("sodipodi", "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")
        self.del_namespace("inkscape", "http://www.inkscape.org/namespaces/inkscape")
        
        # Translate text
        if self.translation is not None:
            for text in root.xpath('//text()',namespaces=self.nsmap):
                text = str(text).strip()
                if len(text) > 0 and text.startswith("_("):
                    translated = self.translation.ugettext(text[2:-1])
                
        
    def del_namespace(self, prefix, uri):
        for e in self.document.getroot().xpath("//*[namespace-uri()='%s' or @*[namespace-uri()='%s']]" % ( uri, uri ) ,namespaces=self.nsmap):
            attr = e.attrib
            for k in list(attr.keys()):
                if k.startswith("{%s}" % uri):
                    del attr[k]
            if e.getparent() is not None and e.prefix == prefix:
                e.getparent().remove(e)
        

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
        if not "text-align" in styles:
            styles["text-align"] = "start"
        return styles
    
    def format_styles(self, styles):
        buf = ""
        for style in styles:
            buf += style + ":" + styles[style] + ";"
        return buf.rstrip(';')

    def get_element(self, id, root = None):
        if root == None:
            root = self.document.getroot()
        els = root.xpath('//svg:*[@id=\'%s\']' % str(id),namespaces=self.nsmap)
        return els[0] if len(els) > 0 else None

    def get_element_by_tag(self, tag, root = None):
        if root == None:
            root = self.document.getroot()
        els = root.xpath('svg:%s' % str(tag),namespaces=self.nsmap)
        return els[0] if len(els) > 0 else None
    
    def mark_dirty(self):
        self.dirty = True
            
    def draw(self, canvas, properties = {}, attributes = {}):
        if self.render != None and self.auto_dirty:
            if self.render.properties != properties or self.render.attributes != attributes or \
               self.render.properties.values() != properties.values() or self.render.attributes.values() != attributes.values():
                self.dirty = True
        
        self.text.set_canvas(canvas)
        
        if self.render == None or self.dirty:
            self.render_lock.acquire()
            
            if self.document is None:
                raise Exception("No document available! Paint called before component finished initialising")
            
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
                         
                # Process the SVG         
                self._process_deletes(root, properties)
                self._process_components(root)
                self._set_progress_bars(root, properties) 
                self._set_relative_image_paths(root)
                self._convert_image_urls(root, properties)
                self._do_shadow("shadow", self.screen.driver.get_color_as_hexrgb(g15driver.HINT_BACKGROUND, (255, 255,255)), root)
                self._do_shadow("reverseshadow", self.screen.driver.get_color_as_hexrgb(g15driver.HINT_FOREGROUND, (0, 0, 0)), root)
                self._set_highlight_color(root)
                
                text_boxes = []
                self._handle_text_boxes(root, text_boxes, properties, canvas)        
                    
                # Pass the SVG document to the SVG processor if there is one
                if self.svg_processor != None:
                    self.svg_processor(document, properties, attributes)
                
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
                    
                self._set_default_style(root)
                    
                self.render = Render(document, properties, text_boxes, attributes, processing_result)
                self.dirty = False
            finally:
                self.render_lock.release()
            
                        
        self._render_document(canvas, self.render)
        return self.render.document
            
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
    
    """
    Private
    """
    
    def _process_components(self, root):
        """
        Find all elements that are associated with child components in the component this
        theme is attached to, and draw them too.
        
        Keyword arguments:
        root        -- root of document
        """
        if self.component:
            for component_id in self.component.child_map.keys():
                component_elements = root.xpath('//svg:*[@id=\'%s\']' % component_id,namespaces=self.nsmap)
                if len(component_elements) > 0:
                    c = component_elements[0]
                    c_class = c.get("class")
                    if c_class and "hidden-root" in c_class:
                        c.getparent().remove(c)
                    self.component.child_map[component_id].draw(self, c)
                else:
                    logger.warning("Cannot find SVG element for component %s" % component_id)
    
    def _process_deletes(self, root, properties):
        """
        Remove all elements that are dependent on properties having non blank values
        
        Keyword arguments:
        root        -- root of document 
        properties  -- theme properties
        """ 
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
    
    def _set_progress_bars(self, root, properties):
        """
        Sets the width attribute for any elements that have a style of "progress" based on
        the value in the theme properties (with a key that is equal to the ID of the
        element, less the _progress suffix).
        
        Keyword arguments:
        root        -- root of document 
        properties  -- theme properties
        """ 
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
    
    def _set_highlight_color(self, root):
        """
        Replaces any elements that have a color equal to the "highlight" colour
        default with the configured highlight color
        
        Keyword arguments:
        root        -- root of document
        """
        if self.screen.driver.get_control_for_hint(g15driver.HINT_HIGHLIGHT):  
            for element in root.xpath('//svg:*[@style]',namespaces=self.nsmap):
                element.set("style", element.get("style").replace(DEFAULT_HIGHLIGHT_COLOR, self.screen.driver.get_color_as_hexrgb(g15driver.HINT_HIGHLIGHT, (255, 0, 0 ))))
                
    def _set_relative_image_paths(self, root):
        for element in root.xpath('//svg:image[@xlink:href]',namespaces=self.nsmap):
            href = element.get("{http://www.w3.org/1999/xlink}href")
            if href and not "${" in href and ( href.startswith("./") or ( not href.startswith("http:") and not \
                                          href.startswith("https:") and not href.startswith("file:") \
                                          and not href.startswith("/") ) ):
                href = os.path.join(self.dir, href)
                element.set("{http://www.w3.org/1999/xlink}href", href)
    
    def _convert_image_urls(self, root, properties):
        """
        Inserts either a local file URL or an embedded image URL into all
        elements that have 'title' attribute whose value exists as a property
        in the theme properties.
        
        Keyword arguments:
        root        -- root of document
        properties  -- theme properties
        """
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
    
    def _set_default_style(self, root):        
        """
        Set the default fill color to be the default foreground. If elements don't specify their
        own colour, they will inherit this
        
        Keyword arguments:
        root        -- root document element
        """
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
    
    def _handle_text_boxes(self, root, text_boxes, properties, canvas):
        
        # Look for text elements that have a clip path. If the rendered text is wider than
        # the clip path, then this element may be scrolled. This clipped text can also
        # be used to wrap and scroll vertical text, replacing the old 'text box' mechanism
        
        for element in root.xpath('//svg:text[@clip-path]',namespaces=self.nsmap):
            id = element.get("id")
            clip_path_node = self._get_clip_path_element(element)
            vertical_wrap = "vertical-wrap" == element.get("title")
            if clip_path_node is not None:
                
                t_span_node = self.get_element_by_tag("tspan", root = element)
                t_span_text = t_span_node.text
                if not t_span_text:
                    raise Exception("Text node had clip path, but no tspan->text could be found")
                
                clip_path_rect_node = self.get_element_by_tag("rect", clip_path_node)
                if clip_path_rect_node is None:
                    raise Exception("No svg:rect for clip %s" % str(clip_path_node))
                clip_path_bounds = g15util.get_actual_bounds(clip_path_rect_node, element)
                text_bounds = g15util.get_actual_bounds(element)
                
                text_box = TextBox()            
                text_box.text = Template(t_span_text).safe_substitute(properties) 
                text_box.css = self.parse_css(element.get("style"))
                text_class = element.get("class")
                if text_class:
                    if "reverseshadow" in text_class:
                        text_box.reverse_shadow = True
                    elif "shadow" in text_class:
                        text_box.normal_shadow = True
                text_box.clip = clip_path_bounds
                
                self._update_text(text_box, vertical_wrap)
                tx, ty, text_width, text_height = self.text.measure()
#                text_width, text_height = self._get_actual_size(element, text_width, text_height)
                text_box.bounds = ( text_bounds[0], text_bounds[1], text_width, text_height )

                self._scroll_text_boxes(vertical_wrap, text_box, text_boxes, t_span_node, element)

        # Find all of the  text boxes. This is a hack to get around rsvg not supporting
        # flowText completely. The SVG must contain two elements. The first must have
        # a class attribute of 'textbox' and the ID must be the property key that it 
        # will contain. The next should be the text element (which defines style etc)
        # and must have an id attribute of <propertyKey>_text. The text layer is
        # then rendered by after the SVG using Pango.
        for element in root.xpath('//svg:rect[@class=\'textbox\']',namespaces=self.nsmap):
            id = element.get("id")
            logger.warning("DEPRECATED Text box with ID %s in %s" % (id, self.dir))
            text_node = root.xpath('//*[@id=\'' + id + '_text\']',namespaces=self.nsmap)[0]
            if text_node != None:            
                styles = self.parse_css(text_node.get("style"))                

                # Store the text box
                text_box = TextBox()            
                text_box.text = properties[id]
                text_box.css = styles
                text_box.wrap = True
                text_boxes.append(text_box)
                text_box.bounds = g15util.get_actual_bounds(element)
                text_box.clip = text_box.bounds
                
                # Remove the textnod SVG element
                text_node.getparent().remove(text_node)
                element.getparent().remove(element)
                
    def _scroll_text_boxes(self, vertical_wrap, text_box, text_boxes, t_span_node, element):        
        id = element.get("id")
        text_height = text_box.bounds[3]
        text_width =  text_box.bounds[2]
        clip_path_bounds = text_box.clip
        
        if vertical_wrap:
            text_box.wrap = True
            text_boxes.append(text_box)
            if self.screen.service.scroll_amount > 0 and text_height > clip_path_bounds[3]:
                if id in self.scroll_state:
                    scroll_item = self.scroll_state[id]
                    scroll_item.text_box = text_box
                    text_box.base = scroll_item.val
                else:
                    scroll_item = VerticalWrapScrollState(text_box)
                    scroll_item.vertical = True
                    self.scroll_state[id] = scroll_item
                    diff = text_height - clip_path_bounds[3]
                    scroll_item.range = ( 0, diff)
                scroll_item.step = self.screen.service.scroll_amount                               
                scroll_item.transform_elements()
            elif id in self.scroll_state:
                del self.scroll_state[id]
                
            element.getparent().remove(element)
        else:
#            text_boxes.append(text_box)
            
            # Enable or disable scrolling            
            if self.screen.service.scroll_amount > 0 and text_width > clip_path_bounds[2]:
                if id in self.scroll_state:
                    scroll_item = self.scroll_state[id]
                    scroll_item.element = element
                else:
                    scroll_item = HorizontalScrollState(element)
                    
                    self.scroll_state[id] = scroll_item
                    diff = text_width - clip_path_bounds[2]
                    
                    #+ ( clip_path_bounds[0] - text_box.bounds[0] )
                    if diff < 0:
                        raise Exception("Negative diff!?")
                    scroll_item.alignment = text_box.css["text-align"]
                    scroll_item.original = float(element.get("x"))
                    if scroll_item.alignment == "center":
                        scroll_item.range = ( -(diff / 2), (diff / 2))
                    elif scroll_item.alignment == "start":
                        scroll_item.range = ( -diff, 0)
                    elif scroll_item.alignment == "end":
                        scroll_item.range = ( 0, diff)
                        
                    scroll_item.reset()
                    
                scroll_item.step = self.screen.service.scroll_amount
                scroll_item.other_elements = [t_span_node]
                scroll_item.transform_elements()
            elif id in self.scroll_state:
                del self.scroll_state[id]      
#            element.getparent().remove(element)
    
    def _get_clip_path_element(self, element):
        clip_val = element.get("clip-path")
        if clip_val and len(clip_val) > 0 and clip_val != "none":
            id = clip_val[5:-1]
            el = self.get_element(id, element.getroottree().getroot())
            if el is None:
                raise Exception("Text node had clip path (%s), but no clip path element with matching ID of %s could be found" % ( id, element.get("clip-path") ) )
            return el
    
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
        try :
            svg.write(xml)
        except:
            traceback.print_exc(file=sys.stderr)
        
        svg.close()
        svg.render_cairo(canvas)
         
        if len(render.text_boxes) > 0:
            rgb = self.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, ( 0, 0, 0 ))
            bg_rgb = self.screen.driver.get_color_as_ratios(g15driver.HINT_BACKGROUND, ( 255, 255, 255 ))
            for text_box in render.text_boxes:
                self._render_text_box(canvas, text_box, rgb, bg_rgb)
        
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
            
    def _render_text_box(self, canvas, text_box, rgb, bg_rgb):
        self._update_text(text_box, text_box.wrap)
        
#        if "fill" in text_css:
#            rgb = g15util. css["fill"]
#        else:
#            foreground = None
        
        if text_box.normal_shadow or text_box.reverse_shadow:
            if text_box.normal_shadow:
                canvas.set_source_rgb(bg_rgb[0], bg_rgb[1], bg_rgb[2])
            else:
                canvas.set_source_rgb(rgb[0], rgb[1], rgb[2])
            for x in range(-1, 2):
                for y in range(-1, 2):
                    if x != 0 or y != 0:
                        self.text.draw(text_box.bounds[0] + x, text_box.bounds[1] + y - text_box.base)
        
        # Draw primary text to canvas                
        canvas.set_source_rgb(rgb[0], rgb[1], rgb[2])
        self.text.draw(text_box.bounds[0], text_box.bounds[1] - text_box.base)
            
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
    
    def _update_text(self, text_box, wrap = False):
        
        css = text_box.css         
        
        font_size_css = css["font-size"] if "font-size" in css else None
        font_pt_size = None
        if font_size_css:
            nw = "".join(font_size_css.split()).lower()                 
            if nw.endswith("px"):   
                fs = float(font_size_css[:-2])
                font_pt_size = int(g15util.approx_px_to_pt(fs))
            elif nw.endswith("pt"):
                font_pt_size = int(font_size_css[:-2])
                

        font_family = css["font-family"] if "font-family" in css else None
        font_weight = css["font-weight"] if "font-weight" in css else None
        font_style = css["font-style"] if "font-style" in css else None
        if "text-align" in css:
            text_align = css["text-align"]
        else:
            text_align = "start"
        alignment = pango.ALIGN_LEFT
        if text_align == "end":
            alignment =pango.ALIGN_RIGHT
        elif text_align == "center":
            alignment = pango.ALIGN_CENTER
        
        # Determine wrap and width to use
        if wrap:
            width = int(pango.SCALE * text_box.clip[2])
            wrap = pango.WRAP_WORD_CHAR
        else:      
            wrap = 0
            width = -1
            
        # Update the text handler
        self.text.set_attributes(text_box.text, bounds = text_box.clip, wrap = wrap, align = alignment, \
                                 width = width, spacing = 0,  \
                                 style = font_style, weight = font_weight, \
                                 font_pt_size = font_pt_size, \
                                 font_desc = font_family)
    
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
        
        
        for element in root.xpath('//svg:*[@class=\'%s\']' % id,namespaces=self.nsmap):
            clip_path_element = self._get_clip_path_element(element)
            bounds = g15util.get_bounds(element)
            idx = 1
            for x in range(-1, 2):
                for y in range(-1, 2):
                    if x != 0 or y != 0:
                        shadowed_id = element.get("id") + "_" + str(idx)
                        
                        # Copy the element itself
                        shadowed = deepcopy(element)                        
                        shadowed.set("id", shadowed_id)
                        for bound_element in shadowed.iter():
                            bound_element.set("x", str(bounds[0] + x))
                            bound_element.set("y", str(bounds[1] + y))                        
                        styles = self.parse_css(shadowed.get("style"))
                        if styles == None:
                            styles = {}
                        styles["fill"] = color
                        shadowed.set("style", self.format_styles(styles))
                        element.addprevious(shadowed)
                        
                        # Copy the clip path
                        if clip_path_element is not None:
                            clip_copy = deepcopy(clip_path_element)
                            clip_id = clip_path_element.get("id")
                            new_clip_id = "%s_%d" % ( clip_id, idx )
                            clip_copy.set("id", new_clip_id )
                            shadowed.set("clip-path", "url(#%s)" % new_clip_id)
                            clip_path_element.addprevious(clip_copy)
                        
                        
                        idx += 1