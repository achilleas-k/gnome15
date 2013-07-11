#!/bin/bash
DIR=$(dirname $0)
cd "${DIR}"
export G15_PLUGINS=../gnome15-plugins/src
src/scripts/g15-systemtray
