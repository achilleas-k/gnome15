if ENABLE_DRIVER_G19DIRECT
    MAYBE_PYLIBG19 = pylibg19
endif
if ENABLE_IMPULSE15_PLUGIN
    MAYBE_LIBIMPULSE = libimpulse
endif
SUBDIRS = src $(MAYBE_PYLIBG19) $(MAYBE_LIBIMPULSE) data man

DIST_SUBDIRS = src pylibg19 libimpulse data

# For Python autoconf macros
ACLOCAL_AMFLAGS = -I m4

