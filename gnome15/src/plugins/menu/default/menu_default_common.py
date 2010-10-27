import gnome15.g15_theme as g15theme
import gnome15.g15_util as g15util
import os
import time

class Theme():
    
    def __init__(self, screen, theme):
        self.theme = theme  
        self.entry_theme = g15theme.G15Theme(os.path.dirname(__file__), screen, "entry")
        self.screen = screen
    
    def paint_foreground(self, canvas, properties, attributes, args, x_offset, y_offset):  
        items = attributes["items"]
        selected = attributes["selected"]
        
        canvas.save()
        y = y_offset
        
        # How many complete items fit on the screen? Make sure the selected item is visible
        item_height = self.entry_theme.bounds[3]
        max_items = int( ( self.screen.height - y )  / item_height)
        sel_index = items.index(selected)
        diff = sel_index + 1 - max_items
        if diff > 0:
            y -= diff  * item_height
        canvas.rectangle(x_offset, y_offset, self.screen.width - ( x_offset * 2 ), self.screen.height - y_offset)
        canvas.clip() 
        
        canvas.translate(x_offset, y)
        for item in items:
            item_properties = {}
            if selected == item:
                item_properties["item_selected"] = True
            item_properties["item_name"] = item.page.title 
            if item.thumbnail != None:
                item_properties["item_icon"] = item.thumbnail
            self.entry_theme.draw(canvas, item_properties)
            canvas.translate(0, item_height)
            y += item_height
            if y + item_height > self.theme.screen.height:
                break
        canvas.restore() 