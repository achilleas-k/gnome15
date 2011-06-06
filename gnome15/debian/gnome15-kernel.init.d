#! /bin/sh

### BEGIN INIT INFO
# Provides:          gnome15-kernel
# Required-Start:    $syslog $local_fs
# Required-Stop:     $syslog $local_fs
# Should-Start:      $remote_fs
# Should-Stop:       $remote_fs
# X-Start-Before:    xdm kdm gdm ldm sdm
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Configure lg4l kernel module for Logitech keyboards
# Description:       Configure lg4l kernel module for Logitech keyboards
### END INIT INFO

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
NAME=gnome15-kernel
DESC="Gnome15 Kernel Driver Setup"

# Include gnome15-kernel defaults if available
if [ -f /etc/default/gnome15-kernel ] ; then
        . /etc/default/gnome15-kernel
fi

set -e

if [ "$G_DEBUG" = "on" ]; then
log() {
    logger -p daemon.debug -t lg4l -- "$*"
}
else
log() {
    true
}
fi

wait_for_file() {
        local file=$1
        local timeout=$2
        [ "$timeout" ] || timeout=120

        local count=$(($timeout * 10))
        while [ $count != 0 ]; do
                [ -e "$file" ] && return 0
                sleep 0.1
                count=$(($count - 1))
        done
        return 1
}

load_uinput() {
    if [ ! -e /dev/input/uinput ] ; then
        modprobe -q uinput || true
        wait_for_file /dev/input/uinput 3  ||  wait_for_file /dev/input/by-id 3 || return 1
    fi
}

wait_usr_mount() {
    if [ ! -e "$DAEMON" ] ; then
        wait_for_file "$DAEMON" 7  ||  return 1
    fi
}

is_running() {
	lsmod|grep "hid_g"|grep -v "hid_gfb"
}

do_start() {
		set x $MODULES hid-gfb
		shift
		for i in $*
		do
		    i=`echo $i|tr '-' '_'`
			if ! grep "^$i" /proc/modules >/dev/null
			then if modprobe $i
				 then log "Inserted module $i"
				 else log "Failed to insert module $i"
		         fi
		    fi
		done
		unbind
		bind
}

bind() {
		# now bind to correct module
		for dev in `ls /sys/bus/hid/devices/ | egrep '046D:C21C'`
		do 
		   log "Binding G13 $dev"
		   if ! echo -n $dev > /sys/bus/hid/drivers/hid-g13/bind 2>/dev/null
		   then log "Failed to bind G13 $dev"
		   fi
		done
		
		for dev in `ls /sys/bus/hid/devices/ | egrep '046D:C222'`
		do 
		   log "Binding G15 $dev"
		   if ! echo -n $dev > /sys/bus/hid/drivers/hid-g15/bind 2>/dev/null
		   then log "Failed to bind G15 $dev"
		   fi
		done
		
		for dev in `ls /sys/bus/hid/devices/ | egrep '046D:C229'`
		do 
		   log "Binding G19 $dev"
		   if ! echo -n $dev > /sys/bus/hid/drivers/hid-g19/bind 2>/dev/null
		   then log "Failed to bind G19 $dev"
		   fi
		done
		
		for dev in `ls /sys/bus/hid/devices/ | egrep '046D:C22B'`
		do 
		   log "Binding G110 $dev"
		   if ! echo -n $dev > /sys/bus/hid/drivers/hid-g110/bind 2>/dev/null
		   then log "Failed to bind G110 $dev"
		   fi
		done
}

unbind() {
		for dev in `ls /sys/bus/hid/drivers/generic-usb/ | egrep '046D:(C21C|C222|C229|C22B)'`
		do
    		log "Unbinding $dev"
    		echo -n $dev > /sys/bus/hid/drivers/generic-usb/unbind
		done
}

do_stop() {
		unbind
		set x $MODULES
		shift
		for i in $*
		do
		    i=`echo $i|tr '-' '_'`
		    if rmmod $i >/dev/null 2>&1 
		    then log "Removed module for $i"
		    else log "Failed to remove module $i"
		    fi
		done
}


case "$1" in
  start)
        echo -n "Starting $DESC: "
        load_uinput || echo -n ".../dev/input/uinput not found ..."
        do_start
        echo "$NAME."
        ;;
  stop)
        echo -n "Stopping $DESC: "
        do_stop
        echo "$NAME."
        ;;
  #reload)
        #
        #       If the daemon can reload its config files on the fly
        #       for example by sending it SIGHUP, do it here.
        #
        #       If the daemon responds to changes in its config file
        #       directly anyway, make this a do-nothing entry.
        #
        # echo "Reloading $DESC configuration files."
        # start-stop-daemon --stop --signal 1 --quiet --pidfile \
        #       /var/run/$NAME.pid --exec $DAEMON
        #;;
  force-reload)
        #
        #       If the "reload" option is implemented, move the "force-reload"
        #       option to the "reload" entry above. If not, "force-reload" is
        #       just the same as "restart" except that it does nothing if the
        #   daemon isn't already running.
        # check wether $DAEMON is running. If so, restart
        is_running  &&  $0 restart  ||  exit 0
        ;;
  restart)
    echo -n "Restarting $DESC: "
        do_stop
        # the device is slow to shut-down
        sleep 1
        do_start
        echo "$NAME."
        ;;
  udev)
        log "calling g15 udev; action: $ACTION, product $PRODUCT"
        if [ "x$ACTION" = "xadd" ] ; then
            load_uinput || true
            wait_usr_mount || true
            # it seems udev will not release a device if userspace is still
            # connected
            is_running && ( do_stop; sleep 1 )
            do_start
        elif [ "x$ACTION" = "xremove" ] ; then
            do_stop
        else
            echo "unknow udev action '$ACTION'"
            exit 1

        fi
        ;;
  shared-udev)
        # some devices share usb also for audio, which causes some spourios
        # udev messages.
        log "calling g15 shared-dev; action: $ACTION, product $PRODUCT"
        if [ "x$ACTION" = "xadd" ] ; then
            load_uinput || true
            wait_usr_mount || true
            do_start
        elif [ "x$ACTION" = "xremove" ] ; then
            do_stop
        else
            echo "unknow udev action '$ACTION'"
            exit 1

        fi
        ;;

  *)
        N=/etc/init.d/$NAME
        echo "Usage: $N {start|stop|restart|force-reload|udev}" >&2
        exit 1
        ;;
esac

exit 0
            
        
