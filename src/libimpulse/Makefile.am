#AM_CPPFLAGS = $(all_includes)
#AM_CFLAGS = -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC $(all_includes) 

AM_CFLAGS = $(all_includes)
AM_LDFLAGS = $(all_libraries)

lib_LTLIBRARIES = libimpulse.la
libimpulse_la_LDFLAGS = -version-info 1:0:1 -no-undefined -pthread -shared -Wl, -fPIC
libimpulse_la_SOURCES = Impulse.c
#libimpulse_la_CFLAGS = -pthread -Wall -fPIC 

pyexec_LTLIBRARIES = impulse.la
impulse_la_LIBADD = libimpulse.la
impulse_la_LDFLAGS = -avoid-version -module $(PYTHON_LDFLAGS) $(all_libraries) 
impulse_la_SOURCES = impulsemodule.c
#impulse_la_CFLAGS = -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC $(PYTHON_CPPFLAGS)  $(all_includes)
impulse_la_CFLAGS = $(all_includes) $(PYTHON_CPPFLAGS) 

pkginclude_HEADERS = Impulse.h

METASOURCES = AUTO
