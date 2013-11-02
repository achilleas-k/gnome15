#  Gnome15 - Suite of tools for the Logitech G series keyboards and headsets
#  Copyright (C) 2010 Brett Smith <tanktarta@blueyonder.co.uk>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

from receivers import G19Receiver

import sys
import threading
import time
import usb
from PIL import Image as Img
import logging
import array
logger = logging.getLogger(__name__)

class G19(object):
    '''Simple access to Logitech G19 features.

    All methods are thread-safe if not denoted otherwise.

    '''

    def __init__(self, resetOnStart=False, enable_mm_keys=False, write_timeout = 10000, reset_wait = 0):
        '''Initializes and opens the USB device.'''
        
        logger.info("Setting up G19 with write timeout of %d", write_timeout)
        self.enable_mm_keys = enable_mm_keys
        self.__write_timeout = write_timeout
        self.__usbDevice = G19UsbController(resetOnStart, enable_mm_keys, reset_wait)
        self.__usbDeviceMutex = threading.Lock()
        self.__keyReceiver = G19Receiver(self)
        self.__threadDisplay = None
        
        self.__frame_content = [0x10, 0x0F, 0x00, 0x58, 0x02, 0x00, 0x00, 0x00,
                 0x00, 0x00, 0x00, 0x3F, 0x01, 0xEF, 0x00, 0x0F]
        for i in range(16, 256):
            self.__frame_content.append(i)
        for i in range(256):
            self.__frame_content.append(i)

    @staticmethod
    def convert_image_to_frame(filename):
        '''Loads image from given file.

        Format will be auto-detected.  If neccessary, the image will be resized
        to 320x240.

        @return Frame data to be used with send_frame().

        '''
        img = Img.open(filename)
        access = img.load()
        if img.size != (320, 240):
            img = img.resize((320, 240), Img.CUBIC)
            access = img.load()
        data = []
        for x in range(320):
            for y in range(240):
                ax = access[x, y]
                if len(ax) == 3:
                    r, g, b = ax
                else:
                    r, g, b, a = ax
                val = G19.rgb_to_uint16(r, g, b)
                data.append(val >> 8)
                data.append(val & 0xff)
        return data

    @staticmethod
    def rgb_to_uint16(r, g, b):
        '''Converts a RGB value to 16bit highcolor (5-6-5).

        @return 16bit highcolor value in little-endian.

        '''
        rBits = r * 2**5 / 255
        gBits = g * 2**6 / 255
        bBits = b * 2**5 / 255

        rBits = rBits if rBits <= 0b00011111 else 0b00011111
        gBits = gBits if gBits <= 0b00111111 else 0b00111111
        bBits = bBits if bBits <= 0b00011111 else 0b00011111

        valueH = (rBits << 3) | (gBits >> 3)
        valueL = (gBits << 5) | bBits
        return valueL << 8 | valueH
    
    def add_input_processor(self, input_processor):
        self.__keyReceiver.add_input_processor(input_processor)

    def add_applet(self, applet):
        '''Starts an applet.'''
        self.add_input_processor(applet.get_input_processor())

    def fill_display_with_color(self, r, g, b):
        '''Fills display with given color.'''
        # 16bit highcolor format: 5 red, 6 gree, 5 blue
        # saved in little-endian, because USB is little-endian
        value = self.rgb_to_uint16(r, g, b)
        valueH = value & 0xff
        valueL = value >> 8
        frame = [valueL, valueH] * (320 * 240)
        self.send_frame(frame)

    def load_image(self, filename):
        '''Loads image from given file.

        Format will be auto-detected.  If neccessary, the image will be resized
        to 320x240.

        '''
        self.send_frame(self.convert_image_to_frame(filename))

    def read_g_and_m_keys(self, maxLen=20):
        '''Reads interrupt data from G, M and light switch keys.

        @return maxLen Maximum number of bytes to read.
        @return Read data or empty list.

        '''
        self.__usbDeviceMutex.acquire()
        val = []
        try:
            val = list(self.__usbDevice.handleIf1.interruptRead(
                0x83, maxLen, 10))
        except usb.USBError as e:
            if e.message != "Connection timed out":
                logger.debug("Error reading g and m keys", exc_info = e)
            pass
        finally:
            self.__usbDeviceMutex.release()
        return val

    def read_display_menu_keys(self):
        '''Reads interrupt data from display keys.

        @return Read data or empty list.

        '''
        self.__usbDeviceMutex.acquire()
        val = []
        try:
            val = list(self.__usbDevice.handleIf0.interruptRead(0x81, 2, 10))
        except usb.USBError as e:
            if e.message != "Connection timed out":
                logger.debug("Error reading display menu keys", exc_info = e)
            pass
        finally:
            self.__usbDeviceMutex.release()
        return val

    def read_multimedia_keys(self):
        '''Reads interrupt data from multimedia keys.

        @return Read data or empty list.

        '''
        if not self.enable_mm_keys:
            return False
        
        self.__usbDeviceMutex.acquire()
        val = []
        try:
            val = list(self.__usbDevice.handleIfMM.interruptRead(0x82, 2, 10))
        except usb.USBError as e:
            if e.message != "Connection timed out":
                logger.debug("Error reading multimedia keys", exc_info = e)
            pass
        finally:
            self.__usbDeviceMutex.release()
        return val

    def reset(self):
        '''Initiates a bus reset to USB device.'''
        self.__usbDeviceMutex.acquire()
        try:
            self.__usbDevice.reset()
        finally:
            self.__usbDeviceMutex.release()

    def save_default_bg_color(self, r, g, b):
        '''This stores given color permanently to keyboard.

        After a reset this will be color used by default.

        '''
        rtype = usb.TYPE_CLASS | usb.RECIP_INTERFACE
        colorData = [7, r, g, b]
        self.__usbDeviceMutex.acquire()
        try:
            self.__usbDevice.handleIf1.controlMsg(
                rtype, 0x09, colorData, 0x308, 0x01, self.__write_timeout)
        finally:
            self.__usbDeviceMutex.release()

    def send_frame(self, data):
        '''Sends a frame to display.

        @param data 320x240x2 bytes, containing the frame in little-endian
        16bit highcolor (5-6-5) format.
        Image must be row-wise, starting at upper left corner and ending at
        lower right.  This means (data[0], data[1]) is the first pixel and
        (data[239 * 2], data[239 * 2 + 1]) the lower left one.

        '''
        if len(data) != (320 * 240 * 2):
            raise ValueError("illegal frame size: " + str(len(data))
                    + " should be 320x240x2=" + str(320 * 240 * 2))
        frame = list(self.__frame_content)
        frame += data

        self.__usbDeviceMutex.acquire()
        try:
            self.__usbDevice.handleIf0.bulkWrite(2, frame, self.__write_timeout)
        finally:
            self.__usbDeviceMutex.release()

    def set_bg_color(self, r, g, b):
        '''Sets backlight to given color.'''
        rtype = usb.TYPE_CLASS | usb.RECIP_INTERFACE
        colorData = [7, r, g, b]
        self.__usbDeviceMutex.acquire()
        try:
            self.__usbDevice.handleIf1.controlMsg(
                rtype, 0x09, colorData, 0x307, 0x01, 10000)
        finally:
            self.__usbDeviceMutex.release()

    def set_enabled_m_keys(self, keys):
        '''Sets currently lit keys as an OR-combination of LIGHT_KEY_M1..3,R.

        example:
            from logitech.g19_keys import Data
            lg19 = G19()
            lg19.set_enabled_m_keys(Data.LIGHT_KEY_M1 | Data.LIGHT_KEY_MR)

        '''
        rtype = usb.TYPE_CLASS | usb.RECIP_INTERFACE
        self.__usbDeviceMutex.acquire()
        try:
            self.__usbDevice.handleIf1.controlMsg(
                rtype, 0x09, [5, keys], 0x305, 0x01, self.__write_timeout)
        finally:
            self.__usbDeviceMutex.release()

    def set_display_brightness(self, val):
        '''Sets display brightness.

        @param val in [0,100] (off..maximum).

        '''
        data = [val, 0xe2, 0x12, 0x00, 0x8c, 0x11, 0x00, 0x10, 0x00]
        rtype = usb.TYPE_VENDOR | usb.RECIP_INTERFACE
        self.__usbDeviceMutex.acquire()
        try:
            self.__usbDevice.handleIf1.controlMsg(rtype, 0x0a, data, 0x0, 0x0, self.__write_timeout)
        finally:
            self.__usbDeviceMutex.release()

    def start_event_handling(self):
        '''Start event processing (aka keyboard driver).

        This method is NOT thread-safe.

        '''
        self.stop_event_handling()
        self.__threadDisplay = threading.Thread(
                target=self.__keyReceiver.run)
        self.__keyReceiver.start()
        self.__threadDisplay.name = "EventThread"
        self.__threadDisplay.setDaemon(True)
        self.__threadDisplay.start()

    def stop_event_handling(self):
        '''Stops event processing (aka keyboard driver).

        This method is NOT thread-safe.

        '''
        self.__keyReceiver.stop()
        if self.__threadDisplay:
            self.__threadDisplay.join()
            self.__threadDisplay = None

    def close(self):
        logger.info("Closing G19")
        self.stop_event_handling()
        self.__usbDevice.close()


