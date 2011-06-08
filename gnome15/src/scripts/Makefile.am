
if ENABLE_INDICATOR
    MAYBE_INDICATOR = g15-indicator
endif

if ENABLE_SYSTEMTRAY
    MAYBE_SYSTEMTRAY = g15-systemtray
endif

if ENABLE_DRIVER_KERNEL
    MAYBE_KERNEL = g15-system-service
endif

bin_SCRIPTS = g15-config g15-desktop-service $(MAYBE_INDICATOR) $(MAYBE_SYSTEMTRAY) $(MAYBE_KERNEL)

EXTRA_DIST = g15-config g15-desktop-service g15-systemtray g15-indicator g15-system-service
