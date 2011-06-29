package org.gnome15;

import org.freedesktop.dbus.DBusInterface;
import org.freedesktop.dbus.UInt32;

public interface Device extends DBusInterface {

	public void Enable();

	public String GetUID();

	public String GetScreen();

	public String GetUsbID();

	public Pair<UInt32, UInt32> GetSize();

	public String GetModelFullName();

	public void Disable();

	public UInt32 GetBPP();

}