class G19UsbController(object):
    '''Controller for accessing the G19 USB device.

    The G19 consists of two composite USB devices:
        * 046d:c228
          The keyboard consisting of two interfaces:
              MI00: keyboard
                  EP 0x81(in)  - INT the keyboard itself
              MI01: (ifacMM)
                  EP 0x82(in)  - multimedia keys, incl. scroll and Winkey-switch

        * 046d:c229
          LCD display with two interfaces:
              MI00 (0x05): (iface0) via control data in: display keys
                  EP 0x81(in)  - INT
                  EP 0x02(out) - BULK display itself
              MI01 (0x06): (iface1) backlight
                  EP 0x83(in)  - INT G-keys, M1..3/MR key, light key

    '''

    def __init__(self, resetOnStart=False, enable_mm_keys=False, resetWait = 0):
        self.enable_mm_keys = enable_mm_keys
        logger.info("Looking for LCD device")
        self.__lcd_device = self._find_device(0x046d, 0xc229)
        if not self.__lcd_device:
            raise usb.USBError("G19 LCD not found on USB bus")
        
        # Reset
        self.handleIf0 = self.__lcd_device.open()
        if resetOnStart:
            logger.info("Resetting LCD device")
            self.handleIf0.reset()
            time.sleep(float(resetWait) / 1000.0)
            logger.info("Re-opening LCD device")
            self.handleIf0 = self.__lcd_device.open()
            logger.info("Re-opened LCD device")

        self.handleIf1 = self.__lcd_device.open()
        
        config = self.__lcd_device.configurations[0]
        display_interface = config.interfaces[0][0]
        
        # This is to cope with a difference in pyusb 1.0 compatibility layer
        if len(config.interfaces) > 1:
            macro_and_backlight_interface = config.interfaces[1][0]
        else:
            macro_and_backlight_interface = config.interfaces[0][1]

        try:
            logger.debug("Detaching kernel driver for LCD device")
            # Use .interfaceNumber for pyusb 1.0 compatibility layer
            self.handleIf0.detachKernelDriver(display_interface.interfaceNumber)
            logger.debug("Detached kernel driver for LCD device")
        except usb.USBError as e:
            logger.debug("Detaching kernel driver for LCD device failed.", exc_info = e)
            
        try:
            logger.debug("Detaching kernel driver for macro / backlight device")
            # Use .interfaceNumber for pyusb 1.0 compatibility layer
            self.handleIf1.detachKernelDriver(macro_and_backlight_interface.interfaceNumber)
            logger.debug("Detached kernel driver for macro / backlight device")
        except usb.USBError as e:
            logger.debug("Detaching kernel driver for macro / backlight device failed.", exc_info = e)

        logger.debug("Setting configuration")
        
        #self.handleIf0.setConfiguration(1)
        #self.handleIf1.setConfiguration(1)
        
        logger.debug("Claiming LCD interface")
        self.handleIf0.claimInterface(display_interface)
        logger.info("Claimed LCD interface")
        logger.debug("Claiming macro interface")
        self.handleIf1.claimInterface(macro_and_backlight_interface)
        logger.info("Claimed macro interface")
        
        if self.enable_mm_keys:
            logger.debug("Looking for multimedia keys device")
            self.__kbd_device = self._find_device(0x046d, 0xc228)
            if not self.__kbd_device:
                raise usb.USBError("G19 keyboard not found on USB bus")
            self.handleIfMM = self.__kbd_device.open()
            
            if resetOnStart:
                logger.debug("Resetting multimedia keys device")
                self.handleIfMM.reset()
                logger.debug("Re-opening multimedia keys device")
                self.handleIfMM = self.__kbd_device.open()
                logger.debug("Re-opened multimedia keys device")
                
        
            config = self.__kbd_device.configurations[0]
            ifacMM = config.interfaces[1][0]
        
            try:
                self.handleIfMM.setConfiguration(1)
            except usb.USBError as e:
                logger.debug("Error when trying to set configuration", exc_info = e)
                pass
            try:
                logger.debug("Detaching kernel driver for multimedia keys device")
                self.handleIfMM.detachKernelDriver(ifacMM)
                logger.debug("Detached kernel driver for multimedia keys device")
            except usb.USBError as e:
                logger.debug("Detaching kernel driver for multimedia keys device failed.", exc_info = e)
            
            logger.debug("Claiming multimedia interface")
            self.handleIfMM.claimInterface(1)
            logger.info("Claimed multimedia keys interface")


    def close(self):
        if self.enable_mm_keys:
            self.handleIfMM.releaseInterface()
        self.handleIf1.releaseInterface()
        self.handleIf0.releaseInterface()

    @staticmethod
    def _find_device(idVendor, idProduct):
        for bus in usb.busses():
            for dev in bus.devices:
                if dev.idVendor == idVendor and \
                        dev.idProduct == idProduct:
                    return dev
        return None

    def reset(self):
        '''Resets the device on the USB.'''
        self.handleIf0.reset()
        self.handleIf1.reset()

def main():
    lg19 = G19()
    lg19.start_event_handling()
    time.sleep(20)
    lg19.stop_event_handling()

if __name__ == '__main__':
    main()
