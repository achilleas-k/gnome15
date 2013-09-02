#!/bin/bash

echo -e "Locale: \c"
read locale
if [ -n "${locale}" ]; then
	
	cd $(dirname $0)
	basedir=$(pwd)
	for i in src/*; do
	    if [ -d ${i} ]; then
	        modname=$(basename $i)
                echo $modname
	        pushd ${i} >/dev/null
	        mkdir -p i18n
	        
	        # Generate python / glade
	        pushd i18n >/dev/null
			for i in *.pot; do
				bn=$(basename $i .pot).${locale}.po
				msginit --no-translator --input=${i} --output=${bn} --locale=${locale} 
			done
			popd >/dev/null
			
			# Generate theme
                        for j in *
                        do
   			   if [ -d $j/i18n ]; then
		           pushd $j/i18n >/dev/null
				for k in *.pot ; do
					bn=$(basename $k .pot).${locale}.po
					echo "$k -> $bn [$locale]" 
					msginit --no-translator --input=${k} --output=${bn} --locale=${locale} 
				done
				popd >/dev/null
		           fi
                        done
	        
	        popd >/dev/null
		fi
	done
fi
