package org.gnome15;

import org.freedesktop.dbus.DBusInterface;
import org.freedesktop.dbus.UInt64;

public interface Control extends DBusInterface {
	public void Blink(double off_val, double delay, double duration);
	public void CancelReset();
	public void Fade(double percentage, double duration, boolean release);
	public UInt64 GetHint();
	public String GetValue();
	public void Release();
	public void Reset();
	public void SetValue(String value, double reset_after);

}
