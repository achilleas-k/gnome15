if ENABLE_DRIVER_KERNEL
    systemdbusconfdir = $(sysconfdir)/dbus-1/system.d
    systemdbusconf_DATA = g15-system-service.conf
    systemdbusdir = $(datadir)/dbus-1/system-services
    systemdbus_DATA = org.gnome15.SystemService.service
endif 

dbusdir = $(datadir)/dbus-1/services
dbus_DATA = org.gnome15.Gnome15.service
EXTRA_DIST =  org.gnome15.Gnome15.service org.gnome15.SystemService.service g15-system-service.conf
