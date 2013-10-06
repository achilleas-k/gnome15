#!/bin/bash

#
# Creates the initial i18n structure for plugins
#

cd $(dirname $0)
basedir=$(pwd)
for i in src/*; do
    if [ -d ${i} ]; then
        modname=$(basename $i)
        pushd ${i}
        mkdir -p i18n
    
        # Python
        xgettext --language=Python --keyword=_ --output=i18n/${modname}.pot *.py
    
        # Theme files

        for m in *; do
            if [ -d "$m" ]; then
             pushd $m
             if [ $(ls *.svg 2>/dev/null|wc -l) -gt 0 ]; then 
                 mkdir -p i18n
                 echo "Found SVG"
                 for s in *.svg; do
                     echo "Generating C header$s"
                     svgname=$(basename ${s} .svg)
                     ${basedir}/../gnome15/mksvgheaders.py ${s} > i18n/${svgname}.h
                    if [ -s i18n/${svgname}.h ]; then
                        echo "Generating POT for ${svgname}.h"
                    	xgettext --language=Python --keyword=_ --keyword=N_ --output=i18n/${svgname}.pot i18n/${svgname}.h
                	else
                		rm -f i18n/${svgname}.h
                	fi
                 done 
             fi
             popd
           fi
        done

        # .ui files
        if [ $(ls *.ui 2>/dev/null|wc -l) -gt 0 ]; then
            for i in *.ui; do
                intltool-extract --type=gettext/glade ${i}
                uiname=$(basename $i .ui)
                mv -f ${i}.h i18n
                xgettext --language=Python --keyword=_ --keyword=N_ --output=i18n/${uiname}.pot i18n/${i}.h
            done
        fi

        popd
    fi
done 
