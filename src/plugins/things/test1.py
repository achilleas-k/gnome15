#!/usr/bin/env python
# -*- coding: utf8 -*-

##	Things Copyright(C) 2009 Donn.C.Ingle
##
##	Contact: donn.ingle@gmail.com - I hope this email lasts.
##
##  This file is part of Things.
##
##  Things is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  Things is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with Things.  If not, see <http://www.gnu.org/licenses/>.


from Things.ThingsApp import *
from Things.Thinglets import *
from Things.BoxOfTricks import *

## NOTE:
##   Head down to the end: look for the first scene (class FadeStart) and work from there.
##   Written with Version 0.1 of the API: 2 May 2009


## ---- General
CAIROHEXBLUE="#162284"; CAIROBLUE=hexfloat(CAIROHEXBLUE)

class Backdrop(Thing):
	## This Thing holds three frames with three draw methods; one for each.
	## We use the frame number to decide which to employ.
	## This thing serves as a background drawer for each scene.
	def __init__(self):
		Thing.__init__(self)
		self.keys ( "#==", Props())
		self.stops( "^^^" )
		self.loops=False

		self.draws=[self.draw1,self.draw2,self.draw3]

		self.L = cairo.LinearGradient(0, -300, 0, 300)
		self.L.add_color_stop_rgba(0,    1, 1, 1, 1)
		self.L.add_color_stop_rgba(0.25, 0, 0.6, 1, 1)
		self.L.add_color_stop_rgba(0.5,  0, 0.8, 1, 1)
		self.L.add_color_stop_rgba(1,    1, 1, 1, 1)

		self.yell = hexfloat("#dfaa00")

		self.R = cairo.RadialGradient(0,-20,50,0,-20,300)
		self.R.add_color_stop_rgb(0, 1,1,1)
		self.R.add_color_stop_rgb(1, *self.yell)
	def draw(self, ctx, fr):
		self.draws[fr-1](ctx)
	
	def draw1(self, ctx):
		ctx.set_source(self.L)
		ctx.paint() 
	def draw2(self, ctx):
		ctx.set_source(self.R)
		ctx.paint() 
	def draw3(self, ctx):
		ctx.set_source_rgb(*self.yell)
		ctx.paint() 

class ScarabShape(DrawThing):
	def draw(self, ctx, fr):
		BOS["CG:cairo_scarab"].draw(ctx)
SCARABsh=ScarabShape()

## ----------------------------------- SCENE 3

class Exit(Thing):
	def __init__(self, app):
		Thing.__init__(self)
		self.keys  ( "#======================================================================================.", Props())
		self.stops ( ".......................................................................................^")
		self.funcs ( "^.....................................................................................^", (BACKDROP.goStop,3), app.quit )

		class EndScarab(Thing):
			def __init__(self):
				Thing.__init__(self)
				self.keys( "#----------------------------------#---------------------------#",Props(),Props(sz=6,rot=pi),Props(a=0,rot=pi2))
				self.loops=False
				self.add(SCARABsh)
		self.add( EndScarab() )

	#def draw(self,ctx,fr):
	#	ctx.set_source_rgb(0,0,0)
	#	ctx.paint()

## ----------------------------------- SCENE 2

class ClipWord(ClipThing):
	def __init__(self):
		ClipThing.__init__(self)
		self.keys( "#", Props())
		self.loops = False

		class CairoWord(Thing):
			def __init__(self):
				Thing.__init__(self)
				self.keys(   ".#-----------------------------------------------------------------#", Props(y=45),Props())
				self.stops(  "^..................................................................^")
				self.funcs(  "..................................................................^",self.dostuff )
			def dostuff(self):
				self.parentThing.parentThing.SUN.goPlay(2)

			def draw(self, ctx, fr):
				BOS["CG:cairo_word"].draw(ctx)
		self.CAIROWORD = CairoWord()
		self.add( self.CAIROWORD )

	def draw(self,ctx,fr):
		ctx.rectangle(-150,-35,260,65)


# Prep some shapes from the SVG file
class ArrowButtonN(DrawThing):
	def draw(self,ctx,fr):
		BOS["CG:button_right_normal"].draw(ctx)
