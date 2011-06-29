#!/bin/bash

if ! which javac
then echo "$0: Java compiler must be on PATH" >&2
     exit 1
fi

cd $(pwd)
classpath=../gnome15-java-al.jar
if javac -classpath "${classpath}" Gnome15DBUSExample.java
then java -Djava.library.path=.. -classpath ":${classpath}" Gnome15DBUSExample
else exit $?
fi
