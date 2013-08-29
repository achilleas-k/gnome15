AC_INIT(gnome15, 0.9.5, https://projects.russo79.com/projects/gnome15/issues/new)
AC_CONFIG_SRCDIR([src/gnome15/g15service.py])
AM_INIT_AUTOMAKE([tar-ustar])
AM_MAINTAINER_MODE

AC_CONFIG_MACRO_DIR([m4])

dnl
dnl Dependencies
dnl

dnl C compiler toolchain
AC_PROG_LIBTOOL
AC_PROG_CC

dnl Python
AM_PATH_PYTHON
AX_PYTHON_DEVEL([2.6])

dnl Python modules (mandatory)
PKG_CHECK_MODULES(PYGTK, pygtk-2.0)
AC_SUBST(PYGTK_CFLAGS)
AC_SUBST(PYGTK_LIBS)

AX_PYTHON_MODULE(keyring, [])
AS_IF([test "x${HAVE_PYMOD_KEYRING}" = "xno"],
	[AC_MSG_ERROR([Requires Python Keyring Library])])

AX_PYTHON_MODULE(virtkey, [])
AS_IF([test "x${HAVE_PYMOD_VIRTKEY}" = "xno"],
	[AC_MSG_ERROR([Requires Python Virtkey Library])])

AX_PYTHON_MODULE(Image, [])
AS_IF([test "x${HAVE_PYMOD_IMAGE}" = "xno"],
	[AC_MSG_ERROR([Requires Python Image Library])])

AX_PYTHON_MODULE(cairo, [])
AS_IF([test "x${HAVE_PYMOD_CAIRO}" = "xno"],
	[AC_MSG_ERROR([Requires Python bindings for the Cairo vector graphics library])])

AX_PYTHON_MODULE(dbus, [])
AS_IF([test "x${HAVE_PYMOD_DBUS}" = "xno"],
	[AC_MSG_ERROR([Requires DBUS bindings for Python])])

AX_PYTHON_MODULE(pyinotify, [])
AS_IF([test "x${HAVE_PYMOD_PYINOTIFY}" = "xno"],
	[AC_MSG_ERROR([Requires Pyinotify bindings for Python])])

AX_PYTHON_MODULE(lxml, [])
AS_IF([test "x${HAVE_PYMOD_LXML}" = "xno"],
	[AC_MSG_ERROR([Requires LXML bindings for Python])])

AX_PYTHON_MODULE(gobject, [])
AS_IF([test "x${HAVE_PYMOD_GOBJECT}" = "xno"],
	[AC_MSG_ERROR([Requires GObject for Python])])

AX_PYTHON_MODULE(xdg, [])
AS_IF([test "x${HAVE_PYMOD_XDG}" = "xno"],
	[AC_MSG_ERROR([Requires Python XDG])])

AX_PYTHON_MODULE(usb, [])
AS_IF([test "x${HAVE_PYMOD_USB}" = "xno"],
	[AC_MSG_ERROR([Requires PyUSB, python bindings for libusb])])

AX_PYTHON_MODULE(gconf, [])
AS_IF([test "x${HAVE_PYMOD_GCONF}" = "xno"],
	[AC_MSG_ERROR([Requires GConf bindings for Python])])

AX_PYTHON_MODULE(rsvg, [])
AS_IF([test "x${HAVE_PYMOD_RSVG}" = "xno"],
	[AC_MSG_ERROR([Requires RSVG for Python])])

AX_PYTHON_MODULE(pango, [])
AS_IF([test "x${HAVE_PYMOD_PANGO}" = "xno"],
	[AC_MSG_ERROR([Requires Pango for Python])])

AX_PYTHON_MODULE(uinput, [])
AS_IF([test "x${HAVE_PYMOD_UINPUT}" = "xno"],
	[AC_MSG_ERROR([Requires Python uinput and libsuinput])])

AX_PYTHON_MODULE(Xlib, [])
AS_IF([test "x${HAVE_PYMOD_XLIB}" = "xno"],
	[AC_MSG_ERROR([Requires Python Xlib - Python Xlib bindings])])

dnl Python modules (optional)
AX_PYTHON_MODULE(setproctitle, [])
AS_IF([test "x${HAVE_PYMOD_SETPROCTITLE}" = "xno"],
	[AC_MSG_WARN([It is recommend that setproctitle is installed])])

AX_PYTHON_MODULE(pyudev, [])
AS_IF([test "x${HAVE_PYUDEV}" = "xno"],
	[AC_MSG_WARN([It is recommended that PyUdev is installed. Without this, there will be no hot-plugging support])])

dnl Python modules (mandatory for some drivers)
AX_PYTHON_MODULE(pyinputevent, [])
AS_IF([test "x${HAVE_PYMOD_PYINPUTEVENT}" = "xyes"],
	[have_pyinputevent=yes],
	[have_pyinputevent=no])

dnl Python modules (mandatory for some plugins)
AX_PYTHON_MODULE(gst, [])
AS_IF([test "x${HAVE_PYMOD_GST}" = "xyes"],
	[have_gst=yes],
	[have_gst=no])

AX_PYTHON_MODULE(appindicator, [])
AS_IF([test "x${HAVE_PYMOD_APPINDICATOR}" = "xyes"],
	[have_appindicator=yes],
	[have_appindicator=no])

AX_PYTHON_MODULE(telepathy, [])
AS_IF([test "x${HAVE_PYMOD_TELEPATHY}" = "xyes"],
	[have_telepathy=yes],
	[have_telepathy=no])

AX_PYTHON_MODULE(alsaaudio, [])
AS_IF([test "x${HAVE_PYMOD_ALSAAUDIO}" = "xyes"],
	[have_alsaaudio=yes],
	[have_alsaaudio=no])

AX_PYTHON_MODULE(feedparser, [])
AS_IF([test "x${HAVE_PYMOD_FEEDPARSER}" = "xyes"],
	[have_feedparser=yes],
	[have_feedparser=no])

AX_PYTHON_MODULE(vobject, [])
AS_IF([test "x${HAVE_PYMOD_VOBJECT}" = "xyes" ],
	[have_vobject=yes],
	[have_vobject=no])

AX_PYTHON_MODULE(gdata.calendar, [])
AS_IF([test "x${HAVE_PYMOD_GDATA_CALENDAR}" = "xyes" ],
	[have_gdata_calendar=yes],
	[have_gdata_calendar=no])

AX_PYTHON_MODULE(gdata.analytics, [])
AS_IF([test "x${HAVE_PYMOD_GDATA_ANALYTICS}" = "xyes" ],
	[have_gdata_analytics=yes],
	[have_gdata_analytics=no])

AX_PYTHON_MODULE(cairoplot, [])
AS_IF([test "x${HAVE_PYMOD_CAIROPLOT}" = "xyes" ],
	[have_cairoplot=yes],
	[have_cairoplot=no])

AX_PYTHON_MODULE(sensors, [])
AS_IF([test "x${HAVE_PYMOD_SENSORS}" = "xyes" ],
	[have_sensors=yes],
	[have_sensors=no])

dnl libg15 (Gnome15 version)
AC_SEARCH_LIBS(initLibG15, g15,
	[have_libg15=yes],
	[have_libg15=no])

dnl fftw3
AC_CHECK_HEADER(fftw3.h,
	[have_fftw3_header=yes],
	[have_fftw3_header=no])

AC_CHECK_LIB([fftw3], fftw_execute,
	[have_fftw3=yes],
	[have_fftw3=no])

dnl libpulse
AC_CHECK_LIB([pulse], pa_stream_new,
	[have_pulse=yes],
	[have_pulse=no])

dnl
dnl Parse configure arguments
dnl

dnl Enabled locales
AC_ARG_VAR(ENABLED_LOCALES, [List of locales to enable])
AS_IF([test -z "${ENABLED_LOCALES}"],
	AC_SUBST([ENABLED_LOCALES], [en_GB]))

dnl Name of Fixed size font
AC_ARG_VAR(FIXED_SIZE_FONT, [Font to use for fixed fonts. Defaults to Fixed])
AS_IF([test -z "${FIXED_SIZE_FONT}"],
	AC_SUBST([FIXED_SIZE_FONT], [Fixed]))

dnl udev file path and settings
AC_ARG_VAR(UDEV_RULES_PATH, [Path for udev rules. Defaults to /lib/udev/rules.d])
AS_IF([test -z "${UDEV_RULES_PATH}"],
	AC_SUBST([UDEV_RULES_PATH], [/lib/udev/rules.d]))
AC_ARG_VAR(DEVICEGROUP, [Group that the devices will be owned by. Defaults to plugdev])
AS_IF([test -z "${DEVICEGROUP}"],
	AC_SUBST([DEVICEGROUP], [plugdev]))
AC_ARG_VAR(DEVICEMODE, [Permissions of the devices. Defaults to 0660])
AS_IF([test -z "${DEVICEMODE}"],
	AC_SUBST([DEVICEMODE], [0660]))

dnl Drivers
AC_ARG_ENABLE([driver-kernel],
	[AS_HELP_STRING([--enable-driver-kernel],
		[Enable Kernel driver support (requires pyinputevent and lg4l kernel drivers).])],
	[case "${enableval}" in
		yes) driver_kernel=yes ;;
		no)  driver_kernel=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-driver-kernel]) ;;
	esac],
	[driver_kernel=${have_pyinputevent}])
