
driversdir = $(pkgpythondir)/drivers

if PYINPUTEVENT
drivers_PYTHON = __init__.py \
	driver_g15.py \
	driver_g19.py \
	driver_gtk.py \
	driver_g19direct.py \
	driver_kernel.py \
	fb.py
else
drivers_PYTHON = __init__.py \
	driver_g15.py \
	driver_g19.py \
	driver_g19direct.py \
	driver_gtk.py
endif
	
EXTRA_DIST =  			\
	$(drivers_PYTHON)	