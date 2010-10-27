import menu_default_common

class Theme(menu_default_common.Theme):
 
    
    def __init__(self, screen, theme):
        menu_default_common.Theme.__init__(self, screen, theme)

    def paint_foreground(self, canvas, properties, attributes, args):
        menu_default_common.Theme.paint_foreground(self, canvas, properties, attributes, args, 1, 12) 