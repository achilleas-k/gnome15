import gnome15.g15_theme as g15theme
import gnome15.g15_util as g15util
import os
import time

class Theme():
    
    def __init__(self, screen, theme):
        self.theme = theme  
        self.entry_theme = g15theme.G15Theme(os.path.dirname(__file__), screen, "entry")
    
    def paint_foreground(self, canvas, properties, attributes, args, x_offset, y_offset):  
        if "entries" in attributes:
            entries = attributes["entries"]
            canvas.save()
            y = y_offset
            canvas.translate(x_offset, y)
            for entry in entries:
                element_properties = dict(properties)
                if "selected" in attributes and attributes["selected"] == entry:
                    element_properties["ent_selected"] = True
                element_properties["ent_title"] = entry.title
                element_properties["ent_link"] = entry.link
                element_properties["ent_description"] = entry.description
                
                element_properties["ent_locale_date_time"] = time.strftime("%x %X", entry.date_parsed)            
                element_properties["ent_locale_time"] = time.strftime("%X", entry.date_parsed)            
                element_properties["ent_locale_date"] = time.strftime("%x", entry.date_parsed)
                element_properties["ent_time_24"] = time.strftime("%H:%M") 
                element_properties["ent_full_time_24"] = time.strftime("%H:%M:%S") 
                element_properties["ent_time_12"] = time.strftime("%I:%M %p") 
                element_properties["ent_full_time_12"] = time.strftime("%I:%M:%S %p")
                element_properties["ent_short_date"] = time.strftime("%a %d %b")
                element_properties["ent_full_date"] = time.strftime("%A %d %B")
                element_properties["ent_month_year"] = time.strftime("%m/%y")
                
                self.entry_theme.draw(canvas, element_properties)
                canvas.translate(0, self.entry_theme.bounds[3])
                y += self.entry_theme.bounds[3]
                if y + self.entry_theme.bounds[3] > self.theme.screen.height:
                    break
            canvas.restore() 