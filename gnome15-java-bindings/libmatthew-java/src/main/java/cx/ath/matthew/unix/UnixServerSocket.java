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

import java.io.IOException;

/**
 * Represents a listening UNIX Socket.
 */
public class UnixServerSocket
{
   static { System.loadLibrary("unix-java"); }
   private native int native_bind(String address, boolean abs) throws IOException;
   private native void native_close(int sock) throws IOException;
   private native int native_accept(int sock) throws IOException;
   private UnixSocketAddress address = null;
   private boolean bound = false;
   private boolean closed = false;
   private int sock;
   /**
    * Create an un-bound server socket.
    */
   public UnixServerSocket()
   {
   }
   /**
    * Create a server socket bound to the given address.
    * @param address Path to the socket.
    */
   public UnixServerSocket(UnixSocketAddress address) throws IOException
   {
      bind(address);
   }
   /**
    * Create a server socket bound to the given address.
    * @param address Path to the socket.
    */
   public UnixServerSocket(String address) throws IOException
   {
      this(new UnixSocketAddress(address));
   }
   /**
    * Accepts a connection on the ServerSocket.
    * @return A UnixSocket connected to the accepted connection.
    */
   public UnixSocket accept() throws IOException
   {
      int client_sock = native_accept(sock);
      return new UnixSocket(client_sock, address);
   }
   /**
    * Closes the ServerSocket.
    */
   public synchronized void close() throws IOException
   {
      native_close(sock);
      sock = 0;
      closed = true;
      bound = false;
   }
   /**
    * Binds a server socket to the given address.
    * @param address Path to the socket.
    */
   public void bind(UnixSocketAddress address) throws IOException
   {
      if (bound) close();
      sock = native_bind(address.path, address.abs);
      bound = true;
      closed = false;
      this.address = address;
   }
   /**
    * Binds a server socket to the given address.
    * @param address Path to the socket.
    */
   public void bind(String address) throws IOException
   {
      bind(new UnixSocketAddress(address));
   }   
   /**
    * Return the address this socket is bound to.
    * @return The UnixSocketAddress if bound or null if unbound.
    */
   public UnixSocketAddress getAddress()
   {
      return address;
   }
   /**
    * Check the status of the socket.
    * @return True if closed.
    */
   public boolean isClosed()
   {
      return closed;
   }
   /**
    * Check the status of the socket.
    * @return True if bound.
    */
   public boolean isBound()
   {
      return bound;
   }
}
