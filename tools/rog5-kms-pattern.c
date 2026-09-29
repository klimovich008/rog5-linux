// SPDX-License-Identifier: GPL-2.0-only
/*
 * rog5-kms-pattern: light a connector with a linear dumb-buffer colour-bar
 * pattern in a chosen format and page-flip it for a while, to check whether
 * the display engine can scan that format out (the DPU underrun counter in
 * debugfs core_irq, IRQ [0, 24] for INTF_0 on SM8350, tells). Run as root
 * with no compositor holding DRM master.
 *
 * Usage: rog5-kms-pattern <connector-name> <W>x<H> <XR24|XR30> <seconds> [/dev/dri/cardN]
 *
 * Build: cc -O2 -o rog5-kms-pattern rog5-kms-pattern.c $(pkg-config --cflags --libs libdrm)
 */
#include <drm_fourcc.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

struct buf { uint32_t handle, pitch, fb; uint64_t size; uint8_t *map; };

static uint32_t prop(int fd, uint32_t obj, uint32_t type, const char *name)
{
	drmModeObjectProperties *props = drmModeObjectGetProperties(fd, obj, type);
	uint32_t id = 0;

	for (uint32_t i = 0; props && i < props->count_props && !id; i++) {
		drmModePropertyRes *p = drmModeGetProperty(fd, props->props[i]);

		if (p && !strcmp(p->name, name))
			id = p->prop_id;
		drmModeFreeProperty(p);
	}
	drmModeFreeObjectProperties(props);
	return id;
}

static int make_buf(int fd, struct buf *b, uint32_t w, uint32_t h, uint32_t fourcc, int shift)
{
	struct drm_mode_create_dumb c = { .width = w, .height = h, .bpp = 32 };
	struct drm_mode_map_dumb m = { 0 };
	uint32_t handles[4] = { 0 }, pitches[4] = { 0 }, offsets[4] = { 0 };
	static const uint32_t bars[8][3] = {
		{255, 255, 255}, {255, 255, 0}, {0, 255, 255}, {0, 255, 0},
		{255, 0, 255}, {255, 0, 0}, {0, 0, 255}, {0, 0, 0} };

	if (drmIoctl(fd, DRM_IOCTL_MODE_CREATE_DUMB, &c))
		return -1;
	b->handle = c.handle; b->pitch = c.pitch; b->size = c.size;
	m.handle = c.handle;
	if (drmIoctl(fd, DRM_IOCTL_MODE_MAP_DUMB, &m))
		return -1;
	b->map = mmap(NULL, c.size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, m.offset);
	if (b->map == MAP_FAILED)
		return -1;
	for (uint32_t y = 0; y < h; y++) {
		uint32_t *row = (uint32_t *)(b->map + (size_t)y * c.pitch);

		for (uint32_t x = 0; x < w; x++) {
			const uint32_t *rgb = bars[((x * 8 / w) + shift) % 8];

			if (fourcc == DRM_FORMAT_XRGB2101010)
				row[x] = (rgb[0] * 1023 / 255) << 20 | (rgb[1] * 1023 / 255) << 10 |
					 (rgb[2] * 1023 / 255);
			else
				row[x] = rgb[0] << 16 | rgb[1] << 8 | rgb[2];
		}
	}
	handles[0] = c.handle; pitches[0] = c.pitch;
	return drmModeAddFB2(fd, w, h, fourcc, handles, pitches, offsets, &b->fb, 0);
}

