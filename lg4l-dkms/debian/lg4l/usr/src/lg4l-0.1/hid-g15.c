/***************************************************************************
 *   Copyright (C) 2010 by Alistair Buxton                                 *
 *   a.j.buxton@gmail.com                                                  *
 *   based on hid-g13.c                                                    *
 *                                                                         *
 *   This program is free software: you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation, either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 *   This driver is distributed in the hope that it will be useful, but    *
 *   WITHOUT ANY WARRANTY; without even the implied warranty of            *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU      *
 *   General Public License for more details.                              *
 *                                                                         *
 *   You should have received a copy of the GNU General Public License     *
 *   along with this software. If not see <http://www.gnu.org/licenses/>.  *
 ***************************************************************************/
#include <linux/fb.h>
#include <linux/hid.h>
#include <linux/init.h>
#include <linux/input.h>
#include <linux/mm.h>
#include <linux/sysfs.h>
#include <linux/uaccess.h>
#include <linux/usb.h>
#include <linux/vmalloc.h>
#include <linux/leds.h>
#include <linux/completion.h>
#include <linux/version.h>

#include "hid-ids.h"
#include "usbhid/usbhid.h"

#include "hid-gfb.h"

#define G15_NAME "Logitech G15"

/* Key defines */
#define G15_KEYS 64
#define G15_KEYMAP_SIZE (G15_KEYS*3)

/* Backlight defaults */
#define G15_DEFAULT_RED (0)
#define G15_DEFAULT_GREEN (255)
#define G15_DEFAULT_BLUE (0)

/* LED array indices */
#define G15_LED_M1 0
#define G15_LED_M2 1
#define G15_LED_M3 2
#define G15_LED_MR 3
#define G15_LED_BL_KEYS 4
#define G15_LED_BL_SCREEN 5
#define G15_LED_BL_CONTRAST 6 /* HACK ALERT contrast is nothing like a LED */

#define G15_REPORT_4_INIT	0x00
#define G15_REPORT_4_FINALIZE	0x01

#define G15_READY_SUBSTAGE_1 0x01
#define G15_READY_SUBSTAGE_2 0x02
#define G15_READY_SUBSTAGE_3 0x04
#define G15_READY_STAGE_1    0x07
#define G15_READY_SUBSTAGE_4 0x08
#define G15_READY_SUBSTAGE_5 0x10
#define G15_READY_STAGE_2    0x1F
#define G15_READY_SUBSTAGE_6 0x20
#define G15_READY_SUBSTAGE_7 0x40
#define G15_READY_STAGE_3    0x7F

#define G15_RESET_POST 0x01
#define G15_RESET_MESSAGE_1 0x02
#define G15_RESET_READY 0x03

/* Per device data structure */
struct g15_data {
	/* HID reports */
	struct hid_device *hdev;
	struct hid_report *backlight_report;
	struct hid_report *start_input_report;
	struct hid_report *feature_report_4;
	struct hid_report *led_report;
	struct hid_report *output_report_3;
	struct input_dev *input_dev;

	/* core state */
	char *name;
	int keycode[G15_KEYMAP_SIZE];
	int scancode_state[G15_KEYS];
	u8 keys_bl;
	u8 screen_bl;
	u8 screen_contrast;
	u8 led;
	u8 curkeymap;
	u8 keymap_switching;

	/* Framebuffer */
	struct gfb_data *gfb_data;

	/* LED stuff */
	struct led_classdev *led_cdev[7];

	/* Housekeeping stuff */
	spinlock_t lock;
	struct completion ready;
	int ready_stages;
	int need_reset;
};

/* Convenience macros */
#define hid_get_g15data(hdev) \
	((struct g15_data *)(hid_get_drvdata(hdev)))

#define input_get_hdev(idev) \
	((struct hid_device *)(input_get_drvdata(idev)))

#define input_get_g15data(idev) (hid_get_g15data(input_get_hdev(idev)))

/*
 * Keymap array indices
 *
 * Key    Byte  Mask Index
 * -----  ----  ---- -----
 * G1     0     0x01  0
 * G13    0     0x04  2
 * LIT    0     0x80  7
 * G7     1     0x01  8
 * G2     1     0x02  9
 * G14    1     0x08 11
 * S2     1     0x80 15
 * G8     2     0x02 17
 * G3     2     0x04 18
 * G15    2     0x10 20
 * S3     2     0x80 23
 * G9     3     0x04 26
 * G4     3     0x08 27
 * G16    3     0x20 29
 * S4     3     0x80 31
 * G10    4     0x08 35
 * G5     4     0x10 36
 * G17    4     0x40 38
 * S5     4     0x80 39
 * M1     5     0x01 40
 * G11    5     0x10 44
 * G6     5     0x20 45
 * M2     6     0x02 49
 * G12    6     0x20 53
 * MR     6     0x40 54
 * M3     7     0x04 58
 * G18    7     0x40 62
 * S1     7     0x80 63
 */
static const unsigned int g15_default_key_map[G15_KEYS] = {
KEY_RESERVED,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_F, /* LIGHT */
KEY_RESERVED,
KEY_RESERVED,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_B, /* S2 */
KEY_UNKNOWN,
KEY_RESERVED,
KEY_RESERVED,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_C, /* S3 */
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_RESERVED,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_UNKNOWN,
KEY_D, /* S4 */
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_RESERVED,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_E, /* S5 */
KEY_F21, /* M1 */
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_RESERVED,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_F22, /* M2 */
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_F24, /* MR */
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_F23, /* M3 */
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_UNKNOWN,
KEY_RESERVED,
KEY_A, /* S1 */
};

