import indicator_messages_default_common

class Theme(indicator_messages_default_common.Theme):
 
    def __init__(self, screen, theme):
        indicator_messages_default_common.Theme.__init__(self, screen, theme)

    def paint_foreground(self, canvas, properties, attributes, args):
        indicator_messages_default_common.Theme.paint_foreground(self, canvas, properties, attributes, args, 0, 42) 