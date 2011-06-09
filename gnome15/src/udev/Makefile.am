if ENABLE_DRIVER_KERNEL
    MAYBE_KERNEL = 99-gnome15-kernel.rules
endif

if ENABLE_DRIVER_G19DIRECT
    MAYBE_G19DIRECT = 99-gnome15-g19direct.rules
endif

udevdir = @UDEV_RULES_PATH@
udev_DATA = $(MAYBE_KERNEL) $(MAYBE_G19DIRECT)

EXTRA_DIST = 99-gnome15-g19direct.rules 99-gnome15-kernel.rules