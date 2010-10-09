import rss_default_common

class Theme(rss_default_common.Theme):
 
    
    def __init__(self, screen, theme):
        rss_default_common.Theme.__init__(self, screen, theme)

    def paint_foreground(self, canvas, properties, attributes, args):
        rss_default_common.Theme.paint_foreground(self, canvas, properties, attributes, args, 1, 12) 