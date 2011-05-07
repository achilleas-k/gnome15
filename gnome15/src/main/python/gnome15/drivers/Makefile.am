if ENABLE_DRIVER_KERNEL
    MAYBE_KERNEL = driver_kernel.py fb.py
endif
if ENABLE_DRIVER_G19DIRECT
    MAYBE_G19DIRECT = driver_g19direct.py
endif

driversdir = $(pkgpythondir)/drivers

drivers_PYTHON = __init__.py \
	driver_g15.py \
	driver_g19.py \
	driver_gtk.py \
	$(MAYBE_KERNEL) $(MAYBE_G19DIRECT)
	
EXTRA_DIST = $(drivers_PYTHON)	
	