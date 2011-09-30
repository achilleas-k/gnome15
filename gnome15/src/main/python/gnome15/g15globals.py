import os

name = "gnome15"
version = "0.8.0"

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
	i18n_dir = os.path.realpath(os.path.join(package_dir, "..", "..", "..", "i18n"))
else: 
	image_dir = "/usr/local/share/gnome15/images"
	glade_dir = "/usr/local/share/gnome15/glade"
	font_dir = "/usr/local/share/gnome15"
	plugin_dir = "/usr/local/share/gnome15/plugins"
	themes_dir = "/usr/local/share/gnome15/themes"
	i18n_dir = "/usr/local/share/gnome15/i18n"
	icons_dir = "/usr/local/share/icons"
	scripts_dir = "/usr/local/bin"

# Differs from distro to distro, and so is a ./configure option. See
# --enable-fixed-size-font=[name] 
fixed_size_font_name = "Fixed"
