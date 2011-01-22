#! /bin/sh

### BEGIN INIT INFO
# Provides:          g15daemon
# Required-Start:    $syslog $local_fs
# Required-Stop:     $syslog $local_fs
# Should-Start:      $remote_fs
# Should-Stop:       $remote_fs
# X-Start-Before:    xdm kdm gdm ldm sdm
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: load deamon for Logitech G19 keyboard lcd display
# Description:       load deamon for Logitech G19 keyboard lcd display
### END INIT INFO


#
# Based on g15daemon
#

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=/usr/sbin/g19daemon
NAME=g19d
DESC=g19d

[ -x "$DAEMON" ] || exit 0

# Include g15daemon defaults if available
if [ -f /etc/default/g19d ] ; then
        . /etc/default/g19d
fi

if [ "$G19D_ENABLED" != "y" -a "$G19D_ENABLED" != "Y" ]; then
    echo "G19D is not enabled, edit /etc/default/g19d and uncomment the G19D_ENABLED variable"
    exit
fi


if [ "$SWITCH_KEY" = "MR" ]; then
        DAEMON_OPTS="-s $DAEMON_OPTS"
fi

set -e

if [ "$G15DEBUG" = "on" ]; then
log() {
    logger -p daemon.debug -t g15 -- "$*"
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
        wait_for_file /dev/input/uinput 3  ||  return 1
    fi
}

wait_usr_mount() {
    if [ ! -e "$DAEMON" ] ; then
        wait_for_file "$DAEMON" 7  ||  return 1
    fi
}

is_running() {
        start-stop-daemon --stop --test --quiet --pidfile \
                /var/run/$NAME.pid --exec $DAEMON
}

do_start() {
        start-stop-daemon --start --quiet --pidfile /var/run/$NAME.pid \
                --exec $DAEMON -- $DAEMON_OPTS
}

do_stop() {
        #$DAEMON -k
        test -f /var/run/$NAME.pid && PID=$(cat /var/run/$NAME.pid)
        if [ -z "$PID" ]
        then PID=$(ps -ef|grep "python.*g19"|grep -v "grep"|awk '{ print $2 }')        
        fi
        if [ -n "$PID" ]
        then kill $PID
        fi 
        start-stop-daemon --stop --quiet --pidfile /var/run/$NAME.pid \
                --oknodo --retry 5 --exec $DAEMON
}


case "$1" in
  start)
        echo -n "Starting $DESC: "
        #load_uinput || echo -n ".../dev/input/uinput not found ..."
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
            
        
