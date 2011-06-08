/***************************************************************************
 *   Copyright (C) 2009 by Rick L. Vinyard, Jr.                            *
 *   rvinyard@cs.nmsu.edu                                                  *
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

#define G13_NAME "Logitech G13"

/* Key defines */
#define G13_KEYS 35
#define G13_KEYMAP_SIZE (G13_KEYS*3)

/* Framebuffer defines */
#define G13FB_NAME "g13fb"
#define G13FB_WIDTH (160)
#define G13FB_LINE_LENGTH (160/8)
#define G13FB_HEIGHT (43)
#define G13FB_SIZE (G13FB_LINE_LENGTH*G13FB_HEIGHT)

#define G13FB_UPDATE_RATE_LIMIT (20)
#define G13FB_UPDATE_RATE_DEFAULT (10)

/*
 * The native G13 format uses vertical bits. Therefore the number of bytes
 * needed to represent the first column is 43/8 (rows/bits) rounded up.
 * Additionally, the format requires a padding of 32 bits in front of the
 * image data.
 *
 * Therefore the vbitmap size must be:
 *   160 * ceil(43/8) + 32 = 160 * 6 + 32 = 992
 */
#define G13_VBITMAP_SIZE (992)

/* Backlight defaults */
#define G13_DEFAULT_RED (0)
#define G13_DEFAULT_GREEN (255)
#define G13_DEFAULT_BLUE (0)

/* LED array indices */
#define G13_LED_M1 0
#define G13_LED_M2 1
#define G13_LED_M3 2
#define G13_LED_MR 3

#define G13_REPORT_4_INIT	0x00
#define G13_REPORT_4_FINALIZE	0x01

#define G13_READY_SUBSTAGE_1 0x01
#define G13_READY_SUBSTAGE_2 0x02
#define G13_READY_SUBSTAGE_3 0x04
#define G13_READY_STAGE_1    0x07
#define G13_READY_SUBSTAGE_4 0x08
#define G13_READY_SUBSTAGE_5 0x10
#define G13_READY_STAGE_2    0x1F
#define G13_READY_SUBSTAGE_6 0x20
#define G13_READY_SUBSTAGE_7 0x40
#define G13_READY_STAGE_3    0x7F

#define G13_RESET_POST 0x01
#define G13_RESET_MESSAGE_1 0x02
#define G13_RESET_READY 0x03

/* Per device data structure */
struct g13_data {
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
	int keycode[G13_KEYMAP_SIZE];
	int scancode_state[G13_KEYS];
	u8 rgb[3];
	u8 led;
	u8 curkeymap;
	u8 keymap_switching;

	/* Framebuffer stuff */
	struct gfb_data *gfb_data;

	/* LED stuff */
	struct led_classdev *led_cdev[4];

	/* Housekeeping stuff */
	spinlock_t lock;
	struct completion ready;
	int ready_stages;
	int need_reset;
};

/* Convenience macros */
#define hid_get_g13data(hdev) \
	((struct g13_data *)(hid_get_drvdata(hdev)))

#define input_get_hdev(idev) \
	((struct hid_device *)(input_get_drvdata(idev)))

#define input_get_g13data(idev) (hid_get_g13data(input_get_hdev(idev)))

/*
 * Keymap array indices
 *
 * Key        Index
 * ---------  ------
 * G1-G22     0-21
 * FUNC       22
 * LCD1       23
 * LCD2       24
 * LCD3       25
 * LCD4       26
 * M1         27
 * M2         28
 * M3         29
 * MR         30
 * BTN_LEFT   31
 * BTN_DOWN   32
 * BTN_STICK  33
 * LIGHT      34
 */
static const unsigned int g13_default_key_map[G13_KEYS] = {
/* first row g1 - g7 */
KEY_F1, KEY_F2, KEY_F3, KEY_F4, KEY_F5, KEY_F6, KEY_F7,
/* second row g8 - g11 */
KEY_UNKNOWN, KEY_UNKNOWN, KEY_BACK, KEY_UP,
/* second row g12 - g13 */
KEY_FORWARD, KEY_UNKNOWN, KEY_UNKNOWN,
/* third row g15 - g19 */
KEY_UNKNOWN, KEY_LEFT, KEY_DOWN, KEY_RIGHT, KEY_UNKNOWN,
/* fourth row g20 - g22 */
KEY_BACKSPACE, KEY_ENTER, KEY_SPACE,
/* next, light left, light center left, light center right, light right */
BTN_0, BTN_1, BTN_2, BTN_3, BTN_4,
/* M1, M2, M3, MR */
KEY_RESERVED, KEY_RESERVED, KEY_RESERVED, KEY_RESERVED,
/* button left, button down, button stick, light */
BTN_LEFT, BTN_RIGHT, BTN_MIDDLE, KEY_RESERVED,
};


