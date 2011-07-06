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

#include "hid-ids.h"
#include "usbhid/usbhid.h"

#include "hid-gfb.h"

#define GFB_NAME "Logitech GamePanel Framebuffer"

/* Framebuffer defines */
#define GFB_UPDATE_RATE_LIMIT (30)
#define GFB_UPDATE_RATE_DEFAULT (30)

/* Convenience macros */
#define hid_get_gfbdata(hdev) \
	((struct gfb_data *)(hid_get_drvdata(hdev)))

static uint32_t pseudo_palette[16];

/* Unlock the urb so we can reuse it */
static void gfb_fb_urb_completion(struct urb *urb)
{ 
        /* we need to unlock fb_vbitmap regardless of urb success status */
        unsigned long irq_flags;
        struct gfb_data *data = urb->context;
        spin_lock_irqsave(&data->fb_urb_lock, irq_flags);
        data->fb_vbitmap_busy = 0;
        spin_unlock_irqrestore(&data->fb_urb_lock, irq_flags);
}

/* Send the current framebuffer vbitmap as an interrupt message */
static int gfb_fb_send(struct gfb_data *data)
{
	struct usb_interface *intf;
	struct usb_device *usb_dev;
	struct hid_device *hdev = data->hdev;

	struct usb_host_endpoint *ep;
	unsigned int pipe;
	int retval = 0;
	unsigned long irq_flags;

	/*
	 * Try and lock the framebuffer urb to prevent access if we have
	 * submitted it. If we can't lock it we'll have to delay this update
	 * until the next framebuffer interval.
	 *
	 * Fortunately, we already have the infrastructure in place with the
	 * framebuffer deferred I/O driver to schedule the delayed update.
	 */

        spin_lock_irqsave(&data->fb_urb_lock, irq_flags);
	if (likely(!data->fb_vbitmap_busy)) {
		/* Get the usb device to send the image on */
		intf = to_usb_interface(hdev->dev.parent);
		usb_dev = interface_to_usbdev(intf);

		switch (data->panel_type) {
		case GFB_PANEL_TYPE_160_43_1:
			pipe = usb_sndintpipe(usb_dev, 0x02);
			break;
		case GFB_PANEL_TYPE_320_240_16:
			pipe = usb_sndbulkpipe(usb_dev, 0x02);
			break;
		default:
                        spin_unlock_irqrestore(&data->fb_urb_lock, irq_flags);
			return -EINVAL;
		}

		ep = (usb_pipein(pipe) ? usb_dev->ep_in : usb_dev->ep_out)[usb_pipeendpoint(pipe)];

		if (unlikely(!ep)) {
			spin_unlock_irqrestore(&data->fb_urb_lock, irq_flags);
			return -EINVAL;
		}

		switch (data->panel_type) {
		case GFB_PANEL_TYPE_160_43_1:
			usb_fill_int_urb(data->fb_urb, usb_dev, pipe, data->fb_vbitmap, data->vbitmap_size,
				 gfb_fb_urb_completion, data, ep->desc.bInterval);
			break;
		case GFB_PANEL_TYPE_320_240_16:
			usb_fill_bulk_urb(data->fb_urb, usb_dev, pipe, data->fb_vbitmap, data->vbitmap_size,
				 gfb_fb_urb_completion, data);
			break;
		default:
			spin_unlock_irqrestore(&data->fb_urb_lock, irq_flags);
			return -EINVAL;
		}

		data->fb_urb->actual_length = 0;

		retval = usb_submit_urb(data->fb_urb, GFP_NOIO);
		if (unlikely(retval < 0)) {
			/*
			 * We need to unlock the framebuffer urb lock since
			 * the urb submission failed and therefore
			 * g19_fb_urb_completion() won't be called.
			 */
			spin_unlock_irqrestore(&data->fb_urb_lock, irq_flags);
			return retval;
		}

                /* All succeeded - mark the softlock and unlock the spinlock */
                data->fb_vbitmap_busy = 1;
                spin_unlock_irqrestore(&data->fb_urb_lock, irq_flags);
	} else {
                spin_unlock_irqrestore(&data->fb_urb_lock, irq_flags); /* locked before if test */
		schedule_delayed_work(&data->fb_info->deferred_work, data->fb_defio.delay);
	}

	return retval;
}


