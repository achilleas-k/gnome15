#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2012 Brett Smith <tanktarta@blueyonder.co.uk>
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

import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import gnome15.util.g15convert as g15convert
import cairoplot
import cairo

def create(theme):
    page = theme.component
    plugin = theme.plugin           
    page.add_child(G15CPUGraph("cpu", plugin))
    page.add_child(G15NetGraph("net", plugin))
    page.add_child(G15MemGraph("mem", plugin))
    
def destroy(theme):
    page = theme.component
#    page.remove_child(page.get_child_by_id("cpu"))
#    page.remove_child(page.get_child_by_id("net"))
#    page.remove_child(page.get_child_by_id("mem"))
    
class G15Graph(g15theme.Component):
    
    def __init__(self, component_id, plugin):
        g15theme.Component.__init__(self, component_id)
        self.plugin = plugin

    def get_colors(self):
        if self.plugin.screen.driver.get_bpp() == 1:
            return (0.0,0.0,0.0,1.0), (0.0,0.0,0.0,1.0)
        elif self.plugin.screen.driver.get_control_for_hint(g15driver.HINT_HIGHLIGHT): 
            highlight_color = self.plugin.screen.driver.get_color_as_ratios(g15driver.HINT_HIGHLIGHT, (255, 0, 0 ))
            return (highlight_color[0],highlight_color[1],highlight_color[2], 1.0), \
                   (highlight_color[0],highlight_color[1],highlight_color[2], 0.50)
        
    def create_plot(self, graph_surface):
        raise Exception("Not implemented")
        
    def paint(self, canvas):
        g15theme.Component.paint(self, canvas)    
        if self.view_bounds:
            graph_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 
                                               int(self.view_bounds[2]), 
                                               int(self.view_bounds[3]))
            plot =  self.create_plot(graph_surface)
            
            if self.plugin.screen.driver.get_bpp() == 1:
                plot.line_color = (1.0,1.0,1.0)
                plot.line_width = 1.0
                plot.display_labels = False
            else:
                plot.line_width = 2.0
                plot.bounding_box = False
                plot.line_color = self.plugin.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, (255, 255, 255))
                plot.label_color = self.plugin.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, (255, 255, 255))
            plot.shadow = True
            plot.render()
            plot.commit()
            
            canvas.save()    
            canvas.translate(self.view_bounds[0], self.view_bounds[1])
            canvas.set_source_surface(graph_surface, 0.0, 0.0)
            canvas.paint()
            canvas.restore()

class G15CPUGraph(G15Graph):
    
    def __init__(self, component_id, plugin):
        G15Graph.__init__(self, component_id, plugin)
        
    def create_plot(self, graph_surface):
        series_colors, fill_colors = self.get_colors()
        return cairoplot.AreaPlot(graph_surface, self.plugin.selected_cpu.history, 
                                 self.view_bounds[2], 
                                 self.view_bounds[3], 
                                 background = None,
                                 grid = False, 
                                 x_labels = [],
                                 y_labels = ["%-6d" % 0, "%-6d" % 50, "%-6d" % 100],
                                 y_bounds = (0, 100),
                                 series_colors = [ series_colors ],
                                 fill_colors = [ fill_colors ])


class G15NetGraph(G15Graph):
    
    def __init__(self, component_id, plugin):
        G15Graph.__init__(self, component_id, plugin)
        
    def create_plot(self, graph_surface):
        y_labels = []
        max_y = max(max(self.plugin.selected_net.max_send, self.plugin.selected_net.max_recv), 102400)
        for x in range(0, int(max_y), int(max_y / 4)):
            y_labels.append("%-3.2f" % ( float(x) / 102400.0 ) )
        series_color, fill_color = self.get_colors()            
        if self.plugin.screen.driver.get_bpp() == 1:
            alt_series_color = (1.0,1.0,1.0,1.0)
            alt_fill_color = (1.0,1.0,1.0,1.0)
        else:
            alt_series_color = g15convert.get_alt_color(series_color)
            alt_fill_color = g15convert.get_alt_color(fill_color)
        return cairoplot.AreaPlot( graph_surface, [ self.plugin.selected_net.send_history, self.plugin.selected_net.recv_history ], 
                                      self.view_bounds[2], 
                                      self.view_bounds[3], 
                                      background = None,
                                      grid = False, 
                                      x_labels = [],
                                      y_labels = y_labels,
                                      y_bounds = (0, max_y ),
                                      series_colors = [ series_color, alt_series_color ],
                                      fill_colors = [ fill_color, alt_fill_color ]  )

class G15MemGraph(G15Graph):
    """
    Memory graph
    """
    def __init__(self, component_id, plugin):
        G15Graph.__init__(self, component_id, plugin)
        
    def create_plot(self, graph_surface):
        y_labels = []
        max_y = self.plugin.max_total_mem
        for x in range(0, int(max_y), int(max_y / 4)):
            y_labels.append("%-4d" % int( float(x) / 1024.0 / 1024.0 ) )
        series_color, fill_color = self.get_colors()
        
        if self.plugin.screen.driver.get_bpp() == 1:
            alt_series_color = (1.0,1.0,1.0,1.0)
            alt_fill_color = (1.0,1.0,1.0,1.0)
        else:
            alt_series_color = g15convert.get_alt_color(series_color)
            alt_fill_color = g15convert.get_alt_color(fill_color)
        return cairoplot.AreaPlot( graph_surface, [ self.plugin.used_history, self.plugin.cached_history ], 
                                      self.view_bounds[2], 
                                      self.view_bounds[3], 
                                      background = None,
                                      grid = False, 
                                      x_labels = [],
                                      y_labels = y_labels,
                                      y_bounds = (0, max_y ),
                                      series_colors = [ series_color, alt_series_color ],
                                      fill_colors = [ fill_color, alt_fill_color ]  )