/*
 * Java DOM Printing Library
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

import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintStream;

import org.w3c.dom.Document;
import org.w3c.dom.DocumentType;
import org.w3c.dom.Element;
import org.w3c.dom.NamedNodeMap;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

/**
 * Print a DOM tree to the given OutputStream
 */
public class DOMPrinter
{
   /**
    * Print the given node and all its children.
    * @param n The Node to print.
    * @param os The Stream to print to.
    */
   public static void printNode(Node n, OutputStream os)
   {
      PrintStream p = new PrintStream(os);
      printNode(n, p);
   }
   /**
    * Print the given node and all its children.
    * @param n The Node to print.
    * @param p The Stream to print to.
    */
   public static void printNode(Node n, PrintStream p)
   {
      if (null != n.getNodeValue()) p.print(n.getNodeValue());
      else {
         p.print("<"+n.getNodeName());      
         if (n.hasAttributes()) {
            NamedNodeMap nnm = n.getAttributes();
            for (int i = 0; i < nnm.getLength(); i++) {
               Node attr = nnm.item(i);
               p.print(" "+attr.getNodeName()+"='"+attr.getNodeValue()+"'");
            }
         }
         if (n.hasChildNodes()) {
            p.print(">");
            NodeList nl = n.getChildNodes();
            for (int i = 0; i < nl.getLength(); i++)
               printNode(nl.item(i), p);
            p.print("</"+n.getNodeName()+">");
         } else {
            p.print("/>");
         }
      }
   }
   /**
    * Print the given document and all its children.
    * @param d The Document to print.
    * @param p The Stream to print to.
    */
   public static void printDOM(Document d, PrintStream p)
   {
      DocumentType dt = d.getDoctype();
      if (null != dt) {
         p.print("<!DOCTYPE "+dt.getName());
         String pub = dt.getPublicId();
         String sys = dt.getSystemId();
         if (null != pub) p.print(" PUBLIC \""+pub+"\" \""+sys+"\"");
         else if (null != sys) p.print(" SYSTEM \""+sys+"\"");
         p.println(">");
      }
      Element e = d.getDocumentElement();
      printNode(e, p);
   }
   /**
    * Print the given document and all its children.
    * @param d The Document to print.
    * @param os The Stream to print to.
    */
   public static void printDOM(Document d, OutputStream os)
   {
      PrintStream p = new PrintStream(os);
      printDOM(d, p);
   }
}

