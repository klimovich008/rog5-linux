/* Bounded diagnostic client for the owned single-output Wayland VM only.
 * Generate wlr-screencopy-client-protocol.h and protocol code with
 * wayland-scanner from pinned wlr-screencopy-unstable-v1.xml. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define MAX_BYTES (8U * 1024U * 1024U)
struct pixels {
    uint32_t format, width, height, stride, flags;
    int offered, flags_seen, copying, ready, failed;
};

/* These functions are also compiled directly by the offline semantic tests.
 * wl_shm ARGB8888=0 and XRGB8888=1 have native-endian 0xAARRGGBB words. */
int capture_offer(struct pixels *p, uint32_t format, uint32_t width,
                  uint32_t height, uint32_t stride)
{
    if (p->offered || p->copying || p->failed || format > 1 || !width || !height ||
        width > 540 || height > 1224 || stride < width * 4 || stride % 4 ||
        (uint64_t)stride * height > MAX_BYTES) {
        p->failed = 1;
        return -1;
    }
    p->format = format; p->width = width; p->height = height; p->stride = stride;
    p->offered = 1;
    return 0;
}

int capture_flags(struct pixels *p, uint32_t flags)
{
    if (!p->copying || p->flags_seen || p->ready || p->failed || (flags & ~1U)) {
        p->failed = 1;
        return -1;
    }
    p->flags = flags; p->flags_seen = 1;
    return 0;
}

int capture_ready(struct pixels *p, uint32_t nanoseconds)
{
    if (!p->copying || !p->flags_seen || p->ready || p->failed || nanoseconds >= 1000000000U) {
        p->failed = 1;
        return -1;
    }
    p->ready = 1;
    return 0;
}

int capture_write_ppm(struct pixels *p, const void *data, int fd)
{
    if (!p->ready || p->failed || !data) return -1;
    char header[64];
    int n = snprintf(header, sizeof(header), "P6\n%u %u\n255\n", p->width, p->height);
    if (write(fd, header, (size_t)n) != n) return -1;
    unsigned char row[540 * 3];
    for (uint32_t y = 0; y < p->height; y++) {
        uint32_t source_y = p->flags & 1 ? p->height - 1 - y : y;
        const unsigned char *source = (const unsigned char *)data + source_y * p->stride;
        for (uint32_t x = 0; x < p->width; x++) {
            uint32_t word;
            memcpy(&word, source + x * 4, sizeof(word));
            row[x * 3] = word >> 16;
            row[x * 3 + 1] = word >> 8;
            row[x * 3 + 2] = word;
        }
        size_t size = p->width * 3;
        if (write(fd, row, size) != (ssize_t)size) return -1;
    }
    return 0;
}

#ifndef SCREENCOPY_TEST
#include <wayland-client.h>
#include "wlr-screencopy-client-protocol.h"

struct capture {
    struct pixels pixels;
    struct wl_display *display;
    struct wl_registry *registry;
    struct wl_output *output;
    struct wl_shm *shm;
    struct zwlr_screencopy_manager_v1 *manager;
    struct zwlr_screencopy_frame_v1 *frame;
    struct wl_buffer *buffer;
    void *map;
    size_t size;
    unsigned int outputs, version;
    int sync_done;
};
static const char *partial_output;

static void expired(int signal_number)
{
    (void)signal_number;
    if (partial_output) unlink(partial_output);
    static const char message[] = "screencopy: five-second deadline exceeded\n";
    (void)write(STDERR_FILENO, message, sizeof(message) - 1);
    _exit(124);
}

static int64_t milliseconds(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) return -1;
    return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static void global(void *data, struct wl_registry *registry, uint32_t name,
                   const char *interface, uint32_t version)
{
    struct capture *c = data;
    if (!strcmp(interface, wl_output_interface.name)) {
        c->outputs++;
        if (!c->output) c->output = wl_registry_bind(registry, name, &wl_output_interface, 1);
    } else if (!strcmp(interface, wl_shm_interface.name)) {
        if (c->shm) c->pixels.failed = 1;
        else c->shm = wl_registry_bind(registry, name, &wl_shm_interface, 1);
    } else if (!strcmp(interface, zwlr_screencopy_manager_v1_interface.name)) {
        if (c->manager) c->pixels.failed = 1;
        else {
            c->version = version < 3 ? version : 3;
            c->manager = wl_registry_bind(registry, name, &zwlr_screencopy_manager_v1_interface, c->version);
        }
    }
}
static void global_remove(void *data, struct wl_registry *registry, uint32_t name)
{
    (void)registry; (void)name;
    ((struct capture *)data)->pixels.failed = 1;
}
static const struct wl_registry_listener registry_listener = {global, global_remove};

