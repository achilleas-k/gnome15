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

Now load the correct module for your device, eg:

    # modprobe hid-g19

The modules will now be available but the device will still be grabbed by generic-usb. Run the
rebind script to put the new module in control of the device:

    # ./rebind

