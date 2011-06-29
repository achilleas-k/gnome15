package org.gnome15;
import java.util.List;
import java.util.Map;
import org.freedesktop.dbus.DBusInterface;
import org.freedesktop.dbus.DBusSignal;
import org.freedesktop.dbus.exceptions.DBusException;
public interface Page extends DBusInterface
{
   public static class KeysPressed extends DBusSignal
   {
      public final List<String> keys;
      public KeysPressed(String path, List<String> keys) throws DBusException
      {
         super(path, keys);
         this.keys = keys;
      }
   }
   public static class KeysReleased extends DBusSignal
   {
      public final List<String> keys;
      public KeysReleased(String path, List<String> keys) throws DBusException
      {
         super(path, keys);
         this.keys = keys;
      }
   }

  public void CancelTimer();
  public void Raise();
  public void CycleTo();
  public void SetThemeSVG(String svg_text);
  public boolean IsVisible();
  public void SetFont(double font_size, String font_family, String font_style, String font_weight);
  public void Circle(double x, double y, double radius, boolean fill);
  public void Save();
  public void Rectangle(double x, double y, double width, double height, boolean fill);
  public void Foreground(short r, short g, short b, short a);
  public void ImageData(List<Byte> image_data, double x, double y);
  public short GetPriority();
  public void SetPriority(short priority, double revert_after, double delete_after);
  public void ReserveKey(String key_name);
  public void Line(double x1, double y1, double x2, double y2);
  public void UnreserveKey(String key_name);
  public String GetId();
  public void DrawSurface();
  public void SetThemeProperty(String name, String value);
  public void Redraw();
  public void Delete();
  public void Restore();
  public void NewSurface();
  public void SetThemeProperties(Map<String,String> properties);
  public void Text(String text, double x, double y, double width, double height, String text_align);
  public void Image(String path, double x, double y, double width, double height);
  public void Arc(double x, double y, double radius, double startAngle, double endAngle, boolean fill);
  public String GetTitle();
  public void LoadTheme(String dir, String variant);
  public void SetLineWidth(double line_width);

}
