/* SPDX-License-Identifier: MIT */
static struct ams678_er2_plus_dsc ctx;
static struct mipi_dsi_device dsi;
static struct regulator regs[2] = { { .index = 0 }, { .index = 1 } };
static struct regulator_bulk_data supplies[2] = {
 { .supply = "vddio", .consumer = &regs[0] },
 { .supply = "vdd", .consumer = &regs[1] },
};
static struct gpio_desc reset_gpio, wake_gpio = {1}, ready_gpio = {2};
static struct backlight_device bl;
static const struct drm_panel_funcs funcs = {
 .prepare = ams678_er2_plus_dsc_prepare,
 .enable = ams678_er2_plus_dsc_enable,
 .unprepare = ams678_er2_plus_dsc_unprepare,
};
static void setup(void)
{
 ctx.dsi = &dsi; dsi.data = &ctx; ctx.supplies = supplies;
 ctx.reset_gpio = &reset_gpio; ctx.iris_wakeup_gpio = &wake_gpio;
 ctx.iris_bypass_ready_gpio = &ready_gpio;
 ctx.panel.dev = &dsi.dev; ctx.panel.funcs = &funcs;
 mutex_init(&ctx.panel.follower_lock);
 /* DRIVER_MUTEX_INIT is generated from the patch's actual probe. */
 DRIVER_MUTEX_INIT
 bl.data = &dsi; bl.brightness = 0x123;
}
static void start(void)
{ drm_panel_prepare(&ctx.panel); assert(ctx.panel.prepared); drm_panel_enable(&ctx.panel); assert(ctx.panel.enabled); }
static void stop(void)
{ drm_panel_disable(&ctx.panel); drm_panel_unprepare(&ctx.panel); }
static void no_commands(void)
{
 int before = dsi_calls; unsigned long flags = dsi.mode_flags;
 drm_panel_enable(&ctx.panel);
 assert(!ctx.panel.enabled);
 assert(ams678_er2_plus_dsc_bl_update_status(&bl) == -EPERM);
 assert(dsi_calls == before); assert(dsi.mode_flags == flags);
}
static void *brightness_thread(void *arg)
{ assert(!ams678_er2_plus_dsc_bl_update_status(&bl)); return NULL; }
static void *off_thread(void *arg)
{
 stop(); pthread_mutex_lock(&io_lock); off_finished = 1;
 pthread_cond_broadcast(&io_cond); pthread_mutex_unlock(&io_lock); return NULL;
}
int main(int argc, char **argv)
{
 assert(argc == 2); setup(); const char *name = argv[1];
 if (!strcmp(name, "iris-timeout") || !strcmp(name, "iris-gpio-error") ||
     !strcmp(name, "init-error") || !strcmp(name, "pps-error") ||
     !strcmp(name, "compression-error")) {
  if (!strcmp(name, "iris-timeout")) ready = 0;
  if (!strcmp(name, "iris-gpio-error")) ready = -EIO;
  fail_init = !strcmp(name, "init-error"); fail_pps = !strcmp(name, "pps-error");
  fail_compression = !strcmp(name, "compression-error");
  drm_panel_prepare(&ctx.panel); assert(!ctx.panel.prepared);
  assert(regs[0].refs == 0 && regs[1].refs == 0);
  if (ready == 0) assert(gpio_reads == 51);
  if (ready < 0) assert(gpio_reads == 1);
  no_commands();
 } else if (!strcmp(name, "off-error-reprepare")) {
  start(); fail_multi = 1; stop(); assert(diagnostics);
  assert(!ctx.panel.prepared); assert(!regs[0].refs && !regs[1].refs);
  start(); stop(); assert(!ctx.panel.prepared);
 } else if (!strcmp(name, "disable-error")) {
  start(); fail_disable = 0; stop(); assert(ctx.panel.prepared);
  assert(regs[0].refs == 1 && regs[1].refs == 0);
  no_commands(); int calls = enable_calls;
  drm_panel_prepare(&ctx.panel); assert(enable_calls == calls);
  fail_disable = -1; drm_panel_unprepare(&ctx.panel);
  assert(!ctx.panel.prepared); assert(!regs[0].refs && !regs[1].refs);
  start(); stop();
 } else if (!strcmp(name, "prepare-cleanup-error")) {
  fail_init = 1; fail_disable = 0; drm_panel_prepare(&ctx.panel);
  assert(!ctx.panel.prepared); assert(regs[0].refs == 1 && regs[1].refs == 0);
  no_commands(); fail_init = 0; int calls = enable_calls;
  drm_panel_prepare(&ctx.panel); assert(!ctx.panel.prepared);
  assert(enable_calls == calls); fail_disable = -1;
  start(); stop(); assert(!regs[0].refs && !regs[1].refs);
 } else if (!strcmp(name, "enable-supply-error")) {
  fail_enable = 1; drm_panel_prepare(&ctx.panel); assert(!ctx.panel.prepared);
  assert(!regs[0].refs && !regs[1].refs); no_commands();
  fail_enable = -1; start(); stop();
 } else if (!strcmp(name, "disable-second-supply-error")) {
  start(); fail_disable = 1; stop(); assert(ctx.panel.prepared);
  assert(regs[0].refs == 0 && regs[1].refs == 1); no_commands();
  fail_disable = -1; drm_panel_unprepare(&ctx.panel);
  assert(!ctx.panel.prepared && !regs[0].refs && !regs[1].refs); start(); stop();
 } else if (!strcmp(name, "normal-cycles")) {
  for (int i = 0; i < 20; i++) {
   start(); assert(!ams678_er2_plus_dsc_bl_update_status(&bl)); stop();
   assert(!ctx.panel.prepared && !ctx.panel.enabled);
   assert(!regs[0].refs && !regs[1].refs); no_commands();
  }
 } else if (!strcmp(name, "brightness-order")) {
  static const unsigned values[] = {0, 1, 255, 256, 1023};
  start();
  for (unsigned i = 0; i < sizeof(values) / sizeof(values[0]); i++) {
   for (unsigned flags = 0x42; flags <= 0x43; flags++) {
    dsi.mode_flags = flags; bl.brightness = values[i];
    assert(!ams678_er2_plus_dsc_bl_update_status(&bl));
    assert(brightness_payload[0] == 0x51);
    assert(brightness_payload[1] == (values[i] >> 8));
    assert(brightness_payload[2] == (values[i] & 0xff));
    assert(dsi.mode_flags == flags);
   }
  }
  stop();
 } else if (!strcmp(name, "brightness-error-flags")) {
  start(); fail_brightness = 1;
  for (unsigned flags = 0x42; flags <= 0x43; flags++) {
   dsi.mode_flags = flags;
   assert(ams678_er2_plus_dsc_bl_update_status(&bl) == -EIO);
   assert(dsi.mode_flags == flags);
  }
  stop();
 } else if (!strcmp(name, "enable-error")) {
  drm_panel_prepare(&ctx.panel); assert(ctx.panel.prepared);
  fail_multi = 1; drm_panel_enable(&ctx.panel); assert(!ctx.panel.enabled);
  drm_panel_enable(&ctx.panel); assert(ctx.panel.enabled); stop();
 } else if (!strcmp(name, "serialized-backlight")) {
  pthread_t a, b; start(); block_brightness = 1;
  assert(!pthread_create(&a, NULL, brightness_thread, NULL));
  pthread_mutex_lock(&io_lock);
  while (!brightness_entered) pthread_cond_wait(&io_cond, &io_lock);
  pthread_mutex_unlock(&io_lock);
  assert(!pthread_create(&b, NULL, off_thread, NULL));
  usleep(100000); pthread_mutex_lock(&io_lock); assert(!off_finished);
  release_brightness = 1; pthread_cond_broadcast(&io_cond); pthread_mutex_unlock(&io_lock);
  assert(!pthread_join(a, NULL)); assert(!pthread_join(b, NULL));
  assert(off_finished && !ctx.panel.prepared);
 } else { assert(!"unknown case"); }
 return 0;
}
