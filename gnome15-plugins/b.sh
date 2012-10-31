#!/bin/bash

version=0.9.0

autoreconf -f && ./configure --enable-udev=/lib/udev/rules.d && make && make dist && cp gnome15-plugins-${version}.tar.gz ~/Workspaces/home\:tanktarta\:gnome15-unstable/gnome15-plugins/ && cp gnome15-plugins-${version}.tar.gz ~/Workspaces/home\:tanktarta\:gnome15-unstable/gnome15-ubuntu-plugins/
