STATUS OF GNOME15
=================

The latest updates to Fedora 21 seem to have broken the G15logging scripts for python.  There's quite a bit of outdated code that's being used so I expect getting this project up to speed may take a while.

I'm going to be attempting to find the issue preventing the logs from being imported to get the GUI running again.  The install was switched somewhere down the line to automake so the build instructions need a little updating to get running.  Because of the Russo79 website going down it appears we may have lost some commits.  Anyways I'm picking up maintance of the project and will be setting up a bug tracker to help get this project rolling again.

Gnome15
=======

A set of tools for configuring the Logitech G15 keyboard.

Contains pylibg19, a library providing support for the Logitech G19 until there
is kernel support available. It was based "Logitech-G19-Linux-Daemon" [1],
the work of "MultiCoreNop" [2].

[1] http://github.com/MultiCoreNop/Logitech-G19-Linux-Daemon
[2] http://github.com/MultiCoreNop

Installation
============

See the 'INSTALL' file.

How to report bugs
==================

Issues can be submited on the contributors website [3].

[3] https://projects.russo79.com/projects/gnome15

Requirements
============

Python 2.6
PyUSB 0.4
PIL (Python Image Library, just about any version should be ok)
