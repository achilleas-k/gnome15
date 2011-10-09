#!/bin/bash

echo -e "Locale: \c"
read locale
if [ -n "${locale}" ]; then
	
	cd $(dirname $0)
	basedir=$(pwd)
	for i in src/*; do
	    if [ -d ${i} ]; then
	        modname=$(basename $i)
	        pushd ${i}
	        mkdir -p i18n
	        
	        # Generate python / glade
	        pushd i18n
			for i in *.pot; do
				bn=$(basename $i .pot).${locale}.po
				msginit --input=${i} --output=${bn} --locale=${locale} 
			done
			popd
			
			# Generate theme
			if [ -d default ]; then
		        pushd default/i18n
				for i in *.pot; do
					bn=$(basename $i .pot).${locale}.po
					msginit --input=${i} --output=${bn} --locale=${locale} 
				done
				popd
			fi
	        
	        popd
		fi
	done
fi