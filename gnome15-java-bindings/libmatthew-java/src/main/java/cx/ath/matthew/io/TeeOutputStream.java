/*
 * Java Tee Stream Library
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

package cx.ath.matthew.io;

import java.io.File;
import java.io.FileOutputStream;
import java.io.FilterOutputStream;
import java.io.OutputStream;
import java.io.IOException;

/**
 * Class to copy a stream to another stream or file as it is being sent through a stream pipe
 * E.g.
 * <pre>
 *    PrintWriter r = new PrintWriter(new TeeOutputStream(new FileOutputStream("file"), new File("otherfile")));
 * </pre>
 */
public class TeeOutputStream extends FilterOutputStream
{
   private File f;
   private OutputStream out;
   private OutputStream fos;
   /**
    * Create a new TeeOutputStream on the given OutputStream
    * and copy the stream to the other OuputStream.
    * @param os Writes to this OutputStream
    * @param tos Write to this OutputStream
    */
   public TeeOutputStream(OutputStream os, OutputStream tos) throws IOException
   {
      super(os);
      this.out = os;
      this.fos = tos;
   }
   /**
    * Create a new TeeOutputStream on the given OutputStream
    * and copy the stream to the given File.
    * @param os Writes to this OutputStream
    * @param f Write to this File
    * @param append Append to file not overwrite
    */
   public TeeOutputStream(OutputStream os, File f, boolean append) throws IOException
   {
      super(os);
      this.out = os;
      this.fos = new FileOutputStream(f, append);
   }
   /**
    * Create a new TeeOutputStream on the given OutputStream
    * and copy the stream to the given File.
    * @param os Writes to this OutputStream
    * @param f Write to this File
    */
   public TeeOutputStream(OutputStream os, File f) throws IOException
   {
      super(os);
      this.out = os;
      this.fos = new FileOutputStream(f);
   }
   /**
    * Create a new TeeOutputStream on the given OutputStream
    * and copy the stream to the given File.
    * @param os Writes to this OutputStream
    * @param f Write to this File
    * @param append Append to file not overwrite
    */
   public TeeOutputStream(OutputStream os, String f, boolean append) throws IOException
   {
      this(os, new File(f), append);
   }
   /**
    * Create a new TeeOutputStream on the given OutputStream
    * and copy the stream to the given File.
    * @param os Writes to this OutputStream
    * @param f Write to this File
    */
   public TeeOutputStream(OutputStream os, String f) throws IOException
   {
      this(os, new File(f));
   }
   public void close() throws IOException
   {
      out.close();
      fos.close();
   }
   public void flush() throws IOException
   {
      fos.flush();
      out.flush();
   }
   public void write(int b) throws IOException
   {
      fos.write(b);
      out.write(b);
   }
   public void write(byte[] b) throws IOException
   {
      fos.write(b);
      out.write(b);
   }
   public void write(byte[] b, int off, int len) throws IOException
   {  
      fos.write(b, off, len);
      out.write(b, off, len);
   }

   public void finalize()
   {
      try {
         close();
      } catch (Exception e) {}
   }
}



