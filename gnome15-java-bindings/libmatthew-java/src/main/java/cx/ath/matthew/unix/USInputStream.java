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

import java.io.InputStream;
import java.io.IOException;

public class USInputStream extends InputStream
{ 
   public static final int MSG_DONTWAIT = 0x40;
   private native int native_recv(int sock, byte[] b, int off, int len, int flags, int timeout) throws IOException;
   private int sock;
   boolean closed = false;
   private byte[] onebuf = new byte[1];
   private UnixSocket us;
   private boolean blocking = true;
   private int flags = 0;
   private int timeout = 0;
   public USInputStream(int sock, UnixSocket us)
   {
      this.sock = sock;
      this.us = us;
   }
   public void close() throws IOException
   {
      closed = true;
      us.close();
   }
   public boolean markSupported() { return false; }
   public int read() throws IOException
   {
      int rv = 0;
      while (0 >= rv) rv = read(onebuf);
      if (-1 == rv) return -1;
      return 0 > onebuf[0] ? -onebuf[0] : onebuf[0];
   }
   public int read(byte[] b, int off, int len) throws IOException
   {
      if (closed) throw new NotConnectedException();
      int count = native_recv(sock, b, off, len, flags, timeout);
      /* Yes, I really want to do this. Recv returns 0 for 'connection shut down'.
       * read() returns -1 for 'end of stream.
       * Recv returns -1 for 'EAGAIN' (all other errors cause an exception to be raised)
       * whereas read() returns 0 for '0 bytes read', so yes, I really want to swap them here.
       */
      if (0 == count) return -1;
      else if (-1 == count) return 0;
      else return count;
   }
   public boolean isClosed() { return closed; }
   public UnixSocket getSocket() { return us; }
   public void setBlocking(boolean enable)
   {
      flags = enable ? 0 : MSG_DONTWAIT;
   }
   public void setSoTimeout(int timeout)
   {
      this.timeout = timeout;
   }
}
