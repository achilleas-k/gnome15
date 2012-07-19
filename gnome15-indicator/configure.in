AC_INIT(gnome15-indicator, 0.9.0)
AC_CONFIG_SRCDIR([g15-indicator.desktop.in])
AM_INIT_AUTOMAKE([tar-ustar])
AM_MAINTAINER_MODE
LT_INIT
AC_CONFIG_MACRO_DIR([m4])

dnl check for python
AM_PATH_PYTHON

dnl Build locales
AC_ARG_ENABLE([locales],
	[AS_HELP_STRING([--enable-locales=list-of-locales],
		[List of locales to build for])],
	[build_locales=${enableval}],
	[build_locales=en_GB])	
AC_SUBST(BUILD_LOCALES, $build_locales)

AX_PYTHON_MODULE(gnome15,[])
AS_IF([test "x${HAVE_PYMOD_GNOME15}" = "xno"],
     [AC_MSG_ERROR([Requires Gnome15])])
     
dnl check for Appindicator
AX_PYTHON_MODULE(appindicator, [])
AS_IF([test "x${HAVE_PYMOD_APPINDICATOR}" = "xno"],
     [AC_MSG_ERROR([Requires Python Appindicator])])
         
AC_OUTPUT([
Makefile
g15-indicator.desktop
])


AS_ECHO("Building i18n for locales: $build_locales")
AS_ECHO("")
