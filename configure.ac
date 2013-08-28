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
 				yes)	systemtray=yes ;;
 				no)		systemtray=no ;;
 				*)		AC_MSG_ERROR([bad value ${enableval} for --enable-systemtray]) ;;
 	esac],
	systemtray=yes)
AM_CONDITIONAL([ENABLE_SYSTEMTRAY], [test x$systemtray = xyes])

dnl Ubuntu Indicator
AC_ARG_ENABLE([indicator],
	[AS_HELP_STRING([--enable-indicator],
		[Enable Ubuntu Indicator integration.])],
	[case "${enableval}" in
		yes)	indicator=yes ;;
 		no)	indicator=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-indicator]) ;;
 	esac],
	indicator=yes)
AS_IF([test "x${HAVE_PYMOD_APPINDICATOR}" = "xyes"],
	  [indicator=$indicator],
	  [indicator=no])
AM_CONDITIONAL([ENABLE_INDICATOR], [test x$indicator = xyes])

dnl Gnome Shell Extension
AC_ARG_ENABLE([gnome-shell-extension],
	[AS_HELP_STRING([--enable-gnome-shell-extension],
		[Enable Gnome Shell extension.])],
	[case "${enableval}" in
		yes)	gnome_shell_extension=yes ;;
		no)	gnome_shell_extension=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-gnome-shell-extension]) ;;
	esac],
	gnome_shell_extension=yes)
AM_CONDITIONAL([ENABLE_GNOME_SHELL_EXTENSION], [test x$gnome_shell_extension = xyes])

dnl Icons

AC_ARG_ENABLE([icons-awoken],
	[AS_HELP_STRING([--enable-icons-awoken],
		[Build and deploy awoken icons.])],
	[case "${enableval}" in
		yes)	icons_awoken=yes ;;
		no)	icons_awoken=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-icons-awoken]) ;;
	esac],
	[icons_awoken=no])
AM_CONDITIONAL([ENABLE_ICONS_AWOKEN], [test x$icons_awoken = xyes])

AC_ARG_ENABLE([icons-mono],
	[AS_HELP_STRING([--enable-icons-mono],
		[Build and deploy monochrome icons.])],
	[case "${enableval}" in
		yes)	icons_mono=yes ;;
		no)	icons_mono=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-icons-mono]) ;;
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
AC_ARG_ENABLE([background],
	[AS_HELP_STRING([--enable-background],
		[Enable Background plugin.])],
	[case "${enableval}" in
		yes)	background_plugin=yes ;;
		no)	background_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-background]) ;;
	esac],
	[background_plugin=yes])
AM_CONDITIONAL([ENABLE_BACKGROUND_PLUGIN], [test x$background_plugin = xyes])

dnl Cairo Clock plugin
AC_ARG_ENABLE([cairo-clock],
	[AS_HELP_STRING([--enable-cairo-clock],
		[Enable Cairo Clock plugin.])],
	[case "${enableval}" in
		yes)	cairo_clock_plugin=yes ;;
		no)	cairo_clock_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-cairo-clock]) ;;
	esac],
	[cairo_clock_plugin=yes])
AM_CONDITIONAL([ENABLE_CAIRO_CLOCK_PLUGIN], [test x$cairo_clock_plugin = xyes])

dnl Clock plugin
AC_ARG_ENABLE([clock],
	[AS_HELP_STRING([--enable-clock],
		[Enable Simple Clock plugin (plugin used in website example).])],
	[case "${enableval}" in
		yes)	clock_plugin=yes ;;
		no)	clock_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-clock]) ;;
	esac],
	[clock_plugin=yes])
AM_CONDITIONAL([ENABLE_CLOCK_PLUGIN], [test x$clock_plugin = xyes])

dnl Special effects plugin
AC_ARG_ENABLE([fx],
	[AS_HELP_STRING([--enable-fx],
		[Enable Special Effects plugin.])],
	[case "${enableval}" in
		yes)	fx_plugin=yes ;;
		no)	fx_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-fx]) ;;
	esac],
	[fx_plugin=yes])
AM_CONDITIONAL([ENABLE_FX_PLUGIN], [test x$fx_plugin = xyes])

