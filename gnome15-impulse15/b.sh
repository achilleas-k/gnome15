#!/bin/bash

version=0.0.13

autoreconf -f && ./configure && make && make dist && cp gnome15-impulse15-${version}.tar.gz ~/Workspaces/home\:tanktarta\:gnome15-unstable/gnome15-impulse15/ 
