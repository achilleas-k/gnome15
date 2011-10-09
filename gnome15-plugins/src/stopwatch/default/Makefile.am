themedir = $(datadir)/gnome15/plugins/stopwatch/default
theme_DATA = \
	g19.svg \
	g19-one_timer.svg \
	g19-two_timers.svg \
	up.gif \
	playpause.gif \
	reset.gif \
	mx5500.svg \
	mx5500-one_timer.svg \
	mx5500-two_timers.svg \
	default.svg \
	default-one_timer.svg \
	default-two_timers.svg

EXTRA_DIST = \
	$(theme_DATA)

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
		mkdir -p $(datadir)/gnome15/plugins/stopwatch/default/i18n; \
		cp -pR i18n/$$M_LOCALE $(datadir)/gnome15/plugins/stopwatch/default/i18n; \
	done