dnl G15daemon Server plugin
AC_ARG_ENABLE([g15daemon-server],
	[AS_HELP_STRING([--enable-g15daemon-server],
		[Enable G15Daemon Server plugin (network server with protocol compatible with g15daemon, allows g15daemon scripts to be used when it is not installed).])],
	[case "${enableval}" in
		yes)	g15daemon_server_plugin=yes ;;
		no)	g15daemon_server_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-g15daemon-server]) ;;
	esac],
	[g15daemon_server_plugin=yes])
AM_CONDITIONAL([ENABLE_G15DAEMON_SERVER_PLUGIN], [test x$g15daemon_server_plugin = xyes])

dnl Instant Messenger plugin
AC_ARG_ENABLE([im],
	[AS_HELP_STRING([--enable-im],
		[Enable Instant Messenger plugin. Displays current contact list and status (currently works with Telepathy framework based clients).])],
	[case "${enableval}" in
		yes)	im_plugin=yes ;;
		no)	im_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-im]) ;;
	esac],
	[im_plugin=${have_telepathy}])
AM_CONDITIONAL([ENABLE_IM_PLUGIN], [test x$im_plugin = xyes])

dnl Macro Recorder plugin
AC_ARG_ENABLE([macro-recorder],
	[AS_HELP_STRING([--enable-macro-recorder],
		[Enable Macro Recorder plugin.])],
	[case "${enableval}" in
		yes)	macro_recorder_plugin=yes ;;
		no)	macro_recorder_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-macro-recorder]) ;;
	esac],
	[macro_recorder_plugin=yes])
AM_CONDITIONAL([ENABLE_MACRO_RECORDER_PLUGIN], [test x$macro_recorder_plugin = xyes])

dnl Macro Display plugin
AC_ARG_ENABLE([macros],
	[AS_HELP_STRING([--enable-macros],
		[Enable Macro Display plugin.])],
	[case "${enableval}" in
		yes)	macros_plugin=yes ;;
		no)	macros_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-macros]) ;;
	esac],
	[macros_plugin=yes])
AM_CONDITIONAL([ENABLE_MACROS_PLUGIN], [test x$macros_plugin = xyes])

dnl Profile selection plugin
AC_ARG_ENABLE([profiles],
	[AS_HELP_STRING([--enable-profiles],
		[Enable profile selector plugin.])],
	[case "${enableval}" in
		yes)	profiles_plugin=yes ;;
		no)	profiles_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-profiles]) ;;
	esac],
	[profiles_plugin=yes])
AM_CONDITIONAL([ENABLE_PROFILES_PLUGIN], [test x$profiles_plugin = xyes])

dnl Menu plugin
AC_ARG_ENABLE([menu],
	[AS_HELP_STRING([--enable-menu],
		[Enable Menu plugin.])],
	[case "${enableval}" in
		yes)	menu_plugin=yes ;;
		no)	menu_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-menu]) ;;
	esac],
	[menu_plugin=yes])
AM_CONDITIONAL([ENABLE_MENU_PLUGIN], [test x$menu_plugin = xyes])

dnl Mounts plugin
AC_ARG_ENABLE([mounts],
	[AS_HELP_STRING([--enable-mounts],
		[Enable Mounts plugin.])],
	[case "${enableval}" in
		yes)	mounts_plugin=yes ;;
		no)	mounts_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-mounts]) ;;
	esac],
	[mounts_plugin=yes])
AM_CONDITIONAL([ENABLE_MOUNTS_PLUGIN], [test x$mounts_plugin = xyes])

dnl MPRIS plugin
AC_ARG_ENABLE([mpris],
	[AS_HELP_STRING([--enable-mpris],
		[Enable MPRIS plugin. Displays currently playing media players that support MPRIS])],
	[case "${enableval}" in
		yes)	mpris_plugin=yes ;;
		no)	mpris_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-mpris]) ;;
	esac],
	[mpris_plugin=yes])
AM_CONDITIONAL([ENABLE_MPRIS_PLUGIN], [test x$mpris_plugin = xyes])

dnl Notify plugin
AC_ARG_ENABLE([notify-lcd],
	[AS_HELP_STRING([--enable-notify-lcd],
		[Enable Notify LCD plugin. Takes over as notification daemon and displays messages on LCD, blinks keyboard])],
	[case "${enableval}" in
		yes)	notify_lcd_plugin=yes ;;
		no)	notify_lcd_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-notify-lcd]) ;;
	esac],
	[notify_lcd_plugin=yes])
AM_CONDITIONAL([ENABLE_NOTIFY_LCD_PLUGIN], [test x$notify_lcd_plugin = xyes])