AS_IF([test "x${driver_kernel}" = "xyes" -a "x$have_pyinputevent" = "xno"],
	[AC_MSG_ERROR([kernel driver cannot be built without pyinputevent])])
AM_CONDITIONAL([ENABLE_DRIVER_KERNEL], [test x$driver_kernel = xyes])
     
AC_ARG_ENABLE([driver-g19direct],
	[AS_HELP_STRING([--enable-driver-g19direct],
		[Enable G19Direct driver support.])],
	[case "${enableval}" in
		yes) driver_g19direct=yes ;;
		no)  driver_g19direct=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-driver-g19direct]) ;;
	esac],
	[driver_g19direct=yes])
AM_CONDITIONAL([ENABLE_DRIVER_G19DIRECT], [test x$driver_g19direct = xyes])

AC_ARG_ENABLE([driver-g930],
	[AS_HELP_STRING([--enable-driver-g930],
		[Enable G930 headset driver support])],
	[case "${enableval}" in
		yes) driver_g930=yes ;;
		no)  driver_g930=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-driver-g930]) ;;
 	esac],
	[driver_g930=yes])
AM_CONDITIONAL([ENABLE_DRIVER_G930], [test x$driver_g930 = xyes])

AC_ARG_ENABLE([driver-g15direct],
	[AS_HELP_STRING([--enable-driver-g15direct],
		[Enable G15 direct driver support (requires libg15).])],
	[case "${enableval}" in
		yes) driver_g15direct=yes ;;
		no)  driver_g15direct=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-driver-g15direct]) ;;
	esac],
	[driver_g15direct=${have_libg15}])
AS_IF([test "x${driver_g15direct}" = "xyes" -a "x$have_libg15" = "xno"],
	[AC_MSG_ERROR([g5direct driver cannot be built without libg15])])
AM_CONDITIONAL([ENABLE_DRIVER_G15DIRECT], [test x$driver_g15direct = xyes])
     
dnl System Tray
AC_ARG_ENABLE([systemtray],
	[AS_HELP_STRING([--enable-systemtray],
		[Enable System Tray panel integration.])],
	[case "${enableval}" in
		yes) systemtray=yes ;;
		no)  systemtray=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-systemtray]) ;;
	esac],
	systemtray=yes)
AM_CONDITIONAL([ENABLE_SYSTEMTRAY], [test x$systemtray = xyes])

dnl Ubuntu Indicator
AC_ARG_ENABLE([indicator],
	[AS_HELP_STRING([--enable-indicator],
		[Enable Ubuntu Indicator integration.])],
	[case "${enableval}" in
		yes) indicator=yes ;;
		no)  indicator=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-indicator]) ;;
	esac],
	indicator=yes)
AS_IF([test "x${indicator}" = "xyes" -a "x$have_appindicator" = "xno"],
	[AC_MSG_ERROR([Ubuntu indicator cannot be built without appindicator python module])])
AM_CONDITIONAL([ENABLE_INDICATOR], [test x$indicator = xyes])

dnl Gnome Shell Extension
AC_ARG_ENABLE([gnome-shell-extension],
	[AS_HELP_STRING([--enable-gnome-shell-extension],
		[Enable Gnome Shell extension.])],
	[case "${enableval}" in
		yes) gnome_shell_extension=yes ;;
		no)  gnome_shell_extension=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-gnome-shell-extension]) ;;
	esac],
	gnome_shell_extension=yes)
AM_CONDITIONAL([ENABLE_GNOME_SHELL_EXTENSION], [test x$gnome_shell_extension = xyes])

dnl Icons

AC_ARG_ENABLE([icons-awoken],
	[AS_HELP_STRING([--enable-icons-awoken],
		[Build and deploy awoken icons.])],
	[case "${enableval}" in
		yes) icons_awoken=yes ;;
		no)  icons_awoken=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-icons-awoken]) ;;
	esac],
	[icons_awoken=no])
AM_CONDITIONAL([ENABLE_ICONS_AWOKEN], [test x$icons_awoken = xyes])

AC_ARG_ENABLE([icons-mono],
	[AS_HELP_STRING([--enable-icons-mono],
		[Build and deploy monochrome icons.])],
	[case "${enableval}" in
		yes) icons_mono=yes ;;
		no)  icons_mono=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-icons-mono]) ;;
	esac],
	[icons_mono=yes])
AM_CONDITIONAL([ENABLE_ICONS_MONO], [test x$icons_mono = xyes])

dnl
dnl Plugins
dnl

dnl Each plugin by default is only enabled
dnl if dependencies are available. Each plugin may also be
dnl individually enabled / disabled using configure options

