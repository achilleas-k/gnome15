package org.gnome15;
import org.freedesktop.dbus.DBusInterface;
public interface Debug extends DBusInterface
{

  public void ShowGraph();
  public void MostCommonTypes();
  public void Objects(String typename);
  public void GC();
  public void Refererents(String typename);
  public void Referrers(String typename);

}