dnl Panel plugin
AC_ARG_ENABLE([panel],
	[AS_HELP_STRING([--enable-panel],
		[Enable Panel plugin. Reserves area of screen for other plugins to display permanent information])],
	[case "${enableval}" in
		yes)	panel_plugin=yes ;;
		no)	panel_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-panel]) ;;
	esac],
	[panel_plugin=yes])
AM_CONDITIONAL([ENABLE_PANEL_PLUGIN], [test x$panel_plugin = xyes])

dnl Screensaver plugin
AC_ARG_ENABLE([screensaver],
	[AS_HELP_STRING([--enable-screensaver],
		[Enable Screensaver plugin. Displays mesage and dims keyboard when desktop screesaver is activated])],
	[case "${enableval}" in
		yes)	screensaver_plugin=yes ;;
		no)	screensaver_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-screensaver]) ;;
	esac],
	[screensaver_plugin=yes])
AM_CONDITIONAL([ENABLE_SCREENSAVER_PLUGIN], [test x$screensaver_plugin = xyes])

dnl Stopwatch plugin
AC_ARG_ENABLE([stopwatch],
	[AS_HELP_STRING([--enable-stopwatch],
		[Enable Stopwatch plugin. Dual mode, dual timer stopwatch])],
	[case "${enableval}" in
		yes)	stopwatch_plugin=yes ;;
		no)	stopwatch_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-stopwatch]) ;;
	esac],
	[stopwatch_plugin=yes])
AM_CONDITIONAL([ENABLE_STOPWATCH_PLUGIN], [test x$stopwatch_plugin = xyes])

dnl Media Player plugin
AC_ARG_ENABLE([mediaplayer],
	[AS_HELP_STRING([--enable-mediaplayer],
		[Enable Media Player plugin. Requires GStreamer])],
	[case "${enableval}" in
		yes)	mediaplayer_plugin=yes ;;
		no)	mediaplayer_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-mediaplayer]) ;;
	esac],
	[mediaplayer_plugin=${have_gst}])
AM_CONDITIONAL([ENABLE_MEDIAPLAYER_PLUGIN], [test x$mediaplayer_plugin = xyes])

dnl Weather plugin
AC_ARG_ENABLE([weather],
	[AS_HELP_STRING([--enable-weather],
		[Enable Weather plugin. Requires additional backend plugin such as weather-noaa])],
	[case "${enableval}" in
		yes)	weather_plugin=yes ;;
		no)	weather_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-weather]) ;;
	esac],
	[weather_plugin=yes])
AM_CONDITIONAL([ENABLE_WEATHER_PLUGIN], [test x$weather_plugin = xyes])

AC_ARG_ENABLE([weather-noaa],
	[AS_HELP_STRING([--enable-weather-noaa],
		[Enable NOAA support for the Weather plugin.])],
	[case "${enableval}" in
		yes)	weather_noaa_plugin=yes ;;
		no)	weather_noaa_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-weather-noaa]) ;;
	esac],
	[weather_noaa_plugin=yes])
AM_CONDITIONAL([ENABLE_WEATHER_NOAA_PLUGIN], [test x$weather_noaa_plugin = xyes])

AC_ARG_ENABLE([weather-yahoo],
	[AS_HELP_STRING([--enable-weather-yahoo],
		[Enable Yahoo support for the Weather plugin.])],
	[case "${enableval}" in
		yes)	weather_yahoo_plugin=yes ;;
		no)	weather_yahoo_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-weather-yahoo]) ;;
	esac],
	[weather_yahoo_plugin=yes])
AM_CONDITIONAL([ENABLE_WEATHER_YAHOO_PLUGIN], [test x$weather_yahoo_plugin = xyes])

dnl Indicator Messages Plugin
AC_ARG_ENABLE([indicator-messages],
	[AS_HELP_STRING([--enable-indicator-messages],
		[Enable Indicator Messages plugin.])],
	[case "${enableval}" in
		yes)	indicator_messages_plugin=yes ;;
		no)	indicator_messages_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-indicator-messages]) ;;
	esac],
	[indicator_messages_plugin=${have_appindicator}])
AM_CONDITIONAL([ENABLE_INDICATOR_MESSAGES_PLUGIN], [test x$indicator_messages_plugin = xyes])

