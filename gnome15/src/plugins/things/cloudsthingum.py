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



## ---- General
SKYHEXBLUE="#aaccff"; SKYBLUE=hexfloat(SKYHEXBLUE)

class BlueSky(DrawThing):
	R = cairo.RadialGradient(0,200,0,0,200,400)
	R.add_color_stop_rgb(0, 1,1,1 )
	R.add_color_stop_rgb(1, *SKYBLUE )
	def draw(self,ctx,fr):
		ctx.set_source( BlueSky.R )
		ctx.paint()

class Cloud1(DrawThing):
	def draw(self,ctx,fr):
		BOS['clouds:cloud1'].draw(ctx)
class Cloud2(DrawThing):
	def draw(self,ctx,fr):
		BOS['clouds:cloud2'].draw(ctx)
	
class Puffer(Thing):
	def __init__(self,smax,smin):
		Thing.__init__(self)
		self.keys("#----------------#----------------------#--------#",Props(),Props(sz=smax),Props(sz=smin),Props() )

class CloudA(Thing):
	def __init__(self):
		Thing.__init__(self)
		self.keys("#" + "-"*190 + "#" + "-"*190 + "#",Props(x=250),Props(x=-250),Props(x=250))
		self.loops=True

		self.P = Puffer(1.5,0.6)
		self.P.add( Cloud1() )
		self.add( self.P)

class CloudB(Thing):
	def __init__(self):
		Thing.__init__(self)
		self.keys("#" + "-"*90 + "#" + "-"*90 + "#",Props(x=-220),Props(x=220),Props(x=-220))
		self.loops=True
		self.P = Puffer(1.2,0.8)
		self.P.add( Cloud2() )
		self.add( self.P)

class HugeCloud(Thing):
	def __init__(self):
		Thing.__init__(self)
		self.keys('#',Props(sz=3,a=0.5, x=-90, y=-80))
		self.add( Cloud1() )

class SpinCity(Thing):
	def __init__(self):
		Thing.__init__(self)
		## Let's use the Python multiply string trick to get lots of tween frames:
		self.keys  ( "#" + "-"*250 + "#",  Props(), Props(rot=-pi2))
		
	def draw(self,ctx,fr):
		BOS['clouds:city'].draw(ctx)

## Here we use two LoopThings.
class Walking(LoopThing):
	## The legs - on the loops->walkloop layer in the Inkscape SVG file.
	def __init__(self):
		LoopThing.__init__(self)
		self.keys("#--#---#---#---#---#----#---#---#---#---#===",Props(),Props(),Props(),Props(),Props(),Props(),Props(),Props(),Props(),Props(),Props())

		self.addLoop( BOS["clouds:walkloop"])
class Torso(LoopThing):
	## The 'torso' -- loops->torsoloop layer in the SVG
	def __init__(self):
		LoopThing.__init__(self)
		self.keys("#--#---#---#",Props(),Props(),Props(),Props())

		self.addLoop( BOS["clouds:torsoloop"])

class Walker(Thing):
	def __init__(self):
		Thing.__init__(self)
		self.keys('#',Props())
		self.add( Walking() )
		self.add( Torso(), globalProps=Props(x=-10, y=10) )

class Madness(Thing):
	### This is our 'main' Thing. It holds all the action.
	def __init__(self):
		Thing.__init__(self)
		self.keys("#",Props())
		self.loops = False

		self.add( SpinCity(), globalProps=Props(y=250,sz=1.3), layer=10)
		self.add( CloudA(), layer=5 )
		self.add( CloudB(), layer=20 )
		self.add( HugeCloud(), layer=1)

		self.add( Walker(), globalProps=Props(sz=1, y=100),layer=30 )

## BEGIN THE APP

## Get a Bag of stuff
BOS = BagOfStuff()

# Add stuff to it
BOS.add(os.path.join(os.path.dirname(__file__), "clouds.stuff/clouds.svg"),"clouds")
