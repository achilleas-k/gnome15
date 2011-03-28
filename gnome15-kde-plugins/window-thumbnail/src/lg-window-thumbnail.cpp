/********************************************************************
 lg-window-thumbnail.cpp

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

#include "lg-window-thumbnail.h"
#include <kwinglutils.h>
#include <KDE/KDebug>
#include <QtDBus/QDBusConnection>
#include <QtCore/QVarLengthArray>
#include <QtGui/QPainter>

#include <X11/extensions/Xfixes.h>
#include <QX11Info>

#include "fbdevoutput.h"
#include "sharedmemoryoutput.h"

using namespace KWin;

KWIN_EFFECT ( gnome15thumbw, LGWindowThumbnailEffect )
KWIN_EFFECT_SUPPORTED ( gnome15thumbw, LGWindowThumbnailEffect::supported() )

bool LGWindowThumbnailEffect::supported()
{
    return effects->compositingType() == KWin::OpenGLCompositing && GLRenderTarget::supported();
}

LGWindowThumbnailEffect::LGWindowThumbnailEffect()
    : m_capturedWindow ( NULL ),
      m_bNeedCaptureStarted ( false ),
      m_targetWidth ( 320 ), // TODO: get these from framebuffer
      m_targetHeight ( 240 ),
      m_outputHandler ( NULL ),
      m_offscreenTexture ( NULL ),
      m_tex ( NULL ),
      m_target ( NULL )

{
    QDBusConnection::sessionBus().registerObject ( "/LGWindowThumbnailEffect", this, QDBusConnection::ExportScriptableContents );
    QDBusConnection::sessionBus().registerService ( "org.gnome15.kde.LGWindowThumbnailEffect" );

    reconfigure ( ReconfigureAll );
}

LGWindowThumbnailEffect::~LGWindowThumbnailEffect()
{
    stopCapture();

    if ( m_outputHandler != NULL )
        delete m_outputHandler;

    QDBusConnection::sessionBus().unregisterObject ( "/LGWindowThumbnailEffect" );
    QDBusConnection::sessionBus().unregisterService ( "org.gnome15.kde.LGWindowThumbnailEffect" );
}

void LGWindowThumbnailEffect::reconfigure ( ReconfigureFlags /*flags*/ )
{
    KConfigGroup conf = EffectsHandler::effectConfig ( "Gnome15ThumbW" );

    int output = conf.readEntry ( "OutputHandler", int ( enSharedMemory ) );
    QString fbdev = conf.readEntry ( "FramebufferDevice", "/dev/fb0" );

    if ( m_outputHandler != NULL ) {
        delete m_outputHandler;
        m_outputHandler = NULL;
    }

    if ( output == enFramebufferDevice ) {
        m_outputHandler = new FbdevOutput ( fbdev );
    } else { /* if (output == enSharedMemory) */
        m_outputHandler = new SharedMemoryOutput();
    }

    effects->addRepaintFull();
}


void LGWindowThumbnailEffect::prePaintWindow ( EffectWindow* w, WindowPrePaintData& data, int time )
{
    if ( m_outputHandler != NULL && m_capturedWindow != NULL && m_capturedWindow == w ) {
        // we want to route the window to Logitech's LCD even if on another desktop
        // below we pretend to be window managers and only paint the window if on the proper desktops
        w->enablePainting ( EffectWindow::PAINT_DISABLED_BY_DESKTOP );
    }
    effects->prePaintWindow ( w, data, time );
}

