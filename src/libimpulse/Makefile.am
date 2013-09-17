lib_LTLIBRARIES = libimpulse.la
libimpulse_la_SOURCES = Impulse.c
libimpulse_la_CFLAGS = ${PULSE_CFLAGS} ${FFTW_CFLAGS}
libimpulse_la_LDFLAGS = -version-info 1:0:1 -no-undefined -pthread -shared -Wl ${PULSE_LIBS} ${FFTW_LIBS}, -fPIC

pyexec_LTLIBRARIES = impulse.la
impulse_la_SOURCES = impulsemodule.c
impulse_la_CFLAGS = $(PYTHON_CPPFLAGS)
impulse_la_LDFLAGS = -avoid-version -module $(PYTHON_LDFLAGS)
impulse_la_LIBADD = libimpulse.la

pkginclude_HEADERS = Impulse.h

METASOURCES = AUTO
