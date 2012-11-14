#!/bin/bash
DIR=$(dirname $0)
cd "${DIR}"
export G15_PLUGINS=../gnome15-plugins/src
winpdb src/scripts/g15-desktop-service -f -l INFO restart
