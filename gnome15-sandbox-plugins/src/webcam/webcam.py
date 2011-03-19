#!/usr/bin/env python
 
#        +-----------------------------------------------------------------------------+
#        | GPL                                                                         |
#        +-----------------------------------------------------------------------------+
#        | Copyright (c) Brett Smith <tanktarta@blueyonder.co.uk>                      |
#        |                                                                             |
#        | This program is free software; you can redistribute it and/or               |
#        | modify it under the terms of the GNU General Public License                 |
#        | as published by the Free Software Foundation; either version 2              |
#        | of the License, or (at your option) any later version.                      |
#        |                                                                             |
#        | This program is distributed in the hope that it will be useful,             |
#        | but WITHOUT ANY WARRANTY; without even the implied warranty of              |
#        | MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               |
#        | GNU General Public License for more details.                                |
#        |                                                                             |
#        | You should have received a copy of the GNU General Public License           |
#        | along with this program; if not, write to the Free Software                 |
#        | Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA. |
#        +-----------------------------------------------------------------------------+
 
import gnome15.g15_util as g15util
import gnome15.g15_screen as g15screen
import gtk
import opencv
import os
#this is important for capturing/displaying images
from opencv import highgui
from threading import RLock
import logging
logger = logging.getLogger("webcam")

id="webcam"
name="Webcam"
description="Watch webcam video on your keyboard's LCD"
author="Brett Smith <tanktarta@blueyonder.co.uk>"
copyright="Copyright (C)2010 Brett Smith"
site="http://www.gnome15.org/"
has_preferences=True 

def create(gconf_key, gconf_client, screen):
    return G15Webcam(gconf_client, gconf_key, screen)

def show_preferences(parent, gconf_client, gconf_key):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(os.path.dirname(__file__), "webcam.glade"))    
    dialog = widget_tree.get_object("WebcamDialog") 
    model = widget_tree.get_object("DeviceModel")
    for i in range(0, 8):
        model.append([i])
    dialog.set_transient_for(parent)    
    g15util.configure_combo_from_gconf(gconf_client, gconf_key + "/device", "DeviceCombo", 0, widget_tree)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/contrast", "Contrast", 128, widget_tree, False)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/brightness", "Brightness", 128, widget_tree, False)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/saturation", "Saturation", 128, widget_tree, False)
    g15util.configure_spinner_from_gconf(gconf_client, gconf_key + "/hue", "Hue", 128, widget_tree, False)
    dialog.run()
    dialog.hide()

class G15Webcam():
    
    def __init__(self, gconf_client, gconf_key, screen):
        self._screen = screen
        self._gconf_client = gconf_client
        self._gconf_key = gconf_key
        self._timer = None
        self._lock = RLock()
        self._camera = None
        self._device_no = -1
        self._surface = None
    
    def activate(self):
        self._load_config()
        self._page = self._screen.new_page(self.paint, id="Webcam", priority = g15screen.PRI_NORMAL)
        self._redraw()
        self._notify_handler = self._gconf_client.notify_add(self._gconf_key, self._config_changed)
        
    def deactivate(self):
        self._release_camera()
        self._screen.del_page(self._page)
        self._timer.cancel()
        self._gconf_client.notify_remove(self._notify_handler)
        
    def destroy(self):
        pass
    
    def paint(self, canvas):
        if self._surface:
            sc = self.get_scale(highgui.cvGetCaptureProperty(self._camera, highgui.CV_CAP_PROP_FRAME_WIDTH ), highgui.cvGetCaptureProperty(self._camera, highgui.CV_CAP_PROP_FRAME_HEIGHT ))
            canvas.save()
            canvas.scale(sc, sc)
            canvas.set_source_surface(self._surface)
            canvas.paint()
            canvas.restore()
        
    def get_scale(self, w, h):
        size = self._screen.driver.get_size()
        sx = float(size[0]) / max(float(w), 1)
        sy = float(size[1]) / max(float(h), 1)
        return min(sx, sy)

    def _get_image(self):
        self._lock.acquire()
        try:
            im = highgui.cvQueryFrame(self._camera)
            if im:
                im = opencv.cvGetMat(im)
                return opencv.adaptors.Ipl2PIL(im)
        finally:
            self._lock.release()
    
    '''
    Private
    '''
    def _config_changed(self, client, connection_id, entry, args):
        self._timer.cancel()    
        self._load_config()
        
        # Get one frame to test the camera
        im = self._get_image()
        if not im:
            raise Exception("No frame retrieved from camera")
        
        self._redraw()
        
    def _release_camera(self):
        if self._camera != None:
            logger.info("Releasing camera")
            highgui.cvReleaseCapture(self._camera)
            self._camera = None
        
    def _load_config(self):
        device_no = self._gconf_client.get_int(self._gconf_key + "/device")
        if device_no != self._device_no:
            self._device_no = device_no
            self._release_camera()
            logger.info("Opening camera %d" % device_no)
            self._surface = None
            self._camera = highgui.cvCreateCameraCapture(device_no)
            if not self._camera:
                raise Exception("No camera")
            
        self._fps = highgui.cvGetCaptureProperty(self._camera, highgui.CV_CAP_PROP_FPS )
        device_no = self._gconf_client.get_int(self._gconf_key + "/device")
        entry = self._gconf_client.get(self._gconf_key + "/brightness")
        brightness = entry.get_int() if entry else 128
        entry = self._gconf_client.get(self._gconf_key + "/contrast")
        contrast = entry.get_int() if entry else 128
        entry = self._gconf_client.get(self._gconf_key + "/saturation")
        saturation = entry.get_int() if entry else 128
        entry = self._gconf_client.get(self._gconf_key + "/hue")
        hue = entry.get_int() if entry else 128
        logger.info("Camera %d has FPS of %d, brightness %d, contrast %d, saturation %d, hue %d" % ( device_no, self._fps, brightness, contrast, saturation, hue ) )
        
        highgui.cvSetCaptureProperty(self._camera, highgui.CV_CAP_PROP_BRIGHTNESS, brightness)
        highgui.cvSetCaptureProperty(self._camera, highgui.CV_CAP_PROP_CONTRAST, contrast)
        highgui.cvSetCaptureProperty(self._camera, highgui.CV_CAP_PROP_SATURATION, saturation)
        highgui.cvSetCaptureProperty(self._camera, highgui.CV_CAP_PROP_HUE, hue)
            
    def _schedule_redraw(self, interval = 0.1):
        self._timer = g15util.schedule("RedrawWebcam", interval, self._redraw)
    
    def _redraw(self):
        im = self._get_image()
        if im:
            self._surface = g15util.image_to_surface(im)
            self._screen.redraw(self._page)
            interval = 1.0 / float(10 if self._fps == -1 else self._fps)
            self._schedule_redraw(interval)
        else:
            logger.debug("No image, delaying refresh")
            self._schedule_redraw(5.0)