char hdata[512] = {
0x10, 0x0f, 0x00, 0x58, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3f, 0x01, 0xef, 0x00, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f, 0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8, 0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf, 0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf, 0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xcb, 0xcc, 0xcd, 0xce, 0xcf, 0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xdb, 0xdc, 0xdd, 0xde, 0xdf, 0xe0, 0xe1, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea, 0xeb, 0xec, 0xed, 0xee, 0xef, 0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4a, 0x4b, 0x4c, 0x4d, 0x4e, 0x4f, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e, 0x5f, 0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e, 0x6f, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e, 0x7f, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8, 0xa9, 0xaa, 0xab, 0xac, 0xad, 0xae, 0xaf, 0xb0, 0xb1, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xbb, 0xbc, 0xbd, 0xbe, 0xbf, 0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xcb, 0xcc, 0xcd, 0xce, 0xcf, 0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xdb, 0xdc, 0xdd, 0xde, 0xdf, 0xe0, 0xe1, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea, 0xeb, 0xec, 0xed, 0xee, 0xef, 0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff};

/* Update fb_vbitmap from the screen_base and send to the device */
static void gfb_fb_qvga_update(struct gfb_data *data)
{
	int row;
	int col;
	int x, y;
	u16 *src, *dst;

	/* Clear the vbitmap and set the necessary magic number */
	memset(data->fb_vbitmap, 0x00, data->vbitmap_size);
	memcpy(data->fb_vbitmap, &hdata, sizeof(hdata));

	/* LCD is a portrait mode one so we have to rotate the framebuffer */

	src = (u16 *)data->fb_bitmap;
	dst = (u16 *)(data->fb_vbitmap+512);

	x = data->fb_info->var.xres;
	y = data->fb_info->var.yres;
	for (col = 0; col < x; col++)
		for (row = 0; row < y; row++)
			*dst++ = *(src+col+(row*x));


	/*
	 * Now that we have translated screen_base into a format expected by
	 * the gfb let's send out the vbitmap
	 */
	gfb_fb_send(data);

}

static void gfb_fb_mono_update(struct gfb_data *data)
{
	int row;
	int col;
	int bit;
	int x, y, ll;
	u8 *u;
	size_t offset;
	u8 temp;

	/* Clear the vbitmap and set the necessary magic number */
	memset(data->fb_vbitmap, 0x00, data->vbitmap_size);
	data->fb_vbitmap[0] = 0x03;

	/*
	 * Translate the XBM format screen_base into the format needed by the
	 * G15. This format places the pixels in a vertical rather than
	 * horizontal format. Assuming a grid with 0,0 in the upper left corner
	 * and 159,42 in the lower right corner, the first byte contains the
	 * pixels 0,0 through 0,7 and the second byte contains the pixels 1,0
	 * through 1,7. Within the byte, bit 0 represents 0,0; bit 1 0,1; etc.
	 *
	 * This loop operates in reverse to shift the lower bits into their
	 * respective positions, shifting the lower rows into the higher bits.
	 *
	 * The offset is calculated for every 8 rows and is adjusted by 32 since
	 * that is what the G15 image message expects.
	 */

	x = data->fb_info->var.xres;
	y = data->fb_info->var.yres;
	ll = data->fb_info->fix.line_length;

	for (row = y-1; row >= 0; row--) {
		offset = 32 + row/8 * x;
		u = data->fb_vbitmap + offset;
		/*
		 * Iterate across the screen_base columns to get the
		 * individual bits
		 */
		for (col = 0; col < ll; col++) {
			/*
			 * We will work with a temporary value since we don't
			 * want to modify screen_base as we shift each bit
			 * downward.
			 */
			temp = data->fb_bitmap[row * ll + col];

			/*
			 * For each bit in the pixel row we will shift it onto
			 * the appropriate by by shift the g15 byte up by 1 and
			 * simply doing a bitwise or of the low byte
			 */
			for (bit = 0; bit < 8; bit++) {
				/*Shift the g15 byte up by 1 for this new row*/
				u[bit] <<= 1;
				/* Bring in the new pixel of temp */
				u[bit] |= (temp & 0x01);
				/*
				 * Shift temp down so the low pixel is ready
				 * for the next byte
				 */
				temp >>= 1;
			}

			/*
			 * The last byte represented 8 vertical pixels so we'll
			 * jump ahead 8
			 */
			u += 8;
		}
	}

	/*
	 * Now that we have translated screen_base into a format expected by
	 * the g15 let's send out the vbitmap
	 */
	gfb_fb_send(data);

}

