#!/bin/bash

cd $(dirname $0)

# Python
xgettext --from-code=UTF-8 --language=Python --keyword=N_ --keyword=_ --output=gnome15-drivers.pot ../src/gnome15/util/*.py
xgettext --from-code=UTF-8 --language=Python --keyword=N_ --keyword=_ --output=gnome15-drivers.pot ../src/gnome15/drivers/*.py
xgettext --from-code=UTF-8 --language=Python --keyword=N_ --keyword=_ --output=gnome15.pot ../src/gnome15/*.py

# Glade
for i in ../data/glade/*.glade; do
	intltool-extract --type=gettext/glade $i
        mv ${i}.h .
done
for i in *.h; do
	bn=$(basename ${i} .h)
	bn=$(basename ${bn} .glade).pot
	xgettext --from-code=UTF-8 --language=Python --keyword=N_ --keyword=_ --output=${bn} ${i}
done 
