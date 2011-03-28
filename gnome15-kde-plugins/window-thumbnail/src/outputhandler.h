/*
    outputhandler.h
    
    Copyright (C) 2011  Ciprian Ciubotariu <cheepeero@gmx.net>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/


#ifndef OUTPUTHANDLER_H
#define OUTPUTHANDLER_H

#include <sys/types.h>

/** Interface for effect output handlers. */
class OutputHandler
{
public:
    virtual ~OutputHandler();

    /** Initialize the internals of the handler. 
     * @param size Size of the buffer used later on in bytes.
     */
    virtual void initialize(size_t size) = 0;
    
    /** Unitialize the internals of the handler.
     * @note The object can be reused afterwards, by calling @c initialize . */
    virtual void uninitialize() = 0;

    /** Gets the buffer where the image gets placed. */
    virtual u_int16_t * getWriteableBuffer() const = 0;
    
    /** Notifies the handler the frame is ready in its buffer. */
    virtual void frameReady() = 0;
};

#endif // OUTPUTHANDLER_H
