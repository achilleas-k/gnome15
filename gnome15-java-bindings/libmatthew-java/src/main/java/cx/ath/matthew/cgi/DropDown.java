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

import java.util.List;

public class DropDown extends Field
{
   Object[] values;
   Object defval;
   boolean indexed = false;
   /**
    * Create a new DropDown list.
    *
    * @param name The HTML field name.
    * @param label The label to display
    * @param values The values for the drop down list
    * @param defval If this parameter is set then this element will be selected by default.
    * @param indexed If this is set to true, then indexes will be returned, rather than values.
    */
   public DropDown(String name, String label, Object[] values, Object defval, boolean indexed)
   {
      this.name = name;
      this.label = label;
      this.values = values;
      this.indexed = indexed;
      this.defval = defval;
   }
   /**
    * Create a new DropDown list.
    *
    * @param name The HTML field name.
    * @param label The label to display
    * @param values The values for the drop down list
    * @param defval If this parameter is set then this element will be selected by default.
    * @param indexed If this is set to true, then indexes will be returned, rather than values.
    */
   public DropDown(String name, String label, Object[] values, int defval, boolean indexed)
   {
      this.name = name;
      this.label = label;
      this.values = values;
      if (defval < 0)
         this.defval = null;
      else
         this.defval = values[defval];
      this.indexed = indexed;
   }
   /**
    * Create a new DropDown list.
    *
    * @param name The HTML field name.
    * @param label The label to display
    * @param values The values for the drop down list
    * @param defval If this parameter is set then this element will be selected by default.
    * @param indexed If this is set to true, then indexes will be returned, rather than values.
    */
   public DropDown(String name, String label, List values, Object defval, boolean indexed)
   {
      this.name = name;
      this.label = label;
      this.values = (Object[]) values.toArray(new Object[] {});
      this.defval = defval;
      this.indexed = indexed;
   }
   /**
    * Create a new DropDown list.
    *
    * @param name The HTML field name.
    * @param label The label to display
    * @param values The values for the drop down list
    * @param defval If this parameter is set then this element will be selected by default.
    * @param indexed If this is set to true, then indexes will be returned, rather than values.
    */
   public DropDown(String name, String label, List values, int defval, boolean indexed)
   {
      this.name = name;
      this.label = label;
      this.values = (Object[]) values.toArray(new Object[] {});
      if (defval < 0)
         this.defval = null;
      else
         this.defval = values.get(defval);
      this.indexed = indexed;
   }
   protected String print()
   {
      String s = "";
      s += "<select name='"+name+"'>\n";
      for (int i=0; i<values.length; i++) {
         if (indexed)
            s += "   <option value='"+i+"'";
         else
            s += "   <option";
         if (values[i].equals(defval))
            s += " selected='selected'>"+values[i]+"</option>\n";
         else
            s += ">"+values[i]+"</option>\n";
      }
      s += "</select>\n";
      return s;
   }
}


