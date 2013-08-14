#!/usr/bin/env python

from distutils.core import setup

setup(name='pylibg19',
      version='0.0.7',
      description='Python interface to the Logitech G19',
      requires='usb',
      author='MultiCoreNop,Brett Smith',
      author_email='tanktarta@blueyonder.co.uk',
      license="GPL",
      url='http://www.russo79.com/gnome15',
      packages= [ 'g19' ],
      )
