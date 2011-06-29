/*
 * Java IO Library
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

package cx.ath.matthew.io;
import java.io.PrintWriter;
import java.io.BufferedReader;
import java.io.InputStreamReader;
class test3
{
   public static void main(String[] args) throws Exception
   {
      String file = args[0];
      PrintWriter p = new PrintWriter(new TeeOutputStream(System.out, file));
      BufferedReader r = new BufferedReader(new InputStreamReader(System.in));
      String s;
      while (null != (s = r.readLine()))
         p.println(s);
      p.close();
      r.close();
   }
}
