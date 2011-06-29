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


public class TextField extends Field
{
   String defval;
   int length;
   public TextField(String name, String label)
   {
      this.name = name;
      this.label = label;
      this.defval = "";
      this.length = 0;
   }
   public TextField(String name, String label, String defval)
   {
      this.name = name;
      this.label = label;
      if (null == defval)
         this.defval = "";
      else
         this.defval = defval;
      this.length = 0;
   }
   public TextField(String name, String label, String defval, int length)
   {
      this.name = name;
      this.label = label;
      if (null == defval)
         this.defval = "";
      else
         this.defval = defval;
      this.length = length;
   }
   protected String print()
   {
      return "<input type=\"text\" name=\""+name+"\" value=\""+CGITools.escapeChar(defval,'"')+"\" "+(length==0?"":"size=\""+length+"\"")+" />";
   }
}


