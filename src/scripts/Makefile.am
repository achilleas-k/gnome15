
if INDICATOR
bin_SCRIPTS = g15-macros g15-config g15-indicator
else
bin_SCRIPTS = g15-macros g15-config
endif

if APPLET
scriptsdir = @libdir@/gnome15
scripts_SCRIPTS = g15-applet
endif
	
EXTRA_DIST = $(scripts_SCRIPTS) \
	$(bin_SCRIPTS)
