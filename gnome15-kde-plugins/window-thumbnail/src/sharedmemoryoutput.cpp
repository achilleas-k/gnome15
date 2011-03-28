/*
    sharedmemoryoutput.cpp

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


#include "sharedmemoryoutput.h"


SharedMemoryOutput::SharedMemoryOutput()
    : m_sharedMemory("gnome15thumbw_shmem")
{
}

void SharedMemoryOutput::initialize(size_t size)
{
    m_sharedMemory.create(size);
}

void SharedMemoryOutput::uninitialize()
{
    m_sharedMemory.detach();
}

u_int16_t * SharedMemoryOutput::getWriteableBuffer() const
{
    if (m_sharedMemory.lock())
        return reinterpret_cast<u_int16_t*>(m_sharedMemory.data());

    return NULL;
}

void SharedMemoryOutput::frameReady()
{
    m_sharedMemory.unlock();
}