static DEVICE_ATTR(fb_node, 0444, gfb_fb_node_show, NULL);

static DEVICE_ATTR(fb_update_rate, 0666,
		   gfb_fb_update_rate_show,
		   gfb_fb_update_rate_store);

static int g15_input_get_keycode(struct input_dev * dev,
                                 unsigned int scancode,
                                 unsigned int * keycode)
{
	int retval;
	
#if LINUX_VERSION_CODE >= KERNEL_VERSION(2,6,37)
	
	struct input_keymap_entry ke = {
		.flags    = 0,
		.len      = sizeof(scancode),
		.index    = scancode,
		.scancode = scancode,
	};
	
	retval   = input_get_keycode(dev, &ke);
	*keycode = ke.keycode;
	
#else
	
	retval   = input_get_keycode(dev, scancode, keycode);
	
#endif
	
	return retval;
}

static void g15_msg_send(struct hid_device *hdev, u8 msg, u8 value1, u8 value2)
{
	struct g15_data *data = hid_get_g15data(hdev);

	data->led_report->field[0]->value[0] = msg;
	data->led_report->field[0]->value[1] = value1;
	data->led_report->field[0]->value[2] = value2;

	usbhid_submit_report(hdev, data->led_report, USB_DIR_OUT);
}

static void g15_led_set(struct led_classdev *led_cdev,
			 enum led_brightness value,
			 int led_num)
{
	struct device *dev;
	struct hid_device *hdev;
	struct g15_data *data;
	u8 mask;

	/* Get the device associated with the led */
	dev = led_cdev->dev->parent;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* Get the underlying data value */
	data = hid_get_g15data(hdev);

	mask = 0x01<<led_num;
	if (value)
		data->led |= mask;
	else
		data->led &= ~mask;

	g15_msg_send(hdev, 0x04, ~(data->led), 0);
}

static void g15_led_m1_brightness_set(struct led_classdev *led_cdev,
				      enum led_brightness value)
{
	g15_led_set(led_cdev, value, G15_LED_M1);
}

static void g15_led_m2_brightness_set(struct led_classdev *led_cdev,
				      enum led_brightness value)
{
	g15_led_set(led_cdev, value, G15_LED_M2);
}

static void g15_led_m3_brightness_set(struct led_classdev *led_cdev,
				      enum led_brightness value)
{
	g15_led_set(led_cdev, value, G15_LED_M3);
}

static void g15_led_mr_brightness_set(struct led_classdev *led_cdev,
				      enum led_brightness value)
{
	g15_led_set(led_cdev, value, G15_LED_MR);
}

static enum led_brightness g15_led_brightness_get(struct led_classdev *led_cdev)
{
	struct device *dev;
	struct hid_device *hdev;
	struct g15_data *data;
	int value = 0;

	/* Get the device associated with the led */
	dev = led_cdev->dev->parent;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* Get the underlying data value */
	data = hid_get_g15data(hdev);

	if (led_cdev == data->led_cdev[G15_LED_M1])
		value = data->led & 0x01;
	else if (led_cdev == data->led_cdev[G15_LED_M2])
		value = data->led & 0x02;
	else if (led_cdev == data->led_cdev[G15_LED_M3])
		value = data->led & 0x04;
	else if (led_cdev == data->led_cdev[G15_LED_MR])
		value = data->led & 0x08;
	else
		dev_info(dev, G15_NAME " error retrieving LED brightness\n");

	if (value)
		return LED_FULL;
	return LED_OFF;
}

static void g15_led_bl_set(struct led_classdev *led_cdev,
				      enum led_brightness value)
{
	struct device *dev;
	struct hid_device *hdev;
	struct g15_data *data;

	/* Get the device associated with the led */
	dev = led_cdev->dev->parent;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* Get the underlying data value */
	data = hid_get_g15data(hdev);

	if (led_cdev == data->led_cdev[G15_LED_BL_KEYS]) {
		if (value > 2)
			value = 2;
		data->keys_bl = value;
		g15_msg_send(hdev, 0x01, data->keys_bl, 0);
	} else if (led_cdev == data->led_cdev[G15_LED_BL_SCREEN]) {
		if (value > 2)
			value = 2;
		data->screen_bl = value<<4;
		g15_msg_send(hdev, 0x02, data->screen_bl, 0);
	} else if (led_cdev == data->led_cdev[G15_LED_BL_CONTRAST]) {
		if (value > 63)
			value = 63;
		data->screen_contrast = value;
		g15_msg_send(hdev, 32, 129, data->screen_contrast);
	} else
		dev_info(dev, G15_NAME " error retrieving LED brightness\n");

}