static void gfb_fb_update(struct gfb_data *data)
{
	switch (data->panel_type) {
	case GFB_PANEL_TYPE_160_43_1:
		gfb_fb_mono_update(data);
		break;
	case GFB_PANEL_TYPE_320_240_16:
		gfb_fb_qvga_update(data);
		break;
	default:
		break;
	}
}

/* Callback from deferred IO workqueue */
static void gfb_fb_deferred_io(struct fb_info *info, struct list_head *pagelist)
{
	gfb_fb_update(info->par);
}


/* Blame vfb.c if things go wrong in gfb_fb_setcolreg */

static int gfb_fb_setcolreg(unsigned regno, unsigned red, unsigned green,
			    unsigned blue, unsigned transp,
			    struct fb_info *info)
{
	/* struct gfb_data *par = info->par; */

	if (regno >= 16)
		return 1;

	/* grayscale works only partially under directcolor */
	if (info->var.grayscale) {
		/* grayscale = 0.30*R + 0.59*G + 0.11*B */
		red = green = blue =
		    (red * 77 + green * 151 + blue * 28) >> 8;
	}

	/* Truecolor has hardware independent palette */
	if (info->fix.visual == FB_VISUAL_TRUECOLOR) {
		u32 v;

#define CNVT_TOHW(val,width) ((((val)<<(width))+0x7FFF-(val))>>16)
		red = CNVT_TOHW(red, info->var.red.length);
		green = CNVT_TOHW(green, info->var.green.length);
		blue = CNVT_TOHW(blue, info->var.blue.length);
		transp = CNVT_TOHW(transp, info->var.transp.length);
#undef CNVT_TOHW

		v = (red << info->var.red.offset) |
		    (green << info->var.green.offset) |
		    (blue << info->var.blue.offset) |
		    (transp << info->var.transp.offset);
		switch (info->var.bits_per_pixel) {
		case 8:
			break;
		case 16:
			((u32 *) (info->pseudo_palette))[regno] = v;
			break;
		case 24:
		case 32:
			((u32 *) (info->pseudo_palette))[regno] = v;
			break;
		}
		return 0;
	}

	return 0;
}

/* Stub to call the system default and update the image on the gfb */
static void gfb_fb_fillrect(struct fb_info *info,
			    const struct fb_fillrect *rect)
{
	struct gfb_data *par = info->par;
	sys_fillrect(info, rect);
	gfb_fb_update(par);
}

/* Stub to call the system default and update the image on the gfb */
static void gfb_fb_copyarea(struct fb_info *info,
			    const struct fb_copyarea *area)
{
	struct gfb_data *par = info->par;
	sys_copyarea(info, area);
	gfb_fb_update(par);
}

/* Stub to call the system default and update the image on the gfb */
static void gfb_fb_imageblit(struct fb_info *info, const struct fb_image *image)
{
	struct gfb_data *par = info->par;
	sys_imageblit(info, image);
	gfb_fb_update(par);
}

/*
 * this is the slow path from userspace. they can seek and write to
 * the fb. it's inefficient to do anything less than a full screen draw
 */
static ssize_t gfb_fb_write(struct fb_info *info, const char __user *buf,
			    size_t count, loff_t *ppos)
{
	struct gfb_data *par = info->par;
	ssize_t result;

	result = fb_sys_write(info, buf, count, ppos);
	if (result != -EFAULT && result != -EPERM)
		gfb_fb_update(par);
	return result;
}

static struct fb_ops gfb_ops = {
	.owner = THIS_MODULE,
	.fb_read = fb_sys_read,
	.fb_write = gfb_fb_write,
        .fb_setcolreg = gfb_fb_setcolreg,
	.fb_fillrect  = gfb_fb_fillrect,
	.fb_copyarea  = gfb_fb_copyarea,
	.fb_imageblit = gfb_fb_imageblit,
};

/*
 * The "fb_node" attribute
 */
