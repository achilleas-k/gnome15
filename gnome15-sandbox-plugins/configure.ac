AC_INIT(gnome15-sanbox-plugins, 0.0.9)
AC_CONFIG_SRCDIR([src/browser/browser.py])
AM_INIT_AUTOMAKE

AM_MAINTAINER_MODE

AC_CONFIG_MACRO_DIR([m4])

AC_PROG_LIBTOOL
AC_PROG_CC
     
AX_PYTHON_DEVEL([2.6])

AM_PATH_PYTHON([2.6])

AX_PYTHON_MODULE(gnome15, [])
AS_IF([test "x${HAVE_PYMOD_GNOME15}" = "xno"],
     [AC_MSG_ERROR([Requires Gnome15])])

AC_OUTPUT([
Makefile
src/Makefile
src/browser/Makefile
src/browser/default/Makefile
src/indicator-messages/Makefile
src/indicator-messages/default/Makefile
src/nm/Makefile
src/nm/default/Makefile
src/tk-test/Makefile
src/tk-text/default/Makefile
src/videoplayer/Makefile
src/videoplayer/default/Makefile
])
