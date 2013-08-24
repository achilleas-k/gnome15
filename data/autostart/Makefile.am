if ENABLE_SYSTEMTRAY
    MAYBE_SYSTEMTRAY = g15-systemtray.desktop
endif
if ENABLE_INDICATOR
    MAYBE_INDICATOR = g15-indicator.desktop
endif

autostartdir = $(sysconfdir)/xdg/autostart
autostart_DATA = gnome15.desktop $(MAYBE_SYSTEMTRAY) $(MAYBE_INDICATOR)

EXTRA_DIST =  			\
	gnome15.desktop g15-systemtray.desktop g15-indicator.desktop