dnl Background plugin
AC_ARG_ENABLE([plugin-background],
	[AS_HELP_STRING([--enable-plugin-background],
		[Enable Background plugin.])],
	[case "${enableval}" in
		yes) plugin_background=yes ;;
		no)  plugin_background=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-background]) ;;
	esac],
	[plugin_background=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_BACKGROUND], [test x$plugin_background = xyes])

dnl Cairo Clock plugin
AC_ARG_ENABLE([plugin-cairo-clock],
	[AS_HELP_STRING([--enable-plugin-cairo-clock],
		[Enable Cairo Clock plugin.])],
	[case "${enableval}" in
		yes) plugin_cairo_clock=yes ;;
		no)  plugin_cairo_clock=no ;;
		*)  AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-cairo-clock]) ;;
	esac],
	[plugin_cairo_clock=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_CAIRO_CLOCK], [test x$plugin_cairo_clock = xyes])

dnl Clock plugin
AC_ARG_ENABLE([plugin-clock],
	[AS_HELP_STRING([--enable-plugin-clock],
		[Enable Simple Clock plugin (plugin used in website example).])],
	[case "${enableval}" in
		yes) plugin_clock=yes ;;
		no)  plugin_clock=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-clock]) ;;
	esac],
	[plugin_clock=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_CLOCK], [test x$plugin_clock = xyes])

dnl Special effects plugin
AC_ARG_ENABLE([plugin-fx],
	[AS_HELP_STRING([--enable-plugin-fx],
		[Enable Special Effects plugin.])],
	[case "${enableval}" in
		yes) plugin_fx=yes ;;
		no)  plugin_fx=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-fx]) ;;
	esac],
	[plugin_fx=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_FX], [test x$plugin_fx = xyes])

dnl G15daemon Server plugin
AC_ARG_ENABLE([plugin-g15daemon-server],
	[AS_HELP_STRING([--enable-plugin-g15daemon-server],
		[Enable G15Daemon Server plugin (network server with protocol compatible with g15daemon, allows g15daemon scripts to be used when it is not installed).])],
	[case "${enableval}" in
		yes) plugin_g15daemon_server=yes ;;
		no)  plugin_g15daemon_server=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-g15daemon-server]) ;;
	esac],
	[plugin_g15daemon_server=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_G15DAEMON_SERVER], [test x$plugin_g15daemon_server = xyes])

dnl Instant Messenger plugin
AC_ARG_ENABLE([plugin-im],
	[AS_HELP_STRING([--enable-plugin-im],
		[Enable Instant Messenger plugin. Displays current contact list and status (currently works with Telepathy framework based clients).])],
	[case "${enableval}" in
		yes) plugin_im=yes ;;
		no)  plugin_im=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-im]) ;;
	esac],
	[plugin_im=${have_telepathy}])
AS_IF([test "x${plugin_im}" = "xyes" -a "x$have_telepathy" = "xno"],
	[AC_MSG_ERROR([Plugin Instant Messenger cannot be built without telepathy python module])])
AM_CONDITIONAL([ENABLE_PLUGIN_IM], [test x$plugin_im = xyes])

dnl Macro Recorder plugin
AC_ARG_ENABLE([plugin-macro-recorder],
	[AS_HELP_STRING([--enable-plugin-macro-recorder],
		[Enable Macro Recorder plugin.])],
	[case "${enableval}" in
		yes) plugin_macro_recorder=yes ;;
		no)  plugin_macro_recorder=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-macro-recorder]) ;;
	esac],
	[plugin_macro_recorder=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_MACRO_RECORDER], [test x$plugin_macro_recorder = xyes])

dnl Macro Display plugin
AC_ARG_ENABLE([plugin-macros],
	[AS_HELP_STRING([--enable-plugin-macros],
		[Enable Macro Display plugin.])],
	[case "${enableval}" in
		yes) plugin_macros=yes ;;
		no)  plugin_macros=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-macros]) ;;
	esac],
	[plugin_macros=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_MACROS], [test x$plugin_macros = xyes])

dnl Profile selection plugin
AC_ARG_ENABLE([plugin-profiles],
	[AS_HELP_STRING([--enable-plugin-profiles],
		[Enable profile selector plugin.])],
	[case "${enableval}" in
		yes) plugin_profiles=yes ;;
		no)  plugin_profiles=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-profiles]) ;;
	esac],
	[plugin_profiles=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_PROFILES], [test x$plugin_profiles = xyes])

dnl Menu plugin
AC_ARG_ENABLE([plugin-menu],
	[AS_HELP_STRING([--enable-plugin-menu],
		[Enable Menu plugin.])],
	[case "${enableval}" in
		yes) plugin_menu=yes ;;
		no)  plugin_menu=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-menu]) ;;
	esac],
	[plugin_menu=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_MENU], [test x$plugin_menu = xyes])

dnl Mounts plugin
AC_ARG_ENABLE([plugin-mounts],
	[AS_HELP_STRING([--enable-plugin-mounts],
		[Enable Mounts plugin.])],
	[case "${enableval}" in
		yes) plugin_mounts=yes ;;
		no)  plugin_mounts=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-mounts]) ;;
	esac],
	[plugin_mounts=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_MOUNTS], [test x$plugin_mounts = xyes])

dnl MPRIS plugin
AC_ARG_ENABLE([plugin-mpris],
	[AS_HELP_STRING([--enable-plugin-mpris],
		[Enable MPRIS plugin. Displays currently playing media players that support MPRIS])],
	[case "${enableval}" in
		yes) plugin_mpris=yes ;;
		no)  plugin_mpris=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-mpris]) ;;
	esac],
	[plugin_mpris=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_MPRIS], [test x$plugin_mpris = xyes])

dnl Notify plugin
AC_ARG_ENABLE([plugin-notify-lcd],
	[AS_HELP_STRING([--enable-plugin-notify-lcd],
		[Enable Notify LCD plugin. Takes over as notification daemon and displays messages on LCD, blinks keyboard])],
	[case "${enableval}" in
		yes) plugin_notify_lcd=yes ;;
		no)  plugin_notify_lcd=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-notify-lcd]) ;;
	esac],
	[plugin_notify_lcd=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_NOTIFY_LCD], [test x$plugin_notify_lcd = xyes])

dnl Panel plugin
AC_ARG_ENABLE([plugin-panel],
	[AS_HELP_STRING([--enable-plugin-panel],
		[Enable Panel plugin. Reserves area of screen for other plugins to display permanent information])],
	[case "${enableval}" in
		yes) plugin_panel=yes ;;
		no)  plugin_panel=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-panel]) ;;
	esac],
	[plugin_panel=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_PANEL], [test x$plugin_panel = xyes])

dnl Screensaver plugin
AC_ARG_ENABLE([plugin-screensaver],
	[AS_HELP_STRING([--enable-plugin-screensaver],
		[Enable Screensaver plugin. Displays mesage and dims keyboard when desktop screesaver is activated])],
	[case "${enableval}" in
		yes) plugin_screensaver=yes ;;
		no)  plugin_screensaver=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-screensaver]) ;;
	esac],
	[plugin_screensaver=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_SCREENSAVER], [test x$plugin_screensaver = xyes])

