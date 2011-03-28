/********************************************************************
 lg-window-thumbnail.h

  Copyright (C) 2011 Ciprian Ciubotariu <cheepeero@gmx.net>

  Based on the screenshot effect from KWin 4.6.1
  Copyright (C) 2010 Martin Gräßlin <kde@martin-graesslin.com>
  Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies)

  and taskbarthumbnail effect from KWin 4.6.1
  Copyright (C) 2007 Rivo Laks <rivolaks@hot.ee>
  Copyright (C) 2007 Lubos Lunak <l.lunak@kde.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*********************************************************************/

#ifndef LG_WINDOW_THUMBNAIL_H
#define LG_WINDOW_THUMBNAIL_H

#include <kwineffects.h>
#include <QObject>
#include <QImage>
#include "outputhandler.h"


class LGWindowThumbnailEffect : public QObject, public KWin::Effect
{
    Q_OBJECT
    Q_CLASSINFO ( "D-Bus Interface", "org.gnome15.kde.LGWindowThumbnailEffect" )

public:
    static bool supported();

    enum OutputType {
        enFramebufferDevice,
        enSharedMemory,
    };

    LGWindowThumbnailEffect();
    virtual ~LGWindowThumbnailEffect();

    virtual void reconfigure ( ReconfigureFlags flags );

    virtual void prePaintWindow ( KWin::EffectWindow* w, KWin::WindowPrePaintData& data, int time );
    virtual void paintWindow ( KWin::EffectWindow* w, int mask, QRegion region, KWin::WindowPaintData& paintData );

    virtual void windowClosed ( KWin::EffectWindow* c );
    virtual void windowDeleted ( KWin::EffectWindow* c );

public Q_SLOTS:
    Q_SCRIPTABLE void startCaptureWindowUnderCursor ( bool includeDecoration );
    Q_SCRIPTABLE void stopCapture( );

Q_SIGNALS:
    Q_SCRIPTABLE void captureStarted( );
    Q_SCRIPTABLE void captureStopped( );

private:
  /** The window to be captured, or @c NULL */
    KWin::EffectWindow * m_capturedWindow;
    
    /** Internal management of events. */
    bool m_bNeedCaptureStarted;
    
    /** target framebuffer size */
    int m_targetWidth, m_targetHeight;

    /** configuration */
    bool m_includeDecoration;
    OutputHandler * m_outputHandler;
    
    /** opengl objects */
    KWin::GLTexture* m_offscreenTexture;
    KWin::GLTexture * m_tex;
    KWin::GLRenderTarget* m_target;
    void createGLObjects();
    void destroyGLObjects();
};

#endif // LG_WINDOW_THUMBNAIL_H