class ArrowButtonO(DrawThing):
	def draw(self,ctx,fr):
		BOS["CG:button_right_over"].draw(ctx)
class ArrowButtonD(DrawThing):
	def draw(self,ctx,fr):
		BOS["CG:button_right_down"].draw(ctx)
class ArrowButtonU(DrawThing):
	def draw(self,ctx,fr):
		BOS["CG:button_right_up"].draw(ctx)

class Next(Thing):
	def __init__(self):
		Thing.__init__(self)
		self.keys("#--#-----#", Props(sz=2,a=0),Props(sz=0.5),Props())
		self.loops = False
		# Just define the button within myself -- it shows the relationship better.
		class NextButton(ButtonThing):
			"""ButtonThings cannot have keys()."""
			def __init__(self):
				ButtonThing.__init__(self,"testbutton")
				self.addStates({"normal":ArrowButtonN(),"over":ArrowButtonO(),"down":ArrowButtonD(),"up":ArrowButtonU()} )
			def drawHitarea(self,ctx,frame):
				ctx.rectangle(-14,-14,30,30)
			def onButtonUp(self):
				self.parentThing.parentThing.parentThing.goPlay('hide')

		self.add(NextButton())

class IntroText(Thing):
	def __init__(self):
		Thing.__init__(self)
		self.keys ( "#----------------------------------------------------------------#",Props(a=0),Props(a=1))
		self.stops( ".................................................................^")

		## Button appears a little later in the animation:
		self.add( Next(), parentFrame=65, globalProps=Props(x=200,y=240),layer=20)

		fname = "Sans 10"
		
		txt= """Thanks to <b>Cairo</b>, <b>Python</b> and <b>many</b> others, there is now an easy way to produce vector animations in Python code. This library is called "Things" and it's what you are seeing right now.
		
It needs work. It's slow and inefficient. But, oddly, it runs! If it could be <i>converted into a C library</i> "Things" would really start to cook! A GUI timeline &amp; on-canvas designer would then be possible.

"Things" works alongside <b>Inkscape</b>. You can pull items out by id and employ them in the API. You can also add images and font files as you need them.

<b>Please check it out and hack!</b>"""

		self.text = '<span font_desc="%s" foreground="%s">%s</span>' % (fname, CAIROHEXBLUE, txt )

		self.tbox = TextBlock()
		self.tbox.setup(self.text, x=-250, y=40, align=pango.ALIGN_LEFT, width=500)
	def draw(self,ctx,fr):
		self.tbox.draw(ctx)



class BlueBox(Thing):
	def __init__(self):
		Thing.__init__(self)
		self.keys  ( "#-------------------------#==================",Props(sx=0.1),Props())
		self.stops ( "..........................^.................^")
		self.funcs ( ".........................^.^", self.tell,self.dostuff)
		self.labels( "...........................^", "grow")
	
		self.h=1
	def dostuff(self): 
		## Change a flag so draw can do stuff.
		self.h=2

	def tell(self):
		## Tell logo to pop-up.
		self.parentThing.CAIROCLIP.CAIROWORD.play()

	def draw(self,ctx,fr):
		## Rather than tween this box down, I draw it bigger every time, to avoid distortion.
		if self.h > 1:
			fr = self.h
			self.h  += 1
			if self.h > 25: self.h=25

		ctx.rectangle(-260,30,510,((self.h-1)*10))

		# The blue outline that grows.
		ctx.set_line_width(5)
		ctx.set_source_rgb(*CAIROBLUE) # The * means make a list of CAIROBLUE -- so it's passed into the func as three params!
		ctx.stroke_preserve()
		ctx.set_source_rgba(1,1,1,0.7)
		ctx.fill()

class RisingSun(Thing):
	def __init__(self):
		Thing.__init__(self)
		## Starts on a blank + stop frame : i.e. it is not visible at first.
		## Somewhere there will be a command to tell this to play from frame 2.
		self.keys  (  ".#----#--#--------#",Props(a=0,sz=2),Props(sz=0.5),Props(sz=2),Props() )
		self.stops (  "^.................^")
		self.funcs (  ".................^",self.dostuff)

		## Here we add a pre-prepared Thing. It will draw itself.
		self.add( SCARABsh )

	def dostuff(self):
		## A func to tell some other thing to do something.
		self.parentThing.BLUEBOX.goPlay("grow")


