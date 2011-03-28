cmake_minimum_required(VERSION 2.8)

project(kwin4_effect_gnome15thumbw)

find_package(KDE4)
add_definitions( ${KDE4_DEFINITIONS} )

find_package(X11)
include(KDE4Defaults)
include(MacroLibrary)
include_directories(${KDE4_INCLUDES})

find_package(OpenGL)
include_directories(${OPENGL_INCLUDE_DIR})

#the main effect
set( kwin4_effect_gnome15thumbw_SOURCES fbdevoutput.cpp sharedmemoryoutput.cpp outputhandler.cpp lg-window-thumbnail.cpp)
kde4_add_plugin(kwin4_effect_gnome15thumbw ${kwin4_effect_gnome15thumbw_SOURCES})
target_link_libraries(kwin4_effect_gnome15thumbw ${KDE4_KDEUI_LIBS} kwineffects ${X11_LIBRARIES} ${OPENGL_LIBRARIES})
install(TARGETS kwin4_effect_gnome15thumbw DESTINATION ${PLUGIN_INSTALL_DIR})
install(FILES gnome15thumbw.desktop DESTINATION ${SERVICES_INSTALL_DIR}/kwin )


#the config
project(kcm_kwin4_effect_gnome15thumbw)
include_directories(${CMAKE_CURRENT_BINARY_DIR})

set (kcm_kwin4_effect_gnome15thumbw_SOURCES lg-window-thumbnail_config.cpp)
kde4_add_ui_files( kcm_kwin4_effect_gnome15thumbw_SOURCES lg-window-thumbnail_config.ui )
kde4_add_plugin (kcm_kwin4_effect_gnome15thumbw ${kcm_kwin4_effect_gnome15thumbw_SOURCES} )
target_link_libraries(kcm_kwin4_effect_gnome15thumbw ${KDE4_KDEUI_LIBS} kwineffects )
install (TARGETS kcm_kwin4_effect_gnome15thumbw DESTINATION ${PLUGIN_INSTALL_DIR})
install(FILES gnome15thumbw_config.desktop DESTINATION ${SERVICES_INSTALL_DIR}/kwin )

# TODO: add icons
kde4_install_icons(${ICON_INSTALL_DIR})
