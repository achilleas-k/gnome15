#!/usr/bin/python

import gst
import gtk

class Main:
    def __init__(self):

        # Create GUI objects
        self.window = gtk.Window()
        self.vbox = gtk.VBox()
        self.da = gtk.DrawingArea()
        self.bb = gtk.HButtonBox()
        self.da.set_size_request(300, 150)
        self.playButton = gtk.Button(stock="gtk - media - play")
        self.playButton.connect("clicked", self.OnPlay)
        self.stopButton = gtk.Button(stock="gtk - media - stop")
        self.stopButton.connect("clicked", self.OnStop)
        self.quitButton = gtk.Button(stock="gtk - quit")
        self.quitButton.connect("clicked", self.OnQuit)
        self.vbox.pack_start(self.da)
        self.bb.add(self.playButton)
        self.bb.add(self.stopButton)
        self.bb.add(self.quitButton)
        self.vbox.pack_start(self.bb)
        self.window.add(self.vbox)

        # Create GStreamer pipeline
        self.pipeline = gst.Pipeline("mypipeline")
        # Set up our video test source
        self.videotestsrc = gst.element_factory_make("videotestsrc", "video")
        # Add it to the pipeline
        self.pipeline.add(self.videotestsrc)
        # Now we need somewhere to send the video
        self.sink = gst.element_factory_make("xvimagesink", "sink")
        # Add it to the pipeline
        self.pipeline.add(self.sink)
        # Link the video source to the sink - xv
        self.videotestsrc.link(self.sink)
        self.window.show_all()

    def OnPlay(self, widget):
        print "play"
        # Tell the video sink to display the output in our DrawingArea
        self.sink.set_xwindow_id(self.da.window.xid)
        self.pipeline.set_state(gst.STATE_PLAYING)

    def OnStop(self, widget):
        print "stop"
        self.pipeline.set_state(gst.STATE_READY)

    def OnQuit(self, widget):
        gtk.main_quit()

start = Main()
gtk.main() 
