import cal_common

class Theme(cal_common.Theme):
 
    def __init__(self, screen, theme):
        cal_common.Theme.__init__(self, screen, theme)
        
    def paint_foreground(self, canvas, properties, attributes, args):
        cal_common.Theme.paint_foreground(self, canvas,properties,attributes,args, 0, 7, 91, 19)        