SUBDIRS = scripts gnome main man themes udev i18n plugins

if ENABLE_INDICATOR
SUBDIRS += indicator
endif

all-local:
	for PLUGIN in `ls plugins`; do \
		PLUGIN_DIR=plugins/$$PLUGIN; \
		if [ -d $$PLUGIN_DIR ]; then \
			pushd $$PLUGIN_DIR; \
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
			done; \
			for THEME_DIR in *; do \
				if [ -d $$THEME_DIR -a -d $$THEME_DIR/i18n ]; then \
					pushd $$THEME_DIR; \
					mkdir -p i18n/$$M_LOCALE/LC_MESSAGES ; \
			        if [ `ls i18n/*.po 2>/dev/null|wc -l` -gt 0 ]; then \
						for M_PO in i18n/*.po; do \
							BN=`basename $$M_PO .po`; \
							LL=`basename $$BN .$$M_LOCALE`.mo; \
							echo "$$M_PO -> $$LL"; \
							msgfmt $$M_PO --output-file i18n/$$M_LOCALE/LC_MESSAGES/$$LL; \
						done; \
					fi; \
					popd; \
				fi; \
			done; \
			popd; \
		fi; \
	done;
	
clean-local:
	find . -name '*.pyc' -exec rm {} \; ; \
	find . -name '*.pyo' -exec rm {} \; ; \
	for PLUGIN in `ls plugins`; do \
		PLUGIN_DIR=plugins/$$PLUGIN; \
		if [ -d $$PLUGIN_DIR ]; then \
			pushd $$PLUGIN_DIR; \
			for M_LOCALE in  @BUILD_LOCALES@; do \
				if [ -d i18n/$$M_LOCALE ]; then \
					rm -fr i18n/$$M_LOCALE; \
				fi; \
				for THEME_DIR in *; do \
					if [ -d $$THEME_DIR/i18n/$$M_LOCALE ]; then \
						pushd $$THEME_DIR; \
						rm -fr i18n/$$M_LOCALE; \
						popd; \
					fi; \
				done; \
			done; \
			popd; \
		fi; \
	done;
	
install-exec-hook:
	for PLUGIN in `ls plugins`; do \
		PLUGIN_DIR=plugins/$$PLUGIN; \
		if [ -d $(DESTDIR)$(datadir)/gnome15/plugins/$$PLUGIN ]; then \
			pushd $$PLUGIN_DIR; \
			for M_LOCALE in  @BUILD_LOCALES@; do \
				mkdir -p $(DESTDIR)$(datadir)/gnome15/plugins/$$PLUGIN/i18n; \
				cp -pR i18n/$$M_LOCALE $(DESTDIR)$(datadir)/gnome15/plugins/$$PLUGIN/i18n; \
			done; \
			for THEME_DIR in *; do \
				if [ -d $$THEME_DIR -a -d $$THEME_DIR/i18n ]; then \
					pushd $$THEME_DIR; \
					for M_LOCALE in @BUILD_LOCALES@; do \
						mkdir -p $(DESTDIR)$(datadir)/gnome15/plugins/$$PLUGIN/$$THEME_DIR/i18n; \
						cp -pR i18n/$$M_LOCALE $(DESTDIR)$(datadir)/gnome15/plugins/$$PLUGIN/$$THEME_DIR/i18n; \
					done; \
					popd; \
				fi; \
			done; \
			popd; \
		fi; \
	done;
