package org.gnome15;

import java.util.List;

import org.freedesktop.dbus.DBusConnection;
import org.freedesktop.dbus.exceptions.DBusException;

public class Gnome15 {

	public final static short PRI_POPUP = 999;
	public final static short PRI_EXCLUSIVE = 100;
	public final static short PRI_HIGH = 99;
	public final static short PRI_NORMAL = 50;
	public final static short PRI_LOW = 20;
	public final static short PRI_INVISIBLE = 0;

	private final static String BUS_NAME = "org.gnome15.Gnome15";
	private final static String SERVICE_NAME = "/org/gnome15/Service";

	private DBusConnection conn;
	private Service service;

	public Gnome15() throws DBusException {
		conn = DBusConnection.getConnection(DBusConnection.SESSION);
		service = (Service) conn.getRemoteObject(BUS_NAME, SERVICE_NAME, Service.class);
	}
	
	public Screen getPrimaryScreen() throws DBusException {
		List<String> screens = service.GetScreens();
		if(screens.size() == 0) {
			throw new DBusException("There are no screens configured. Do you have all the drivers installed and configured?");
		}
		return getScreen(screens.get(0));
	}

	public Screen getScreen(String screenPath) throws DBusException {
		Screen screen = (Screen) conn.getRemoteObject(BUS_NAME, screenPath, Screen.class);
		return screen;
	}

	public Service getService() {
		return service;
	}

	public Page createPage(Screen screen, String id, String title, short priority) throws DBusException {
		return getPage(screen.CreatePage(id, title, priority));
	}

	public Page getPage(String pagePath) throws DBusException {
		return (Page) conn.getRemoteObject(BUS_NAME, pagePath, Page.class);
	}

	public Control getControl(String controlPath) throws DBusException {
		return (Control) conn.getRemoteObject(BUS_NAME, controlPath, Control.class);
	}

	public Debug getDebug() throws DBusException {
		return (Debug) conn.getRemoteObject(BUS_NAME, "/org/gnome15/Debug", Debug.class);
	}

	public void close() {
		conn.disconnect();
	}

	public Control acquireControl(Screen screen, String controlId, double releaseAfter, String value) throws DBusException {
		return getControl(screen.AcquireControl(controlId, releaseAfter, value));
	}
}