dnl Stopwatch plugin
AC_ARG_ENABLE([plugin-stopwatch],
	[AS_HELP_STRING([--enable-plugin-stopwatch],
		[Enable Stopwatch plugin. Dual mode, dual timer stopwatch])],
	[case "${enableval}" in
		yes) plugin_stopwatch=yes ;;
		no)  plugin_stopwatch=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-stopwatch]) ;;
	esac],
	[plugin_stopwatch=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_STOPWATCH], [test x$plugin_stopwatch = xyes])

dnl Media Player plugin
AC_ARG_ENABLE([plugin-mediaplayer],
	[AS_HELP_STRING([--enable-plugin-mediaplayer],
		[Enable Media Player plugin. Requires GStreamer])],
	[case "${enableval}" in
		yes) plugin_mediaplayer=yes ;;
		no)  plugin_mediaplayer=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-mediaplayer]) ;;
	esac],
	[plugin_mediaplayer=${have_gst}])
AS_IF([test "x${plugin_mediaplayer}" = "xyes" -a "x$have_gst" = "xno"],
	[AC_MSG_ERROR([Plugin Mediaplayer cannot be built without gst python module])])
AM_CONDITIONAL([ENABLE_PLUGIN_MEDIAPLAYER], [test x$plugin_mediaplayer = xyes])

dnl Weather plugin
AC_ARG_ENABLE([plugin-weather],
	[AS_HELP_STRING([--enable-plugin-weather],
		[Enable Weather plugin. Requires additional backend plugin such as weather-noaa])],
	[case "${enableval}" in
		yes) plugin_weather=yes ;;
		no)  plugin_weather=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-weather]) ;;
	esac],
	[plugin_weather=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_WEATHER], [test x$plugin_weather = xyes])

AC_ARG_ENABLE([plugin-weather-noaa],
	[AS_HELP_STRING([--enable-plugin-weather-noaa],
		[Enable NOAA support for the Weather plugin.])],
	[case "${enableval}" in
		yes) plugin_weather_noaa=yes ;;
		no)  plugin_weather_noaa=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-weather-noaa]) ;;
	esac],
	[plugin_weather_noaa=${plugin_weather}])
AS_IF([test "x${plugin_weather_noaa}" = "xyes" -a "x$plugin_weather" = "xno"],
	[AC_MSG_ERROR([Weather NOAA backend plugin cannot be built without Weather plugin])])
AM_CONDITIONAL([ENABLE_PLUGIN_WEATHER_NOAA], [test x$plugin_weather_noaa = xyes])

AC_ARG_ENABLE([plugin-weather-yahoo],
	[AS_HELP_STRING([--enable-plugin-weather-yahoo],
		[Enable Yahoo support for the Weather plugin.])],
	[case "${enableval}" in
		yes) plugin_weather_yahoo=yes ;;
		no)  plugin_weather_yahoo=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-weather-yahoo]) ;;
	esac],
	[plugin_weather_yahoo=${plugin_weather}])
AS_IF([test "x${plugin_weather_yahoo}" = "xyes" -a "x$plugin_weather" = "xno"],
	[AC_MSG_ERROR([Weather Yahoo backend plugin cannot be built without Weather plugin])])
AM_CONDITIONAL([ENABLE_PLUGIN_WEATHER_YAHOO], [test x$plugin_weather_yahoo = xyes])

dnl Indicator Messages Plugin
AC_ARG_ENABLE([plugin-indicator-messages],
	[AS_HELP_STRING([--enable-plugin-indicator-messages],
		[Enable Indicator Messages plugin.])],
	[case "${enableval}" in
		yes) plugin_indicator_messages=yes ;;
		no)  plugin_indicator_messages=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-indicator-messages]) ;;
	esac],
	[plugin_indicator_messages=${have_appindicator}])
AS_IF([test "x${plugin_indicator_messages}" = "xyes" -a "x$have_appindicator" = "xno"],
	[AC_MSG_ERROR([Plugin Indicator Messages cannot be built without appindicator python module])])
AM_CONDITIONAL([ENABLE_PLUGIN_INDICATOR_MESSAGES], [test x$plugin_indicator_messages = xyes])

dnl ALSA Volume Monitor Plugin
AC_ARG_ENABLE([plugin-volume],
	[AS_HELP_STRING([--enable-volume],
		[Enable ALSA volume monitor plugin. Requires python-alsaaudio])],
	[case "${enableval}" in
		yes) plugin_volume=yes ;;
		no)  plugin_volume=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-volume]) ;;
	esac],
	[plugin_volume=${have_alsaaudio}])
AS_IF([test "x${plugin_volume}" = "xyes" -a "x$have_alsaaudio" = "xno"],
	[AC_MSG_ERROR([Plugin Volume cannot be built without alsaaudio python module])])
AM_CONDITIONAL([ENABLE_PLUGIN_VOLUME], [test x$plugin_volume = xyes])

dnl RSS Plugin
AC_ARG_ENABLE([plugin-rss],
	[AS_HELP_STRING([--enable-plugin-rss],
		[Enable RSS feed plugin. Requires python feedparser])],
	[case "${enableval}" in
		yes) plugin_rss=yes ;;
		no)  plugin_rss=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-rss]) ;;
	esac],
	[plugin_rss=${have_feedparser}])
AS_IF([test "x${plugin_rss}" = "xyes" -a "x$have_feedparser" = "xno"],
	[AC_MSG_ERROR([Plugin RSS cannot be built without feedparser python module])])
AM_CONDITIONAL([ENABLE_PLUGIN_RSS], [test x$plugin_rss = xyes])

dnl System Monitor Plugin
AC_ARG_ENABLE([plugin-sysmon],
	[AS_HELP_STRING([--enable-plugin-sysmon],
		[Enable System Monitor plugin. Recommends python gtop])],
	[case "${enableval}" in
		yes) plugin_sysmon=yes ;;
		no)  plugin_sysmon=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-sysmon]) ;;
	esac],
	[plugin_sysmon=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_SYSMON], [test x$plugin_sysmon = xyes])

dnl Processes Plugin
AC_ARG_ENABLE([plugin-processes],
	[AS_HELP_STRING([--enable-plugin-processes],
		[Enable Processes plugin. Recommends python gtop])],
	[case "${enableval}" in
		yes) plugin_processes=yes ;;
		no)  plugin_processes=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-processes]) ;;
	esac],
	[plugin_processes=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_PROCESSES], [test x$plugin_processes = xyes])

dnl Debug Plugin
AC_ARG_ENABLE([plugin-debug],
	[AS_HELP_STRING([--enable-plugin-debug],
		[Enable Debug plugin.])],
	[case "${enableval}" in
		yes) plugin_debug=yes ;;
		no)  plugin_debug=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-debug]) ;;
	esac],
	[plugin_debug=no])
