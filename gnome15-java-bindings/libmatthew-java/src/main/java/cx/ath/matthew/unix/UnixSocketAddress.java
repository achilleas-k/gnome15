/*
 * Java Unix Sockets Library
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
package cx.ath.matthew.unix;

/**
 * Represents an address for a Unix Socket
 */
public class UnixSocketAddress
{
   String path;
   boolean abs;
  /**
    * Create the address.
    * @param path The path to the Unix Socket.
    * @param abs True if this should be an abstract socket.
    */
   public UnixSocketAddress(String path, boolean abs)
   {
      this.path = path;
      this.abs = abs;
   }
   /**
    * Create the address.
    * @param path The path to the Unix Socket.
    */
   public UnixSocketAddress(String path)
   {
      this.path = path;
      this.abs = false;
   }
   /**
    * Return the path.
    */
   public String getPath()
   {
      return path;
   }
   /**
    * Returns true if this an address for an abstract socket.
    */
   public boolean isAbstract()
   {
      return abs;
   }
   /**
    * Return the Address as a String.
    */
   public String toString()
   {
      return "unix"+(abs?":abstract":"")+":path="+path;
   }
   public boolean equals(Object o)
   {
      if (!(o instanceof UnixSocketAddress)) return false;
      return ((UnixSocketAddress) o).path.equals(this.path);
   }
   public int hashCode()
   {
      return path.hashCode();
   }
}
