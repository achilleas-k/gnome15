/*
 * Java Exec Pipe Library
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

import java.io.FilterOutputStream;
import java.io.InputStream;
import java.io.IOException;
import java.io.OutputStream;

/**
 * Class to pipe an OutputStream through a command using stdin/stdout.
 * E.g.
 * <pre>
 *    Writer w = new OutputStreamWriter(new ExecOutputStream(new FileOutputStream("file"), "command"));
 * </pre>
 */
public class ExecOutputStream extends FilterOutputStream
{
   private Process proc;
   private InputStream stdout;
   private OutputStream stdin;
   private InOutCopier copy;

   /**
    * Create a new ExecOutputStream on the given OutputStream
    * using the process to filter the stream.
    * @param os Writes to this OutputStream
    * @param p Filters data through stdin/out on this Process
    */
   public ExecOutputStream(OutputStream os, Process p) throws IOException
   {
      super(os);
      proc = p;
      stdin = p.getOutputStream();
      stdout = p.getInputStream();
      copy = new InOutCopier(stdout, out);
      copy.start();
   }
   /**
    * Create a new ExecOutputStream on the given OutputStream
    * using the process to filter the stream.
    * @param os Writes to this OutputStream
    * @param cmd Creates a Process from this string to filter data through stdin/out 
    */
   public ExecOutputStream(OutputStream os, String cmd) throws IOException
   { this(os, Runtime.getRuntime().exec(cmd)); }
   /**
    * Create a new ExecOutputStream on the given OutputStream
    * using the process to filter the stream.
    * @param os Writes to this OutputStream
    * @param cmd Creates a Process from this string array (command, arg, ...) to filter data through stdin/out 
    */
   public ExecOutputStream(OutputStream os, String[] cmd) throws IOException
   { this(os, Runtime.getRuntime().exec(cmd)); }
   /**
    * Create a new ExecOutputStream on the given OutputStream
    * using the process to filter the stream.
    * @param os Writes to this OutputStream
    * @param cmd Creates a Process from this string to filter data through stdin/out 
    * @param env Setup the environment for the command
    */
   public ExecOutputStream(OutputStream os, String cmd, String[] env) throws IOException
   { this(os, Runtime.getRuntime().exec(cmd, env)); }
   /**
    * Create a new ExecOutputStream on the given OutputStream
    * using the process to filter the stream.
    * @param os Writes to this OutputStream
    * @param cmd Creates a Process from this string array (command, arg, ...) to filter data through stdin/out 
    * @param env Setup the environment for the command
    */
   public ExecOutputStream(OutputStream os, String[] cmd, String[] env) throws IOException
   { this(os, Runtime.getRuntime().exec(cmd, env)); }

   public void close() throws IOException
   {
      stdin.close();
      try {
         proc.waitFor();
      } catch (InterruptedException Ie)  {}
      //copy.close();
      try {
         copy.join();
      } catch (InterruptedException Ie)  {}
      stdout.close();
      out.close();
   }
   public void flush() throws IOException
   {
      stdin.flush();
      copy.flush();
      out.flush();
   }
   public void write(byte[] b) throws IOException
   {
      stdin.write(b);
   }
   public void write(byte[] b, int off, int len) throws IOException
   {
      stdin.write(b, off, len);
   }
   public void write(int b) throws IOException
   {
      stdin.write(b);
   }
   public void finalize()
   {
      try {
         close();
      } catch (Exception e) {}
   }
}