static ssize_t gfb_fb_node_show(struct device *dev,
				struct device_attribute *attr,
				char *buf)
{
	unsigned fb_node;
	struct gfb_data *data = dev_get_drvdata(dev);

	fb_node = data->fb_info->node;

	return sprintf(buf, "%u\n", fb_node);
}
EXPORT_SYMBOL(gfb_fb_node_show);

/*
 * The "fb_update_rate" attribute
 */
static ssize_t gfb_fb_update_rate_show(struct device *dev,
				       struct device_attribute *attr,
				       char *buf)
{
	unsigned fb_update_rate;
	struct gfb_data *data = dev_get_drvdata(dev);

	fb_update_rate = data->fb_update_rate;

	return sprintf(buf, "%u\n", fb_update_rate);
}
EXPORT_SYMBOL(gfb_fb_update_rate_show);

static ssize_t gfb_set_fb_update_rate(struct hid_device *hdev,
				      unsigned fb_update_rate)
{
	struct gfb_data *data = hid_get_gfbdata(hdev);

	if (fb_update_rate > GFB_UPDATE_RATE_LIMIT)
		data->fb_update_rate = GFB_UPDATE_RATE_LIMIT;
	else if (fb_update_rate == 0)
		data->fb_update_rate = 1;
	else
		data->fb_update_rate = fb_update_rate;

	data->fb_defio.delay = HZ / data->fb_update_rate;

	return 0;
}

static ssize_t gfb_fb_update_rate_store(struct device *dev,
					struct device_attribute *attr,
					const char *buf, size_t count)
{
	struct hid_device *hdev;
	int i;
	unsigned u;
	ssize_t set_result;

	/* Get the hid associated with the device */
	hdev = container_of(dev, struct hid_device, dev);

	/* If we have an invalid pointer we'll return ENODATA */
	if (hdev == NULL || &(hdev->dev) != dev)
		return -ENODATA;

	i = sscanf(buf, "%u", &u);
	if (i != 1) {
		dev_warn(dev, GFB_NAME " unrecognized input: %s", buf);
		return -1;
	}

	set_result = gfb_set_fb_update_rate(hdev, u);

	if (set_result < 0)
		return set_result;

	return count;
}
EXPORT_SYMBOL(gfb_fb_update_rate_store);

static struct fb_deferred_io gfb_fb_defio = {
	.delay = HZ / GFB_UPDATE_RATE_DEFAULT,
	.deferred_io = gfb_fb_deferred_io,
};

