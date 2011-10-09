plugindir = $(datadir)/gnome15/plugins/background
plugin_DATA = background.glade \
	background.py \
	background-160x43.png \
	background-320x240.png

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
	for M_LOCALE in  @BUILD_LOCALES@; do \
		mkdir -p $(datadir)/gnome15/plugins/background/i18n; \
		cp -pR i18n/$$M_LOCALE $(datadir)/gnome15/plugins/background/i18n; \
	done
