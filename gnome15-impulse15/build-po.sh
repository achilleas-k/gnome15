#!/bin/bash

echo -e "Locale: \c"
read locale
if [ -n "${locale}" ]; then
	cd $(dirname $0)
	basedir=$(pwd)
	modname=impulse15
	pushd impulse15
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