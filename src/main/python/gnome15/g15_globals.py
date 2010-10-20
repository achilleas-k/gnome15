#!/usr/bin/env python
 
import os
import sys

name = "gnome15"
version = "0.0.5"
 
package_dir = os.path.abspath(os.path.dirname(__file__))
image_dir = os.path.join(package_dir, "..", "..", "resources", "images" )
dev = False
if os.path.exists(image_dir):
	dev = True 
	glade_dir = os.path.join(package_dir, "..", "..", "resources", "glade")
	font_dir = os.path.join(package_dir, "..", "..", "resources", "fonts")
	icons_dir = os.path.join(package_dir, "..", "..", "resources", "icons")
	plugin_dir = os.path.join(package_dir, "..", "..", "..", "plugins")
else: 
	image_dir = "/usr/share/gnome15/images"
	glade_dir = "/usr/share/gnome15/glade"
	font_dir = "/usr/share/gnome15"
	plugin_dir = "/usr/share/gnome15/plugins"
	icons_dir = "/usr/share/icons/hicolor/scalable/"
