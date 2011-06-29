/*
 * Java CGI Library
 *
 * Copyright (c) Matthew Johnson 2004
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

package cx.ath.matthew.cgi;

import java.util.Iterator;
import java.util.Map;

class testcgi extends CGI
{
   protected void cgi(Map POST, Map GET, Map ENV, Map COOKIE, String[] params) throws Exception
   {
      header("Content-type", "text/plain");
      setcookie("testcgi", "You have visited us already");
      out("This is a test CGI program");
      out("These are the params:");
      for (int i=0; i < params.length; i++)
         out("-- "+params[i]);
      
      out("These are the POST vars:");
      Iterator i = POST.keySet().iterator();
      while (i.hasNext()) {
         String s = (String) i.next();
         out("-- "+s+" => "+POST.get(s));
      }
      
      out("These are the GET vars:");
      i = GET.keySet().iterator();
      while (i.hasNext()) {
         String s = (String) i.next();
         out("-- "+s+" => "+GET.get(s));
      }
        
      out("These are the ENV vars:");
      i = ENV.keySet().iterator();
      while (i.hasNext()) {
         String s = (String) i.next();
         out("-- "+s+" => "+ENV.get(s));
      }
      
      out("These are the COOKIEs:");
      i = COOKIE.keySet().iterator();
      while (i.hasNext()) {
         String s = (String) i.next();
         out("-- "+s+" => "+COOKIE.get(s));
      }   
   }

   public static void main(String[] args)
   {
      CGI cgi = new testcgi();
      cgi.doCGI(args);
   }
}
