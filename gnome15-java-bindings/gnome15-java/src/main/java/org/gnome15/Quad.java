package org.gnome15;
import org.freedesktop.dbus.Position;
import org.freedesktop.dbus.Tuple;
/** Just a typed container class */
public final class Quad <A,B,C,D> extends Tuple
{
   @Position(0)
   public final A a;
   @Position(1)
   public final B b;
   @Position(2)
   public final C c;
   @Position(3)
   public final D d;
   public Quad(A a, B b, C c, D d)
   {
      this.a = a;
      this.b = b;
      this.c = c;
      this.d = d;
   }
}
