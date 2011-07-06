#define GFB_PANEL_TYPE_160_43_1		0
#define GFB_PANEL_TYPE_320_240_16	1

/* Per device data structure */
struct gfb_data {
	struct hid_device *hdev;

	/* Framebuffer stuff */
	int panel_type;

	int vbitmap_size;

	u8 fb_update_rate;
	u8 *fb_vbitmap;
	u8 *fb_bitmap;
	struct fb_info *fb_info;
	struct fb_deferred_io fb_defio;
	struct urb *fb_urb;
	spinlock_t fb_urb_lock;
        int fb_vbitmap_busy;
};

static ssize_t gfb_fb_node_show(struct device *dev,
				struct device_attribute *attr,
				char *buf);

static ssize_t gfb_fb_update_rate_show(struct device *dev,
				       struct device_attribute *attr,
				       char *buf);

static ssize_t gfb_fb_update_rate_store(struct device *dev,
					struct device_attribute *attr,
					const char *buf, size_t count);

static struct gfb_data *gfb_probe(struct hid_device *hdev, const int panel_type);

static void gfb_remove(struct gfb_data *data);

