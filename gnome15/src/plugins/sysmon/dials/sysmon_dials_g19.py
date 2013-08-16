import gnome15.util.g15convert as g15convert
import gnome15.util.g15cairo as g15cairo
import os
import rsvg
import cairo
      
needles = {
        "cpu_pc"        : (170, 90,    rsvg.Handle(os.path.join(os.path.dirname(__file__), "g19-large-needle.svg"))),
        "net_send_pc"   : (82, 198,     rsvg.Handle(os.path.join(os.path.dirname(__file__), "g19-tiny-needle.svg"))), 
        "net_recv_pc"   : (82, 198,     rsvg.Handle(os.path.join(os.path.dirname(__file__), "g19-small-needle.svg"))), 
        "mem_used_pc"   : (254, 198,    rsvg.Handle(os.path.join(os.path.dirname(__file__), "g19-small-needle.svg"))),
        "mem_cached_pc" : (254, 198,    rsvg.Handle(os.path.join(os.path.dirname(__file__), "g19-tiny-needle.svg")))
           }

def paint_foreground(theme, canvas, properties, attributes, args): 
    for key in needles.keys():
        needle = needles[key]
        svg = needle[2]      
        surface = create_needle_surface(svg, ( ( 180.0 / 100.0 ) * float(properties[key]) ) )
        canvas.save()
        svg_size = svg.get_dimension_data()[2:4]  
        canvas.translate (needle[0] - svg_size[0], needle[1] - svg_size[1])
        canvas.set_source_surface(surface)
        canvas.paint()
        canvas.restore()
        
def create_needle_surface(svg, degrees):
    svg_size = svg.get_dimension_data()[2:4]  
    surface = cairo.SVGSurface(None, svg_size[0] * 2,svg_size[1] *2)
    context = cairo.Context(surface)
    context.translate(svg_size[0], svg_size[1])
    g15cairo.rotate(context, -180)
    g15cairo.rotate(context, degrees)
    svg.render_cairo(context)
    context.translate(-svg_size[0], -svg_size[1])
    return surface