static void copy(struct capture *c)
{
    struct pixels *p = &c->pixels;
    if (!p->offered || p->copying || p->failed) { p->failed = 1; return; }
    c->size = (size_t)p->stride * p->height;
    int fd = memfd_create("rog5-vm-screencopy", MFD_CLOEXEC | MFD_ALLOW_SEALING);
    if (fd < 0) { p->failed = 1; return; }
    if (ftruncate(fd, (off_t)c->size) || fcntl(fd, F_ADD_SEALS, F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL)) {
        close(fd); p->failed = 1; return;
    }
    c->map = mmap(NULL, c->size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (c->map == MAP_FAILED) { c->map = NULL; close(fd); p->failed = 1; return; }
    struct wl_shm_pool *pool = wl_shm_create_pool(c->shm, fd, (int)c->size);
    close(fd);
    if (!pool) { p->failed = 1; return; }
    c->buffer = wl_shm_pool_create_buffer(pool, 0, (int)p->width, (int)p->height,
                                          (int)p->stride, p->format);
    wl_shm_pool_destroy(pool);
    if (!c->buffer) { p->failed = 1; return; }
    p->copying = 1;
    zwlr_screencopy_frame_v1_copy(c->frame, c->buffer);
}
static void buffer(void *data, struct zwlr_screencopy_frame_v1 *frame,
                   uint32_t format, uint32_t width, uint32_t height, uint32_t stride)
{
    (void)frame;
    struct capture *c = data;
    if (!capture_offer(&c->pixels, format, width, height, stride) && c->version < 3) copy(c);
}
static void flags(void *data, struct zwlr_screencopy_frame_v1 *frame, uint32_t value)
{
    (void)frame; capture_flags(&((struct capture *)data)->pixels, value);
}
static void ready(void *data, struct zwlr_screencopy_frame_v1 *frame,
                  uint32_t hi, uint32_t lo, uint32_t ns)
{
    (void)frame; (void)hi; (void)lo;
    capture_ready(&((struct capture *)data)->pixels, ns);
}
static void failed(void *data, struct zwlr_screencopy_frame_v1 *frame)
{
    (void)frame; ((struct capture *)data)->pixels.failed = 1;
}
static void damage(void *data, struct zwlr_screencopy_frame_v1 *frame,
                   uint32_t x, uint32_t y, uint32_t width, uint32_t height)
{
    (void)data; (void)frame; (void)x; (void)y; (void)width; (void)height;
}
static void dmabuf(void *data, struct zwlr_screencopy_frame_v1 *frame,
                   uint32_t format, uint32_t width, uint32_t height)
{
    (void)data; (void)frame; (void)format; (void)width; (void)height;
}
static void buffer_done(void *data, struct zwlr_screencopy_frame_v1 *frame)
{
    (void)frame; copy(data);
}
static const struct zwlr_screencopy_frame_v1_listener frame_listener = {
    buffer, flags, ready, failed, damage, dmabuf, buffer_done
};
static void synced(void *data, struct wl_callback *callback, uint32_t serial)
{
    (void)serial; ((struct capture *)data)->sync_done = 1;
    wl_callback_destroy(callback);
}
static const struct wl_callback_listener sync_listener = {synced};

static int pump(struct capture *c, int64_t deadline, int *done)
{
    while (!*done && !c->pixels.failed) {
        while (wl_display_prepare_read(c->display)) {
            if (wl_display_dispatch_pending(c->display) < 0) return -1;
            if (*done || c->pixels.failed) return c->pixels.failed ? -1 : 0;
        }
        int events = POLLIN;
        if (wl_display_flush(c->display) < 0) {
            if (errno != EAGAIN) { wl_display_cancel_read(c->display); return -1; }
            events |= POLLOUT;
        }
        int64_t remaining = deadline - milliseconds();
        if (remaining <= 0) { wl_display_cancel_read(c->display); errno = ETIMEDOUT; return -1; }
        struct pollfd pollfd = {wl_display_get_fd(c->display), (short)events, 0};
        int result = poll(&pollfd, 1, (int)remaining);
        if (result <= 0 || (pollfd.revents & (POLLERR | POLLHUP | POLLNVAL))) {
            wl_display_cancel_read(c->display);
            if (result < 0 && errno == EINTR) continue;
            return -1;
        }
        if (pollfd.revents & POLLIN) {
            if (wl_display_read_events(c->display) < 0) return -1;
        } else wl_display_cancel_read(c->display);
        if (wl_display_dispatch_pending(c->display) < 0) return -1;
    }
    return c->pixels.failed ? -1 : 0;
}

int main(int argc, char **argv)
{
    const char *display_name = getenv("WAYLAND_DISPLAY");
    if (argc != 2 || !display_name || !*display_name || getenv("WAYLAND_SOCKET")) {
        fprintf(stderr, "usage: WAYLAND_DISPLAY=owned-vm-socket screencopy NEW_OUTPUT.ppm (no WAYLAND_SOCKET)\n");
        return 2;
    }
    struct sigaction action = {.sa_handler = expired};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL)) return 1;
    alarm(5);
    int64_t deadline = milliseconds() + 5000;
    struct capture c = {0};
    int result = 1, output_fd = -1;
    c.display = wl_display_connect(display_name);
    if (!c.display) goto cleanup;
    c.registry = wl_display_get_registry(c.display);
    if (!c.registry) goto cleanup;
    wl_registry_add_listener(c.registry, &registry_listener, &c);
    struct wl_callback *callback = wl_display_sync(c.display);
    if (!callback) goto cleanup;
    wl_callback_add_listener(callback, &sync_listener, &c);
    if (pump(&c, deadline, &c.sync_done)) goto cleanup;
    if (c.outputs != 1 || !c.output || !c.shm || !c.manager) {
        fprintf(stderr, "screencopy: requires exactly one output, wl_shm and screencopy manager\n");
        goto cleanup;
    }
    c.frame = zwlr_screencopy_manager_v1_capture_output(c.manager, 0, c.output);
    if (!c.frame) goto cleanup;
    zwlr_screencopy_frame_v1_add_listener(c.frame, &frame_listener, &c);
    if (pump(&c, deadline, &c.pixels.ready)) goto cleanup;
    output_fd = open(argv[1], O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (output_fd < 0) goto cleanup;
    partial_output = argv[1];
    if (capture_write_ppm(&c.pixels, c.map, output_fd) || fsync(output_fd)) goto cleanup;
    if (close(output_fd)) { output_fd = -1; goto cleanup; }
    output_fd = -1;
    printf("{\"status\":\"PASS\",\"width\":%u,\"height\":%u,\"stride\":%u,\"wl_shm_format\":%u,\"y_invert\":%s,\"capture\":\"native-wayland-screencopy\",\"encoding\":\"P6-RGB\"}\n",
           c.pixels.width, c.pixels.height, c.pixels.stride, c.pixels.format,
           c.pixels.flags & 1 ? "true" : "false");
    if (fflush(stdout)) goto cleanup;
    result = 0;
cleanup:
    if (output_fd >= 0) close(output_fd);
    if (result && partial_output) unlink(partial_output);
    partial_output = NULL;
    if (c.frame) zwlr_screencopy_frame_v1_destroy(c.frame);
    if (c.buffer) wl_buffer_destroy(c.buffer);
    if (c.manager) zwlr_screencopy_manager_v1_destroy(c.manager);
    if (c.output) wl_output_destroy(c.output);
    if (c.shm) wl_shm_destroy(c.shm);
    if (c.registry) wl_registry_destroy(c.registry);
    if (c.map) munmap(c.map, c.size);
    if (c.display) wl_display_disconnect(c.display);
    alarm(0);
    if (result) fprintf(stderr, "screencopy: FAIL (offered=%d copying=%d flags=%d ready=%d failed=%d): %s\n",
                        c.pixels.offered, c.pixels.copying, c.pixels.flags_seen,
                        c.pixels.ready, c.pixels.failed, strerror(errno));
    return result;
}
#endif
