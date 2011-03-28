/*
    sharedmemoryoutput.h

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


#ifndef SHAREDMEMORYOUTPUT_H
#define SHAREDMEMORYOUTPUT_H

#include "outputhandler.h"
#include <QSharedMemory>

class SharedMemoryOutput : public OutputHandler
{
    mutable QSharedMemory m_sharedMemory;

public:
    SharedMemoryOutput();

    virtual void initialize(size_t size);
    virtual void uninitialize();
    virtual u_int16_t * getWriteableBuffer() const;
    virtual void frameReady();
};

#endif // SHAREDMEMORYOUTPUT_H