class IntroduceLogo(Thing):
	"""
	This is the main Thing in scene 2. It was elected thus when we added it to the scene2 var.
	"""
	def __init__(self, app):
		Thing.__init__(self)
		self.keys  ( "#==============.", Props())
		self.stops ( ".........^.....^")
		## I want to spend some time simply
		## looping so that sub-animations get a chance to
		## finish. Hence this ^.^ cute hello-kitty stuff:
		self.labels( ".^.^......^"            ,"pause","go","hide")
		self.funcs ( "^.^...........^", (BACKDROP.goStop,2), self.Delay, app.playNextScene )
		
		## Add the elements of my animation:
		##  Some are given instance in self because I will refer to them from elsewhere.
		self.BLUEBOX=BlueBox()
		self.add( self.BLUEBOX, layer=12)

		self.CAIROCLIP = ClipWord()
		self.add( self.CAIROCLIP, layer=11)	

		self.SUN=RisingSun()
		self.add( self.SUN, layer=0, globalProps=Props(x=5,y=-70))

		## This one starts on frame 6, just after the delay.
		self.add( IntroText(), layer=15, parentFrame=6) # It's instanced on-the-fly.

		## Used in Delay func.
		self.countdown=60

	def Delay(self):
		## So, we are on frame 3 and this func is called.
		self.countdown -=1
		if self.countdown == 0:
			self.goPlay("go") # all done, continue animation.
		else:
			self.goPlay("pause") # rewind and loop again.



## ----------------------------------- SCENE 1
class BuzzWord(Thing):
	def __init__(self, pFrom, buzz):
		Thing.__init__(self)
		pFrom2 = Props(x=pFrom.y/2, y=pFrom.x/2,sz=5) 
		self.keys  ( "#----------------------#----------------------------------------------------------#",pFrom,Props(),pFrom2)
		## Run a func in myself on the last frame.
		self.funcs ( "..................................................................................^", self.atend)

		self.loops=False
		self.buzz=buzz

		fname = "Serif 11"
		self.text = '<span font_desc="%s" foreground="#ffffff">%s</span>' % (fname, buzz )
		self.tbox = TextBlock()
		self.tbox.setup(self.text, x=0, y=0, align=pango.ALIGN_CENTER)
	def draw(self,ctx,fr):
		self.tbox.draw(ctx)
	def atend(self):
		## I am finished, so tell my parent.
		self.parentThing.atend(self.buzz) # pass my buzz phrase.

class BuzzWords(Thing):
	def __init__(self):
		Thing.__init__(self)
		## We provide a bunch of frames because we want to start manu instances
		## of a Thing -- and space them out every so-many frames.
		self.keys  ( "#=============================",Props())
		self.loops=False

		bzz=["Animation","Vectors","Cairo","Python","Tweening","Keyframes","Simple","API","Things","GPL"]
		for bw in range(0,10):
			x,y=circrandom(600)
			BW = BuzzWord( Props(x=x,y=y,sz=20), bzz[bw] )
			self.add( BW, parentFrame=bw*3) # Here we start each one on different frames; this staggers the animation.

	def atend(self,buzz):
		## Am I done with the animations?
		## only the last one in the list is what we want.
		if buzz=="GPL":
			self.parentThing.play() # We tell the parentThing (FadeStart) to carry on playing now.

class FadeStart(Thing):
	"""
	Start looking here to understand the whole animation.
	"""
	def __init__(self, app):
		Thing.__init__(self)
		## We have a stop on frame 2. The BuzzWords() Thing is playing all the time, but this
		## timeline does not go past frame 2; until we tell it to...
		self.keys  ( "##----------#.", Props(),Props(),Props(a=0,sz=0.1))
		self.stops ( ".^...........^")
		## When this gets to the end, it will run a method of app:
		self.funcs ( "............^", app.playNextScene ) # Off we go to scene2!

		self.add( BuzzWords() )


## Get a Bag of stuff
BOS = BagOfStuff()

# Add stuff to it
BOS.add(os.path.join(os.path.dirname(__file__), "cg.stuff/cairo.svg"),"CG")

## Add Things to app
BACKDROP=Backdrop()

