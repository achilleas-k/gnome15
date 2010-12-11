bin_PROGRAMS = lgsetled
lgsetled_SOURCES = lgsetled.c
ACLOCAL_AMFLAGS = -I m4

install-exec-hook:
	chown root $(DESTDIR)$(bindir)/lgsetled
	chmod ug+rxs $(DESTDIR)$(bindir)/lgsetled
