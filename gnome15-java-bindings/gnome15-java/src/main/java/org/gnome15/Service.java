package org.gnome15;

import java.util.List;
import org.freedesktop.dbus.DBusInterface;
import org.freedesktop.dbus.DBusSignal;
import org.freedesktop.dbus.Variant;
import org.freedesktop.dbus.exceptions.DBusException;

public interface Service extends DBusInterface {
	public static class ScreenAdded extends DBusSignal {
		public final Variant screen_name;

		public ScreenAdded(String path, Variant screen_name) throws DBusException {
			super(path, screen_name);
			this.screen_name = screen_name;
		}
	}

	public static class Started extends DBusSignal {
		public Started(String path) throws DBusException {
			super(path);
		}
	}

	public static class ScreenRemoved extends DBusSignal {
		public final Variant screen_name;

		public ScreenRemoved(String path, Variant screen_name) throws DBusException {
			super(path, screen_name);
			this.screen_name = screen_name;
		}
	}

	public static class Stopped extends DBusSignal {
		public Stopped(String path) throws DBusException {
			super(path);
		}
	}

	public static class Stopping extends DBusSignal {
		public Stopping(String path) throws DBusException {
			super(path);
		}
	}

	public static class Starting extends DBusSignal {
		public Starting(String path) throws DBusException {
			super(path);
		}
	}

	public boolean IsStopping();

	public Quad<String, String, String, String> GetServerInformation();

	public void Stop();

	public boolean IsStarted();

	public List<String> GetDevices();

	public List<String> GetScreens();

	public boolean IsStarting();

}