static int g15_led_bl_get(struct led_classdev *led_cdev)
{
	struct device *dev;
	struct hid_device *hdev;
	struct g15_data *data;

	/* Get the device associated with the led */
	dev = led_cdev->dev->parent;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* Get the underlying data value */
	data = hid_get_g15data(hdev);

	if (led_cdev == data->led_cdev[G15_LED_BL_KEYS])
		return data->keys_bl;
	else if (led_cdev == data->led_cdev[G15_LED_BL_SCREEN])
		return data->screen_bl;
	else if (led_cdev == data->led_cdev[G15_LED_BL_CONTRAST])
		return data->screen_contrast;
	else
		dev_info(dev, G15_NAME " error retrieving LED brightness\n");

	return 0;
}

static const struct led_classdev g15_led_cdevs[7] = {
	{
		.brightness_set		= g15_led_m1_brightness_set,
		.brightness_get		= g15_led_brightness_get,
	},
	{
		.brightness_set		= g15_led_m2_brightness_set,
		.brightness_get		= g15_led_brightness_get,
	},
	{
		.brightness_set		= g15_led_m3_brightness_set,
		.brightness_get		= g15_led_brightness_get,
	},
	{
		.brightness_set		= g15_led_mr_brightness_set,
		.brightness_get		= g15_led_brightness_get,
	},
	{
		.brightness_set		= g15_led_bl_set,
		.brightness_get		= g15_led_bl_get,
	},
	{
		.brightness_set		= g15_led_bl_set,
		.brightness_get		= g15_led_bl_get,
	},
	{
		.brightness_set		= g15_led_bl_set,
		.brightness_get		= g15_led_bl_get,
	},
};

static int g15_input_setkeycode(struct input_dev *dev,
				int scancode,
				int keycode)
{
	int old_keycode;
	int i;
	struct g15_data *data = input_get_g15data(dev);

	if (scancode >= dev->keycodemax)
		return -EINVAL;

	spin_lock(&data->lock);

	old_keycode = data->keycode[scancode];
	data->keycode[scancode] = keycode;

	__clear_bit(old_keycode, dev->keybit);
	__set_bit(keycode, dev->keybit);

	for (i = 0; i < dev->keycodemax; i++) {
		if (data->keycode[i] == old_keycode) {
			__set_bit(old_keycode, dev->keybit);
			break; /* Setting the bit twice is useless, so break*/
		}
	}

	spin_unlock(&data->lock);

	return 0;
}

static int g15_input_getkeycode(struct input_dev *dev,
				int scancode,
				int *keycode)
{
	struct g15_data *data = input_get_g15data(dev);

	if (!dev->keycodesize)
		return -EINVAL;

	if (scancode >= dev->keycodemax)
		return -EINVAL;

	*keycode = data->keycode[scancode];

	return 0;
}


/*
 * The "keymap" attribute
 */
static ssize_t g15_keymap_index_show(struct device *dev,
				     struct device_attribute *attr,
				     char *buf)
{
	struct g15_data *data = dev_get_drvdata(dev);

	return sprintf(buf, "%u\n", data->curkeymap);
}

static ssize_t g15_set_keymap_index(struct hid_device *hdev, unsigned k)
{
	int scancode;
	int offset_old;
	int offset_new;
	int keycode_old;
	int keycode_new;
	struct g15_data *data = hid_get_g15data(hdev);
	struct input_dev *idev = data->input_dev;

	if (k > 2)
		return -EINVAL;

	/*
	 * Release all the pressed keys unless the new keymap has the same key
	 * in the same scancode position.
	 *
	 * Also, clear the scancode state unless the new keymap has the same
	 * key in the same scancode position.
	 *
	 * This allows a keycode mapped to the same scancode in two different
	 * keymaps to remain pressed without a key up code when the keymap is
	 * switched.
	 */
	offset_old = G15_KEYS * data->curkeymap;
	offset_new = G15_KEYS * k;
	for (scancode = 0; scancode < G15_KEYS; scancode++) {
		keycode_old = data->keycode[offset_old+scancode];
		keycode_new = data->keycode[offset_new+scancode];
		if (keycode_old != keycode_new) {
			if (keycode_old != KEY_RESERVED)
				input_report_key(idev, keycode_old, 0);
			data->scancode_state[scancode] = 0;
		}
	}

	data->curkeymap = k;

	if (data->keymap_switching) {
		data->led = 1 << k;
		g15_msg_send(hdev, 4, ~data->led, 0);
	}

	return 0;
}

static ssize_t g15_keymap_index_store(struct device *dev,
				      struct device_attribute *attr,
				      const char *buf, size_t count)
{
	struct hid_device *hdev;
	int i;
	unsigned k;
	ssize_t set_result;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* If we have an invalid pointer we'll return ENODATA */
	if (hdev == NULL || &(hdev->dev) != dev)
		return -ENODATA;

	i = sscanf(buf, "%u", &k);
	if (i != 1) {
		dev_warn(dev, G15_NAME " unrecognized input: %s", buf);
		return -1;
	}

	set_result = g15_set_keymap_index(hdev, k);

	if (set_result < 0)
		return set_result;

	return count;
}

static DEVICE_ATTR(keymap_index, 0666,
		   g15_keymap_index_show,
		   g15_keymap_index_store);

/*
 * The "keycode" attribute
 */
