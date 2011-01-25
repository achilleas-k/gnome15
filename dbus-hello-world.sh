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
       y="790.9259"
       id="text4014"
       transform="matrix(0.73491181,0,0,0.85727643,0,352.45774)"><tspan
         id="tspan4016"
         x="217.7132"
         y="790.9259">Using SVG - \${ticker}</tspan></text>
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
        # --print-reply is usd to block until reply is sent
    dbus-send --print-reply --dest="${BUS_NAME}" ${NAME} ${IF_NAME}.${METHOD} "$@"
} 

# Just show some stuff about the DBUS API
do_dbus GetServerInformation
do_dbus GetDriverInformation

# Create a new page to draw on. Because this script demonstrates both the SVG
# method of drawing, and using the drawing functions, we load the SVG theme
# text here

do_dbus CreatePage string:HelloWorld string:'HelloWorld !'
do_dbus SetPageThemeSVG string:HelloWorld string:"${SVG}"

# Make this page visible
do_dbus RaisePage string:HelloWorld

for i in 1 2 3 4 5 6 7 8 9 10
do
        # This demonstrates using the drawing functions. Create a new surface
        # everytime you want to redraw. Call DrawSurface when all drawn,
        # then redraw the page 

    do_dbus NewSurface string:HelloWorld
    do_dbus Foreground string:HelloWorld int16:0 int16:255: int16:0 int16:255
    do_dbus Rectangle string:HelloWorld double:40 double:0 double:80 double:80 boolean:true
    do_dbus Foreground string:HelloWorld int16:0 int16:0: int16:255 int16:255
    do_dbus Line string:HelloWorld double:130 double:0 double:130 double:80
    do_dbus Line string:HelloWorld double:130 double:80 double:210 double:80 
    do_dbus Line string:HelloWorld double:210 double:80 double:130 double:0
    do_dbus Foreground string:HelloWorld int16:255 int16:0: int16:255 int16:128
    do_dbus Circle string:HelloWorld double:260 double:40 double:40 boolean:true
    do_dbus SetFont string:HelloWorld double:20.0 string:"Sans" string:"normal" string:"normal"
    do_dbus Foreground string:HelloWorld int16:0 int16:255: int16:255 int16:255
    do_dbus DrawSurface string:HelloWorld
    do_dbus Text string:HelloWorld string:"Using Drawing Functions!! $i" double:0 double:60 double:320 double:80 string:center
    do_dbus Image string:HelloWorld string:utilities-system-monitor double:140 double:60 double:40 double:40
    do_dbus ImageData string:HelloWorld array:byte:"$(cat /usr/share/pixmaps/gnome-logo-icon.png)" double:280 double:30

        # This demonstrates using theme properties
    do_dbus SetPageThemeProperty string:HelloWorld string:ticker string:"$i"

        # Now redraw the page, this sends it to the LCD
    do_dbus RedrawPage string:HelloWorld
    sleep 1
done

# Remember to destroy the page when done
do_dbus DestroyPage string:HelloWorld

        