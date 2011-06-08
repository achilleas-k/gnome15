if ENABLE_DRIVER_KERNEL
    systemdbusdir = $(sysconfdir)/dbus-1/system.d
    systemdbus_DATA = g15-desktop-service.conf
    MAYBE_KERNEL = org.gnome15.SystemService.service
endif 

dbusdir = $(datadir)/dbus-1/services
dbus_DATA = org.gnome15.Gnome15.service $(MAYBE_KERNEL)

EXTRA_DIST =  			\
	$(dbus_DATA) g15-desktop-service.conf
