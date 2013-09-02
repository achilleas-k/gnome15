#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2011 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 
import gnome15.g15driver as g15driver
import gnome15.g15screen as g15screen
import gnome15.util.g15convert as g15convert
import gnome15.util.g15scheduler as g15scheduler
import logging
logger = logging.getLogger("things")

from Things.ThingsApp import *
from Things.Thinglets import *
from Things.BoxOfTricks import *
from Things.OutputDevice import *
        

# Plugin details - All of these must be provided
id="things"
name="Things" 
description="Integrates the Things. A python animation API. Doesn't do anything " + \
            "by itself, but provides a framework for other plugins to add " + \
            "animations and special effects"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2011 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=False
unsupported_models = [ g15driver.MODEL_G110, g15driver.MODEL_G11 ]

def create(gconf_key, gconf_client, screen):
    return G15Things(gconf_key, gconf_client, screen)

class G15ThingOutputDevice(OutputDevice):
    
    def __init__(self, canvas_width, canvas_height, screen):
        OutputDevice.__init__(self)        
        self._screen = screen
        self._windowSize = (canvas_width, canvas_height, canvas_width, canvas_height) 
        
    def is_button_press(self, e):
        return False
    
    def is_button_release(self, e):
        return False
    
    def is_motion(self, e):
        return False
    
    def comeToLife(self, owner):
        self.owner = owner
        g15scheduler.schedule("ThingPaint", self.owner.speed / 1000.0, self._mainLoop)
        
    ## This gives life to the whole show.
    def _mainLoop(self): 
        """
        Private
        =======

        Called by timeout in comeToLife. Keeps looping on timeout. This is the heart of the app.
        
        """
        if self.pauseapp: return True
        self.owner._tick()
        self._screen.redraw()
        if not self.stack.quitApp:
            g15scheduler.schedule("ThingPaint", self.owner.speed / 1000.0, self._mainLoop)
        
class G15ThingPainter(g15screen.Painter):
    
    def __init__(self, screen):
        g15screen.Painter.__init__(self, g15screen.BACKGROUND_PAINTER, -9999)
        self.output_device = G15ThingOutputDevice(screen.available_size[0], screen.available_size[1], screen)
        self.screen = screen
        self.app2()
        
    def app1(self):
        ## BEGIN THE APP
        
        ## Get an app ref.
        ## Fiddle with the speed param. Make it bigger if you want the animation slower.
        
        import test1
        
        app = AllThings ( self.screen.available_size[0], self.screen.available_size[1], speed = 20, output = self.output_device)
        app.add(test1.BACKDROP)
        
        ## Make some scene Things to hold many items each
        scene1 = test1.SceneThing()
        scene2 = test1.SceneThing()
        scene3 = test1.SceneThing()
        
        ## Add Things to each scene
        scene1.add( test1.FadeStart(app) )
        scene2.add( test1.IntroduceLogo(app) )
        scene3.add( test1.Exit(app) )
        
        ## Add the scences to the app
        app.add( scene1 )
        app.add( scene2 )
        app.add( scene3 )
        
        ## Tell it which one to start with
        app.startScene(1)
        
        
        #app.showGrid() # optional for debugging
        
        ## Bring app to life!
        app.comeToLife ( )
        
    def app2(self):
        
        ## Get an app ref.
        ## Fiddle with the speed param. Make it bigger if you want the animation slower.
        import cloudsthingum
        app = AllThings ( self.screen.available_size[0], self.screen.available_size[1], speed = 20, output = self.output_device)
        app.add( cloudsthingum.BlueSky() )
        ## Add the main thing to the app
        app.add( cloudsthingum.Madness() )
        
        app.panZoom(True)
        ## Bring app to life!
        app.comeToLife ( )
        
    def paint(self, canvas):    
        canvas.save()    
        self.output_device.stack._expose(canvas)    
        canvas.restore()    
        
class G15Things():
    
    def __init__(self, gconf_key, gconf_client, screen):
        self.screen = screen
        self.gconf_client = gconf_client
        self.gconf_key = gconf_key
        self.target_surface = None
        self.target_context = None
    
    def activate(self):
        self.bg_img = None
        self.this_image = None
        self.current_style = None
        self.notify_handlers = []
        self.painter = G15ThingPainter(self.screen)
        self.screen.painters.append(self.painter)
    
    def deactivate(self):
        self.screen.painters.remove(self.painter)
        self.screen.redraw()
        
    def destroy(self):
        pass