dnl ALSA Volume Monitor Plugin
AC_ARG_ENABLE([volume],
	[AS_HELP_STRING([--enable-volume],
		[Enable ALSA volume monitor plugin. Requires python-alsaaudio])],
	[case "${enableval}" in
		yes)	volume_plugin=yes ;;
		no)	volume_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-volume]) ;;
	esac],
	[volume_plugin=${have_alsaaudio}])
AM_CONDITIONAL([ENABLE_VOLUME_PLUGIN], [test x$volume_plugin = xyes])

dnl RSS Plugin
AC_ARG_ENABLE([rss],
	[AS_HELP_STRING([--enable-rss],
		[Enable RSS feed plugin. Requires python feedparser])],
	[case "${enableval}" in
		yes)	rss_plugin=yes ;;
		no)	rss_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-rss]) ;;
	esac],
	[rss_plugin=${have_feedparser}])
AM_CONDITIONAL([ENABLE_RSS_PLUGIN], [test x$rss_plugin = xyes])

dnl System Monitor Plugin
AC_ARG_ENABLE([sysmon],
	[AS_HELP_STRING([--enable-sysmon],
		[Enable System Monitor plugin. Recommends python gtop])],
	[case "${enableval}" in
		yes)	sysmon_plugin=yes ;;
		no)	sysmon_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-sysmon]) ;;
	esac],
	[sysmon_plugin=yes])
AM_CONDITIONAL([ENABLE_SYSMON_PLUGIN], [test x$sysmon_plugin = xyes])

dnl Processes Plugin
AC_ARG_ENABLE([processes],
	[AS_HELP_STRING([--enable-processes],
		[Enable Processes plugin. Recommends python gtop])],
	[case "${enableval}" in
		yes)	processes_plugin=yes ;;
		no)	processes_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-processes]) ;;
	esac],
	[processes_plugin=yes])
AM_CONDITIONAL([ENABLE_PROCESSES_PLUGIN], [test x$processes_plugin = xyes])

dnl Debug Plugin
AC_ARG_ENABLE([debug],
	[AS_HELP_STRING([--enable-debug],
		[Enable Debug plugin.])],
	[case "${enableval}" in
		yes)	debug_plugin=yes ;;
		no)	debug_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-debug]) ;;
	esac],
	[debug_plugin=no])
AM_CONDITIONAL([ENABLE_DEBUG_PLUGIN], [test x$debug_plugin = xyes])

dnl Calendar plugin (base)
AC_ARG_ENABLE([cal],
	[AS_HELP_STRING([--enable-cal],
		[Enable calendar plugin. (required for any calendar support)])],
	[case "${enableval}" in
		yes)	cal_plugin=yes ;;
		no)	cal_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-cal]) ;;
	esac],
	[cal_plugin=yes])
AM_CONDITIONAL([ENABLE_CAL_PLUGIN], [test x$cal_plugin = xyes])

dnl Evolution Calendar plugin
AC_ARG_ENABLE([cal-evolution],
	[AS_HELP_STRING([--enable-cal-evolution],
		[Enable Evolution calendar plugin. Requires python vobject])],
	[case "${enableval}" in
		yes)	cal_evolution_plugin=yes ;;
		no)	cal_evolution_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-cal-evolution]) ;;
	esac],
	[cal_evolution_plugin=${have_vobject}])
AM_CONDITIONAL([ENABLE_CAL_EVOLUTION_PLUGIN], [test x$cal_evolution_plugin = xyes])

dnl Google Calendar plugin
AC_ARG_ENABLE([cal-google],
	[AS_HELP_STRING([--enable-cal-google],
		[Enable Google calendar plugin. Requires calendar plugin, python gdata])],
	[case "${enableval}" in
		yes)	cal_google_plugin=yes ;;
		no)	cal_google_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-cal-google]) ;;
	esac],
	[cal_google_plugin=${have_gdata_calendar}])
AM_CONDITIONAL([ENABLE_CAL_GOOGLE_PLUGIN], [test x$cal_google_plugin = xyes])

dnl Google Analytics plugin
AS_IF([test "x${have_gdata_analytics}" = "xyes" -a "x${have_cairoplot}" = "xyes" ],
	  [deps_plugin_google_analytics=yes],
	  [deps_plugin_google_analytics=no])
AC_ARG_ENABLE([google-analytics],
	[AS_HELP_STRING([--enable-google-analytics],
		[Enable Google Analytics plugin. Requires python gdata and cairoplot])],
	[case "${enableval}" in
		yes)	google_analytics_plugin=yes ;;
		no)	google_analytics_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-google-analytics]) ;;
	esac],
	[google_analytics_plugin=${deps_plugin_google_analytics}])
