/* 
 * CUAG AutoUmpire System
 * 
 * Copyright (C) 2003/2004 Matthew Johnson, Adam Biltcliffe,
 * Michael Cripps, Martin O'Leary, Edward Allcutt and James Osborn
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
 * To Contact the authors, please email assassins@srcf.ucam.org
 *
 */


package cx.ath.matthew.cgi;

abstract class CGITools
{
   /**
    * Escape a character in a string.
    * @param in String to escape in.
    * @param c Character to escape.
    * @return in with c replaced with \c
    */
   public static String escapeChar(String in, char c)
   {
      String out = "";
      for (int i = 0; i < in.length(); i++) {
         if (in.charAt(i) == c) out += '\\';
         out += in.charAt(i);
      }
      return out;
   }
}

