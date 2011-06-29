/*
 * Java CGI Library
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

/*
 *
 * TODO To change the template for this generated file go to
 * Window - Preferences - Java - Code Style - Code Templates
 */
package cx.ath.matthew.cgi;

import java.util.List;

/**
 * @author Agent
 *
 * TODO To change the template for this generated type comment go to
 * Window - Preferences - Java - Code Style - Code Templates
 */
public class MultipleDropDown extends DropDown {

	/**
	 * @param name
	 * @param label
	 * @param values
	 * @param defval
	 * @param indexed
	 */
	public MultipleDropDown(String name, String label, String[] values,
			String defval, boolean indexed) {
		super(name, label, values, defval, indexed);
		// TODO Auto-generated constructor stub
	}

	/**
	 * @param name
	 * @param label
	 * @param values
	 * @param defval
	 * @param indexed
	 */
	public MultipleDropDown(String name, String label, String[] values,
			int defval, boolean indexed) {
		super(name, label, values, defval, indexed);
		// TODO Auto-generated constructor stub
	}

	/**
	 * @param name
	 * @param label
	 * @param values
	 * @param defval
	 * @param indexed
	 */
	public MultipleDropDown(String name, String label, List values,
			String defval, boolean indexed) {
		super(name, label, values, defval, indexed);
		// TODO Auto-generated constructor stub
	}

	/**
	 * @param name
	 * @param label
	 * @param values
	 * @param defval
	 * @param indexed
	 */
	public MultipleDropDown(String name, String label, List values, int defval,
			boolean indexed) {
		super(name, label, values, defval, indexed);
		// TODO Auto-generated constructor stub
	}
	
	protected String print()
	   {
	      String s = "";
	      s += "<select name='"+name+"' multiple='multiple' size='"+values.length+"'>\n";
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
