
if ENABLE_INDICATOR
    MAYBE_INDICATOR = g15-indicator
endif

if ENABLE_SYSTEMTRAY
    MAYBE_SYSTEMTRAY = g15-systemtray
endif

if ENABLE_DRIVER_KERNEL
    MAYBE_KERNEL = g15-system-service
endif

bin_SCRIPTS = g15-launch libg15test g15-diag g15-config g15-desktop-service g15-support-dump $(MAYBE_INDICATOR) $(MAYBE_SYSTEMTRAY) $(MAYBE_KERNEL)

EXTRA_DIST = g15-launch libg15test g15-diag g15-config g15-desktop-service g15-systemtray g15-indicator g15-system-service g15-support-dump
