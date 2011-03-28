/********************************************************************
lg-window-thumbnail_config.h

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

#ifndef LG_WINDOW_THUMBNAIL_CONFIG_H
#define LG_WINDOW_THUMBNAIL_CONFIG_H

#include <kcmodule.h>

#include "ui_lg-window-thumbnail_config.h"

class KActionCollection;

class LGWindowThumbnailEffectConfigForm : public QWidget, public Ui_LGWindowThumbnailConfigForm
{
    Q_OBJECT
public:
    explicit LGWindowThumbnailEffectConfigForm(QWidget* parent);
};

class LGWindowThumbnailEffectConfig : public KCModule
{
    Q_OBJECT
public:
    explicit LGWindowThumbnailEffectConfig(QWidget* parent = 0, const QVariantList& args = QVariantList());
    virtual ~LGWindowThumbnailEffectConfig();

    virtual void save();
    virtual void load();
    virtual void defaults();

private Q_SLOTS:
    void frameBufferToggled(bool checked);
    void sharedMemToggled(bool checked);

private:
    LGWindowThumbnailEffectConfigForm* m_ui;
//     KActionCollection* m_actionCollection;
};

#endif // LG_WINDOW_THUMBNAIL_CONFIG_H

