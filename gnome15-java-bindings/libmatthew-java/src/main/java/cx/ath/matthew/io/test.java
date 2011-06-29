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
import java.io.OutputStreamWriter;
class test
{
   public static void main(String[] args) throws Exception
   {
      PrintWriter out = new PrintWriter(new OutputStreamWriter(new ExecOutputStream(System.out, "xsltproc mcr.xsl -")));///java cx.ath.matthew.io.findeof")));
      
      out.println("<?xml version='1.0'?>");
      out.println("   <?xml-stylesheet href='style/mcr.xsl' type='text/xsl'?>");
      out.println("   <mcr xmlns:xi='http://www.w3.org/2001/XInclude'>");
      out.println("   <title>TEST</title>");
      out.println("   <content title='TEST'>");
      out.println("hello, he is helping tie up helen's lemmings");
      out.println("we are being followed and we break out");
      out.println("   </content>");
      out.println("   </mcr>");
      out.close();
   }
}