int main(int argc, char **argv)
{
	const char *path = argc > 5 ? argv[5] : "/dev/dri/card1";
	uint32_t w, h, fourcc, conn_id = 0, crtc_id = 0, plane_id = 0, blob, crtc_index = 0;
	drmModeModeInfo *mode = NULL;
	drmModeConnector *conn = NULL;
	struct buf bufs[2];
	drmModePlaneRes *pr;
	drmModeRes *res;
	int fd, secs, flips = 0;
	time_t end;

	if (argc < 5 || sscanf(argv[2], "%ux%u", &w, &h) != 2) {
		fprintf(stderr, "usage: %s <connector> <W>x<H> <XR24|XR30> <seconds> [card]\n", argv[0]);
		return 1;
	}
	fourcc = !strcmp(argv[3], "XR30") ? DRM_FORMAT_XRGB2101010 : DRM_FORMAT_XRGB8888;
	secs = atoi(argv[4]);
	fd = open(path, O_RDWR | O_CLOEXEC);
	if (fd < 0 || drmSetMaster(fd) || drmSetClientCap(fd, DRM_CLIENT_CAP_UNIVERSAL_PLANES, 1) ||
	    drmSetClientCap(fd, DRM_CLIENT_CAP_ATOMIC, 1)) {
		fprintf(stderr, "%s: open/master/atomic failed: %s\n", path, strerror(errno));
		return 1;
	}
	res = drmModeGetResources(fd);
	for (int i = 0; res && i < res->count_connectors && !conn_id; i++) {
		drmModeConnector *c = drmModeGetConnector(fd, res->connectors[i]);
		char name[32];

		snprintf(name, sizeof(name), "%s-%u", drmModeGetConnectorTypeName(c->connector_type),
			 c->connector_type_id);
		if (!strcmp(name, argv[1])) {
			conn = c;
			conn_id = c->connector_id;
		} else {
			drmModeFreeConnector(c);
		}
	}
	if (!conn_id) {
		fprintf(stderr, "connector %s not found\n", argv[1]);
		return 1;
	}
	for (int i = 0; i < conn->count_modes && !mode; i++)
		if (conn->modes[i].hdisplay == w && conn->modes[i].vdisplay == h &&
		    conn->modes[i].vrefresh == 60)
			mode = &conn->modes[i];
	if (!mode) {
		fprintf(stderr, "no %ux%u@60 mode\n", w, h);
		return 1;
	}
	crtc_id = res->crtcs[0];
	pr = drmModeGetPlaneResources(fd);
	for (uint32_t i = 0; i < pr->count_planes && !plane_id; i++) {
		drmModePlane *p = drmModeGetPlane(fd, pr->planes[i]);

		if (p->possible_crtcs & (1u << crtc_index))
			for (uint32_t f = 0; f < p->count_formats; f++)
				if (p->formats[f] == fourcc)
					plane_id = p->plane_id;
		drmModeFreePlane(p);
	}
	if (!plane_id) {
		fprintf(stderr, "no plane with %s\n", argv[3]);
		return 1;
	}
	if (make_buf(fd, &bufs[0], w, h, fourcc, 0) || make_buf(fd, &bufs[1], w, h, fourcc, 1)) {
		fprintf(stderr, "buffer: %s\n", strerror(errno));
		return 1;
	}
	drmModeCreatePropertyBlob(fd, mode, sizeof(*mode), &blob);
	printf("%s %ux%u@%u %s on crtc %u plane %u\n", argv[1], w, h, mode->vrefresh, argv[3],
	       crtc_id, plane_id);
	end = time(NULL) + secs;
	for (int i = 0; time(NULL) < end; i++) {
		drmModeAtomicReq *req = drmModeAtomicAlloc();
		uint32_t flags = DRM_MODE_PAGE_FLIP_EVENT;
		struct buf *b = &bufs[i & 1];

		if (i == 0) {
			flags = DRM_MODE_ATOMIC_ALLOW_MODESET | DRM_MODE_PAGE_FLIP_EVENT;
			drmModeAtomicAddProperty(req, conn_id, prop(fd, conn_id, DRM_MODE_OBJECT_CONNECTOR, "CRTC_ID"), crtc_id);
			drmModeAtomicAddProperty(req, crtc_id, prop(fd, crtc_id, DRM_MODE_OBJECT_CRTC, "MODE_ID"), blob);
			drmModeAtomicAddProperty(req, crtc_id, prop(fd, crtc_id, DRM_MODE_OBJECT_CRTC, "ACTIVE"), 1);
			drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "CRTC_ID"), crtc_id);
			drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "SRC_X"), 0);
			drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "SRC_Y"), 0);
			drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "SRC_W"), (uint64_t)w << 16);
			drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "SRC_H"), (uint64_t)h << 16);
			drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "CRTC_X"), 0);
			drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "CRTC_Y"), 0);
			drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "CRTC_W"), w);
			drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "CRTC_H"), h);
		}
		drmModeAtomicAddProperty(req, plane_id, prop(fd, plane_id, DRM_MODE_OBJECT_PLANE, "FB_ID"), b->fb);
		if (drmModeAtomicCommit(fd, req, flags, NULL)) {
			fprintf(stderr, "commit %d failed: %s\n", i, strerror(errno));
			return 1;
		}
		drmModeAtomicFree(req);
		{
			struct pollfd pfd = { .fd = fd, .events = POLLIN };
			char ev[1024];

			if (poll(&pfd, 1, 1000) > 0 && read(fd, ev, sizeof(ev)) > 0)
				flips++;
		}
	}
	printf("%d flips\n", flips);
	drmDropMaster(fd);
	return 0;
}