static ssize_t g15_keymap_show(struct device *dev,
			       struct device_attribute *attr,
			       char *buf)
{
	int offset = 0;
	int result;
	int scancode;
	int keycode;
	int error;

	struct g15_data *data = dev_get_drvdata(dev);

	for (scancode = 0; scancode < G15_KEYMAP_SIZE; scancode++) {
		error = g15_input_get_keycode(data->input_dev, scancode, &keycode);
		if (error) {
			dev_warn(dev, G15_NAME " error accessing scancode %d\n",
				 scancode);
			continue;
		}

		result = sprintf(buf+offset, "0x%03x 0x%04x\n",
				 scancode, keycode);
		if (result < 0)
			return -EINVAL;
		offset += result;
	}

	return offset+1;
}

static ssize_t g15_keymap_store(struct device *dev,
				struct device_attribute *attr,
				const char *buf, size_t count)
{
	struct hid_device *hdev;
	int scanned;
	int consumed;
	int scancd;
	int keycd;
	int error;
	int set = 0;
	int gkey;
	int index;
	int good;
	struct g15_data *data;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* If we have an invalid pointer we'll return ENODATA */
	if (hdev == NULL || &(hdev->dev) != dev)
		return -ENODATA;

	/* Now, let's get the data structure */
	data = hid_get_g15data(hdev);

	do {
		good = 0;

		/* Look for scancode keycode pair in hex */
		scanned = sscanf(buf, "%x %x%n", &scancd, &keycd, &consumed);
		if (scanned == 2) {
			buf += consumed;
			error = g15_input_setkeycode(data->input_dev, scancd, keycd);
			if (error)
				goto err_input_setkeycode;
			set++;
			good = 1;
		} else {
			/*
			 * Look for Gkey keycode pair and assign to current
			 * keymap
			 */
			scanned = sscanf(buf, "G%d %x%n", &gkey, &keycd, &consumed);
			if (scanned == 2 && gkey > 0 && gkey <= G15_KEYS) {
				buf += consumed;
				scancd = data->curkeymap * G15_KEYS + gkey - 1;
				error = g15_input_setkeycode(data->input_dev, scancd, keycd);
				if (error)
					goto err_input_setkeycode;
				set++;
				good = 1;
			} else {
				/*
				 * Look for Gkey-index keycode pair and assign
				 * to indexed keymap
				 */
				scanned = sscanf(buf, "G%d-%d %x%n", &gkey, &index, &keycd, &consumed);
				if (scanned == 3 &&
				    gkey > 0 && gkey <= G15_KEYS &&
				    index >= 0 && index <= 2) {
					buf += consumed;
					scancd = index * G15_KEYS + gkey - 1;
					error = g15_input_setkeycode(data->input_dev, scancd, keycd);
					if (error)
						goto err_input_setkeycode;
					set++;
					good = 1;
				}
			}
		}

	} while (good);

	if (set == 0) {
		dev_warn(dev, G15_NAME " unrecognized keycode input: %s", buf);
		return -1;
	}

	return count;

err_input_setkeycode:
	dev_warn(dev, G15_NAME " error setting scancode %d to keycode %d\n",
		 scancd, keycd);
	return error;
}

static DEVICE_ATTR(keymap, 0666, g15_keymap_show, g15_keymap_store);

/*
 * The "keymap_switching" attribute
 */
static ssize_t g15_keymap_switching_show(struct device *dev,
					 struct device_attribute *attr,
					 char *buf)
{
	struct g15_data *data = dev_get_drvdata(dev);

	return sprintf(buf, "%u\n", data->keymap_switching);
}

static ssize_t g15_set_keymap_switching(struct hid_device *hdev, unsigned k)
{
	struct g15_data *data = hid_get_g15data(hdev);

	data->keymap_switching = k;

	if (data->keymap_switching) {
		data->led = 1 << data->curkeymap;
		g15_msg_send(hdev, 4, ~data->led, 0);
	}

	return 0;
}

static ssize_t g15_keymap_switching_store(struct device *dev,
					  struct device_attribute *attr,
					  const char *buf, size_t count)
{
	struct hid_device *hdev;
	int i;
	unsigned k;
	ssize_t set_result;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* If we have an invalid pointer we'll return ENODATA */
	if (hdev == NULL || &(hdev->dev) != dev)
		return -ENODATA;

	i = sscanf(buf, "%u", &k);
	if (i != 1) {
		dev_warn(dev, G15_NAME "unrecognized input: %s", buf);
		return -1;
	}

	set_result = g15_set_keymap_switching(hdev, k);

	if (set_result < 0)
		return set_result;

	return count;
}

static DEVICE_ATTR(keymap_switching, 0644,
		   g15_keymap_switching_show,
		   g15_keymap_switching_store);


static ssize_t g15_name_show(struct device *dev,
			     struct device_attribute *attr,
			     char *buf)
{
	struct g15_data *data = dev_get_drvdata(dev);
	int result;

	if (data->name == NULL) {
		buf[0] = 0x00;
		return 1;
	}

	spin_lock(&data->lock);
	result = sprintf(buf, "%s", data->name);
	spin_unlock(&data->lock);

	return result;
}

static ssize_t g15_name_store(struct device *dev,
			      struct device_attribute *attr,
			      const char *buf, size_t count)
{
	struct g15_data *data = dev_get_drvdata(dev);
	size_t limit = count;
	char *end;

	spin_lock(&data->lock);

	if (data->name != NULL) {
		kfree(data->name);
		data->name = NULL;
	}

	end = strpbrk(buf, "\n\r");
	if (end != NULL)
		limit = end - buf;

	if (end != buf) {

		if (limit > 100)
			limit = 100;

		data->name = kzalloc(limit+1, GFP_ATOMIC);

		strncpy(data->name, buf, limit);
	}

	spin_unlock(&data->lock);

	return count;
}

