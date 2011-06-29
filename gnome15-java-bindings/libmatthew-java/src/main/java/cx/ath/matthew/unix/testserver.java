/*
 * Java Unix Sockets Library
 *
 * Copyright (c) Matthew Johnson 2005
 *
 * This program is free software; you can redistribute it and/or 
 * modify it under the terms of the GNU Lesser General Public License 
 * as published by the Free Software Foundation, version 2 only.
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details. 
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * To Contact the author, please email src@matthew.ath.cx
 *
 */

package cx.ath.matthew.unix;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.IOException;

public class testserver
{
   public static void main(String args[]) throws IOException
   {
      UnixServerSocket ss = new UnixServerSocket(new UnixSocketAddress("testsock", true));
      UnixSocket s = ss.accept();
      BufferedReader r = new BufferedReader(new InputStreamReader(s.getInputStream()));
      String l;
      while (null != (l = r.readLine()))
         System.out.println(l);/*
      InputStream is = s.getInputStream();
      int r;
      do {
         r = is.read();
         System.out.print((char)r);
      } while (-1 != r);*/
      s.close();
      ss.close();
   }
}
