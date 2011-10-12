SUBDIRS = default 

plugindir = $(datadir)/gnome15/plugins/im
plugin_DATA = im.py

EXTRA_DIST =  			\
	$(plugin_DATA)
	
all-local:
	for M_LOCALE in @BUILD_LOCALES@; do \
		mkdir -p i18n/$$M_LOCALE/LC_MESSAGES ; \
        if [ `ls i18n/*.po 2>/dev/null|wc -l` -gt 0 ]; then \
			for M_PO in i18n/*.po; do \
				BN=`basename $$M_PO .po`; \
				LL=`basename $$BN .$$M_LOCALE`.mo; \
				echo "$$M_PO -> $$LL"; \
				msgfmt $$M_PO --output-file i18n/$$M_LOCALE/LC_MESSAGES/$$LL; \
			done; \
		fi; \
	done
	
install-exec-hook:
	for M_LOCALE in @BUILD_LOCALES@; do \
		mkdir -p $(DESTDIR)$(datadir)/gnome15/plugins/im/i18n; \
		cp -pR i18n/$$M_LOCALE $(DESTDIR)$(datadir)/gnome15/plugins/im/i18n; \
	done
	