static DEVICE_ATTR(name, 0666, g15_name_show, g15_name_store);

static void g15_feature_report_4_send(struct hid_device *hdev, int which)
{
	struct g15_data *data = hid_get_g15data(hdev);

	if (which == G15_REPORT_4_INIT) {
		data->feature_report_4->field[0]->value[0] = 0x02;
		data->feature_report_4->field[0]->value[1] = 0x00;
		data->feature_report_4->field[0]->value[2] = 0x00;
		data->feature_report_4->field[0]->value[3] = 0x00;
	} else if (which == G15_REPORT_4_FINALIZE) {
		data->feature_report_4->field[0]->value[0] = 0x02;
		data->feature_report_4->field[0]->value[1] = 0x80;
		data->feature_report_4->field[0]->value[2] = 0x00;
		data->feature_report_4->field[0]->value[3] = 0xFF;
	} else {
		return;
	}

	usbhid_submit_report(hdev, data->feature_report_4, USB_DIR_OUT);
}

/*
 * The "minor" attribute
 */
static ssize_t g15_minor_show(struct device *dev,
			      struct device_attribute *attr,
			      char *buf)
{
	struct g15_data *data = dev_get_drvdata(dev);

	return sprintf(buf, "%d\n", data->hdev->minor);
}

static DEVICE_ATTR(minor, 0444, g15_minor_show, NULL);

/*
 * Create a group of attributes so that we can create and destroy them all
 * at once.
 */
static struct attribute *g15_attrs[] = {
	&dev_attr_name.attr,
	&dev_attr_keymap_index.attr,
	&dev_attr_keymap_switching.attr,
	&dev_attr_keymap.attr,
	&dev_attr_minor.attr,
	&dev_attr_fb_update_rate.attr,
	&dev_attr_fb_node.attr,
	NULL,	/* need to NULL terminate the list of attributes */
};

/*
 * An unnamed attribute group will put all of the attributes directly in
 * the kobject directory.  If we specify a name, a subdirectory will be
 * created for the attributes with the directory being the name of the
 * attribute group.
 */
static struct attribute_group g15_attr_group = {
	.attrs = g15_attrs,
};

static void g15_handle_key_event(struct g15_data *data,
				 struct input_dev *idev,
				 int scancode,
				 int value)
{
	int error;
	int keycode;
	int offset;

	offset = G15_KEYS * data->curkeymap;

	error = g15_input_get_keycode(idev, scancode+offset, &keycode);

	if (unlikely(error)) {
		dev_warn(&idev->dev, G15_NAME " error in input_get_keycode(): scancode=%d\n", scancode);
		return;
	}

	/* Only report mapped keys */
	if (keycode != KEY_RESERVED)
		input_report_key(idev, keycode, value);
	/* Or report MSC_SCAN on keypress of an unmapped key */
/*	else if (data->scancode_state[scancode] == 0 && value)
		input_event(idev, EV_MSC, MSC_SCAN, scancode);
*/
	data->scancode_state[scancode] = value;
}

static void g15_raw_event_process_input(struct hid_device *hdev,
					struct g15_data *data,
					u8 *raw_data)
{
	struct input_dev *idev = data->input_dev;
	int scancode;
	int value;
	int i;
	int mask;

	/*
	 * We'll check for the M* keys being pressed before processing
	 * the remainder of the key data. That way the new keymap will
	 * be loaded if there is a keymap switch.
	 */
/*	if (unlikely(data->keymap_switching)) {
		if (data->curkeymap != 0 && raw_data[5] & 0x01)
			g15_set_keymap_index(hdev, 0);
		else if (data->curkeymap != 1 && raw_data[6] & 0x02)
			g15_set_keymap_index(hdev, 1);
		else if (data->curkeymap != 2 && raw_data[7] & 0x04)
			g15_set_keymap_index(hdev, 2);
	}
*/
	raw_data[4] &= 0xFE; /* This bit turns on and off at random */

	for (i = 0, mask = 0x01; i < 8; i++, mask <<= 1) {
		scancode = i;
		value = raw_data[1] & mask;
		g15_handle_key_event(data, idev, scancode, value);

		scancode = i + 8;
		value = raw_data[2] & mask;
		g15_handle_key_event(data, idev, scancode, value);

		scancode = i + 16;
		value = raw_data[3] & mask;
		g15_handle_key_event(data, idev, scancode, value);

		scancode = i + 24;
		value = raw_data[4] & mask;
		g15_handle_key_event(data, idev, scancode, value);

		scancode = i + 32;
		value = raw_data[5] & mask;
		g15_handle_key_event(data, idev, scancode, value);

		scancode = i + 40;
		value = raw_data[6] & mask;
		g15_handle_key_event(data, idev, scancode, value);

		scancode = i + 48;
		value = raw_data[7] & mask;
		g15_handle_key_event(data, idev, scancode, value);

		scancode = i + 56;
		value = raw_data[8] & mask;
		g15_handle_key_event(data, idev, scancode, value);
	}

	input_sync(idev);
}

