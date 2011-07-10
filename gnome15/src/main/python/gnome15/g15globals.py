import os

name = "gnome15"
version = "0.7.3"

package_dir = os.path.abspath(os.path.dirname(__file__))
image_dir = os.path.join(package_dir, "..", "..", "resources", "images" )
dev = False
if os.path.exists(image_dir):
	dev = True 
	glade_dir = os.path.realpath(os.path.join(package_dir, "..", "..", "resources", "glade"))
	font_dir = os.path.realpath(os.path.join(package_dir, "..", "..", "resources", "fonts"))
	icons_dir = os.path.realpath(os.path.join(package_dir, "..", "..", "resources", "icons"))
	themes_dir = os.path.realpath(os.path.join(package_dir, "..", "..", "resources", "themes"))
	plugin_dir = os.path.realpath(os.path.join(package_dir, "..", "..", "..", "plugins"))
	scripts_dir = os.path.realpath(os.path.join(package_dir, "..", "..", "..", "scripts"))
	themes_dir = os.path.realpath(os.path.join(package_dir, "..", "..", "..", "themes"))
else: 
	image_dir = "/usr/share/gnome15/images"
	glade_dir = "/usr/share/gnome15/glade"
	font_dir = "/usr/share/gnome15"
	plugin_dir = "/usr/share/gnome15/plugins"
	themes_dir = "/usr/share/gnome15/themes"
	icons_dir = "/usr/share/icons"
	scripts_dir = "/usr/bin"

# Font family has different name on Fedora and probably others. 
fixed_size_font_name = "Fixed"
if os.path.exists("/usr/share/fonts/ucs-miscfixed"):
    fixed_size_font_name = "MiscFixed"