AM_CONDITIONAL([ENABLE_PLUGIN_DEBUG], [test x$plugin_debug = xyes])

dnl Calendar plugin (base)
AC_ARG_ENABLE([plugin-cal],
	[AS_HELP_STRING([--enable-plugin-cal],
		[Enable calendar plugin. (required for any calendar support)])],
	[case "${enableval}" in
		yes) plugin_cal=yes ;;
		no)  plugin_cal=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-cal]) ;;
	esac],
	[plugin_cal=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_CAL], [test x$plugin_cal = xyes])

dnl Evolution Calendar plugin
AS_IF([test "x${plugin_cal}" = "xyes" -a "x${have_vobject}" = "xyes" ],
	  [deps_plugin_cal_evolution=yes],
	  [deps_plugin_cal_evolution=no])
AC_ARG_ENABLE([plugin-cal-evolution],
	[AS_HELP_STRING([--enable-plugin-cal-evolution],
		[Enable Evolution calendar plugin. Requires python vobject])],
	[case "${enableval}" in
		yes) plugin_cal_evolution=yes ;;
		no)  plugin_cal_evolution=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-cal-evolution]) ;;
	esac],
	[plugin_cal_evolution=${deps_plugin_cal_evolution}])
AS_IF([test "x${plugin_cal_evolution}" = "xyes" -a "x$plugin_cal" = "xno"],
	[AC_MSG_ERROR([Plugin Evolution calendar cannot be built without Calendar plugin])])
AS_IF([test "x${plugin_cal_evolution}" = "xyes" -a "x$have_vobject" = "xno"],
	[AC_MSG_ERROR([Plugin Evolution calendar cannot be built without vobject python module])])
AM_CONDITIONAL([ENABLE_PLUGIN_CAL_EVOLUTION], [test x$plugin_cal_evolution = xyes])

dnl Google Calendar plugin
AS_IF([test "x${plugin_cal}" = "xyes" -a "x${have_gdata_calendar}" = "xyes" ],
	  [deps_plugin_cal_google=yes],
	  [deps_plugin_cal_google=no])
AC_ARG_ENABLE([plugin-cal-google],
	[AS_HELP_STRING([--enable-plugin-cal-google],
		[Enable Google calendar plugin. Requires calendar plugin, python gdata])],
	[case "${enableval}" in
		yes) plugin_cal_google=yes ;;
		no)  plugin_cal_google=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-cal-google]) ;;
	esac],
	[plugin_cal_google=${deps_plugin_cal_google}])
AS_IF([test "x${plugin_cal_google}" = "xyes" -a "x$plugin_cal" = "xno"],
	[AC_MSG_ERROR([Plugin Google calendar cannot be built without Calendar plugin])])
AS_IF([test "x${plugin_cal_google}" = "xyes" -a "x$have_gdata_calendar" = "xno"],
	[AC_MSG_ERROR([Plugin Google calendar cannot be built without gdata python modules])])
AM_CONDITIONAL([ENABLE_PLUGIN_CAL_GOOGLE], [test x$plugin_cal_google = xyes])

dnl Google Analytics plugin
AS_IF([test "x${have_gdata_analytics}" = "xyes" -a "x${have_cairoplot}" = "xyes" ],
	  [deps_plugin_google_analytics=yes],
	  [deps_plugin_google_analytics=no])
AC_ARG_ENABLE([plugin-google-analytics],
	[AS_HELP_STRING([--enable-plugin-google-analytics],
		[Enable Google Analytics plugin. Requires python gdata and cairoplot])],
	[case "${enableval}" in
		yes) plugin_google_analytics=yes ;;
		no)  plugin_google_analytics=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-google-analytics]) ;;
	esac],
	[plugin_google_analytics=${deps_plugin_google_analytics}])
AS_IF([test "x${plugin_google_analytics}" = "xyes" -a "x$have_gdata_analytics" = "xno"],
	[AC_MSG_ERROR([Plugin Google analytics cannot be built without gdata python modules])])
AS_IF([test "x${plugin_google_analytics}" = "xyes" -a "x$have_cairoplot" = "xno"],
	[AC_MSG_ERROR([Plugin Google analytics cannot be built without cairoplot python modules])])
AM_CONDITIONAL([ENABLE_PLUGIN_GOOGLE_ANALYTICS], [test x$plugin_google_analytics = xyes])

dnl POP3/IMAP Email Checker plugin
AC_ARG_ENABLE([plugin-lcdbiff],
	[AS_HELP_STRING([--enable-plugin-lcdbiff],
		[Enable POP3 / IMAP email checker.])],
	[case "${enableval}" in
		yes) plugin_lcdbiff=yes ;;
		no)  plugin_lcdbiff=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-lcdbiff]) ;;
	esac],
	[plugin_lcdbiff=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_LCDBIFF], [test x$plugin_lcdbiff = xyes])

dnl Sensors plugin
AC_ARG_ENABLE([plugin-sense],
	[AS_HELP_STRING([--enable-plugin-sense],
		[Enable Sense plugin. Requires pysensors])],
	[case "${enableval}" in
		yes) plugin_sense=yes ;;
		no)  plugin_sense=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-sense]) ;;
	esac],
	[plugin_sense=${have_sensors}])
AS_IF([test "x${plugin_sense}" = "xyes" -a "x$have_sensors" = "xno"],
	[AC_MSG_ERROR([Plugin Sense cannot be built without sensors python modules])])
AM_CONDITIONAL([ENABLE_PLUGIN_SENSE], [test x$plugin_sense = xyes])

dnl LCDShot plugin
AC_ARG_ENABLE([plugin-lcdshot],
	[AS_HELP_STRING([--enable-plugin-lcdshot],
		[Enable LCDShot plugin. Take a picture of whatever is on the LCD])],
	[case "${enableval}" in
		yes) plugin_lcdshot=yes ;;
		no)  plugin_lcdshot=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-lcdshot]) ;;
	esac],
	[plugin_lcdshot=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_LCDSHOT], [test x$plugin_lcdshot = xyes])

dnl Tweak plugin
AC_ARG_ENABLE([plugin-tweak],
	[AS_HELP_STRING([--enable-plugin-tweak],
		[Enable Tweak plugin.])],
	[case "${enableval}" in
		yes) plugin_tweak=yes ;;
		no)  plugin_tweak=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-tweak]) ;;
	esac],
	[plugin_tweak=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_TWEAK], [test x$plugin_tweak = xyes])

dnl Tails plugin
AC_ARG_ENABLE([plugin-tails],
	[AS_HELP_STRING([--enable-plugin-tails],
		[Enable Tails.])],
	[case "${enableval}" in
		yes) plugin_tails=yes ;;
		no)  plugin_tails=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-tails]) ;;
	esac],
	[plugin_tails=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_TAILS], [test x$plugin_tails = xyes])