static int g15_raw_event(struct hid_device *hdev,
			 struct hid_report *report,
			 u8 *raw_data, int size)
{
	/*
	* On initialization receive a 258 byte message with
	* data = 6 0 255 255 255 255 255 255 255 255 ...
	*/
	struct g15_data *data;
	data = dev_get_drvdata(&hdev->dev);

	spin_lock(&data->lock);

	if (unlikely(data->need_reset)) {
		g15_msg_send(hdev, 4, ~data->led, 0);
		data->need_reset = 0;
		spin_unlock(&data->lock);
		return 1;
	}

	if (unlikely(data->ready_stages != G15_READY_STAGE_3)) {
		switch (report->id) {
		case 6:
			if (!(data->ready_stages & G15_READY_SUBSTAGE_1))
				data->ready_stages |= G15_READY_SUBSTAGE_1;
			else if (data->ready_stages & G15_READY_SUBSTAGE_4 &&
				 !(data->ready_stages & G15_READY_SUBSTAGE_5)
				)
				data->ready_stages |= G15_READY_SUBSTAGE_5;
			else if (data->ready_stages & G15_READY_SUBSTAGE_6 &&
				 raw_data[1] >= 0x80)
				data->ready_stages |= G15_READY_SUBSTAGE_7;
			break;
		case 1:
			if (!(data->ready_stages & G15_READY_SUBSTAGE_2))
				data->ready_stages |= G15_READY_SUBSTAGE_2;
			else
				data->ready_stages |= G15_READY_SUBSTAGE_3;
			break;
		}

		if (data->ready_stages == G15_READY_STAGE_1 ||
		    data->ready_stages == G15_READY_STAGE_2 ||
		    data->ready_stages == G15_READY_STAGE_3)
			complete_all(&data->ready);

		spin_unlock(&data->lock);
		return 1;
	}

	spin_unlock(&data->lock);

	if (likely(report->id == 2)) {
		g15_raw_event_process_input(hdev, data, raw_data);
		return 1;
	}

	return 0;
}

static void g15_initialize_keymap(struct g15_data *data)
{
	int i;

	for (i = 0; i < G15_KEYS; i++) {
		data->keycode[i] = g15_default_key_map[i];
		__set_bit(data->keycode[i], data->input_dev->keybit);
	}

	__clear_bit(KEY_RESERVED, data->input_dev->keybit);
}

