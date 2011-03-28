/********************************************************************
 lg-window-thumbnail_config.cpp

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

#include "lg-window-thumbnail_config.h"

#include <kwineffects.h>

#include <klocale.h>
#include <kdebug.h>
#include <kconfiggroup.h>
#include <KActionCollection>
#include <kaction.h>
#include <KShortcutsEditor>

#include <QWidget>
#include <QVBoxLayout>
#include <QFileSystemModel>

#include "lg-window-thumbnail.h"

using namespace KWin;

//KWIN_EFFECT_CONFIG_FACTORY
KWIN_EFFECT_CONFIG ( gnome15thumbw, LGWindowThumbnailEffectConfig )

LGWindowThumbnailEffectConfigForm::LGWindowThumbnailEffectConfigForm ( QWidget* parent ) : QWidget ( parent )
{
    setupUi ( this );
}

LGWindowThumbnailEffectConfig::LGWindowThumbnailEffectConfig ( QWidget* parent, const QVariantList& args ) :
    KCModule ( EffectFactory::componentData(), parent, args )
{
    m_ui = new LGWindowThumbnailEffectConfigForm ( this );

    QVBoxLayout* layout = new QVBoxLayout ( this );

    layout->addWidget ( m_ui );

//     QFileSystemModel * fbDeviceModel = new QFileSystemModel ( this );
//     fbDeviceModel->setRootPath ( "/dev" );
//
//     QStringList nameFilters;
//     nameFilters << "/dev/fb*";
//     fbDeviceModel->setNameFilters ( nameFilters );
    /*
        m_ui->framebufferDevice->setModel ( fbDeviceModel );*/

    connect ( m_ui->outputFramebuffer, SIGNAL ( toggled ( bool ) ), this, SLOT ( frameBufferToggled ( bool ) ) );
    connect ( m_ui->outputSharedmem, SIGNAL ( toggled ( bool ) ), this, SLOT ( sharedMemToggled ( bool ) ) );
    connect ( m_ui->framebufferDevice, SIGNAL ( textChanged ( QString ) ) , this, SLOT ( changed() ) );

//     // Shortcut config. The shortcut belongs to the component "kwin"!
//     m_actionCollection = new KActionCollection( this, KComponentData("kwin") );
//
//     m_actionCollection->setConfigGroup("Gnome15ThumbW");
//     m_actionCollection->setConfigGlobal(true);
//
//     KAction* a = (KAction*)m_actionCollection->addAction( "ToggleCurrentThumbnail" );
//     a->setText( i18n("Toggle Thumbnail for Current Window" ));
//     a->setProperty("isConfigurationAction", true);
//     a->setGlobalShortcut(KShortcut(Qt::META + Qt::CTRL + Qt::Key_T));
//
//     m_ui->editor->addCollection(m_actionCollection);

}

LGWindowThumbnailEffectConfig::~LGWindowThumbnailEffectConfig()
{
    /*    // Undo (only) unsaved changes to global key shortcuts
        m_ui->editor->undoChanges();*/
}

void LGWindowThumbnailEffectConfig::frameBufferToggled ( bool checked )
{
    m_ui->outputSharedmem->setChecked ( !checked );
    m_ui->framebufferDevice->setEnabled ( checked );
    emit changed();
}

void LGWindowThumbnailEffectConfig::sharedMemToggled ( bool checked )
{
    m_ui->outputFramebuffer->setChecked ( !checked );
    m_ui->framebufferDevice->setEnabled ( !checked );
    emit changed();
}

void LGWindowThumbnailEffectConfig::load()
{
    KCModule::load();

    KConfigGroup conf = EffectsHandler::effectConfig ( "Gnome15ThumbW" );

    int output = conf.readEntry ( "OutputHandler", int ( LGWindowThumbnailEffect::enSharedMemory ) );
    QString fbdev = conf.readEntry ( "FramebufferDevice", "/dev/fb0" );

    m_ui->outputFramebuffer->setChecked ( output == LGWindowThumbnailEffect::enFramebufferDevice );
    m_ui->outputSharedmem->setChecked ( output == LGWindowThumbnailEffect::enSharedMemory );
    m_ui->framebufferDevice->setText ( fbdev );

    emit changed ( false );
}

void LGWindowThumbnailEffectConfig::save()
{
    //KCModule::save();

    KConfigGroup conf = EffectsHandler::effectConfig ( "Gnome15ThumbW" );

    conf.writeEntry ( "OutputHandler", int ( m_ui->outputFramebuffer->isChecked() ?
                      LGWindowThumbnailEffect::enFramebufferDevice : LGWindowThumbnailEffect::enSharedMemory ) );
    conf.writeEntry ( "FramebufferDevice", m_ui->framebufferDevice->text() );

//     m_actionCollection->writeSettings();
//     m_ui->editor->save();   // undo() will restore to this state from now on

    conf.sync();

    emit changed ( false );
    EffectsHandler::sendReloadMessage ( "gnome15thumbw" );
}

void LGWindowThumbnailEffectConfig::defaults()
{
    m_ui->outputFramebuffer->setChecked ( false );
    m_ui->outputSharedmem->setChecked ( true );
    m_ui->framebufferDevice->setText ( "/dev/fb0" );

    emit changed ( true );
}

