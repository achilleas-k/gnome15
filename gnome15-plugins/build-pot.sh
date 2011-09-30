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
        if [ -d default ]; then
             pushd default
             mkdir -p i18n
             if [ $(ls *.svg 2>/dev/null|wc -l) -gt 0 ]; then 
                 for s in *.svg; do
                     svgname=$(basename ${s} .svg)
                     ${basedir}/../gnome15/mksvgheaders.py ${s} > i18n/${svgname}.h
                    if [ -s i18n/${svgname}.h ]; then
                    	xgettext --language=Python --keyword=_ --keyword=N_ --output=i18n/${svgname}.pot i18n/${svgname}.h
                	else
                		rm -f i18n/${svgname}.h
                	fi
                 done 
             fi
             popd
        fi

        # Glade files
        if [ $(ls *.glade 2>/dev/null|wc -l) -gt 0 ]; then 
            for i in *.glade; do
                intltool-extract --type=gettext/glade ${i}
                gladename=$(basename $i .glade)
                mv -f ${i}.h i18n
                xgettext --language=Python --keyword=_ --keyword=N_ --output=i18n/${gladename}.pot i18n/${i}.h
            done
        fi

        popd
    fi
done 