static int g15_probe(struct hid_device *hdev,
		     const struct hid_device_id *id)
{
	int error;
	struct g15_data *data;
	int i;
	int led_num;
	struct usb_interface *intf;
	struct usb_device *usbdev;
	struct list_head *feature_report_list =
		&hdev->report_enum[HID_FEATURE_REPORT].report_list;
	struct list_head *output_report_list =
			&hdev->report_enum[HID_OUTPUT_REPORT].report_list;
	struct hid_report *report;
	char *led_name;

	dev_dbg(&hdev->dev, "Logitech G15 HID hardware probe...");

	/* Get the usb device to send the start report on */
	intf = to_usb_interface(hdev->dev.parent);
	usbdev = interface_to_usbdev(intf);

	/*
	 * Let's allocate the g15 data structure, set some reasonable
	 * defaults, and associate it with the device
	 */
	data = kzalloc(sizeof(struct g15_data), GFP_KERNEL);
	if (data == NULL) {
		dev_err(&hdev->dev, "can't allocate space for Logitech G15 device attributes\n");
		error = -ENOMEM;
		goto err_no_cleanup;
	}

	spin_lock_init(&data->lock);

	init_completion(&data->ready);

	data->hdev = hdev;

	hid_set_drvdata(hdev, data);

	dbg_hid("Preparing to parse " G15_NAME " hid reports\n");

	/* Parse the device reports and start it up */
	error = hid_parse(hdev);
	if (error) {
		dev_err(&hdev->dev, G15_NAME " device report parse failed\n");
		error = -EINVAL;
		goto err_cleanup_data;
	}

	error = hid_hw_start(hdev, HID_CONNECT_DEFAULT | HID_CONNECT_HIDINPUT_FORCE);
	if (error) {
		dev_err(&hdev->dev, G15_NAME " hardware start failed\n");
		error = -EINVAL;
		goto err_cleanup_data;
	}

	dbg_hid(G15_NAME " claimed: %d\n", hdev->claimed);

	error = hdev->ll_driver->open(hdev);
	if (error) {
		dev_err(&hdev->dev, G15_NAME " failed to open input interrupt pipe for key and joystick events\n");
		error = -EINVAL;
		goto err_cleanup_data;
	}

	/* Set up the input device for the key I/O */
	data->input_dev = input_allocate_device();
	if (data->input_dev == NULL) {
		dev_err(&hdev->dev, G15_NAME " error initializing the input device");
		error = -ENOMEM;
		goto err_cleanup_data;
	}

	input_set_drvdata(data->input_dev, hdev);

	data->input_dev->name = G15_NAME;
	data->input_dev->phys = hdev->phys;
	data->input_dev->uniq = hdev->uniq;
	data->input_dev->id.bustype = hdev->bus;
	data->input_dev->id.vendor = hdev->vendor;
	data->input_dev->id.product = hdev->product;
	data->input_dev->id.version = hdev->version;
	data->input_dev->dev.parent = hdev->dev.parent;
	data->input_dev->keycode = data->keycode;
	data->input_dev->keycodemax = G15_KEYMAP_SIZE;
	data->input_dev->keycodesize = sizeof(int);
	data->input_dev->setkeycode = g15_input_setkeycode;
	data->input_dev->getkeycode = g15_input_getkeycode;

	input_set_capability(data->input_dev, EV_KEY, KEY_UNKNOWN);
	data->input_dev->evbit[0] |= BIT_MASK(EV_REP);

	g15_initialize_keymap(data);

	error = input_register_device(data->input_dev);
	if (error) {
		dev_err(&hdev->dev, G15_NAME " error registering the input device");
		error = -EINVAL;
		goto err_cleanup_input_dev;
	}

	dbg_hid(KERN_INFO G15_NAME " allocated framebuffer\n");

	dbg_hid(KERN_INFO G15_NAME " allocated deferred IO structure\n");

	if (list_empty(feature_report_list)) {
		dev_err(&hdev->dev, "no feature report found\n");
		error = -ENODEV;
		goto err_cleanup_input_dev_reg;
	}
	dbg_hid(G15_NAME " feature report found\n");

	list_for_each_entry(report, feature_report_list, list) {
		switch (report->id) {
		case 0x02: /* G15 has only one feature report 0x02 */
			data->feature_report_4 = data->led_report = data->start_input_report = data->backlight_report = report;
			break;
		default:
			break;
		}
		dbg_hid(G15_NAME " Feature report: id=%u type=%u size=%u maxfield=%u report_count=%u\n",
			report->id, report->type, report->size,
			report->maxfield, report->field[0]->report_count);
	}

	if (list_empty(output_report_list)) {
		dev_err(&hdev->dev, "no output report found\n");
		error = -ENODEV;
		goto err_cleanup_input_dev_reg;
	}
	dbg_hid(G15_NAME " output report found\n");

	list_for_each_entry(report, output_report_list, list) {
		dbg_hid(G15_NAME " output report %d found size=%u maxfield=%u\n", report->id, report->size, report->maxfield);
		if (report->maxfield > 0) {
			dbg_hid(G15_NAME " offset=%u size=%u count=%u type=%u\n",
			       report->field[0]->report_offset,
			       report->field[0]->report_size,
			       report->field[0]->report_count,
			       report->field[0]->report_type);
		}
		switch (report->id) {
		case 0x03:
			data->output_report_3 = report;
			break;
		}
	}

	dbg_hid("Found all reports\n");

	/* Create the LED structures */
	for (i = 0; i < 7; i++) {
		data->led_cdev[i] = kzalloc(sizeof(struct led_classdev), GFP_KERNEL);
		if (data->led_cdev[i] == NULL) {
			dev_err(&hdev->dev, G15_NAME " error allocating memory for led %d", i);
			error = -ENOMEM;
			goto err_cleanup_led_structs;
		}
		/* Set the accessor functions by copying from template*/
		*(data->led_cdev[i]) = g15_led_cdevs[i];

		/*
		 * Allocate memory for the LED name
		 *
		 * Since led_classdev->name is a const char* we'll use an
		 * intermediate until the name is formatted with sprintf().
		 */
		led_name = kzalloc(sizeof(char)*30, GFP_KERNEL);
		if (led_name == NULL) {
			dev_err(&hdev->dev, G15_NAME " error allocating memory for led %d name", i);
			error = -ENOMEM;
			goto err_cleanup_led_structs;
		}
		switch (i) {
		case 0:
		case 1:
		case 2:
			sprintf(led_name, "g15_%d:orange:m%d", hdev->minor, i+1);
			break;
		case 3:
			sprintf(led_name, "g15_%d:blue:mr", hdev->minor);
			break;
		case 4:
			sprintf(led_name, "g15_%d:blue:keys", hdev->minor);
			break;
		case 5:
			sprintf(led_name, "g15_%d:white:screen", hdev->minor);
			break;
		case 6:
			sprintf(led_name, "g15_%d:contrast:screen", hdev->minor);
			break;
		}
		data->led_cdev[i]->name = led_name;
	}

	for (i = 0; i < 7; i++) {
		led_num = i;
		error = led_classdev_register(&hdev->dev, data->led_cdev[i]);
		if (error < 0) {
			dev_err(&hdev->dev, G15_NAME " error registering led %d\n", i);
			error = -EINVAL;
			goto err_cleanup_registered_leds;
		}
	}

	data->gfb_data = gfb_probe(hdev, GFB_PANEL_TYPE_160_43_1);
	if (data->gfb_data == NULL) {
		dev_err(&hdev->dev, G15_NAME " error registering framebuffer\n", i);
		goto err_cleanup_registered_leds;
	}

	dbg_hid("Waiting for G15 to activate\n");

	/* Add the sysfs attributes */
	error = sysfs_create_group(&(hdev->dev.kobj), &g15_attr_group);
	if (error) {
		dev_err(&hdev->dev, G15_NAME " failed to create sysfs group attributes\n");
		goto err_cleanup_registered_leds;
	}

	/*
	 * Wait here for stage 1 (substages 1-3) to complete
	 */
	wait_for_completion_timeout(&data->ready, HZ);

	/* Protect data->ready_stages before checking whether we're ready to proceed */
	spin_lock(&data->lock);
	if (data->ready_stages != G15_READY_STAGE_1) {
		dev_warn(&hdev->dev, G15_NAME " hasn't completed stage 1 yet, forging ahead with initialization\n");
		/* Force the stage */
		data->ready_stages = G15_READY_STAGE_1;
	}
	init_completion(&data->ready);
	data->ready_stages |= G15_READY_SUBSTAGE_4;
	spin_unlock(&data->lock);

	/*
	 * Send the init report, then follow with the input report to trigger
	 * report 6 and wait for us to get a response.
	 */
	g15_feature_report_4_send(hdev, G15_REPORT_4_INIT);
	usbhid_submit_report(hdev, data->start_input_report, USB_DIR_IN);
	wait_for_completion_timeout(&data->ready, HZ);

	/* Protect data->ready_stages before checking whether we're ready to proceed */
	spin_lock(&data->lock);
	if (data->ready_stages != G15_READY_STAGE_2) {
		dev_warn(&hdev->dev, G15_NAME " hasn't completed stage 2 yet, forging ahead with initialization\n");
		/* Force the stage */
		data->ready_stages = G15_READY_STAGE_2;
	}
	init_completion(&data->ready);
	data->ready_stages |= G15_READY_SUBSTAGE_6;
	spin_unlock(&data->lock);

	/*
	 * Clear the LEDs
	 */
	g15_msg_send(hdev, 4, ~data->led, 0);

	/*
	 * Send the finalize report, then follow with the input report to trigger
	 * report 6 and wait for us to get a response.
	 */
	g15_feature_report_4_send(hdev, G15_REPORT_4_FINALIZE);
	usbhid_submit_report(hdev, data->start_input_report, USB_DIR_IN);
	usbhid_submit_report(hdev, data->start_input_report, USB_DIR_IN);
	wait_for_completion_timeout(&data->ready, HZ);

	/* Protect data->ready_stages before checking whether we're ready to proceed */
	spin_lock(&data->lock);

	if (data->ready_stages != G15_READY_STAGE_3) {
		dev_warn(&hdev->dev, G15_NAME " hasn't completed stage 3 yet, forging ahead with initialization\n");
		/* Force the stage */
		data->ready_stages = G15_READY_STAGE_3;
	} else {
		dbg_hid(G15_NAME " stage 3 complete\n");
	}

	spin_unlock(&data->lock);

	g15_set_keymap_switching(hdev, 1);

	dbg_hid("G15 activated and initialized\n");

	/* Everything went well */
	return 0;

err_cleanup_registered_leds:
	for (i = 0; i < led_num; i++)
		led_classdev_unregister(data->led_cdev[i]);

err_cleanup_led_structs:
	for (i = 0; i < 7; i++) {
		if (data->led_cdev[i] != NULL) {
			if (data->led_cdev[i]->name != NULL)
				kfree(data->led_cdev[i]->name);
			kfree(data->led_cdev[i]);
		}
	}

err_cleanup_input_dev_reg:
	input_unregister_device(data->input_dev);

err_cleanup_input_dev:
	input_free_device(data->input_dev);

err_cleanup_data:
	/* Make sure we clean up the allocated data structure */
	kfree(data);

err_no_cleanup:

	hid_set_drvdata(hdev, NULL);

	return error;
}