static struct gfb_data *gfb_probe(struct hid_device *hdev,
		     const int panel_type)
{
	int error;
	struct gfb_data *data;

	dev_dbg(&hdev->dev, "Logitech GamePanel framebuffer probe...");

	/*
	 * Let's allocate the gfb data structure, set some reasonable
	 * defaults, and associate it with the device
	 */
	data = kzalloc(sizeof(struct gfb_data), GFP_KERNEL);
	if (data == NULL) {
		dev_err(&hdev->dev, "can't allocate space for Logitech GFB device attributes\n");
		error = -ENOMEM;
		goto err_no_cleanup;
	}

	data->fb_info = framebuffer_alloc(0, &hdev->dev);
	if (data->fb_info == NULL) {
		dev_err(&hdev->dev, GFB_NAME " failed to allocate a framebuffer\n");
		goto err_cleanup_data;
	}

	/* init Framebuffer visual structures */

	data->panel_type = panel_type;

	switch (panel_type) {
	case GFB_PANEL_TYPE_160_43_1:
		data->fb_info->fix = (struct fb_fix_screeninfo) {
			.id = "GFB_MONO",
			.type = FB_TYPE_PACKED_PIXELS,
			.visual = FB_VISUAL_MONO01,
			.xpanstep = 0,
			.ypanstep = 0,
			.ywrapstep = 0,
			.line_length = 32,
			.accel = FB_ACCEL_NONE,
		};
		data->fb_info->var = (struct fb_var_screeninfo) {
			.xres = 160,
			.yres = 43,
			.xres_virtual = 160,
			.yres_virtual = 43,
			.bits_per_pixel = 1,
		};
		data->vbitmap_size = 992;
		break;
	case GFB_PANEL_TYPE_320_240_16:
		data->fb_info->fix = (struct fb_fix_screeninfo) {
			.id = "GFB_QVGA",
			.type = FB_TYPE_PACKED_PIXELS,
			.visual = FB_VISUAL_TRUECOLOR,
			.xpanstep = 0,
			.ypanstep = 0,
			.ywrapstep = 0,
			.line_length = 640,
			.accel = FB_ACCEL_NONE,
		};
		data->fb_info->var = (struct fb_var_screeninfo) {
			.xres = 320,
			.yres = 240,
			.xres_virtual = 320,
			.yres_virtual = 240,
			.bits_per_pixel = 16,
			.red        = {11, 5, 0}, /* RGB565 */
			.green      = { 5, 6, 0},
			.blue       = { 0, 5, 0},
			.transp     = { 0, 0, 0},
		};
		data->vbitmap_size = 154112;
		break;
	default:
		dev_err(&hdev->dev, GFB_NAME ": ERROR: unknown panel type\n");
		goto err_cleanup_fb;
	}

        data->fb_info->pseudo_palette = &pseudo_palette;
	data->fb_info->fbops = &gfb_ops;
	data->fb_info->fix.smem_len = data->fb_info->fix.line_length * data->fb_info->var.yres;
	data->fb_info->par = data;
	data->fb_info->flags = FBINFO_FLAG_DEFAULT;

	spin_lock_init(&data->fb_urb_lock);

	data->hdev = hdev;

	data->fb_bitmap = vmalloc(data->fb_info->fix.smem_len);
	if (data->fb_bitmap == NULL) {
		dev_err(&hdev->dev, GFB_NAME ": ERROR: can't get a free page for framebuffer\n");
		error = -ENOMEM;
		goto err_cleanup_data;
	}

	data->fb_vbitmap = kmalloc(sizeof(u8) * data->vbitmap_size, GFP_KERNEL);
	if (data->fb_vbitmap == NULL) {
		dev_err(&hdev->dev, GFB_NAME ": ERROR: can't alloc vbitmap image buffer\n");
		error = -ENOMEM;
		goto err_cleanup_fb_bitmap;
	}
        data->fb_vbitmap_busy = 0;

	data->fb_urb = usb_alloc_urb(0, GFP_KERNEL);
	if (data->fb_urb == NULL) {
		dev_err(&hdev->dev, GFB_NAME ": ERROR: can't alloc usb urb\n");
		error = -ENOMEM;
		goto err_cleanup_fb_vbitmap;
	}

	data->fb_info->screen_base = (char __force __iomem *) data->fb_bitmap;

	data->fb_update_rate = GFB_UPDATE_RATE_DEFAULT;

	dbg_hid(KERN_INFO GFB_NAME " allocated framebuffer\n");

	data->fb_defio = gfb_fb_defio;
	data->fb_info->fbdefio = &data->fb_defio;

	dbg_hid(KERN_INFO GFB_NAME " allocated deferred IO structure\n");

	fb_deferred_io_init(data->fb_info);

	if (register_framebuffer(data->fb_info) < 0)
		goto err_cleanup_fb_deferred;

	return data;


err_cleanup_fb_deferred:
	fb_deferred_io_cleanup(data->fb_info);

err_cleanup_fb_urb:
	usb_free_urb(data->fb_urb);

err_cleanup_fb_vbitmap:
	kfree(data->fb_vbitmap);

err_cleanup_fb_bitmap:
	vfree(data->fb_bitmap);

err_cleanup_fb:
	framebuffer_release(data->fb_info);

err_cleanup_data:
	kfree(data);

err_no_cleanup:


	return 0;
}
EXPORT_SYMBOL(gfb_probe);

static void gfb_remove(struct gfb_data *data)
{
	/* Clean up the framebuffer */
	fb_deferred_io_cleanup(data->fb_info);
	unregister_framebuffer(data->fb_info);
	framebuffer_release(data->fb_info);
	vfree(data->fb_bitmap);
	kfree(data->fb_vbitmap);
	usb_free_urb(data->fb_urb);
}
EXPORT_SYMBOL(gfb_remove);

MODULE_DESCRIPTION("Logitech GFB HID Driver");
MODULE_AUTHOR("Rick L Vinyard Jr (rvinyard@cs.nmsu.edu)");
MODULE_AUTHOR("Alistair Buxton (a.j.buxton@gmail.com)");
MODULE_LICENSE("GPL");
