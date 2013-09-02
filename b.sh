#!/bin/bash

SUFFIX=""
VERSION=$(grep "AC_INIT" configure.in|awk -F, '{ print $2 }'|awk -F\) '{ print $1 }'|sed 's/ //g')

autoreconf -f && ./configure --enable-udev=/lib/udev/rules.d && make && make dist && cp gnome15-${VERSION}.tar.gz ~/Workspaces/home\:tanktarta\:gnome15${SUFFIX}/gnome15
