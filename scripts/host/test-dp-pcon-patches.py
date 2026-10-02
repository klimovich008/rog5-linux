#!/usr/bin/env python3
"""Execute DP patch functions with fake resources/AUX, never device I/O.

New helpers are extracted verbatim from their added patch lines. Optional
ROG5_LINUX_SOURCE checks execute existing functions from the applied series.
These tests establish software error/ownership behavior, not a working PCON.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / 'patches/linux-7.2.7'
SOURCE = os.environ.get('ROG5_LINUX_SOURCE')


def added(number):
    path, = PATCHES.glob(number + '-*.patch')
    return '\n'.join(line[1:] for line in path.read_text().splitlines()
                     if line.startswith('+') and not line.startswith('+++'))


def postimage(number):
    """Context plus additions from a patch with full function context."""
    path, = PATCHES.glob(number + '-*.patch')
    return '\n'.join(line[1:] for line in path.read_text().splitlines()
                     if line.startswith((' ', '+')) and not line.startswith('+++'))


def function(text, name):
    match = re.search(r'^(?:static )?(?:int|void|bool) ' + name + r'\([^;]*?\n\{',
                      text, re.M)
    if not match:
        raise AssertionError('missing full function: ' + name)
    end = text.index('\n}', match.end()) + 2
    return text[match.start():end] + '\n'


COMMON = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <errno.h>
#include <string.h>
#include <sys/types.h>
#define container_of(p, t, m) ((t *)((char *)(p) - offsetof(t, m)))
#define DRM_ERROR_RATELIMITED(...) ((void)0)
typedef unsigned char u8;
typedef unsigned int u32;
'''


class Pcon(unittest.TestCase):
    def execute(self, code, mutant=None):
        with tempfile.TemporaryDirectory(prefix='rog5-pcon-test-') as directory:
            root = Path(directory)
            (root / 'test.c').write_text(COMMON + code)
            result = subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                                     '-Wno-unused-parameter', str(root / 'test.c'),
                                     '-o', str(root / 'test')], capture_output=True, text=True,
                                    timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(root / 'test')], capture_output=True, text=True,
                                    timeout=5)
            if mutant:
                self.assertNotEqual(result.returncode, 0, 'surviving mutant: ' + mutant)
            else:
                self.assertEqual(result.returncode, 0, result.stderr)

    def abort_code(self, body):
        return r'''
#define REG_DP_STATE_CTRL 1
struct msm_dp_ctrl { bool wide_bus_en; };
struct msm_dp_panel { int link_info; };
struct msm_dp_ctrl_private {
    struct msm_dp_ctrl msm_dp_ctrl;
    bool core_clks_on, link_clks_on, stream_clks_on, phy_powered;
    void *aux, *link, *dev, *pixel_clk;
    struct msm_dp_panel *panel;
};
static struct msm_dp_ctrl_private *active;
static int panel_stop, writes, tp_stop, d3, pixel_off, link_off, phy_off;
static int connected = 1, aux_result;
static void msm_dp_panel_disable_vsc_sdp(void *p) {
    assert(active->core_clks_on && active->link_clks_on); panel_stop++;
}
static void msm_dp_write_link(void *p, int reg, int value) {
    assert(active->core_clks_on && active->link_clks_on); writes++;
}
static void msm_dp_ctrl_mainlink_disable(void *p) {
    assert(active->core_clks_on && active->link_clks_on);
}
static int msm_dp_aux_is_link_connected(void *p) { return connected; }
static int msm_dp_ctrl_clear_training_pattern(void *p, int phy) {
    assert(active->core_clks_on); tp_stop++; return aux_result;
}
#define DP_PHY_DPRX 0
static int msm_dp_link_psm_config(void *p, void *info, bool down) {
    assert(active->core_clks_on && down); assert(!active->phy_powered || !phy_off);
    d3++; return aux_result;
}
static void clk_disable_unprepare(void *p) { pixel_off++; }
static void msm_dp_ctrl_link_clk_disable(struct msm_dp_ctrl *p) {
    if (active->link_clks_on) { link_off++; active->link_clks_on = false; }
}
static int dev_pm_opp_set_rate(void *p, int rate) { assert(rate == 0); return 0; }
static void msm_dp_ctrl_phy_power_off(void *p) {
    if (active->phy_powered) { phy_off++; active->phy_powered = false; }
}
''' + body + r'''
int main(void) {
    struct msm_dp_panel panel = {};
    for (int bits = 0; bits < 16; bits++) {
        for (int access = 0; access < 2; access++) {
            for (int conn = 0; conn < 2; conn++) {
                for (int error = 0; error < 2; error++) {
                    struct msm_dp_ctrl_private ctrl = { .panel = &panel,
                        .core_clks_on = bits & 1, .link_clks_on = bits & 2,
                        .stream_clks_on = bits & 4, .phy_powered = bits & 8 };
                    active = &ctrl; connected = conn; aux_result = error ? -EIO : 0;
                    panel_stop = writes = tp_stop = d3 = pixel_off = link_off = phy_off = 0;
                    msm_dp_ctrl_abort(&ctrl.msm_dp_ctrl, access);
                    assert(writes == !!((bits & 1) && (bits & 2)));
                    assert(panel_stop == writes);
                    assert(tp_stop == !!(access && conn && (bits & 1)) && d3 == tp_stop);
                    assert(pixel_off == !!(bits & 4) && link_off == !!(bits & 2));
                    assert(phy_off == !!(bits & 8));
                    assert(!ctrl.stream_clks_on && !ctrl.link_clks_on && !ctrl.phy_powered);
                    msm_dp_ctrl_abort(&ctrl.msm_dp_ctrl, access);
                    assert(pixel_off == !!(bits & 4) && link_off == !!(bits & 2));
                    assert(phy_off == !!(bits & 8));
                }
            }
        }
    }
    return 0;
}
'''

    def test_abort_resource_matrix(self):
        self.execute(self.abort_code(function(added('0200'), 'msm_dp_ctrl_abort')))

    def test_abort_unclocked_and_double_release_mutants(self):
        body = function(added('0200'), 'msm_dp_ctrl_abort')
        self.execute(self.abort_code(body.replace('ctrl->core_clks_on && ctrl->link_clks_on',
                                                 'true', 1)), 'unclocked access')
        self.execute(self.abort_code(body.replace('ctrl->stream_clks_on = false;', '', 1)),
                     'double pixel-clock release')

    def test_minimal_wake_rejects_short_reads_and_preserves_errno(self):
        self.execute(r'''
#define DP_DPCD_REV 0
struct msm_dp_link_info { u8 revision; };
struct msm_dp_display_private { void *aux, *link; };
static int read_result, power_result, calls;
static int drm_dp_dpcd_readb(void *aux, int reg, u8 *value) {
    *value = 0x14; return read_result;
}
static int msm_dp_link_psm_config(void *link, struct msm_dp_link_info *info, bool down) {
    assert(info->revision == 0x14 && !down); calls++; return power_result;
}
''' + function(added('0201'), 'msm_dp_display_sink_wake') + r'''
int main(void) {
    struct msm_dp_display_private dp = {};
    int transfers[] = {1, 0, -ETIMEDOUT, -ENXIO};
    for (unsigned int i = 0; i < sizeof(transfers) / sizeof(*transfers); i++) {
        read_result = transfers[i]; calls = 0; power_result = 0;
        int result = msm_dp_display_sink_wake(&dp);
        assert(result == (read_result == 1 ? 0 : read_result < 0 ? read_result : -EIO));
        assert(calls == (read_result == 1));
    }
    read_result = 1; power_result = -EIO;
    assert(msm_dp_display_sink_wake(&dp) == -EIO);
    return 0;
}
''')

    def test_reset_serializes_aux_and_restores_hpd(self):
        self.execute(r'''
#define REG_DP_DP_HPD_CTRL 0
#define REG_DP_DP_HPD_REFTIMER 1
#define REG_DP_DP_HPD_INT_MASK 2
#define REG_DP_DP_HPD_INT_STATUS 3
#define DP_DP_HPD_INT_MASK 15
struct drm_dp_aux { int unused; };
struct msm_dp_ctrl { int unused; };
struct msm_dp_aux_private { struct drm_dp_aux msm_dp_aux; int mutex; bool initted; };
static u32 regs[4];
static int locked, resets, irq_restores, aux_enables;
static int lock_guard(int *mutex) { assert(!locked); locked = 1; return 1; }
static void unlock_guard(int *held) { assert(locked && *held); locked = 0; }
#define guard(kind) int held __attribute__((cleanup(unlock_guard))) = lock_guard
static u32 msm_dp_read_aux(void *aux, int reg) { assert(locked); return regs[reg]; }
static void msm_dp_write_aux(void *aux, int reg, u32 value) { assert(locked); regs[reg] = value; }
static void msm_dp_ctrl_reset(void *ctrl) { assert(locked); memset(regs, 0, sizeof(regs)); resets++; }
static void msm_dp_ctrl_enable_irq(void *ctrl) { assert(locked); irq_restores++; }
static void msm_dp_aux_enable(void *aux) { assert(locked); aux_enables++; }
''' + function(postimage('0207'), 'msm_dp_aux_reset_ctrl') + r'''
int main(void) {
    struct msm_dp_aux_private aux = {};
    struct msm_dp_ctrl ctrl = {};
    assert(msm_dp_aux_reset_ctrl(&aux.msm_dp_aux, &ctrl) == -EIO);
    assert(!locked && !resets && !irq_restores && !aux_enables);
    aux.initted = true; regs[0] = 1; regs[1] = 0x10000; regs[2] = 5;
    assert(msm_dp_aux_reset_ctrl(&aux.msm_dp_aux, &ctrl) == 0);
    assert(!locked && resets == 1 && irq_restores == 1 && aux_enables == 1);
    assert(regs[0] == 1 && regs[1] == 0x10000 && regs[2] == 5);
    regs[3] = 5;
    assert(msm_dp_aux_reset_ctrl(&aux.msm_dp_aux, &ctrl) == -EAGAIN);
    assert(!locked && resets == 1 && regs[3] == 5);
    return 0;
}
''')

    @unittest.skipUnless(SOURCE, 'requires ROG5_LINUX_SOURCE with the applied HDMI series')
    def test_applied_training_exhaustion_is_failure(self):
        source = (Path(SOURCE) / 'drivers/gpu/drm/msm/dp/dp_ctrl.c').read_text()
        self.execute(r'''
#define DP_LINK_STATUS_SIZE 6
#define DP_TRAINING_NONE 0
#define DP_TRAINING_1 1
#define DP_TRAINING_2 2
struct msm_dp_ctrl { int dummy; };
struct msm_dp_link { struct { int num_lanes; } link_params; };
struct msm_dp_ctrl_private { struct msm_dp_ctrl msm_dp_ctrl; void *aux; struct msm_dp_link *link; };
static int outcome, calls, clear_result;
static int msm_dp_ctrl_setup_main_link(void *p, int *step) {
    calls++; *step = DP_TRAINING_2; return outcome;
}
static void msm_dp_ctrl_log_link(void *p, const char *stage, int result) {}
static int msm_dp_aux_is_link_connected(void *p) { return 1; }
static int drm_dp_dpcd_read_link_status(void *p, u8 *status) { return 0; }
static int msm_dp_ctrl_link_rate_down_shift(void *p) { return 0; }
static int msm_dp_ctrl_link_lane_down_shift(void *p) { return 0; }
static bool msm_dp_ctrl_clock_recovery_any_ok(u8 *status, int lanes) { return true; }
static bool drm_dp_clock_recovery_ok(u8 *status, int lanes) { return true; }
#define DP_PHY_DPRX 0
static int msm_dp_ctrl_clear_training_pattern(void *p, int phy) { return clear_result; }
static int msm_dp_ctrl_reinitialize_mainlink(void *p) { return 0; }
''' + function(source, 'msm_dp_ctrl_train_link_downshift') + r'''
int main(void) {
    struct msm_dp_link link = {};
    struct msm_dp_ctrl_private ctrl = { .link = &link };
    outcome = -ETIMEDOUT; calls = 0;
    assert(msm_dp_ctrl_train_link_downshift(&ctrl) == -ETIMEDOUT && calls == 4);
    outcome = 0; calls = 0;
    assert(msm_dp_ctrl_train_link_downshift(&ctrl) == 0 && calls == 1);
    outcome = -ETIMEDOUT; calls = 0; clear_result = -ENXIO;
    assert(msm_dp_ctrl_train_link_downshift(&ctrl) == -ENXIO && calls == 1);
    outcome = -EIO; calls = 0; clear_result = 0;
    assert(msm_dp_ctrl_train_link_downshift(&ctrl) == -EIO && calls == 1);
    return 0;
}
''')

    @unittest.skipUnless(SOURCE, 'requires ROG5_LINUX_SOURCE with the applied HDMI series')
    def test_applied_stream_errors_and_single_training(self):
        source = (Path(SOURCE) / 'drivers/gpu/drm/msm/dp/dp_ctrl.c').read_text()
        self.execute(r'''
#define drm_dbg_dp(...) ((void)0)
#define drm_info(...) ((void)0)
#define DP_PHY_DPRX 0
#define REG_DP_STATE_CTRL 0
#define DP_STATE_CTRL_SEND_VIDEO 0x80
#define REG_DP_CONFIGURATION_CTRL 1
#define REG_DP_MISC1_MISC0 2
struct msm_dp_ctrl { bool wide_bus_en; };
struct msm_dp_panel { struct { struct { unsigned long clock; } drm_mode; bool out_fmt_is_yuv_420; } msm_dp_mode; };
struct msm_dp_link { struct { unsigned int rate, num_lanes; } link_params; };
struct msm_dp_ctrl_private {
    struct msm_dp_ctrl msm_dp_ctrl;
    struct msm_dp_panel *panel; struct msm_dp_link *link;
    void *pixel_clk, *drm_dev; int video_comp;
    bool core_clks_on, link_clks_on, stream_clks_on, pcon_single_train;
};
static int fault, retrains, sends, terminations;
static bool eq_good;
static int msm_dp_ctrl_enable_mainlink_clocks(void *p) { return fault == 1 ? -EIO : 0; }
static int clk_set_rate(void *p, unsigned long rate) { return fault == 2 ? -ERANGE : 0; }
static int clk_prepare_enable(void *p) { return fault == 3 ? -EIO : 0; }
static bool msm_dp_ctrl_channel_eq_ok(void *p) { return eq_good; }
static int msm_dp_ctrl_link_retrain(void *p) { retrains++; return fault == 4 ? -ENXIO : 0; }
static void msm_dp_ctrl_log_link(void *p, const char *stage, int rc) {}
static int msm_dp_ctrl_clear_training_pattern(void *p, int phy) { terminations++; return fault == 5 ? -EIO : 0; }
static void reinit_completion(void *p) {}
static void msm_dp_ctrl_configure_source_params(void *p) {}
static void msm_dp_ctrl_config_msa(void *p, unsigned int rate, unsigned long pixel, bool yuv) {}
static void msm_dp_panel_clear_dsc_dto(void *p) {}
static void msm_dp_ctrl_setup_tr_unit(void *p) {}
static void msm_dp_write_link(void *p, int reg, int value) { assert(value == 0x80); sends++; }
static int msm_dp_ctrl_wait4video_ready(void *p) { return fault == 6 ? -ETIMEDOUT : 0; }
static bool msm_dp_ctrl_mainlink_ready(void *p) { return fault != 7; }
''' + function(source, 'msm_dp_ctrl_on_stream') + r'''
int main(void) {
    struct msm_dp_panel panel = { .msm_dp_mode.drm_mode.clock = 148500 };
    struct msm_dp_link link = { .link_params = {540000, 2} };
    for (fault = 0; fault <= 7; fault++) {
        struct msm_dp_ctrl_private ctrl = { .panel = &panel, .link = &link, .core_clks_on = true };
        retrains = sends = terminations = 0; eq_good = true;
        int rc = msm_dp_ctrl_on_stream(&ctrl.msm_dp_ctrl, true);
        assert(rc == (fault == 0 ? 0 : fault == 2 ? -ERANGE : fault == 4 ? -ENXIO : fault >= 6 ? -ETIMEDOUT : -EIO));
        assert(sends == (fault == 0 || fault >= 6));
        assert(terminations == (fault == 0 || fault >= 5));
    }
    fault = 0;
    for (int single = 0; single < 2; single++) for (int eq = 0; eq < 2; eq++) {
        struct msm_dp_ctrl_private ctrl = { .panel = &panel, .link = &link,
            .core_clks_on = true, .link_clks_on = true, .pcon_single_train = single };
        retrains = sends = terminations = 0; eq_good = eq;
        assert(msm_dp_ctrl_on_stream(&ctrl.msm_dp_ctrl, true) == 0);
        assert(retrains == (!single || !eq));
        assert(sends == 1 && terminations == 1);
    }
    return 0;
}
''')

    @unittest.skipUnless(SOURCE, 'requires ROG5_LINUX_SOURCE with the applied HDMI series')
    def test_applied_d0_d3_exact_transfers(self):
        source = (Path(SOURCE) / 'drivers/gpu/drm/msm/dp/dp_link.c').read_text()
        self.execute(r'''
#define DP_SET_POWER 0x600
#define DP_SET_POWER_MASK 3
#define DP_SET_POWER_D0 1
#define DP_SET_POWER_D3 2
struct drm_dp_aux { int unused; };
struct msm_dp_link_info { u8 revision; };
static int rd, wr, reads, writes, delays, expected;
static int drm_dp_dpcd_readb(void *aux, int reg, u8 *value) { reads++; *value = 0xa0; return rd; }
static int drm_dp_dpcd_writeb(void *aux, int reg, u8 value) { writes++; assert(value == (0xa0 | expected)); return wr; }
static void usleep_range(int a, int b) { assert(a >= 1000 && b >= a); delays++; }
''' + function(source, 'msm_dp_aux_link_power_up') +
                     function(source, 'msm_dp_aux_link_power_down') + r'''
int main(void) {
    struct drm_dp_aux aux = {};
    struct msm_dp_link_info info = { .revision = 0x14 };
    int values[] = {1, 0, -EIO, -ETIMEDOUT};
    for (int down = 0; down < 2; down++) {
        expected = down ? DP_SET_POWER_D3 : DP_SET_POWER_D0;
        for (int i = 0; i < 4; i++) for (int j = 0; j < 4; j++) {
            rd = values[i]; wr = values[j]; reads = writes = delays = 0;
            int result = down ? msm_dp_aux_link_power_down(&aux, &info) : msm_dp_aux_link_power_up(&aux, &info);
            int transfer = rd == 1 ? wr : rd;
            assert(result == (transfer == 1 ? 0 : transfer < 0 ? transfer : -EIO));
            assert(reads == 1);
            assert(writes == (rd != 1 ? 0 : down || wr == 1 ? 1 : 3));
            assert(delays == (down ? 0 : writes));
        }
    }
    return 0;
}
''')


if __name__ == '__main__':
    unittest.main()
