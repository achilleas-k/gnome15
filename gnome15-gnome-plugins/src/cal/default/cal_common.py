import gnome15.g15theme as g15theme
import gnome15.g15util as g15util
import os
import time
import calendar

class Theme():
    
    def __init__(self, screen, theme):
        self.screen = screen
        self.theme = theme            
        self.cell_theme = g15theme.G15Theme(os.path.dirname(__file__), self.screen, "cell")
        self.event_theme = g15theme.G15Theme(os.path.dirname(__file__), self.screen, "event")
        
    def paint_foreground(self, canvas, properties, attributes, args, cal_xoffset, cal_yoffset, event_xoffset, event_yoffset):  

        now = attributes["now"]
        event_days = attributes["event_days"]
        
        # Calendar
        cal = calendar.Calendar()
        y = cal_yoffset
        ld = -1
        for day in cal.itermonthdates(now.year, now.month):
            weekday = day.weekday()
            if weekday < ld:
                y += self.cell_theme.bounds[3]
            ld = weekday
            x = cal_xoffset + ( weekday * self.cell_theme.bounds[2] )
            
            properties = {}
            properties["weekday"] = weekday
            properties["day"] = day.day
            properties["event"] = ""
            
            if now.day == day.day and now.month == day.month:
                properties["today"] = True
            
            if str(day.day) in event_days:
                event = event_days[str(day.day)]
                properties["event"] = event[0].summary.value
                
            canvas.save()
            canvas.translate(x, y)
            self.cell_theme.draw(canvas, properties)
            canvas.restore()
            
        # Events
        y = event_yoffset
        if str(now.day) in event_days:
            events = event_days[str(now.day)]
            for event in events:
                properties = {}
                properties["summary"] = event.summary.value
                properties["time_24"] = "99:99"
                try :
                    event.valarm            
                    properties["icon"] = g15util.get_icon_path("dialog-warning", self.event_theme.bounds[3])
                except AttributeError:            
                    properties["icon"] = ""
                
                canvas.save()
                canvas.translate(event_xoffset, y)
                self.event_theme.draw(canvas, properties)
                canvas.restore()
                y += self.event_theme.bounds[3]
            