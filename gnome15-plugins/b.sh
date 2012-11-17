#!/bin/bash

#!/bin/bash

SUFFIX=""
VERSION=$(grep "AC_INIT" configure.in|awk -F, '{ print $2 }'|awk -F\) '{ print $1 }'|sed 's/ //g')

autoreconf -f && \
./configure --enable-debug && \
make && make dist && \
cp gnome15-plugins-${VERSION}.tar.gz ~/Workspaces/home\:tanktarta\:gnome15${SUFFIX}/gnome15-plugins/ && cp gnome15-plugins-${VERSION}.tar.gz ~/Workspaces/home\:tanktarta\:gnome15${SUFFIX}/gnome15-ubuntu-plugins/
