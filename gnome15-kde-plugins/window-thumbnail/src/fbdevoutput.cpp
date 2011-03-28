/*
    <one line to give the program's name and a brief idea of what it does.>
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


#include "fbdevoutput.h"
#include <stdlib.h>
#include <unistd.h>
#include <stdio.h>
#include <fcntl.h>
#include <sys/mman.h>


FbdevOutput::FbdevOutput(const QString & filename)
    : m_strFilename(filename),
      m_fbdev(0),
      m_mappedMemoryBuffer(NULL),
      m_mappedMemoryBufferSize(0)
{

}

FbdevOutput::~FbdevOutput()
{
    uninitialize();
}

void FbdevOutput::initialize(size_t size)
{
    if (m_fbdev == 0) {
        m_fbdev = ::open(m_strFilename.toLocal8Bit().constData(), O_RDWR);;
        m_mappedMemoryBuffer = reinterpret_cast<u_int16_t *>(::mmap(0, size, PROT_WRITE, MAP_SHARED, m_fbdev, 0));
        m_mappedMemoryBufferSize = size;
    }
}

void FbdevOutput::uninitialize()
{
    if (m_fbdev != 0) {
        ::munmap(m_mappedMemoryBuffer, m_mappedMemoryBufferSize);
        ::close(m_fbdev);

        m_fbdev = 0;
        m_mappedMemoryBuffer = NULL;
        m_mappedMemoryBufferSize = 0;
    }
}

u_int16_t * FbdevOutput::getWriteableBuffer() const
{
    return m_mappedMemoryBuffer;
}

void FbdevOutput::frameReady()
{
}
