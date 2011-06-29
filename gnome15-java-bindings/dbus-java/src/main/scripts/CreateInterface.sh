#!/bin/sh

cd `dirname $0`/../../..
dir=`pwd`

java -DPid=$$ -Djava.library.path=$dir/../libunix-java/linux-x86_64/target -cp \
	$dir/target/classes:$dir/../libmatthew-java/target/classes:$dir/target/classes \
	org.freedesktop.dbus.bin.CreateInterface "$@"
