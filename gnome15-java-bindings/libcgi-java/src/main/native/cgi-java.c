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

#include <jni.h>
#include "cgi-java.h"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

extern char **environ;

extern jobjectArray Java_cx_ath_matthew_cgi_CGI_getfullenv (JNIEnv *env, jobject obj, jclass type)
{
   int i;
   for (i = 0; environ[i]; i++);
   jobjectArray joa =  (*env)->NewObjectArray(env, i+1, type, NULL);
   for (i = 0; environ[i]; i++)
      (*env)->SetObjectArrayElement(env, joa, i, (*env)->NewStringUTF(env, environ[i]));
   return joa;   
}

extern jstring Java_cx_ath_matthew_cgi_CGI_getenv (JNIEnv *env, jobject obj, jstring ename)
{
   const char *estr = (*env)->GetStringUTFChars(env, ename, 0);
   char *eval = getenv(estr);
   (*env)->ReleaseStringUTFChars(env, ename, estr);
   if (NULL == eval)
      return NULL;
   else
      return (*env)->NewStringUTF(env, eval);
}

extern void Java_cx_ath_matthew_cgi_CGI_setenv (JNIEnv *env, jobject obj, jstring var, jstring val)
{
#ifdef setenv
   const char *cvar = (*env)->GetStringUTFChars(env, var, 0);
   const char *cval = (*env)->GetStringUTFChars(env, val, 0);
   setenv(cvar, cval, 1);
#endif
}
