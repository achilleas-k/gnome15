#!/bin/bash

version=0.0.1

autoreconf -f && ./configure && make && make dist && cp gnome15-gnome-shell-${version}.tar.gz ~/Workspaces/home\:tanktarta\:gnome15-unstable/gnome15-plugins/ && cp gnome15-gnome-shell-${version}.tar.gz ~/Workspaces/home\:tanktarta\:gnome15-unstable/gnome15-gnome-shell/
