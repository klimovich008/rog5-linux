// SPDX-License-Identifier: GPL-2.0-only
/*
 * rog5-kms-grab: save the framebuffer a KMS plane is scanning out as a PPM,
 * for checking what an external display shows without a screenshot API
 * (GNOME denies org.gnome.Shell.Screenshot to other clients). Root only.
 *
 * Usage: rog5-kms-grab <plane-id> <out.ppm> [/dev/dri/cardN]
 * Handles linear 8888 and 2101010 RGB buffers only; prints the
 * modifier and exits 2 for anything else (e.g. UBWC-compressed buffers).
 *
 * Build: cc -O2 -o rog5-kms-grab rog5-kms-grab.c $(pkg-config --cflags --libs libdrm)
 */
#include <drm_fourcc.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

int main(int argc, char **argv)
{
	const char *path = argc > 3 ? argv[3] : "/dev/dri/card1";
	uint32_t plane_id;
	drmModePlane *plane;
	drmModeFB2 *fb;
	int fd, dmabuf;
	uint8_t *map;
	size_t size;
	FILE *out;
	int bgr, ten = 0;

	if (argc < 3) {
		fprintf(stderr, "usage: %s <plane-id> <out.ppm> [card]\n", argv[0]);
		return 1;
	}
	plane_id = strtoul(argv[1], NULL, 0);
	fd = open(path, O_RDWR | O_CLOEXEC);
	if (fd < 0 || drmSetClientCap(fd, DRM_CLIENT_CAP_UNIVERSAL_PLANES, 1)) {
		perror(path);
		return 1;
	}
	plane = drmModeGetPlane(fd, plane_id);
	if (!plane || !plane->fb_id) {
		fprintf(stderr, "plane %u has no framebuffer\n", plane_id);
		return 1;
	}
	fb = drmModeGetFB2(fd, plane->fb_id);
	if (!fb || !fb->handles[0]) {
		fprintf(stderr, "fb %u: no handle (need root): %s\n", plane->fb_id, strerror(errno));
		return 1;
	}
	printf("plane %u fb %u %ux%u format %.4s modifier 0x%llx pitch %u\n", plane_id,
	       fb->fb_id, fb->width, fb->height, (char *)&fb->pixel_format,
	       (unsigned long long)fb->modifier, fb->pitches[0]);
	if (fb->modifier != DRM_FORMAT_MOD_LINEAR && fb->modifier != DRM_FORMAT_MOD_INVALID)
		return 2;
	switch (fb->pixel_format) {
	case DRM_FORMAT_XRGB8888: case DRM_FORMAT_ARGB8888: bgr = 1; break;
	case DRM_FORMAT_XBGR8888: case DRM_FORMAT_ABGR8888: bgr = 0; break;
	case DRM_FORMAT_XRGB2101010: case DRM_FORMAT_ARGB2101010: bgr = 1; ten = 1; break;
	case DRM_FORMAT_XBGR2101010: case DRM_FORMAT_ABGR2101010: bgr = 0; ten = 1; break;
	default: return 2;
	}
	if (drmPrimeHandleToFD(fd, fb->handles[0], DRM_CLOEXEC | DRM_RDWR, &dmabuf)) {
		perror("prime export");
		return 1;
	}
	size = (size_t)fb->pitches[0] * fb->height + fb->offsets[0];
	map = mmap(NULL, size, PROT_READ, MAP_SHARED, dmabuf, 0);
	if (map == MAP_FAILED) {
		perror("mmap dmabuf");
		return 1;
	}
	out = fopen(argv[2], "wb");
	if (!out) {
		perror(argv[2]);
		return 1;
	}
	fprintf(out, "P6\n%u %u\n255\n", fb->width, fb->height);
	for (uint32_t y = 0; y < fb->height; y++) {
		const uint8_t *row = map + fb->offsets[0] + (size_t)y * fb->pitches[0];

		for (uint32_t x = 0; x < fb->width; x++) {
			const uint8_t *p = row + 4 * x;
			uint8_t rgb[3] = { bgr ? p[2] : p[0], p[1], bgr ? p[0] : p[2] };

			if (ten) {
				uint32_t v = p[0] | p[1] << 8 | p[2] << 16 | (uint32_t)p[3] << 24;
				uint8_t hi = v >> 22 & 0xff, mid = v >> 12 & 0xff, lo = v >> 2 & 0xff;

				rgb[0] = bgr ? hi : lo;
				rgb[1] = mid;
				rgb[2] = bgr ? lo : hi;
			}

			fwrite(rgb, 1, 3, out);
		}
	}
	fclose(out);
	return 0;
}
