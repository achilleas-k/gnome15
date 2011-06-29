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

public class TextArea extends Field
{
   String defval;
   int cols;
   int rows;
   public TextArea(String name, String label, String defval)
   {
      this(name, label, defval, 30, 4);
   }
   public TextArea(String name, String label, String defval, int cols, int rows)
   {
      this.name = name;
      this.label = label;
      if (null == defval)
         this.defval = "";
      else
         this.defval = defval;
      this.cols = cols;
      this.rows = rows;
   }
   protected String print()
   {
      return "<textarea name='"+name+"' cols='"+cols+"' rows='"+rows+"'>"+defval+"</textarea>";
   }
}


