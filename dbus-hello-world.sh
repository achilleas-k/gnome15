#!/bin/bash

# DBUS names

BUS_NAME=org.gnome15.Gnome15
NAME="/org/gnome15/Service"
IF_NAME="org.gnome15.Service"

# The theme text

SVG=$(cat <<EOF
<svg xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   width="320"
   height="240"
   id="svg2"
   version="1.1">
  <defs
     id="defs4" />
  <g
     id="layer1"
     transform="translate(0,-812.36218)">
    <text
       xml:space="preserve"
       style="font-size:35.27605218px;font-style:normal;font-weight:normal;text-align:center;line-height:125%;letter-spacing:0px;word-spacing:0px;text-anchor:middle;fill-opacity:1;stroke:none;font-family:Bitstream Vera Sans"
       x="217.7132"
       y="710.9259"
       id="text4014"
       transform="matrix(0.73491181,0,0,0.85727643,0,352.45774)"><tspan
         id="tspan4016"
         x="217.7132"
         y="710.9259">Hello \${logname}</tspan></text>
    <path
       style="fill:#950000;fill-opacity:1;stroke:#000000;stroke-opacity:1"
       id="path2992"
       d="M 60.312432,65.003797 A 15,17.5 0 1 1 59.999994,65"
       transform="translate(94.687568,917.35838)"/>
  </g>
</svg>
EOF
)

# Helper function

do_dbus() {
	METHOD="$1"
	shift
	dbus-send --dest="${BUS_NAME}" ${NAME} ${IF_NAME}.${METHOD} "$@"
} 

do_dbus GetServerInformation
do_dbus CreatePage string:HelloWorld string:'Hello World!'
do_dbus SetPageThemeSVG string:HelloWorld string:"${SVG}"
do_dbus SetPageThemeProperty string:HelloWorld string:logname string:"$(logname)"
do_dbus RaisePage string:HelloWorld
for i in 1 2 3 4 5 6 7 8 9 10
do
	do_dbus SetPageThemeProperty string:HelloWorld string:logname string:"$(logname) - $i"
	do_dbus RedrawPage string:HelloWorld
	sleep 1
done
do_dbus DestroyPage string:HelloWorld
