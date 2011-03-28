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


#ifndef FBDEVOUTPUT_H
#define FBDEVOUTPUT_H

#include <QString>
#include "outputhandler.h"

class FbdevOutput : public OutputHandler
{
  QString m_strFilename;
  int m_fbdev;
  u_int16_t * m_mappedMemoryBuffer;
  size_t m_mappedMemoryBufferSize;
  
public:
  FbdevOutput(const QString & strFilename);
    virtual ~FbdevOutput();
    
    virtual void initialize(size_t size);
    virtual void uninitialize();
    virtual u_int16_t * getWriteableBuffer() const;
    virtual void frameReady();
};

#endif // FBDEVOUTPUT_H
