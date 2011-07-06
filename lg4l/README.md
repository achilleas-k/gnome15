Logitech 4 Linux
================

This project is intended to provide kernel modules to support various Logictech
input devices including:

* G110
* G13
* G15
* G19

Personally I don't know too much about any of the devices except the G110 (because I have one).

This work has been mostly done by a couple of friendly people on the Freenode IRC channel #lg4l

If you're looking for some help, best to drop by there and see if anyone's around.

Building
--------

All going well, you should be able to just install your kernel headers and type

    # make
    # make install

After you've installed the modules you need to rebuild your initrd. The easiest way I've found to do this (on Ubuntu) is:

    # sudo update-initramfs -k all -c

Additionally, if you're trying to work out what might be going wrong, enabling HID debugging is useful, simply create a file /etc/modprobe.d/hid-debug.conf with a single line in it:

    options hid debug=2

Note: You have to update the initramfs again after changing hid options.