dnl Display plugin
AC_ARG_ENABLE([plugin-display],
	[AS_HELP_STRING([--enable-plugin-display],
		[Enable Display (XRandR for resolutions and rotation).])],
	[case "${enableval}" in
		yes) plugin_display=yes ;;
		no)  plugin_display=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-display]) ;;
	esac],
	[plugin_display=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_DISPLAY], [test x$plugin_display = xyes])

dnl Voip
AC_ARG_ENABLE([plugin-voip],
	[AS_HELP_STRING([--enable-plugin-voip],
		[Enable Voip plugin. Integrate with Voip apps. Requires backend plugin as well (e.g. voip-teamspeak3)])],
	[case "${enableval}" in
		yes) plugin_voip=yes ;;
		no)  plugin_voip=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-voip]) ;;
	esac],
	[plugin_voip=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_VOIP], [test x$plugin_voip = xyes])

AC_ARG_ENABLE([plugin-voip-teamspeak3],
	[AS_HELP_STRING([--enable-plugin-voip-teamspeak3],
		[Enable Teamspeak3 plugin. Requires Voip plugin as well])],
	[case "${enableval}" in
		yes) plugin_voip_teamspeak3=yes ;;
		no)  plugin_voip_teamspeak3=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-voip-teamspeak3]) ;;
	esac],
	[plugin_voip_teamspeak3=${plugin_voip}])
AS_IF([test "x${plugin_voip_teamspeak3}" = "xyes" -a "x$plugin_voip" = "xno"],
	[AC_MSG_ERROR([Plugin Teamspeak3 cannot be built without Voip plugin])])
AM_CONDITIONAL([ENABLE_PLUGIN_VOIP_TEAMSPEAK3], [test x$plugin_voip_teamspeak3 = xyes])

dnl Traffic Stats Plugin
AC_ARG_ENABLE([plugin-trafficstats],
	[AS_HELP_STRING([--enable-plugin-trafficstats],
		[Enable Traffic Stats plugin.])],
	[case "${enableval}" in
		yes) plugin_trafficstats=yes ;;
		no)  plugin_trafficstats=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-trafficstats]) ;;
	esac],
	[plugin_trafficstats=yes])
AM_CONDITIONAL([ENABLE_PLUGIN_TRAFFIC_STATS], [test x$plugin_trafficstats = xyes])

dnl impulse15 plugin
AS_IF([test "x${have_fftw3_header}" = "xyes" \
       -a "x${have_fftw3}" = "xyes" \
       -a "x${have_pulse}" = "xyes"],
	  [deps_plugin_impulse15=yes],
	  [deps_plugin_impulse15=no])
AC_ARG_ENABLE([plugin-impulse15],
	[AS_HELP_STRING([--enable-plugin-impulse15],
		[Enable Impulse15 plugin.])],
	[case "${enableval}" in
		yes) plugin_impulse15=yes ;;
		no)  plugin_impulse15=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-impulse15]) ;;
	esac],
	[plugin_impulse15=${deps_plugin_impulse15}])
AS_IF([test "x${plugin_impulse15}" = "xyes" -a "x$have_fftw3_header" = "xno"],
	[AC_MSG_ERROR([Plugin Impulse15 cannot be built without fftw3 headers])])
AS_IF([test "x${plugin_impulse15}" = "xyes" -a "x$have_fftw3" = "xno"],
	[AC_MSG_ERROR([Plugin Impulse15 cannot be built without fftw3])])
AS_IF([test "x${plugin_impulse15}" = "xyes" -a "x$have_pulse" = "xno"],
	[AC_MSG_ERROR([Plugin Impulse15 cannot be built without pulse library])])
AM_CONDITIONAL([ENABLE_PLUGIN_IMPULSE15], [test x$plugin_impulse15 = xyes])

dnl
dnl Experimental (under development) plugins
dnl

dnl Nexuiz plugin
AC_ARG_ENABLE([plugin-game-nexuiz],
	[AS_HELP_STRING([--enable-plugin-game-nexuiz],
		[Enable Nexuiz plugin.])],
	[case "${enableval}" in
		yes) plugin_game_nexuiz=yes ;;
		no)  plugin_game_nexuiz=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-game-nexuiz]) ;;
	esac],
	[plugin_game_nexuiz=no])
AM_CONDITIONAL([ENABLE_PLUGIN_GAME_NEXUIZ], [test x$plugin_game_nexuiz = xyes])

dnl Backlight plugin
AC_ARG_ENABLE([plugin-backlight],
	[AS_HELP_STRING([--enable-plugin-backlight],
		[Enable Backlight plugin.])],
	[case "${enableval}" in
		yes) plugin_backlight=yes ;;
		no)  plugin_backlight=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-backlight]) ;;
	esac],
	[plugin_backlight=no])
AM_CONDITIONAL([ENABLE_PLUGIN_BACKLIGHT], [test x$plugin_backlight = xyes])

dnl Notify 2 plugin
AC_ARG_ENABLE([plugin-notify-lcd2],
	[AS_HELP_STRING([--enable-plugin-notify-lcd2],
		[Enable Notify LCD plugin. Takes over as notification daemon and displays messages on LCD, blinks keyboard])],
	[case "${enableval}" in
		yes) plugin_notify_lcd2=yes ;;
		no)  plugin_notify_lcd2=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-notify-lcd2]) ;;
	esac],
	[plugin_notify_lcd2=no])
AM_CONDITIONAL([ENABLE_PLUGIN_NOTIFY_LCD2], [test x$plugin_notify_lcd2 = xyes])

dnl PPAStats plugin
AC_ARG_ENABLE([plugin-ppastats],
	[AS_HELP_STRING([--enable-plugin-ppastats],
		[Enable PPAStats plugin.])],
	[case "${enableval}" in
		yes) plugin_ppastats=yes ;;
		no)  plugin_ppastats=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-ppastats]) ;;
	esac],
	[plugin_ppastats=no])
AM_CONDITIONAL([ENABLE_PLUGIN_PPASTATS], [test x$plugin_ppastats = xyes])

dnl NM plugin
AC_ARG_ENABLE([plugin-nm],
	[AS_HELP_STRING([--enable-plugin-nm],
		[Enable NM (Network Manager) plugin.])],
	[case "${enableval}" in
		yes) plugin_nm=yes ;;
		no)  plugin_nm=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-nm]) ;;
	esac],
	[plugin_nm=no])
AM_CONDITIONAL([ENABLE_PLUGIN_NM], [test x$plugin_nm = xyes])

dnl Lens plugin
AC_ARG_ENABLE([plugin-lens],
	[AS_HELP_STRING([--enable-plugin-lens],
		[Enable Unity Lens plugin.])],
	[case "${enableval}" in
		yes) plugin_lens=yes ;;
		no)  plugin_lens=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-lens]) ;;
	esac],
	[plugin_lens=no])
AM_CONDITIONAL([ENABLE_PLUGIN_LENS], [test x$plugin_lens = xyes])

