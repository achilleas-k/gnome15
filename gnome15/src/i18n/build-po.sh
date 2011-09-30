#!/bin/bash

echo -e "Locale: \c"
read locale
if [ -n "${locale}" ]; then
	for i in *.pot; do
		bn=$(basename $i .pot).${locale}.po
		msginit --input=${i} --output=${bn} --locale=${locale} 
	done
fi