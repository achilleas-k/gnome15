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
import java.io.InputStreamReader;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintWriter;

public class testclient
{
   public static void main(String args[]) throws IOException
   {
      UnixSocket s = new UnixSocket(new UnixSocketAddress("testsock", true));
      OutputStream os = s.getOutputStream();
      PrintWriter o = new PrintWriter(os);
      BufferedReader r = new BufferedReader(new InputStreamReader(System.in));
      String l;
      while (null != (l = r.readLine())) {
         byte[] buf = (l+"\n").getBytes();
         os.write(buf, 0, buf.length);
      }
      s.close();
   }
}
