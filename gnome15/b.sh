#!/bin/bash

autoreconf -f && ./configure --enable-udev=/lib/udev/rules.d && make && make dist && cp gnome15-0.9.0.tar.gz ~/Workspaces/home\:tanktarta\:gnome15-unstable/gnome15
