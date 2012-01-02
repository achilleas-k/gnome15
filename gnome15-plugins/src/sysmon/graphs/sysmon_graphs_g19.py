import gnome15.g15theme as g15theme
import gnome15.g15driver as g15driver
import cairoplot
import cairo

def create(theme):
    page = theme.component
    plugin = theme.plugin           
    page.add_child(G15CPUGraph("cpu", plugin))
    page.add_child(G15NetGraph("net", plugin))
    page.add_child(G15MemGraph("mem", plugin))
    
class G15Graph(g15theme.Component):
    
    def __init__(self, component_id, plugin):
        g15theme.Component.__init__(self, component_id)
        self.plugin = plugin
        
    def create_plot(self, graph_surface):
        raise Exception("Not implemented")
        
    def paint(self, canvas):
        g15theme.Component.paint(self, canvas)    
        if self.view_bounds:
            graph_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 
                                               int(self.view_bounds[2]), 
                                               int(self.view_bounds[3]))
            plot =  self.create_plot(graph_surface)
            plot.line_width = 2.0
            plot.line_color = self.plugin.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, (255, 255, 255))
            plot.label_color = self.plugin.screen.driver.get_color_as_ratios(g15driver.HINT_FOREGROUND, (255, 255, 255))
            plot.shadow = True
            plot.bounding_box = False
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
        return cairoplot.DotLinePlot( graph_surface, self.plugin.selected_cpu.history, 
                                      self.view_bounds[2], 
                                      self.view_bounds[3], 
                                      background = None,
                                      axis = False, grid = False, 
                                      x_labels = [],
                                      y_labels = ["%-6d" % 0, "%-6d" % 50, "%-6d" % 100],
                                      y_bounds = (0, 100))

class G15NetGraph(G15Graph):
    
    def __init__(self, component_id, plugin):
        G15Graph.__init__(self, component_id, plugin)
        
    def create_plot(self, graph_surface):
        y_labels = []
        max_y = max(max(self.plugin.max_send, self.plugin.max_recv), 102400)
        for x in range(0, int(max_y), int(max_y / 4)):
            y_labels.append("%-3.2f" % ( float(x) / 102400.0 ) )
        return cairoplot.DotLinePlot( graph_surface, [ self.plugin.send_history, self.plugin.recv_history ], 
                                      self.view_bounds[2], 
                                      self.view_bounds[3], 
                                      background = None,
                                      axis = False, grid = False, 
                                      x_labels = [],
                                      y_labels = y_labels,
                                      y_bounds = (0, max_y ) )

class G15MemGraph(G15Graph):
    """
    Memory graph
    """
    def __init__(self, component_id, plugin):
        G15Graph.__init__(self, component_id, plugin)
        
    def create_plot(self, graph_surface):
        y_labels = []
        max_y = self.plugin.total
        for x in range(0, int(max_y), int(max_y / 4)):
            y_labels.append("%-4d" % int( float(x) / 1024.0 / 1024.0 ) )
        return cairoplot.DotLinePlot( graph_surface, [ self.plugin.used_history, self.plugin.cached_history ], 
                                      self.view_bounds[2], 
                                      self.view_bounds[3], 
                                      background = None,
                                      axis = False, grid = False, 
                                      x_labels = [],
                                      y_labels = y_labels,
                                      y_bounds = (0, max_y ) )