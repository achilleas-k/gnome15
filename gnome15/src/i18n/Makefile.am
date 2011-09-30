EXTRA_DIST = gnome15.po \
			gnome15-drivers.po \
			gnome15.en_GB.po \
			gnome15-drivers.en_GB.po \
			driver_g15.en_GB.po \
			driver_g15direct.en_GB.po \
			driver_g19.en_GB.po \
			driver_g19direct.en_GB.po \
			driver_gtk.en_GB.po \
			driver_kernel.en_GB.po \
			g15-config.en_GB.po

all-local:
	for M_LOCALE in en_GB; do \
		mkdir -p $$M_LOCALE/LC_MESSAGES ; \
		for M_PO in *.po; do \
			BN=`basename $$M_PO .po`; \
			LL=`basename $$BN .$$M_LOCALE`.mo; \
			echo "$$M_PO -> $$LL"; \
			msgfmt $$M_PO --output-file $$M_LOCALE/LC_MESSAGES/$$LL; \
		done; \
	done
	
install-exec-hook:
	for M_LOCALE in en_GB; do \
		cp -pR $$M_LOCALE $(DESTDIR)$(datadir)/gnome15/i18n; \
	done
	