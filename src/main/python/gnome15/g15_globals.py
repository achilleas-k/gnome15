#!/usr/bin/env python
 
import os
import sys

name = "gnome15"
version = "0.0.1"
 
package_dir = os.path.abspath(os.path.dirname(__file__))
image_dir = os.path.join(package_dir, "..", "..", "resources", "images" )
if os.path.exists(image_dir): 
    glade_dir = os.path.join(package_dir, "..", "..", "resources", "glade" )
    font_dir = os.path.join(package_dir, "..", "..", "resources", "fonts" )
    plugin_dir = os.path.join(package_dir, "..", "..", "..", "plugins" )
else: 
    image_dir = "/usr/share/pixmaps"
    glade_dir = "/usr/share/gnome15"
    font_dir = "/usr/share/gnome15"
    plugin_dir = "/usr/share/gnome15/plugins"