AM_CONDITIONAL([ENABLE_GOOGLE_ANALYTICS_PLUGIN], [test x$google_analytics_plugin = xyes])

dnl POP3/IMAP Email Checker plugin
AC_ARG_ENABLE([lcdbiff],
	[AS_HELP_STRING([--enable-lcdbiff],
		[Enable POP3 / IMAP email checker.])],
	[case "${enableval}" in
		yes)	lcdbiff_plugin=yes ;;
		no)	lcdbiff_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-lcdbiff]) ;;
	esac],
	[lcdbiff_plugin=yes])
AM_CONDITIONAL([ENABLE_LCDBIFF_PLUGIN], [test x$lcdbiff_plugin = xyes])

dnl Sensors plugin
AC_ARG_ENABLE([sense],
	[AS_HELP_STRING([--enable-sense],
		[Enable Sense plugin. Requires pysensors])],
	[case "${enableval}" in
		yes)	sense_plugin=yes ;;
		no)	sense_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-sense]) ;;
	esac],
	[sense_plugin=${have_sensors}])
AM_CONDITIONAL([ENABLE_SENSE_PLUGIN], [test x$sense_plugin = xyes])

dnl LCDShot plugin
AC_ARG_ENABLE([lcdshot],
	[AS_HELP_STRING([--enable-lcdshot],
		[Enable LCDShot plugin. Take a picture of whatever is on the LCD])],
	[case "${enableval}" in
		yes)	lcdshot_plugin=yes ;;
		no)	lcdshot_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-lcdshot]) ;;
	esac],
	[lcdshot_plugin=yes])
AM_CONDITIONAL([ENABLE_LCDSHOT_PLUGIN], [test x$lcdshot_plugin = xyes])

dnl Tweak plugin
AC_ARG_ENABLE([tweak],
	[AS_HELP_STRING([--enable-tweak],
		[Enable Tweak plugin.])],
	[case "${enableval}" in
		yes)	tweak_plugin=yes ;;
		no)	tweak_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-tweak]) ;;
	esac],
	[tweak_plugin=yes])
AM_CONDITIONAL([ENABLE_TWEAK_PLUGIN], [test x$tweak_plugin = xyes])

dnl Tails  plugin
AC_ARG_ENABLE([tails],
	[AS_HELP_STRING([--enable-tails],
		[Enable Tails.])],
	[case "${enableval}" in
		yes)	tails_plugin=yes ;;
		no)	tails_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-tails]) ;;
	esac],
	[tails_plugin=yes])
AM_CONDITIONAL([ENABLE_TAILS_PLUGIN], [test x$tails_plugin = xyes])

dnl XRandR
AC_ARG_ENABLE([display],
	[AS_HELP_STRING([--enable-display],
		[Enable Display (XRandR for resolutions and rotation).])],
	[case "${enableval}" in
		yes)	display_plugin=yes ;;
		no)	display_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-display]) ;;
	esac],
	[display_plugin=yes])
AM_CONDITIONAL([ENABLE_DISPLAY_PLUGIN], [test x$display_plugin = xyes])

dnl Voip
AC_ARG_ENABLE([voip],
	[AS_HELP_STRING([--enable-voip],
		[Enable Voip plugin. Integrate with Voip apps. Requires backend plugin as well (e.g. voip-teamspeak3)])],
	[case "${enableval}" in
		yes)	voip_plugin=yes ;;
		no)	voip_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-voip]) ;;
	esac],
	[voip_plugin=yes])
AM_CONDITIONAL([ENABLE_VOIP_PLUGIN], [test x$voip_plugin = xyes])

AC_ARG_ENABLE([voip-teamspeak3],
	[AS_HELP_STRING([--enable-voip-teamspeak3],
		[Enable Teamspeak3 plugin. Requires Voip plugin as well])],
	[case "${enableval}" in
		yes)	voip_teamspeak3_plugin=yes ;;
		no)	voip_teamspeak3_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-voip-teamspeak3]) ;;
	esac],
	[voip_teamspeak3_plugin=yes])
AM_CONDITIONAL([ENABLE_VOIP_TEAMSPEAK3_PLUGIN], [test x$voip_teamspeak3_plugin = xyes])

