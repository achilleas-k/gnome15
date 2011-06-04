if ENABLE_VOLUME_PLUGIN
    MAYBE_VOLUME = volume
endif
if ENABLE_RSS_PLUGIN
    MAYBE_RSS = rss
endif
if ENABLE_SYSMON_PLUGIN
    MAYBE_SYSMON = sysmon
endif
if ENABLE_PROCESSES_PLUGIN
    MAYBE_PROCESSES = processes
endif
if ENABLE_WEBCAM_PLUGIN
    MAYBE_WEBCAM = webcam
endif

SUBDIRS = background cairo-clock clock fx macro-recorder macros mounts notify-lcd im weather mpris menu panel videoplayer g15daemon-server stopwatch screensaver \
	$(MAYBE_SYSMON) $(MAYBE_VOLUME) $(MAYBE_RSS) $(MAYBE_PROCESSES) $(MAYBE_WEBCAM)
	
DIST_SUBDIRS = background cairo-clock clock fx macro-recorder macros mounts notify-lcd im weather mpris menu panel videoplayer g15daemon-server stopwatch \
	sysmon volume rss processes webcam screensaver