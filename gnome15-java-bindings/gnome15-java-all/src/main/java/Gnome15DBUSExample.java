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
		for (int i = 0; i < 1000; i++) {
			page.NewSurface();
			page.Text("This is some text " + i, 0, 0, 0, 0, "center");
			page.DrawSurface();
			page.Redraw();
		}
		Thread.sleep(10000);
		g15.close();
	}

}