static DEVICE_ATTR(fb_node, 0444, gfb_fb_node_show, NULL);
static DEVICE_ATTR(fb_update_rate, 0666,
		   gfb_fb_update_rate_show,
		   gfb_fb_update_rate_store);

static int g13_input_get_keycode(struct input_dev * dev,
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

static void g13_led_send(struct hid_device *hdev)
{
	struct g13_data *data = hid_get_g13data(hdev);

	data->led_report->field[0]->value[0] = data->led&0x0F;
	data->led_report->field[0]->value[1] = 0x00;
	data->led_report->field[0]->value[2] = 0x00;
	data->led_report->field[0]->value[3] = 0x00;

	usbhid_submit_report(hdev, data->led_report, USB_DIR_OUT);
}

static void g13_led_set(struct led_classdev *led_cdev,
			 enum led_brightness value,
			 int led_num)
{
	struct device *dev;
	struct hid_device *hdev;
	struct g13_data *data;
	u8 mask;

	/* Get the device associated with the led */
	dev = led_cdev->dev->parent;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* Get the underlying data value */
	data = hid_get_g13data(hdev);

	mask = 0x01<<led_num;
	if (value)
		data->led |= mask;
	else
		data->led &= ~mask;

	g13_led_send(hdev);
}

static void g13_led_m1_brightness_set(struct led_classdev *led_cdev,
				      enum led_brightness value)
{
	g13_led_set(led_cdev, value, G13_LED_M1);
}

static void g13_led_m2_brightness_set(struct led_classdev *led_cdev,
				      enum led_brightness value)
{
	g13_led_set(led_cdev, value, G13_LED_M2);
}

static void g13_led_m3_brightness_set(struct led_classdev *led_cdev,
				      enum led_brightness value)
{
	g13_led_set(led_cdev, value, G13_LED_M3);
}

static void g13_led_mr_brightness_set(struct led_classdev *led_cdev,
				      enum led_brightness value)
{
	g13_led_set(led_cdev, value, G13_LED_MR);
}

static enum led_brightness g13_led_brightness_get(struct led_classdev *led_cdev)
{
	struct device *dev;
	struct hid_device *hdev;
	struct g13_data *data;
	int value = 0;

	/* Get the device associated with the led */
	dev = led_cdev->dev->parent;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* Get the underlying data value */
	data = hid_get_g13data(hdev);

	if (led_cdev == data->led_cdev[G13_LED_M1])
		value = data->led & 0x01;
	else if (led_cdev == data->led_cdev[G13_LED_M2])
		value = data->led & 0x02;
	else if (led_cdev == data->led_cdev[G13_LED_M3])
		value = data->led & 0x04;
	else if (led_cdev == data->led_cdev[G13_LED_MR])
		value = data->led & 0x08;
	else
		dev_info(dev, G13_NAME " error retrieving LED brightness\n");

	if (value)
		return LED_FULL;
	return LED_OFF;
}

static const struct led_classdev g13_led_cdevs[4] = {
	{
		.brightness_set		= g13_led_m1_brightness_set,
		.brightness_get		= g13_led_brightness_get,
	},
	{
		.brightness_set		= g13_led_m2_brightness_set,
		.brightness_get		= g13_led_brightness_get,
	},
	{
		.brightness_set		= g13_led_m3_brightness_set,
		.brightness_get		= g13_led_brightness_get,
	},
	{
		.brightness_set		= g13_led_mr_brightness_set,
		.brightness_get		= g13_led_brightness_get,
	},
};

static int g13_input_setkeycode(struct input_dev *dev,
				int scancode,
				int keycode)
{
	int old_keycode;
	int i;
	struct g13_data *data = input_get_g13data(dev);

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

static int g13_input_getkeycode(struct input_dev *dev,
				int scancode,
				int *keycode)
{
	struct g13_data *data = input_get_g13data(dev);

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
static ssize_t g13_keymap_index_show(struct device *dev,
				     struct device_attribute *attr,
				     char *buf)
{
	struct g13_data *data = dev_get_drvdata(dev);

	return sprintf(buf, "%u\n", data->curkeymap);
}

static ssize_t g13_set_keymap_index(struct hid_device *hdev, unsigned k)
{
	int scancode;
	int offset_old;
	int offset_new;
	int keycode_old;
	int keycode_new;
	struct g13_data *data = hid_get_g13data(hdev);
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
	offset_old = G13_KEYS * data->curkeymap;
	offset_new = G13_KEYS * k;
	for (scancode = 0; scancode < G13_KEYS; scancode++) {
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
		g13_led_send(hdev);
	}

	return 0;
}

static ssize_t g13_keymap_index_store(struct device *dev,
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
		dev_warn(dev, G13_NAME " unrecognized input: %s", buf);
		return -1;
	}

	set_result = g13_set_keymap_index(hdev, k);

	if (set_result < 0)
		return set_result;

	return count;
}

static DEVICE_ATTR(keymap_index, 0666,
		   g13_keymap_index_show,
		   g13_keymap_index_store);

/*
 * The "keycode" attribute
 */
static ssize_t g13_keymap_show(struct device *dev,
			       struct device_attribute *attr,
			       char *buf)
{
	int offset = 0;
	int result;
	int scancode;
	int keycode;
	int error;

	struct g13_data *data = dev_get_drvdata(dev);

	for (scancode = 0; scancode < G13_KEYMAP_SIZE; scancode++) {
		error = g13_input_get_keycode(data->input_dev, scancode, &keycode);
		if (error) {
			dev_warn(dev, G13_NAME " error accessing scancode %d\n",
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

static ssize_t g13_keymap_store(struct device *dev,
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
	struct g13_data *data;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* If we have an invalid pointer we'll return ENODATA */
	if (hdev == NULL || &(hdev->dev) != dev)
		return -ENODATA;

	/* Now, let's get the data structure */
	data = hid_get_g13data(hdev);

	do {
		good = 0;

		/* Look for scancode keycode pair in hex */
		scanned = sscanf(buf, "%x %x%n", &scancd, &keycd, &consumed);
		if (scanned == 2) {
			buf += consumed;
			error = g13_input_setkeycode(data->input_dev, scancd, keycd);
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
			if (scanned == 2 && gkey > 0 && gkey <= G13_KEYS) {
				buf += consumed;
				scancd = data->curkeymap * G13_KEYS + gkey - 1;
				error = g13_input_setkeycode(data->input_dev, scancd, keycd);
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
				    gkey > 0 && gkey <= G13_KEYS &&
				    index >= 0 && index <= 2) {
					buf += consumed;
					scancd = index * G13_KEYS + gkey - 1;
					error = g13_input_setkeycode(data->input_dev, scancd, keycd);
					if (error)
						goto err_input_setkeycode;
					set++;
					good = 1;
				}
			}
		}

	} while (good);

	if (set == 0) {
		dev_warn(dev, G13_NAME " unrecognized keycode input: %s", buf);
		return -1;
	}

	return count;

err_input_setkeycode:
	dev_warn(dev, G13_NAME " error setting scancode %d to keycode %d\n",
		 scancd, keycd);
	return error;
}

static DEVICE_ATTR(keymap, 0666, g13_keymap_show, g13_keymap_store);

/*
 * The "keymap_switching" attribute
 */
static ssize_t g13_keymap_switching_show(struct device *dev,
					 struct device_attribute *attr,
					 char *buf)
{
	struct g13_data *data = dev_get_drvdata(dev);

	return sprintf(buf, "%u\n", data->keymap_switching);
}

static ssize_t g13_set_keymap_switching(struct hid_device *hdev, unsigned k)
{
	struct g13_data *data = hid_get_g13data(hdev);

	data->keymap_switching = k;

	if (data->keymap_switching) {
		data->led = 1 << data->curkeymap;
		g13_led_send(hdev);
	}

	return 0;
}

static ssize_t g13_keymap_switching_store(struct device *dev,
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
		dev_warn(dev, G13_NAME "unrecognized input: %s", buf);
		return -1;
	}

	set_result = g13_set_keymap_switching(hdev, k);

	if (set_result < 0)
		return set_result;

	return count;
}

static DEVICE_ATTR(keymap_switching, 0644,
		   g13_keymap_switching_show,
		   g13_keymap_switching_store);


static ssize_t g13_name_show(struct device *dev,
			     struct device_attribute *attr,
			     char *buf)
{
	struct g13_data *data = dev_get_drvdata(dev);
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

static ssize_t g13_name_store(struct device *dev,
			      struct device_attribute *attr,
			      const char *buf, size_t count)
{
	struct g13_data *data = dev_get_drvdata(dev);
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

static DEVICE_ATTR(name, 0666, g13_name_show, g13_name_store);

static void g13_feature_report_4_send(struct hid_device *hdev, int which)
{
	struct g13_data *data = hid_get_g13data(hdev);

	if (which == G13_REPORT_4_INIT) {
		data->feature_report_4->field[0]->value[0] = 0x02;
		data->feature_report_4->field[0]->value[1] = 0x00;
		data->feature_report_4->field[0]->value[2] = 0x00;
		data->feature_report_4->field[0]->value[3] = 0x00;
	} else if (which == G13_REPORT_4_FINALIZE) {
		data->feature_report_4->field[0]->value[0] = 0x02;
		data->feature_report_4->field[0]->value[1] = 0x80;
		data->feature_report_4->field[0]->value[2] = 0x00;
		data->feature_report_4->field[0]->value[3] = 0xFF;
	} else {
		return;
	}

	usbhid_submit_report(hdev, data->feature_report_4, USB_DIR_OUT);
}

static void g13_rgb_send(struct hid_device *hdev)
{
	struct g13_data *data = hid_get_g13data(hdev);

	data->backlight_report->field[0]->value[0] = data->rgb[0];
	data->backlight_report->field[0]->value[1] = data->rgb[1];
	data->backlight_report->field[0]->value[2] = data->rgb[2];
	data->backlight_report->field[0]->value[3] = 0x00;

	usbhid_submit_report(hdev, data->backlight_report, USB_DIR_OUT);
}

/*
 * The "rgb" attribute
 * red green blue
 * each with values 0 - 255 (black - full intensity)
 */
static ssize_t g13_rgb_show(struct device *dev,
			    struct device_attribute *attr,
			    char *buf)
{
	unsigned r, g, b;
	struct g13_data *data = dev_get_drvdata(dev);

	r = data->rgb[0];
	g = data->rgb[1];
	b = data->rgb[2];

	return sprintf(buf, "%u %u %u\n", r, g, b);
}

static void g13_rgb_set(struct hid_device *hdev,
			unsigned r, unsigned g, unsigned b)
{
	struct g13_data *data = hid_get_g13data(hdev);

	data->rgb[0] = r;
	data->rgb[1] = g;
	data->rgb[2] = b;

	g13_rgb_send(hdev);
}

static ssize_t g13_rgb_store(struct device *dev,
			     struct device_attribute *attr,
			     const char *buf, size_t count)
{
	struct hid_device *hdev;
	int i;
	unsigned r;
	unsigned g;
	unsigned b;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* If we have an invalid pointer we'll return ENODATA */
	if (hdev == NULL || &(hdev->dev) != dev)
		return -ENODATA;

	i = sscanf(buf, "%u %u %u", &r, &g, &b);
	if (i != 3) {
		dev_warn(dev, G13_NAME "unrecognized input: %s", buf);
		return -1;
	}

	g13_rgb_set(hdev, r, g, b);

	return count;
}

static DEVICE_ATTR(rgb, 0666, g13_rgb_show, g13_rgb_store);

/*
 * The "minor" attribute
 */
static ssize_t g13_minor_show(struct device *dev,
			      struct device_attribute *attr,
			      char *buf)
{
	struct g13_data *data = dev_get_drvdata(dev);

	return sprintf(buf, "%d\n", data->hdev->minor);
}

static DEVICE_ATTR(minor, 0444, g13_minor_show, NULL);

/*
 * Create a group of attributes so that we can create and destroy them all
 * at once.
 */
static struct attribute *g13_attrs[] = {
	&dev_attr_name.attr,
	&dev_attr_rgb.attr,
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
static struct attribute_group g13_attr_group = {
	.attrs = g13_attrs,
};

static void g13_handle_key_event(struct g13_data *data,
				 struct input_dev *idev,
				 int scancode,
				 int value)
{
	int error;
	int keycode;
	int offset;

	offset = G13_KEYS * data->curkeymap;

	error = g13_input_get_keycode(idev, scancode+offset, &keycode);

	if (unlikely(error)) {
		dev_warn(&idev->dev, G13_NAME " error in input_get_keycode(): scancode=%d\n", scancode);
		return;
	}

	/* Only report mapped keys */
	if (keycode != KEY_RESERVED)
		input_report_key(idev, keycode, value);
	/* Or report MSC_SCAN on keypress of an unmapped key */
	else if (data->scancode_state[scancode] == 0 && value)
		input_event(idev, EV_MSC, MSC_SCAN, scancode);

	data->scancode_state[scancode] = value;
}

static void g13_raw_event_process_input(struct hid_device *hdev,
					struct g13_data *data,
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
	if (unlikely(data->keymap_switching)) {
		if (data->curkeymap != 0 && raw_data[6] & 0x20)
			g13_set_keymap_index(hdev, 0);
		else if (data->curkeymap != 1 && raw_data[6] & 0x40)
			g13_set_keymap_index(hdev, 1);
		else if (data->curkeymap != 2 && raw_data[6] & 0x80)
			g13_set_keymap_index(hdev, 2);
	}

	for (i = 0, mask = 0x01; i < 8; i++, mask <<= 1) {
		/* Keys G1 through G8 */
		scancode = i;
		value = raw_data[3] & mask;
		g13_handle_key_event(data, idev, scancode, value);

		/* Keys G9 through G16 */
		scancode = i + 8;
		value = raw_data[4] & mask;
		g13_handle_key_event(data, idev, scancode, value);

		/* Keys G17 through G22 */
		scancode = i + 16;
		value = raw_data[5] & mask;
		if (i <= 5)
			g13_handle_key_event(data, idev, scancode, value);

		/* Keys FUNC through M3 */
		scancode = i + 22;
		value = raw_data[6] & mask;
		g13_handle_key_event(data, idev, scancode, value);

		/* Keys MR through LIGHT */
		scancode = i + 30;
		value = raw_data[7] & mask;
		if (i <= 4)
			g13_handle_key_event(data, idev, scancode, value);
	}

	input_report_abs(idev, ABS_X, raw_data[1]);
	input_report_abs(idev, ABS_Y, raw_data[2]);
	input_sync(idev);
}

static int g13_raw_event(struct hid_device *hdev,
			 struct hid_report *report,
			 u8 *raw_data, int size)
{
	/*
	* On initialization receive a 258 byte message with
	* data = 6 0 255 255 255 255 255 255 255 255 ...
	*/
	struct g13_data *data;
	data = dev_get_drvdata(&hdev->dev);

	spin_lock(&data->lock);

	if (unlikely(data->need_reset)) {
		g13_rgb_send(hdev);
		g13_led_send(hdev);
		data->need_reset = 0;
		spin_unlock(&data->lock);
		return 1;
	}

	if (unlikely(data->ready_stages != G13_READY_STAGE_3)) {
		switch (report->id) {
		case 6:
			if (!(data->ready_stages & G13_READY_SUBSTAGE_1))
				data->ready_stages |= G13_READY_SUBSTAGE_1;
			else if (data->ready_stages & G13_READY_SUBSTAGE_4 &&
				 !(data->ready_stages & G13_READY_SUBSTAGE_5)
				)
				data->ready_stages |= G13_READY_SUBSTAGE_5;
			else if (data->ready_stages & G13_READY_SUBSTAGE_6 &&
				 raw_data[1] >= 0x80)
				data->ready_stages |= G13_READY_SUBSTAGE_7;
			break;
		case 1:
			if (!(data->ready_stages & G13_READY_SUBSTAGE_2))
				data->ready_stages |= G13_READY_SUBSTAGE_2;
			else
				data->ready_stages |= G13_READY_SUBSTAGE_3;
			break;
		}

		if (data->ready_stages == G13_READY_STAGE_1 ||
		    data->ready_stages == G13_READY_STAGE_2 ||
		    data->ready_stages == G13_READY_STAGE_3)
			complete_all(&data->ready);

		spin_unlock(&data->lock);
		return 1;
	}

	spin_unlock(&data->lock);

	if (likely(report->id == 1)) {
		g13_raw_event_process_input(hdev, data, raw_data);
		return 1;
	}

	return 0;
}

static void g13_initialize_keymap(struct g13_data *data)
{
	int i;

	for (i = 0; i < G13_KEYS; i++) {
		data->keycode[i] = g13_default_key_map[i];
		__set_bit(data->keycode[i], data->input_dev->keybit);
	}

	__clear_bit(KEY_RESERVED, data->input_dev->keybit);
}

static int g13_probe(struct hid_device *hdev,
		     const struct hid_device_id *id)
{
	int error;
	struct g13_data *data;
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

	dev_dbg(&hdev->dev, "Logitech G13 HID hardware probe...");

	/* Get the usb device to send the start report on */
	intf = to_usb_interface(hdev->dev.parent);
	usbdev = interface_to_usbdev(intf);

	/*
	 * Let's allocate the g13 data structure, set some reasonable
	 * defaults, and associate it with the device
	 */
	data = kzalloc(sizeof(struct g13_data), GFP_KERNEL);
	if (data == NULL) {
		dev_err(&hdev->dev, "can't allocate space for Logitech G13 device attributes\n");
		error = -ENOMEM;
		goto err_no_cleanup;
	}

	spin_lock_init(&data->lock);

	init_completion(&data->ready);

	data->hdev = hdev;

	hid_set_drvdata(hdev, data);

	dbg_hid("Preparing to parse " G13_NAME " hid reports\n");

	/* Parse the device reports and start it up */
	error = hid_parse(hdev);
	if (error) {
		dev_err(&hdev->dev, G13_NAME " device report parse failed\n");
		error = -EINVAL;
		goto err_cleanup_data;
	}

	error = hid_hw_start(hdev, HID_CONNECT_DEFAULT | HID_CONNECT_HIDINPUT_FORCE);
	if (error) {
		dev_err(&hdev->dev, G13_NAME " hardware start failed\n");
		error = -EINVAL;
		goto err_cleanup_data;
	}

	dbg_hid(G13_NAME " claimed: %d\n", hdev->claimed);

	error = hdev->ll_driver->open(hdev);
	if (error) {
		dev_err(&hdev->dev, G13_NAME " failed to open input interrupt pipe for key and joystick events\n");
		error = -EINVAL;
		goto err_cleanup_data;
	}

	/* Set up the input device for the key I/O */
	data->input_dev = input_allocate_device();
	if (data->input_dev == NULL) {
		dev_err(&hdev->dev, G13_NAME " error initializing the input device");
		error = -ENOMEM;
		goto err_cleanup_data;
	}

	input_set_drvdata(data->input_dev, hdev);

	data->input_dev->name = G13_NAME;
	data->input_dev->phys = hdev->phys;
	data->input_dev->uniq = hdev->uniq;
	data->input_dev->id.bustype = hdev->bus;
	data->input_dev->id.vendor = hdev->vendor;
	data->input_dev->id.product = hdev->product;
	data->input_dev->id.version = hdev->version;
	data->input_dev->dev.parent = hdev->dev.parent;
	data->input_dev->keycode = data->keycode;
	data->input_dev->keycodemax = G13_KEYMAP_SIZE;
	data->input_dev->keycodesize = sizeof(int);
	data->input_dev->setkeycode = g13_input_setkeycode;
	data->input_dev->getkeycode = g13_input_getkeycode;

	input_set_capability(data->input_dev, EV_ABS, ABS_X);
	input_set_capability(data->input_dev, EV_ABS, ABS_Y);
	input_set_capability(data->input_dev, EV_MSC, MSC_SCAN);
	input_set_capability(data->input_dev, EV_KEY, KEY_UNKNOWN);
	data->input_dev->evbit[0] |= BIT_MASK(EV_REP);

	/* 4 center values */
	input_set_abs_params(data->input_dev, ABS_X, 0, 0xff, 0, 4);
	input_set_abs_params(data->input_dev, ABS_Y, 0, 0xff, 0, 4);

	g13_initialize_keymap(data);

	error = input_register_device(data->input_dev);
	if (error) {
		dev_err(&hdev->dev, G13_NAME " error registering the input device");
		error = -EINVAL;
		goto err_cleanup_input_dev;
	}

	if (list_empty(feature_report_list)) {
		dev_err(&hdev->dev, "no feature report found\n");
		error = -ENODEV;
		goto err_cleanup_input_dev_reg;
	}
	dbg_hid(G13_NAME " feature report found\n");

	list_for_each_entry(report, feature_report_list, list) {
		switch (report->id) {
		case 0x04:
			data->feature_report_4 = report;
			break;
		case 0x05:
			data->led_report = report;
			break;
		case 0x06:
			data->start_input_report = report;
			break;
		case 0x07:
			data->backlight_report = report;
			break;
		default:
			break;
		}
		dbg_hid(G13_NAME " Feature report: id=%u type=%u size=%u maxfield=%u report_count=%u\n",
			report->id, report->type, report->size,
			report->maxfield, report->field[0]->report_count);
	}

	if (list_empty(output_report_list)) {
		dev_err(&hdev->dev, "no output report found\n");
		error = -ENODEV;
		goto err_cleanup_input_dev_reg;
	}
	dbg_hid(G13_NAME " output report found\n");

	list_for_each_entry(report, output_report_list, list) {
		dbg_hid(G13_NAME " output report %d found size=%u maxfield=%u\n", report->id, report->size, report->maxfield);
		if (report->maxfield > 0) {
			dbg_hid(G13_NAME " offset=%u size=%u count=%u type=%u\n",
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
	for (i = 0; i < 4; i++) {
		data->led_cdev[i] = kzalloc(sizeof(struct led_classdev), GFP_KERNEL);
		if (data->led_cdev[i] == NULL) {
			dev_err(&hdev->dev, G13_NAME " error allocating memory for led %d", i);
			error = -ENOMEM;
			goto err_cleanup_led_structs;
		}
		/* Set the accessor functions by copying from template*/
		*(data->led_cdev[i]) = g13_led_cdevs[i];

		/*
		 * Allocate memory for the LED name
		 *
		 * Since led_classdev->name is a const char* we'll use an
		 * intermediate until the name is formatted with sprintf().
		 */
		led_name = kzalloc(sizeof(char)*15, GFP_KERNEL);
		if (led_name == NULL) {
			dev_err(&hdev->dev, G13_NAME " error allocating memory for led %d name", i);
			error = -ENOMEM;
			goto err_cleanup_led_structs;
		}
		switch (i) {
		case 0:
		case 1:
		case 2:
			sprintf(led_name, "g13_%d:red:m%d", hdev->minor, i+1);
			break;
		case 3:
			sprintf(led_name, "g13_%d:red:mr", hdev->minor);
			break;
		}
		data->led_cdev[i]->name = led_name;
	}

	for (i = 0; i < 4; i++) {
		led_num = i;
		error = led_classdev_register(&hdev->dev, data->led_cdev[i]);
		if (error < 0) {
			dev_err(&hdev->dev, G13_NAME " error registering led %d", i);
			error = -EINVAL;
			goto err_cleanup_registered_leds;
		}
	}

	data->gfb_data = gfb_probe(hdev, GFB_PANEL_TYPE_160_43_1);
	if (data->gfb_data == NULL) {
		dev_err(&hdev->dev, G13_NAME " error registering framebuffer\n", i);
		goto err_cleanup_registered_leds;
	}

	dbg_hid("Waiting for G13 to activate\n");

	/* Add the sysfs attributes */
	error = sysfs_create_group(&(hdev->dev.kobj), &g13_attr_group);
	if (error) {
		dev_err(&hdev->dev, G13_NAME " failed to create sysfs group attributes\n");
		goto err_cleanup_registered_leds;
	}

	/*
	 * Wait here for stage 1 (substages 1-3) to complete
	 */
	wait_for_completion_timeout(&data->ready, HZ);

	/* Protect data->ready_stages before checking whether we're ready to proceed */
	spin_lock(&data->lock);
	if (data->ready_stages != G13_READY_STAGE_1) {
		dev_warn(&hdev->dev, G13_NAME " hasn't completed stage 1 yet, forging ahead with initialization\n");
		/* Force the stage */
		data->ready_stages = G13_READY_STAGE_1;
	}
	init_completion(&data->ready);
	data->ready_stages |= G13_READY_SUBSTAGE_4;
	spin_unlock(&data->lock);

	/*
	 * Send the init report, then follow with the input report to trigger
	 * report 6 and wait for us to get a response.
	 */
	g13_feature_report_4_send(hdev, G13_REPORT_4_INIT);
	usbhid_submit_report(hdev, data->start_input_report, USB_DIR_IN);
	wait_for_completion_timeout(&data->ready, HZ);

	/* Protect data->ready_stages before checking whether we're ready to proceed */
	spin_lock(&data->lock);
	if (data->ready_stages != G13_READY_STAGE_2) {
		dev_warn(&hdev->dev, G13_NAME " hasn't completed stage 2 yet, forging ahead with initialization\n");
		/* Force the stage */
		data->ready_stages = G13_READY_STAGE_2;
	}
	init_completion(&data->ready);
	data->ready_stages |= G13_READY_SUBSTAGE_6;
	spin_unlock(&data->lock);

	/*
	 * Clear the LEDs
	 */
	g13_led_send(hdev);

	g13_rgb_set(hdev, G13_DEFAULT_RED, G13_DEFAULT_GREEN, G13_DEFAULT_BLUE);

	/*
	 * Send the finalize report, then follow with the input report to trigger
	 * report 6 and wait for us to get a response.
	 */
	g13_feature_report_4_send(hdev, G13_REPORT_4_FINALIZE);
	usbhid_submit_report(hdev, data->start_input_report, USB_DIR_IN);
	usbhid_submit_report(hdev, data->start_input_report, USB_DIR_IN);
	wait_for_completion_timeout(&data->ready, HZ);

	/* Protect data->ready_stages before checking whether we're ready to proceed */
	spin_lock(&data->lock);

	if (data->ready_stages != G13_READY_STAGE_3) {
		dev_warn(&hdev->dev, G13_NAME " hasn't completed stage 3 yet, forging ahead with initialization\n");
		/* Force the stage */
		data->ready_stages = G13_READY_STAGE_3;
	} else {
		dbg_hid(G13_NAME " stage 3 complete\n");
	}

	spin_unlock(&data->lock);

	g13_set_keymap_switching(hdev, 1);

	dbg_hid("G13 activated and initialized\n");

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

static void g13_remove(struct hid_device *hdev)
{
	struct g13_data *data;
	int i;

	hdev->ll_driver->close(hdev);

	hid_hw_stop(hdev);

	sysfs_remove_group(&(hdev->dev.kobj), &g13_attr_group);

	/* Get the internal g13 data buffer */
	data = hid_get_drvdata(hdev);

	input_unregister_device(data->input_dev);

	kfree(data->name);

	/* Clean up the leds */
	for (i = 0; i < 4; i++) {
		led_classdev_unregister(data->led_cdev[i]);
		kfree(data->led_cdev[i]->name);
		kfree(data->led_cdev[i]);
	}

	gfb_remove(data->gfb_data);

	/* Finally, clean up the g13 data itself */
	kfree(data);
}

static void g13_post_reset_start(struct hid_device *hdev)
{
	struct g13_data *data = hid_get_g13data(hdev);

	spin_lock(&data->lock);
	data->need_reset = 1;
	spin_unlock(&data->lock);
}

static const struct hid_device_id g13_devices[] = {
	{ HID_USB_DEVICE(USB_VENDOR_ID_LOGITECH, USB_DEVICE_ID_LOGITECH_G13)
	},
	{ }
};
MODULE_DEVICE_TABLE(hid, g13_devices);

static struct hid_driver g13_driver = {
	.name			= "hid-g13",
	.id_table		= g13_devices,
	.probe			= g13_probe,
	.remove			= g13_remove,
	.raw_event		= g13_raw_event,
};

static int __init g13_init(void)
{
	return hid_register_driver(&g13_driver);
}

static void __exit g13_exit(void)
{
	hid_unregister_driver(&g13_driver);
}

module_init(g13_init);
module_exit(g13_exit);
MODULE_DESCRIPTION("Logitech G13 HID Driver");
MODULE_AUTHOR("Rick L Vinyard Jr (rvinyard@cs.nmsu.edu)");
MODULE_LICENSE("GPL");