dnl Traffic Stats Plugin
AC_ARG_ENABLE([trafficstats],
	[AS_HELP_STRING([--enable-trafficstats],
		[Enable Traffic Stats plugin.])],
	[case "${enableval}" in
		yes)	trafficstats_plugin=yes ;;
		no)	trafficstats_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-trafficstats]) ;;
	esac],
	[trafficstats_plugin=yes])
AM_CONDITIONAL([ENABLE_TRAFFIC_STATS_PLUGIN], [test x$trafficstats_plugin = xyes])

dnl impulse15 plugin
AS_IF([test "x${have_fftw3_header}" = "xyes" \
       -a "x${have_fftw3}" = "xyes" \
       -a "x${have_pulse}" = "xyes"],
	  [deps_plugin_impulse15=yes],
	  [deps_plugin_impulse15=no])
AC_ARG_ENABLE([impulse15],
	[AS_HELP_STRING([--enable-impulse15],
		[Enable Impulse15 plugin.])],
	[case "${enableval}" in
		yes)	impulse15_plugin=${deps_plugin_impulse15} ;;
		no)	impulse15_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-impulse15]) ;;
	esac],
	[impulse15_plugin=${deps_plugin_impulse15}])
AM_CONDITIONAL([ENABLE_IMPULSE15_PLUGIN], [test x$impulse15_plugin = xyes])

dnl
dnl Experimental (under development) plugins
dnl

dnl Nexuiz plugin
AC_ARG_ENABLE([game-nexuiz],
	[AS_HELP_STRING([--enable-game-nexuiz],
		[Enable Nexuiz plugin.])],
	[case "${enableval}" in
		yes)	game_nexuiz_plugin=yes ;;
		no)	game_nexuiz_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-game-nexuiz]) ;;
	esac],
	[game_nexuiz_plugin=no])
AM_CONDITIONAL([ENABLE_GAME_NEXUIZ_PLUGIN], [test x$game_nexuiz_plugin = xyes])

dnl Backlight plugin
AC_ARG_ENABLE([backlight],
	[AS_HELP_STRING([--enable-backlight],
		[Enable Backlight plugin.])],
	[case "${enableval}" in
		yes)	backlight_plugin=yes ;;
		no)	backlight_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-backlight]) ;;
	esac],
	[backlight_plugin=no])
AM_CONDITIONAL([ENABLE_BACKLIGHT_PLUGIN], [test x$backlight_plugin = xyes])

dnl Notify 2 plugin
AC_ARG_ENABLE([notify-lcd2],
	[AS_HELP_STRING([--enable-notify-lcd2],
		[Enable Notify LCD plugin. Takes over as notification daemon and displays messages on LCD, blinks keyboard])],
	[case "${enableval}" in
		yes)	notify_lcd2_plugin=yes ;;
		no)	notify_lcd2_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-notify-lcd2]) ;;
	esac],
	[notify_lcd2_plugin=no])
AM_CONDITIONAL([ENABLE_NOTIFY_LCD2_PLUGIN], [test x$notify_lcd2_plugin = xyes])

dnl PPAStats plugin
AC_ARG_ENABLE([ppastats],
	[AS_HELP_STRING([--enable-ppastats],
		[Enable PPAStats plugin.])],
	[case "${enableval}" in
		yes)	ppastats_plugin=yes ;;
		no)	ppaststs_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-ppastats]) ;;
	esac],
	[ppastats_plugin=no])
AM_CONDITIONAL([ENABLE_PPASTATS_PLUGIN], [test x$ppastats_plugin = xyes])

dnl NM plugin
AC_ARG_ENABLE([nm],
	[AS_HELP_STRING([--enable-nm],
		[Enable NM (Network Manager) plugin.])],
	[case "${enableval}" in
		yes)	nm_plugin=yes ;;
		no)	nm_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-nm]) ;;
	esac],
	[nm_plugin=no])
AM_CONDITIONAL([ENABLE_NM_PLUGIN], [test x$nm_plugin = xyes])

dnl Lens plugin
AC_ARG_ENABLE([lens],
	[AS_HELP_STRING([--enable-lens],
		[Enable Unity Lens plugin.])],
	[case "${enableval}" in
		yes)	lens_plugin=yes ;;
		no)	lens_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-lens]) ;;
	esac],
	[lens_plugin=no])
AM_CONDITIONAL([ENABLE_LENS_PLUGIN], [test x$lens_plugin = xyes])