void LGWindowThumbnailEffect::paintWindow ( EffectWindow* currentWindow, int mask, QRegion region, WindowPaintData& paintData )
{
    if ( m_outputHandler != NULL && m_capturedWindow != NULL && m_capturedWindow == currentWindow && m_target->valid() ) {
        /* If this is our captured window, draw it only if it's on the current desktop or all desktops,
         * as we have disabled the normal desktop handling. */
        if ( currentWindow->isOnCurrentDesktop() || currentWindow->isOnAllDesktops() )
            effects->paintWindow ( currentWindow, mask, region, paintData );

        WindowPaintData localPaintData ( m_capturedWindow );

        // remove quads that are part of the decoration
        if ( !m_includeDecoration ) {
            WindowQuadList newQuads;
            double left = m_capturedWindow->width();
            double top = m_capturedWindow->height();
            double right = 0;
            double bottom = 0;
            foreach ( const WindowQuad& quad, localPaintData.quads ) {
                if ( quad.type() == WindowQuadContents ) {
                    newQuads << quad;
                    left   = qMin ( left, quad.left() );
                    top    = qMin ( top, quad.top() );
                    right  = qMax ( right, quad.right() );
                    bottom = qMax ( bottom, quad.bottom() );
                }
            }
            localPaintData.quads = newQuads;
        }

        QRect resultRegion;
        QRect dest ( 0,0,m_targetWidth, m_targetHeight );

        /*
         * setPositionTransformations uses the window size + decorations,
         * which creates errors in placement etc when m_includeDecorations == false
         * ignored this issue because the errors are negligible after resize if the source window is big enough
         */
        setPositionTransformations ( localPaintData, resultRegion, m_capturedWindow, dest, Qt::KeepAspectRatio );

        // render window into offscreen texture
        int localMask = PAINT_WINDOW_TRANSFORMED | PAINT_WINDOW_OPAQUE | PAINT_WINDOW_LANCZOS;
        effects->pushRenderTarget ( m_target );
        glClear ( GL_COLOR_BUFFER_BIT );
        effects->drawWindow ( m_capturedWindow, localMask, resultRegion, localPaintData );

        // Create a scratch texture and copy the rendered window into it
        m_tex->bind();
        glCopyTexSubImage2D ( GL_TEXTURE_2D, 0, 0, 0, 0, m_offscreenTexture->height() - m_targetHeight, m_targetWidth, m_targetHeight );
        effects->popRenderTarget();

        // copy content from GL texture into image
        m_tex->bind();

        /*
         * We can use glGetTexImage and hand it the framebuffer's color format,
         * however this (a) may not be supported on all OpenGL implementations and
         * (b) on my computer did not bring any noticeable CPU usage improvement.
         * (c) the image needs to be alseo flipped upside-down on the LCD.
         * As a result I chose to do the transform from the guaranteed RGB888 format
         * to RGB565 in software later on.
         * Perhaps a more knoledgeable dev can enhance this.
         */
//        QImage img( QSize( m_targetWidth, m_targetHeight ), QImage::Format_RGB565);
//        glGetTexImage( GL_TEXTURE_2D, 0, GL_RGB, GL_UNSIGNED_SHORT_5_6_5, img.bits() );

        QImage img ( QSize ( m_targetWidth, m_targetHeight ), QImage::Format_RGB888 );
        glGetTexImage ( GL_TEXTURE_2D, 0, GL_RGB, GL_UNSIGNED_BYTE, img.bits() );
        m_tex->unbind();

        // convert image to RGB565 directly in the target buffer
        int height = img.height();
        u_int16_t *destBuffer = m_outputHandler->getWriteableBuffer();
        if ( destBuffer != NULL ) {
            for ( int y = height - 1; y >= height - m_targetHeight; --y ) {
                u_int8_t *q = ( u_int8_t* ) img.scanLine ( y );
                for ( int x=0; x < m_targetWidth; ++x ) {
                    u_int8_t r = *q++;
                    u_int8_t g = *q++;
                    u_int8_t b = *q++;
                    *destBuffer++ = ( u_int16_t ( r >> 3 ) << 11 ) |
                                    ( u_int16_t ( g >> 2 ) << 5 ) |
                                    ( u_int16_t ( b >> 3 ) );
                }
            }
            m_outputHandler->frameReady();

            if ( m_bNeedCaptureStarted ) {
                m_bNeedCaptureStarted = false;
                emit captureStarted();
            }
        }
    } else {
        effects->paintWindow ( currentWindow, mask, region, paintData );
    }
}

void LGWindowThumbnailEffect::windowClosed ( EffectWindow* c )
{
    if ( m_capturedWindow != NULL && c == m_capturedWindow ) {
        stopCapture();
    }
}

void LGWindowThumbnailEffect::windowDeleted ( EffectWindow* c )
{
    if ( m_capturedWindow != NULL && c == m_capturedWindow ) {
        stopCapture();
    }
}

void LGWindowThumbnailEffect::startCaptureWindowUnderCursor ( bool includeDecoration )
{
    if ( m_capturedWindow == NULL ) {
        m_includeDecoration = includeDecoration;
        const QPoint cursor = effects->cursorPos();
        foreach ( EffectWindow* w, effects->stackingOrder() ) {
            if ( w->geometry().contains ( cursor ) && w->isOnCurrentDesktop() && !w->isMinimized() ) {
                m_capturedWindow = w;
            }
        }
        if ( m_capturedWindow != NULL ) {
            m_outputHandler->initialize ( m_targetWidth * m_targetHeight * 2 /* bytes per pixel */ );
            m_bNeedCaptureStarted = true;
            createGLObjects();
        }
    }
}

void LGWindowThumbnailEffect::stopCapture( )
{
    if ( m_capturedWindow != NULL ) {
        m_capturedWindow = NULL;
        emit captureStopped();

        if ( m_outputHandler != NULL )
            m_outputHandler->uninitialize();

        destroyGLObjects();
    }
}

void LGWindowThumbnailEffect::createGLObjects()
{
    destroyGLObjects();

    /*
      * Initially I tried using an offscreen texture sized after the target framebuffer.
      * Next I tried using an offscreen textured sized after the window size.
      * Both attempts fail silently and lock kwin - I have no idea why.
      * This size works, but it wastes too much memory.
      * Perhaps a more opengl-savvy person can optimize this.
      */
    int w = displayWidth();
    int h = displayHeight();
    if ( !GLTexture::NPOTTextureSupported() ) {
        w = nearestPowerOfTwo ( w );
        h = nearestPowerOfTwo ( h );
    }
    m_offscreenTexture = new GLTexture ( w, h );
    m_offscreenTexture->setFilter ( GL_LINEAR );
    m_offscreenTexture->setWrapMode ( GL_CLAMP_TO_EDGE );
    m_target = new GLRenderTarget ( m_offscreenTexture );

    m_tex = new GLTexture ( m_targetWidth, m_targetHeight );
    m_tex->setFilter ( GL_LINEAR );
    m_tex->setWrapMode ( GL_CLAMP_TO_EDGE );
}

void LGWindowThumbnailEffect::destroyGLObjects()
{
    if ( m_offscreenTexture )
        delete m_offscreenTexture;
    if ( m_tex )
        delete m_tex;
    if ( m_target )
        delete m_target;
    
    m_offscreenTexture = NULL;
    m_tex = NULL;
    m_target = NULL;
}
