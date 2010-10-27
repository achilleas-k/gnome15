import gnome15.g15_theme as g15theme
import gnome15.g15_util as g15util
import os
import time

class Theme():
    
    def __init__(self, screen, theme):
        self.theme = theme  
        self.entry_theme = g15theme.G15Theme(os.path.dirname(__file__), screen, "entry")
        self.separator_theme = g15theme.G15Theme(os.path.dirname(__file__), screen, "separator")
        self.screen = screen
    
    def paint_foreground(self, canvas, properties, attributes, args, x_offset, y_offset):  
        items = attributes["items"]
        selected = attributes["selected"]
        
        canvas.save()
        y = y_offset
        
        # How many complete items fit on the screen? Make sure the selected item is visible
        # TODO again, this needs turning into a re-usable component - see menu and rss
        item_height = self.entry_theme.bounds[3]
        max_items = int( ( self.screen.height - y )  / item_height)
        if selected != None:
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
            item_properties["item_name"] = item.get_label() 
            item_properties["item_alt"] = item.get_right_side_text()
            item_properties["item_type"] = item.get_type()
            icon_name = item.get_icon_name()
            if icon_name != None:
                item_properties["item_icon"], ctx = g15util.load_surface_from_file(g15util.get_icon_path(self.screen.applet.conf_client, icon_name))
            else:
                item_properties["item_icon"] = item.get_icon()
                
            if item.get_type() == "separator":
                self.separator_theme.draw(canvas, item_properties)
            else:
                self.entry_theme.draw(canvas, item_properties)
            canvas.translate(0, item_height)
            y += item_height
            if y + item_height > self.theme.screen.height:
                break
        canvas.restore() 