dnl WebKit browser plugin
AC_ARG_ENABLE([webkit-browser],
	[AS_HELP_STRING([--enable-webkit-browser],
		[Enable Webkit browser plugin.])],
	[case "${enableval}" in
		yes)	webkitbrowser_plugin=yes ;;
		no)	webkitbrowser_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-webkit-browser]) ;;
	esac],
	[webkitbrowser_plugin=no])
AM_CONDITIONAL([ENABLE_WEBKIT_BROWSER_PLUGIN], [test x$webkitbrowser_plugin = xyes])

dnl Things plugin
AC_ARG_ENABLE([things],
	[AS_HELP_STRING([--enable-things],
		[Enable Things python animation API plugin.])],
	[case "${enableval}" in
		yes)	things_plugin=yes ;;
		no)	things_plugin=no ;;
		*)	AC_MSG_ERROR([bad value ${enableval} for --enable-things]) ;;
	esac],
	[things_plugin=no])
AM_CONDITIONAL([ENABLE_THINGS_PLUGIN], [test x$things_plugin = xyes])

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
AS_IF([test "x$volume_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("rss                         - ")
AS_IF([test "x$rss_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("processes                   - ")
AS_IF([test "x$processes_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("sysmon                      - ")
AS_IF([test "x$sysmon_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("cal                         - ")
AS_IF([test "x$cal_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("cal-evolution               - ")
AS_IF([test "x$cal_evolution_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("cal-google                  - ")
AS_IF([test "x$cal_google_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("lcdbiff                     - ")
AS_IF([test "x$lcdbiff_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("background                  - ")
AS_IF([test "x$background_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("cairo-clock                 - ")
AS_IF([test "x$cairo_clock_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("clock                       - ")
AS_IF([test "x$clock_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("fx                          - ")
AS_IF([test "x$fx_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("g15daemon-server            - ")
AS_IF([test "x$g15daemon_server_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("im                          - ")
AS_IF([test "x$im_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("indicator-messages          - ")
AS_IF([test "x$indicator_messages_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("lcdshot                     - ")
AS_IF([test "x$lcdshot_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("macro-recorder              - ")
AS_IF([test "x$macro_recorder_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("macros                      - ")
AS_IF([test "x$macros_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("profiles                    - ")
AS_IF([test "x$profiles_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("menu                        - ")
AS_IF([test "x$menu_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("mounts                      - ")
AS_IF([test "x$mounts_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("mpris                       - ")
AS_IF([test "x$mpris_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("notify-lcd                  - ")
AS_IF([test "x$notify_lcd_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("panel                       - ")
AS_IF([test "x$panel_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("screensaver                 - ")
AS_IF([test "x$screensaver_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("stopwatch                   - ")
AS_IF([test "x$stopwatch_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("tweak                       - ")
AS_IF([test "x$tweak_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("mediaplayer                 - ")
AS_IF([test "x$mediaplayer_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("weather                     - ")
AS_IF([test "x$weather_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("weather-noaa                - ")
AS_IF([test "x$weather_noaa_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("weather-yahoo               - ")
AS_IF([test "x$weather_yahoo_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("sense                       - ")
AS_IF([test "x$sense_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("tails                       - ")
AS_IF([test "x$tails_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("display                     - ")
AS_IF([test "x$display_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("voip                        - ")
AS_IF([test "x$voip_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("voip-teamspeak3             - ")
AS_IF([test "x$voip_teamspeak3_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("google-analytics            - ")
AS_IF([test "x$google_analytics_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("debug                       - ")
AS_IF([test "x$debug_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("trafficstats                - ")
AS_IF([test "x$trafficstats_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("game-nexuiz                 - ")
AS_IF([test "x$game_nexuiz_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("backlight                   - ")
AS_IF([test "x$backlight_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("notify-lcd2                 - ")
AS_IF([test "x$notify_lcd2_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("ppastats                    - ")
AS_IF([test "x$ppastats_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("nm                          - ")
AS_IF([test "x$nm_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("lens                        - ")
AS_IF([test "x$lens_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("webkitbrowser               - ")
AS_IF([test "x$webkitbrowser_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("things                      - ")
AS_IF([test "x$things_plugin" = "xyes" ],
     [AS_ECHO("Enabled")],
     [AS_ECHO("Disabled")])
AS_ECHO_N("impulse15                   - ")
AS_IF([test "x$impulse15_plugin" = "xyes" ],
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
