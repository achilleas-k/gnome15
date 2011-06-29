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

/**
 * Interface to handle exceptions in the CGI.
 */
public class DefaultErrorHandler implements CGIErrorHandler
{
   /**
    * This is called if an exception is not caught in the CGI.
    * It should handle printing the error message nicely to the user,
    * and then exit gracefully.
    */
   public void print(boolean headers_sent, Exception e)
   {
      if (!headers_sent) {
         System.out.println("Content-type: text/html");
         System.out.println("");
         System.out.println("<!DOCTYPE HTML PUBLIC \"-//IETF//DTD HTML 2.0//EN\">");
         System.out.println("<HTML><HEAD>");
         System.out.println("<TITLE>Exception in CGI</TITLE>");
         System.out.println("</HEAD><BODY>");
      }
      System.out.println("<HR>");
      System.out.println("<H1>"+e.getClass().toString()+"</H1>");
      System.out.println("<P>");
      System.out.println("Exception Message: "+e.getMessage());
      System.out.println("</P>");
      System.out.println("<P>");
      System.out.println("Stack Trace:");
      System.out.println("</P>");
      System.out.println("<PRE>");
      e.printStackTrace(System.out);
      System.out.println("</PRE>");
      System.out.println("<HR>");
      if (!headers_sent) {
         System.out.println("</BODY></HTML>");
      }
      System.exit(1);
   }
}