static void g15_remove(struct hid_device *hdev)
{
	struct g15_data *data;
	int i;

	hdev->ll_driver->close(hdev);

	hid_hw_stop(hdev);

	sysfs_remove_group(&(hdev->dev.kobj), &g15_attr_group);

	/* Get the internal g15 data buffer */
	data = hid_get_drvdata(hdev);

	input_unregister_device(data->input_dev);

	kfree(data->name);

	/* Clean up the leds */
	for (i = 0; i < 7; i++) {
		led_classdev_unregister(data->led_cdev[i]);
		kfree(data->led_cdev[i]->name);
		kfree(data->led_cdev[i]);
	}

	gfb_remove(data->gfb_data);

	/* Finally, clean up the g15 data itself */
	kfree(data);
}

static void g15_post_reset_start(struct hid_device *hdev)
{
	struct g15_data *data = hid_get_g15data(hdev);

	spin_lock(&data->lock);
	data->need_reset = 1;
	spin_unlock(&data->lock);
}

static const struct hid_device_id g15_devices[] = {
	{ HID_USB_DEVICE(USB_VENDOR_ID_LOGITECH, USB_DEVICE_ID_LOGITECH_G15_LCD)
	},
	{ }
};
MODULE_DEVICE_TABLE(hid, g15_devices);

static struct hid_driver g15_driver = {
	.name			= "hid-g15",
	.id_table		= g15_devices,
	.probe			= g15_probe,
	.remove			= g15_remove,
	.raw_event		= g15_raw_event,
};

static int __init g15_init(void)
{
	return hid_register_driver(&g15_driver);
}

static void __exit g15_exit(void)
{
	hid_unregister_driver(&g15_driver);
}

module_init(g15_init);
module_exit(g15_exit);
MODULE_DESCRIPTION("Logitech G15 HID Driver");
MODULE_AUTHOR("Alistair Buxton (a.j.buxton@gmail.com)");
MODULE_LICENSE("GPL");
