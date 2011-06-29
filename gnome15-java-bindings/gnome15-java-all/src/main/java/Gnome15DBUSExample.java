import org.gnome15.Control;
import org.gnome15.Gnome15;
import org.gnome15.Page;
import org.gnome15.Screen;

public class Gnome15DBUSExample {

	public static void main(String[] args) throws Exception {
		Gnome15 g15 = new Gnome15();
		Screen screen = g15.getPrimaryScreen();
		Page page = g15.createPage(screen, "MyPage", "This is my page", Gnome15.PRI_NORMAL);
		page.Raise();
		Control control = g15.acquireControl(screen, "backlight_colour", 0, "0,0,0");
		for (int i = 0; i < 1000; i++) {
			// control.SetValue(String.valueOf((int)(Math.random() * 255)) + ","
			// + String.valueOf((int)(Math.random() * 255)) + "," +
			// String.valueOf((int)(Math.random() * 255)), 0);
			page.NewSurface();
			// page.SetFont(20, "Sans", "", "");
			page.Text("This is some text " + i, 0, 0, 0, 0, "center");
			page.DrawSurface();
			page.Redraw();
		}
		Thread.sleep(10000);
		g15.close();
	}

}