dnl WebKit browser plugin
AC_ARG_ENABLE([plugin-webkit-browser],
	[AS_HELP_STRING([--enable-plugin-webkit-browser],
		[Enable Webkit browser plugin.])],
	[case "${enableval}" in
		yes) plugin_webkit_browser=yes ;;
		no)  plugin_webkit_browser=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-webkit-browser]) ;;
	esac],
	[plugin_webkit_browser=no])
AM_CONDITIONAL([ENABLE_PLUGIN_WEBKIT_BROWSER], [test x$plugin_webkit_browser = xyes])

dnl Things plugin
AC_ARG_ENABLE([plugin-things],
	[AS_HELP_STRING([--enable-plugin-things],
		[Enable Things python animation API plugin.])],
	[case "${enableval}" in
		yes) plugin_things=yes ;;
		no)  plugin_things=no ;;
		*)   AC_MSG_ERROR([bad value ${enableval} for --enable-plugin-things]) ;;
	esac],
	[plugin_things=no])
AM_CONDITIONAL([ENABLE_PLUGIN_THINGS], [test x$plugin_things = xyes])

AC_OUTPUT([ 
Makefile
src/pylibg19/Makefile
src/pylibg19/g19/Makefile
src/Makefile
i18n/Makefile
src/scripts/Makefile
data/themes/Makefile
data/themes/default/Makefile
data/udev/Makefile
data/udev/98-gnome15.rules
data/udev/99-gnome15-kernel.rules
data/udev/99-gnome15-g15direct.rules
data/udev/99-gnome15-g19direct.rules
data/udev/99-gnome15-g930.rules
src/gnome-shell-extension/Makefile
src/gnome-shell-extension/icons/Makefile
data/Makefile
data/applications/Makefile
data/applications/g15-config.desktop
data/autostart/Makefile
data/autostart/gnome15.desktop
data/autostart/g15-systemtray.desktop
data/autostart/g15-indicator.desktop
data/dbus/Makefile
src/gnome15/Makefile
src/gnome15/g15globals.py
src/gnome15/drivers/Makefile
src/gnome15/util/Makefile
data/icons/Makefile
data/icons/hicolor/Makefile
data/icons/hicolor/16x16/Makefile
data/icons/hicolor/16x16/status/Makefile
data/icons/hicolor/22x22/Makefile
data/icons/hicolor/22x22/apps/Makefile
data/icons/hicolor/22x22/status/Makefile
data/icons/hicolor/24x24/Makefile
data/icons/hicolor/24x24/apps/Makefile
data/icons/hicolor/24x24/status/Makefile
data/icons/hicolor/48x48/Makefile
data/icons/hicolor/48x48/apps/Makefile
data/icons/hicolor/64x64/Makefile
data/icons/hicolor/64x64/apps/Makefile
data/icons/hicolor/scalable/Makefile
data/icons/hicolor/scalable/apps/Makefile
data/icons/hicolor/scalable/status/Makefile
data/icons/hicolor/scalable/devices/Makefile
data/icons/AwOken/Makefile
data/icons/AwOken/status/Makefile
data/icons/AwOken/status/16/Makefile
data/icons/AwOken/status/22/Makefile
data/icons/AwOken/status/24/Makefile
data/icons/AwOken/status/48/Makefile
data/icons/AwOken/status/64/Makefile
data/icons/AwOken/status/128/Makefile
data/icons/AwOken/apps/Makefile
data/icons/AwOken/apps/16/Makefile
data/icons/AwOken/apps/22/Makefile
data/icons/AwOken/apps/24/Makefile
data/icons/AwOken/apps/48/Makefile
data/icons/AwOken/apps/64/Makefile
data/icons/AwOken/apps/128/Makefile
data/icons/ubuntu-mono-dark/Makefile
data/icons/ubuntu-mono-dark/status/Makefile
data/icons/ubuntu-mono-dark/status/16/Makefile
data/icons/ubuntu-mono-dark/status/22/Makefile
data/icons/ubuntu-mono-dark/status/24/Makefile
data/icons/ubuntu-mono-light/Makefile
data/icons/ubuntu-mono-light/status/Makefile
data/icons/ubuntu-mono-light/status/16/Makefile
data/icons/ubuntu-mono-light/status/22/Makefile
data/icons/ubuntu-mono-light/status/24/Makefile
data/images/Makefile
data/glade/Makefile
data/ukeys/Makefile
man/Makefile
src/plugins/Makefile
src/plugins/cal/Makefile
src/plugins/cal/default/Makefile
src/plugins/cal-evolution/Makefile
src/plugins/cal-google/Makefile
src/plugins/lcdbiff/Makefile
src/plugins/lcdbiff/default/Makefile
src/plugins/debug/Makefile
src/plugins/debug/default/Makefile
src/plugins/background/Makefile
src/plugins/cairo-clock/Makefile
src/plugins/cairo-clock/g15/Makefile
src/plugins/cairo-clock/g15/default/Makefile
src/plugins/cairo-clock/g19/Makefile
src/plugins/cairo-clock/g19/default/Makefile
src/plugins/cairo-clock/mx5500/Makefile
src/plugins/cairo-clock/mx5500/default/Makefile
src/plugins/clock/Makefile
src/plugins/clock/default/Makefile
src/plugins/fx/Makefile
src/plugins/g15daemon-server/Makefile
src/plugins/macro-recorder/Makefile
src/plugins/macro-recorder/default/Makefile
src/plugins/macros/Makefile
src/plugins/macros/default/Makefile
src/plugins/mpris/Makefile
src/plugins/mpris/default/Makefile
src/plugins/mpris/bigcover/Makefile
src/plugins/mounts/Makefile
src/plugins/mounts/default/Makefile
src/plugins/menu/Makefile
src/plugins/panel/Makefile
src/plugins/profiles/Makefile
src/plugins/processes/Makefile
src/plugins/im/Makefile
src/plugins/indicator-messages/Makefile
src/plugins/lcdshot/Makefile
src/plugins/notify-lcd/Makefile
src/plugins/notify-lcd/default/Makefile
src/plugins/screensaver/Makefile
src/plugins/screensaver/default/Makefile
src/plugins/stopwatch/Makefile
src/plugins/stopwatch/default/Makefile
src/plugins/sense/Makefile
src/plugins/sense/default/Makefile
src/plugins/sysmon/Makefile
src/plugins/sysmon/default/Makefile
src/plugins/sysmon/graphs/Makefile
src/plugins/rss/Makefile
src/plugins/rss/default/Makefile
src/plugins/sysmon/dials/Makefile
src/plugins/tweak/Makefile
src/plugins/volume/Makefile
src/plugins/volume/default/Makefile
src/plugins/mediaplayer/Makefile
src/plugins/mediaplayer/default/Makefile
src/plugins/weather/Makefile
src/plugins/weather/default/Makefile
src/plugins/weather/forecasts/Makefile
src/plugins/weather-noaa/Makefile
src/plugins/weather-yahoo/Makefile
src/plugins/tails/Makefile
src/plugins/tails/tailer/Makefile
src/plugins/tails/default/Makefile
src/plugins/display/Makefile
src/plugins/voip/Makefile
src/plugins/voip/default/Makefile
src/plugins/voip-teamspeak3/Makefile
src/plugins/voip-teamspeak3/ts3/Makefile
src/plugins/google-analytics/Makefile
src/plugins/google-analytics/default/Makefile
src/plugins/trafficstats/Makefile
src/plugins/trafficstats/default/Makefile
src/plugins/game-nexuiz/Makefile
src/plugins/game-nexuiz/default/Makefile
src/plugins/game-nexuiz/resources/Makefile
src/plugins/backlight/Makefile
src/plugins/backlight/default/Makefile
src/plugins/notify-lcd2/Makefile
src/plugins/notify-lcd2/default/Makefile
src/plugins/ppastats/Makefile
src/plugins/ppastats/default/Makefile
src/plugins/nm/Makefile
src/plugins/nm/default/Makefile
src/plugins/lens/Makefile
src/plugins/webkitbrowser/Makefile
src/plugins/webkitbrowser/default/Makefile
src/plugins/things/Makefile
src/plugins/things/cg.stuff/Makefile
src/plugins/things/clouds.stuff/Makefile
src/plugins/impulse15/Makefile
src/plugins/impulse15/themes/Makefile
src/plugins/impulse15/themes/default/Makefile
src/plugins/impulse15/themes/circlelcd/Makefile
src/plugins/impulse15/themes/circleline/Makefile
src/plugins/impulse15/themes/original/Makefile
src/libimpulse/Makefile
])

