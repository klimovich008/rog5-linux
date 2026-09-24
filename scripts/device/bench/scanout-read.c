/*
 * Read the framebuffer DSI-1 is scanning out and write it as raw RGBA.
 *
 * The compositor's buffers are UBWC-compressed (DRM_FORMAT_MOD_QCOM_COMPRESSED),
 * which the CPU cannot decode, so the buffer is imported into EGL (surfaceless
 * Mesa platform, render node) with its modifier, attached to an FBO and read
 * back with glReadPixels: the GPU does the decompression. Root only: GETFB2
 * hands out buffer handles to CAP_SYS_ADMIN.
 *
 *   scanout-read OUT.rgba    prints "width height" on success
 *
 * Build: gcc -O2 -o scanout-read scanout-read.c -lEGL -lGLESv2
 */
#define EGL_EGLEXT_PROTOTYPES
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <drm/drm.h>
#include <drm/drm_mode.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static int die(const char *what)
{
	fprintf(stderr, "scanout-read: %s\n", what);
	return 1;
}

static int active_fb(int card, uint32_t *fb_id)
{
	struct drm_set_client_cap cap = { DRM_CLIENT_CAP_UNIVERSAL_PLANES, 1 };
	struct drm_mode_get_plane_res res = { 0 };
	uint32_t ids[64];

	if (ioctl(card, DRM_IOCTL_SET_CLIENT_CAP, &cap) ||
	    ioctl(card, DRM_IOCTL_MODE_GETPLANERESOURCES, &res) || res.count_planes > 64)
		return -1;
	res.plane_id_ptr = (uintptr_t)ids;
	if (ioctl(card, DRM_IOCTL_MODE_GETPLANERESOURCES, &res))
		return -1;
	for (uint32_t i = 0; i < res.count_planes; i++) {
		struct drm_mode_get_plane plane = { .plane_id = ids[i] };

		if (!ioctl(card, DRM_IOCTL_MODE_GETPLANE, &plane) && plane.crtc_id && plane.fb_id) {
			*fb_id = plane.fb_id;
			return 0;
		}
	}
	return -1;
}

int main(int argc, char **argv)
{
	struct drm_mode_fb_cmd2 fb = { 0 };
	struct drm_prime_handle prime = { 0 };
	int card, dmabuf;

	if (argc != 2)
		return die("usage: scanout-read OUT.rgba");
	card = open("/dev/dri/card1", O_RDWR | O_CLOEXEC);
	if (card < 0 || active_fb(card, &fb.fb_id))
		return die("no plane is scanning out (display off?)");
	if (ioctl(card, DRM_IOCTL_MODE_GETFB2, &fb) || !fb.handles[0])
		return die("GETFB2 failed (not root?)");
	prime.handle = fb.handles[0];
	prime.flags = DRM_CLOEXEC;
	if (ioctl(card, DRM_IOCTL_PRIME_HANDLE_TO_FD, &prime))
		return die("PRIME export failed");
	dmabuf = prime.fd;

	EGLDisplay dpy = eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
	EGLint major, minor;
	if (dpy == EGL_NO_DISPLAY || !eglInitialize(dpy, &major, &minor) || !eglBindAPI(EGL_OPENGL_ES_API))
		return die("EGL init failed");
	const EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
	EGLContext ctx = eglCreateContext(dpy, EGL_NO_CONFIG_KHR, EGL_NO_CONTEXT, ctx_attr);
	if (ctx == EGL_NO_CONTEXT || !eglMakeCurrent(dpy, EGL_NO_SURFACE, EGL_NO_SURFACE, ctx))
		return die("EGL context failed");

	const EGLAttrib img_attr[] = {
		EGL_WIDTH, fb.width, EGL_HEIGHT, fb.height,
		EGL_LINUX_DRM_FOURCC_EXT, fb.pixel_format,
		EGL_DMA_BUF_PLANE0_FD_EXT, dmabuf,
		EGL_DMA_BUF_PLANE0_OFFSET_EXT, fb.offsets[0],
		EGL_DMA_BUF_PLANE0_PITCH_EXT, fb.pitches[0],
		EGL_DMA_BUF_PLANE0_MODIFIER_LO_EXT, (EGLAttrib)(fb.modifier[0] & 0xffffffff),
		EGL_DMA_BUF_PLANE0_MODIFIER_HI_EXT, (EGLAttrib)(fb.modifier[0] >> 32),
		EGL_NONE,
	};
	EGLImage img = eglCreateImage(dpy, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, NULL, img_attr);
	if (img == EGL_NO_IMAGE)
		return die("dma-buf import failed");

	GLuint tex, fbo;
	glGenTextures(1, &tex);
	glBindTexture(GL_TEXTURE_2D, tex);
	PFNGLEGLIMAGETARGETTEXTURE2DOESPROC target_texture =
		(PFNGLEGLIMAGETARGETTEXTURE2DOESPROC)eglGetProcAddress("glEGLImageTargetTexture2DOES");
	if (!target_texture)
		return die("glEGLImageTargetTexture2DOES unavailable");
	target_texture(GL_TEXTURE_2D, (GLeglImageOES)img);
	glGenFramebuffers(1, &fbo);
	glBindFramebuffer(GL_FRAMEBUFFER, fbo);
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0);
	if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
		return die("framebuffer incomplete");

	size_t size = (size_t)fb.width * fb.height * 4;
	uint8_t *pixels = malloc(size);
	if (!pixels)
		return die("out of memory");
	glReadPixels(0, 0, fb.width, fb.height, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
	if (glGetError() != GL_NO_ERROR)
		return die("glReadPixels failed");

	FILE *out = fopen(argv[1], "wb");
	if (!out || fwrite(pixels, 1, size, out) != size || fclose(out))
		return die("write failed");
	printf("%u %u\n", fb.width, fb.height);
	return 0;
}
