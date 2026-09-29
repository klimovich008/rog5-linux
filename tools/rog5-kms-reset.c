// SPDX-License-Identifier: GPL-2.0-only
/*
 * rog5-kms-reset: turn every plane, CRTC and connector of a DRM device off
 * in one atomic commit, so the next compositor starts from a clean state.
 *
 * mutter (GNOME) does not detach planes that a previous DRM master left on
 * a CRTC it does not use: after Phosh/phoc, plane-0 stayed bound to the
 * panel CRTC and every GNOME frame on the external display that reused it
 * failed with "switching CRTC directly" (EINVAL). Run between compositors,
 * as root, while no other process is DRM master.
 *
 * Build: cc -O2 -o rog5-kms-reset rog5-kms-reset.c $(pkg-config --cflags --libs libdrm)
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

static uint32_t prop_id(int fd, uint32_t obj, uint32_t type, const char *name)
{
	drmModeObjectProperties *props = drmModeObjectGetProperties(fd, obj, type);
	uint32_t id = 0;

	if (!props)
		return 0;
	for (uint32_t i = 0; i < props->count_props && !id; i++) {
		drmModePropertyRes *p = drmModeGetProperty(fd, props->props[i]);

		if (p && !strcmp(p->name, name))
			id = p->prop_id;
		drmModeFreeProperty(p);
	}
	drmModeFreeObjectProperties(props);
	return id;
}

static int add(drmModeAtomicReq *req, int fd, uint32_t obj, uint32_t type,
	       const char *name, uint64_t value)
{
	uint32_t id = prop_id(fd, obj, type, name);

	return id ? drmModeAtomicAddProperty(req, obj, id, value) : 0;
}

int main(int argc, char **argv)
{
	const char *path = argc > 1 ? argv[1] : "/dev/dri/card1";
	int fd = open(path, O_RDWR | O_CLOEXEC);
	drmModeAtomicReq *req;
	drmModePlaneRes *planes;
	drmModeRes *res;
	int ret;

	if (fd < 0) {
		perror(path);
		return 1;
	}
	if (drmSetMaster(fd)) {
		fprintf(stderr, "%s: cannot become DRM master (another compositor running?): %s\n",
			path, strerror(errno));
		return 1;
	}
	if (drmSetClientCap(fd, DRM_CLIENT_CAP_UNIVERSAL_PLANES, 1) ||
	    drmSetClientCap(fd, DRM_CLIENT_CAP_ATOMIC, 1)) {
		fprintf(stderr, "%s: no atomic modesetting\n", path);
		return 1;
	}
	res = drmModeGetResources(fd);
	planes = drmModeGetPlaneResources(fd);
	if (!res || !planes) {
		fprintf(stderr, "%s: cannot read KMS resources\n", path);
		return 1;
	}
	req = drmModeAtomicAlloc();
	for (uint32_t i = 0; i < planes->count_planes; i++) {
		add(req, fd, planes->planes[i], DRM_MODE_OBJECT_PLANE, "FB_ID", 0);
		add(req, fd, planes->planes[i], DRM_MODE_OBJECT_PLANE, "CRTC_ID", 0);
	}
	for (int i = 0; i < res->count_connectors; i++)
		add(req, fd, res->connectors[i], DRM_MODE_OBJECT_CONNECTOR, "CRTC_ID", 0);
	for (int i = 0; i < res->count_crtcs; i++) {
		add(req, fd, res->crtcs[i], DRM_MODE_OBJECT_CRTC, "ACTIVE", 0);
		add(req, fd, res->crtcs[i], DRM_MODE_OBJECT_CRTC, "MODE_ID", 0);
	}
	ret = drmModeAtomicCommit(fd, req, DRM_MODE_ATOMIC_ALLOW_MODESET, NULL);
	if (ret)
		fprintf(stderr, "%s: reset commit failed: %s\n", path, strerror(errno));
	else
		printf("%s: %u planes, %d CRTCs, %d connectors off\n", path,
		       planes->count_planes, res->count_crtcs, res->count_connectors);
	drmModeAtomicFree(req);
	drmDropMaster(fd);
	close(fd);
	return ret ? 1 : 0;
}