AS_ECHO("Available features :-")
AS_ECHO("")
AS_ECHO("Panel Integration")
AS_ECHO("-----------------")
AS_ECHO_N("systemtray                  - ")
AS_IF([test "x$systemtray" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("Indicator                   - ")
AS_IF([test "x$indicator" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("gnome-shell-extension       - ")
AS_IF([test "x$gnome_shell_extension" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO("")
AS_ECHO("Drivers")
AS_ECHO("-------")
AS_ECHO_N("g15direct                   - ")
AS_IF([test "x$driver_g15direct" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("g930                        - ")
AS_IF([test "x$driver_g930" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("g19direct                   - ")
AS_IF([test "x$driver_g19direct" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("Kernel                      - ")
AS_IF([test "x$driver_kernel" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO("")
AS_ECHO("Icons")
AS_ECHO("-----")
AS_ECHO_N("icons-awoken                - ")
AS_IF([test "x$icons_awoken" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("icons-mono                  - ")
AS_IF([test "x$icons_mono" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO("")
AS_ECHO("Enabled Plugins")
AS_ECHO("---------------")
AS_ECHO_N("volume                      - ")
AS_IF([test "x$plugin_volume" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("rss                         - ")
AS_IF([test "x$plugin_rss" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("processes                   - ")
AS_IF([test "x$plugin_processes" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("sysmon                      - ")
AS_IF([test "x$plugin_sysmon" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("cal                         - ")
AS_IF([test "x$plugin_cal" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("cal-evolution               - ")
AS_IF([test "x$plugin_cal_evolution" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("cal-google                  - ")
AS_IF([test "x$plugin_cal_google" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("lcdbiff                     - ")
AS_IF([test "x$plugin_lcdbiff" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("background                  - ")
AS_IF([test "x$plugin_background" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("cairo-clock                 - ")
AS_IF([test "x$plugin_cairo_clock" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("clock                       - ")
AS_IF([test "x$plugin_clock" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("fx                          - ")
AS_IF([test "x$plugin_fx" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("g15daemon-server            - ")
AS_IF([test "x$plugin_g15daemon_server" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("im                          - ")
AS_IF([test "x$plugin_im" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("indicator-messages          - ")
AS_IF([test "x$plugin_indicator_messages" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("lcdshot                     - ")
AS_IF([test "x$plugin_lcdshot" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("macro-recorder              - ")
AS_IF([test "x$plugin_macro_recorder" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("macros                      - ")
AS_IF([test "x$plugin_macros" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("profiles                    - ")
AS_IF([test "x$plugin_profiles" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("menu                        - ")
AS_IF([test "x$plugin_menu" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("mounts                      - ")
AS_IF([test "x$plugin_mounts" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("mpris                       - ")
AS_IF([test "x$plugin_mpris" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("notify-lcd                  - ")
AS_IF([test "x$plugin_notify_lcd" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("panel                       - ")
AS_IF([test "x$plugin_panel" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("screensaver                 - ")
AS_IF([test "x$plugin_screensaver" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("stopwatch                   - ")
AS_IF([test "x$plugin_stopwatch" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("tweak                       - ")
AS_IF([test "x$plugin_tweak" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("mediaplayer                 - ")
AS_IF([test "x$plugin_mediaplayer" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("weather                     - ")
AS_IF([test "x$plugin_weather" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("weather-noaa                - ")
AS_IF([test "x$plugin_weather_noaa" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("weather-yahoo               - ")
AS_IF([test "x$plugin_weather_yahoo" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("sense                       - ")
AS_IF([test "x$plugin_sense" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("tails                       - ")
AS_IF([test "x$plugin_tails" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("display                     - ")
AS_IF([test "x$plugin_display" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("voip                        - ")
AS_IF([test "x$plugin_voip" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("voip-teamspeak3             - ")
AS_IF([test "x$plugin_voip_teamspeak3" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("google-analytics            - ")
AS_IF([test "x$plugin_google_analytics" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("debug                       - ")
AS_IF([test "x$plugin_debug" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("trafficstats                - ")
AS_IF([test "x$plugin_trafficstats" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("game-nexuiz                 - ")
AS_IF([test "x$plugin_game_nexuiz" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("backlight                   - ")
AS_IF([test "x$plugin_backlight" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("notify-lcd2                 - ")
AS_IF([test "x$plugin_notify_lcd2" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("ppastats                    - ")
AS_IF([test "x$plugin_ppastats" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("nm                          - ")
AS_IF([test "x$plugin_nm" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("lens                        - ")
AS_IF([test "x$plugin_lens" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("webkitbrowser               - ")
AS_IF([test "x$plugin_webkit_browser" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("things                      - ")
AS_IF([test "x$plugin_things" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("impulse15                   - ")
AS_IF([test "x$plugin_impulse15" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO("See ./configure --help for descriptions of these plugins and options to enable and disable them.")
AS_ECHO("")
AS_ECHO("Other Configuration")
AS_ECHO("-------------------")
AS_ECHO("Fixed size font name        - ${FIXED_SIZE_FONT}")
AS_ECHO("udev rules path             - ${UDEV_RULES_PATH}")
AS_ECHO("Device group                - ${DEVICEGROUP}")
AS_ECHO("Device mode                 - ${DEVICEMODE}")
AS_ECHO_N("Hotplugging support         - ")
AS_IF([test "x${HAVE_PYUDEV}" = "xno"],
     [AS_ECHO("No")],
     [AS_ECHO("Yes")])
AS_ECHO("")
AS_ECHO("Building i18n for locales: ${ENABLED_LOCALES}")
AS_ECHO("")
