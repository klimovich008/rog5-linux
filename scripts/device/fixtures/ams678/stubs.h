/* SPDX-License-Identifier: MIT */
/* Fault-injected API boundary; production driver functions are extracted.
 * Regulator errors preserve votes in this controlled fixture. Actual core
 * bookkeeping/error effects are covered by the separate regulator suite. */
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef uint16_t u16;
typedef uint8_t u8;
#define ARRAY_SIZE(a) ((int)(sizeof(a) / sizeof((a)[0])))
#define container_of_const(p, t, m) ((t *)((char *)(p) - offsetof(t, m)))
#define MIPI_DSI_MODE_LPM 1
#define MIPI_DSI_DCS_TEAR_MODE_VBLANK 0
#define MIPI_DCS_SET_DISPLAY_BRIGHTNESS 0x51
struct mutex { pthread_mutex_t native; };
static void mutex_init(struct mutex *m) { assert(!pthread_mutex_init(&m->native, NULL)); }
static void mutex_lock(struct mutex *m) { assert(!pthread_mutex_lock(&m->native)); }
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->native)); }
struct device { int unused; };
struct drm_dsc_config { int unused; };
struct drm_dsc_picture_parameter_set { int unused; };
struct regulator { int refs, index, enable_calls, disable_calls; };
struct regulator_bulk_data { const char *supply; struct regulator *consumer; };
struct gpio_desc { int role; };
struct mipi_dsi_device { struct device dev; unsigned long mode_flags; void *data; };
struct backlight_device { void *data; int brightness; };
struct drm_panel;
struct drm_panel_funcs {
 int (*prepare)(struct drm_panel *), (*enable)(struct drm_panel *);
 int (*unprepare)(struct drm_panel *), (*disable)(struct drm_panel *);
};
struct drm_panel {
 struct device *dev; bool prepared, enabled; struct mutex follower_lock;
 const struct drm_panel_funcs *funcs; struct backlight_device *backlight;
};
struct follower_funcs {
 int (*panel_prepared)(void *), (*panel_unpreparing)(void *);
 int (*panel_enabled)(void *), (*panel_disabling)(void *);
};
struct drm_panel_follower { struct follower_funcs *funcs; };
#define list_for_each_entry(follower, head, member) for ((follower) = NULL; (follower); )
static int diagnostics;
#define dev_err(dev, ...) ((void)(dev), (void)(diagnostics++))
#define dev_warn(dev, ...) ((void)0)
#define dev_info(dev, ...) ((void)0)
#define DRM_DEV_INFO(dev, ...) ((void)0)
static int backlight_enable(void *p) { return 0; }
static int backlight_disable(void *p) { return 0; }
static void *bl_get_data(struct backlight_device *bl) { return bl->data; }
static int backlight_get_brightness(struct backlight_device *bl) { return bl->brightness; }
static void *mipi_dsi_get_drvdata(struct mipi_dsi_device *dsi) { return dsi->data; }
static int ready = 1, gpio_reads, reset_asserted, dsi_calls;
static int fail_init, fail_pps, fail_compression, fail_multi, fail_brightness;
static int fail_disable = -1, fail_enable = -1;
static int regulator_calls, enable_calls;
static unsigned char brightness_payload[3];
static pthread_mutex_t io_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t io_cond = PTHREAD_COND_INITIALIZER;
static int block_brightness, brightness_entered, release_brightness, off_finished;
static void usleep_range(int min, int max) {}
static void msleep(int msec) {}
static void gpiod_set_value_cansleep(struct gpio_desc *g, int value)
{ if (g->role == 0) reset_asserted = value; }
static int gpiod_get_value_cansleep(struct gpio_desc *g) { gpio_reads++; return ready; }
static int regulator_enable(struct regulator *r)
{
 regulator_calls++; enable_calls++; r->enable_calls++;
 if (r->index == fail_enable) return -EIO;
 r->refs++; return 0;
}
static int regulator_disable(struct regulator *r)
{
 regulator_calls++; r->disable_calls++;
 assert(r->refs == 1);
 if (r->index == fail_disable) return -EIO;
 r->refs--; return 0;
}
/* Old driver's bulk APIs retained so regressions execute the unfixed patch. */
static int regulator_bulk_enable(int n, struct regulator_bulk_data *s)
{
 for (int i = 0; i < n; i++) {
  int r = regulator_enable(s[i].consumer);
  if (r) { while (i-- > 0) assert(!regulator_disable(s[i].consumer)); return r; }
 }
 return 0;
}
static int regulator_bulk_disable(int n, struct regulator_bulk_data *s)
{
 for (int i = n - 1; i >= 0; i--) {
  int r = regulator_disable(s[i].consumer);
  if (r) { for (++i; i < n; i++) assert(!regulator_enable(s[i].consumer)); return r; }
 }
 return 0;
}
struct mipi_dsi_multi_context { struct mipi_dsi_device *dsi; int accum_err; };
static void command(struct mipi_dsi_multi_context *c)
{
 if (c->accum_err) return;
 dsi_calls++;
 if (fail_multi) { c->accum_err = -EIO; fail_multi = 0; }
}
static void mipi_dsi_dcs_exit_sleep_mode_multi(struct mipi_dsi_multi_context *c)
{ command(c); if (fail_init) c->accum_err = -EIO; }
#define mipi_dsi_dcs_write_seq_multi(c, ...) command(c)
#define mipi_dsi_dcs_set_tear_on_multi(c, ...) command(c)
#define mipi_dsi_dcs_set_tear_scanline_multi(c, ...) command(c)
#define mipi_dsi_dcs_set_column_address_multi(c, ...) command(c)
#define mipi_dsi_dcs_set_page_address_multi(c, ...) command(c)
#define mipi_dsi_dcs_set_display_off_multi(c) command(c)
#define mipi_dsi_dcs_set_display_on_multi(c) command(c)
#define mipi_dsi_dcs_enter_sleep_mode_multi(c) command(c)
#define mipi_dsi_usleep_range(c, ...) ((void)0)
#define mipi_dsi_msleep(c, ...) ((void)0)
static void drm_dsc_pps_payload_pack(void *p, void *d) {}
static int mipi_dsi_picture_parameter_set(struct mipi_dsi_device *d, void *p)
{ dsi_calls++; return fail_pps ? -EIO : 0; }
static int mipi_dsi_compression_mode(struct mipi_dsi_device *d, bool on)
{ dsi_calls++; return fail_compression ? -EIO : 0; }
static int mipi_dsi_dcs_write_buffer(struct mipi_dsi_device *d, void *p, size_t n)
{
 dsi_calls++;
 memcpy(brightness_payload, p, n);
 pthread_mutex_lock(&io_lock);
 if (block_brightness) {
  brightness_entered = 1; pthread_cond_broadcast(&io_cond);
  while (!release_brightness) pthread_cond_wait(&io_cond, &io_lock);
 }
 pthread_mutex_unlock(&io_lock);
 return fail_brightness ? -EIO : (int)n;
}

static ssize_t mipi_dsi_dcs_write(struct mipi_dsi_device *d, u8 command,
                                 const void *data, size_t len)
{
 u8 payload[3]; assert(len == 2); payload[0] = command;
 memcpy(payload + 1, data, len);
 return mipi_dsi_dcs_write_buffer(d, payload, sizeof(payload));
}
