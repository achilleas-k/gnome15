#!/usr/bin/env python
 
#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) Brett Smith <tanktarta@blueyonder.co.uk>                      |
#        |                                                                             |
#        | This program is free software; you can redistribute it and/or               |
#        | modify it under the terms of the GNU General Public License                 |
#        | as published by the Free Software Foundation; either version 2              |
#        | of the License, or (at your option) any later version.                      |
#        |                                                                             |
#        | This program is distributed in the hope that it will be useful,             |
#        | but WITHOUT ANY WARRANTY; without even the implied warranty of              |
#        | MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               |
#        | GNU General Public License for more details.                                |
#        |                                                                             |
#        | You should have received a copy of the GNU General Public License           |
#        | along with this program; if not, write to the Free Software                 |
#        | Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA. |
#        +-----------------------------------------------------------------------------+

import os,time,Image,ImageDraw,ImageFont,sys,ImageOps,ImageMath,ImageSequence,time

import g15_daemon
import g15_globals as pglobals

FONT_TINY=4
FONT_SMALL=1
FONT_MEDIUM=2
FONT_LARGE=3

LEFT = 0
RIGHT = -1
CENTER = -2
TOP = 0
BOTTOM = -1


class G15Draw:

	def __init__(self, driver):
		self.draw = None
		self.driver = driver
		
		self.font_family="helvB"
		self.tiny_font = ImageFont.load(os.path.join(pglobals.font_dir, "ucs07.pil"))
		self.small_font = ImageFont.load(os.path.join(pglobals.font_dir, self.font_family + "08.pil"))
		self.medium_font = ImageFont.load(os.path.join(pglobals.font_dir, self.font_family + "14.pil"))
		self.large_font = ImageFont.load(os.path.join(pglobals.font_dir, self.font_family + "24.pil"))
		
		self.set_font_size()
		self.clear()
		
	def set_font(self, font):
		self.font = font
		
	def set_font_size(self, size=FONT_SMALL):
		if size == FONT_TINY:
			self.font = self.tiny_font
		elif size == FONT_SMALL:
			self.font = self.small_font
		elif size == FONT_MEDIUM:
			self.font = self.medium_font 
		elif size == FONT_LARGE:
			self.font = self.large_font
		
	def clear(self, color="White"):
		self.img = Image.new("RGBA", self.driver.get_size(), color)	
		self.draw = ImageDraw.Draw(self.img)

	def fill_box(self, geometry, color="Black", outline=None):
		if outline == None:
			outline = color
		self.draw.rectangle(geometry, fill=color, outline=outline)
		
		
	def draw_line(self, geometry, color="Black"):
		self.draw.line(geometry, fill=color)
	
	def draw_box(self, geometry, color="Black"):
		self.draw.rectangle(geometry, outline=color)
		
	def draw_image_from_file(self, file, box, size=None):		
		self.draw_image(Image.open(file), box, size)
		
	def process_image_from_file(self, file, size=None):		
		return self.process_image(Image.open(file), size)
	
	def process_image(self, image, size=None):
		if size != None:
			image = image.resize( ( size[0],size[1] ) ,Image.NEAREST)
		return image
		
	def draw_image(self, image, box, size=None, process=True, mask=False):
		if process:
			image = self.process_image(image,  size)
		if mask:
			self.img.paste(image, box, image)
		else:
			self.img.paste(image, box)
	
	def draw_text(self, text, xy, color="Black", inset_x=0, inset_y=0, clear=None, emboss=None):
		x = xy[0]
		y = xy[1]
		lcd_w = self.driver.get_size()[0]
		lcd_h =  self.driver.get_size()[1]
		text_size = self.draw.textsize(text, self.font)
		if clear != None:
			self.fill_box([xy, (xy[0] + text_size[0], xy[1] + text_size[1])], clear)
		if x == RIGHT:
			x = lcd_w - text_size[0] - inset_x
		elif x == CENTER:
			x = ( lcd_w / 2 ) - ( text_size[0] / 2 ) + inset_x
		else:
			x += inset_x
		if y == BOTTOM:
			y = lcd_h - text_size[1] - inset_y
		elif y == CENTER:
			y = ( lcd_h / 2 ) - ( text_size[1] / 2 ) + inset_y
		else:
			y += inset_y
		if emboss != None:
			for xx in range(0, 3):
				for yy in range(0, 3):
					self.draw.text((x + xx - 1, y + yy - 1), text, emboss, self.font)
		self.draw.text((x, y), text, color, self.font)