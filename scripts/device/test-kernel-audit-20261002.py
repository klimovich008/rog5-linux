#!/usr/bin/env python3
"""Run failure/interleaving cases against real functions reconstructed from patches.

The committed fixture contains only preimage function fragments. Unified hunks
supply new functions; unknown source lines cannot be compiled. With an explicit
ROG5_LINUX_SOURCE, compare and execute the exact fully applied source instead.
No phone, firmware, device node or network access.
"""
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / 'scripts/device/fixtures/kernel-audit-20261002'


def materialize():
    fixture = json.loads((FIXTURE / 'preimage.json').read_text())
    files = {}
    for name, info in fixture['files'].items():
        lines = [None] * info['line_count']
        for fragment in info['fragments']:
            start = fragment['start']
            lines[start:start + len(fragment['lines'])] = fragment['lines']
        files[name] = lines
    names = (REPO / 'patches/linux-7.2.7/series.production').read_text().splitlines()
    for name in names:
        if not name or name.startswith('#') or int(name[:4]) < 198:
            continue
        patch = (REPO / 'patches/linux-7.2.7' / name).read_text().splitlines(True)
        target = None
        delta = 0
        i = 0
        while i < len(patch):
            line = patch[i]
            if line.startswith('+++ b/'):
                target = line[6:].strip()
                delta = 0
            elif line.startswith('@@ ') and target in files:
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if not match:
                    raise ValueError('bad unified hunk')
                old, new = [], []
                i += 1
                while i < len(patch) and patch[i][:1] in (' ', '+', '-') and not patch[i].startswith(('--- ', '+++ ')):
                    op, text = patch[i][0], patch[i][1:]
                    if op != '+':
                        old.append(text)
                    if op != '-':
                        new.append(text)
                    i += 1
                expected = int(match[1]) - 1 + delta
                lines = files[target]
                # Context-only offsets are permitted by git apply too. Require
                # every known preimage line to match, never discard a mismatch.
                candidates = []
                for offset in range(-12, 13):
                    pos = expected + offset
                    if pos < 0 or pos + len(old) > len(lines):
                        continue
                    segment = lines[pos:pos + len(old)]
                    if all(a is None or a == b for a, b in zip(segment, old)):
                        known = sum(a is not None for a in segment)
                        candidates.append((known, -abs(offset), pos))
                if not candidates:
                    raise ValueError(f'{name}: preimage mismatch in {target}')
                pos = max(candidates)[2]
                lines[pos:pos + len(old)] = new
                delta += len(new) - len(old) + pos - expected
                continue
            i += 1
    return {name: ''.join(line if line is not None else '/* unknown */\n' for line in lines)
            for name, lines in files.items()}


def fragment(source, name):
    pattern = r'^[^\n]*\b' + re.escape(name) + r'(?:\[\]|\([^;]*?\))\s*(?:=\s*)?\{\n.*?^}(?:;)?\n'
    match = re.search(pattern, source, re.M | re.S)
    if not match or '/* unknown */' in match[0]:
        raise ValueError(f'incomplete source function {name}')
    return match[0]


class KernelAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = materialize()
        cls.exact = os.environ.get('ROG5_LINUX_SOURCE')

    def case(self, template, functions, mutations=()):
        parts = []
        for path, names in functions.items():
            for name in names:
                text = fragment(self.sources[path], name)
                if self.exact:
                    actual = fragment((Path(self.exact) / path).read_text(), name)
                    self.assertEqual(text, actual, f'fixture/patch/exact source mismatch: {name}')
                    text = actual
                parts.append(text)
        source = (FIXTURE / template).read_text().replace('/* DRIVER_FUNCTIONS */', '\n'.join(parts))
        with tempfile.TemporaryDirectory(prefix='rog5-kernel-audit-') as tmp:
            directory = Path(tmp)
            def run(value):
                c = directory / 'cases.c'
                exe = directory / 'cases'
                c.write_text(value)
                compiled = subprocess.run(['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                                '-Wno-unused-parameter', '-I', str(FIXTURE), str(c), '-o', str(exe)],
                               capture_output=True, text=True)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                return subprocess.run([str(exe)], capture_output=True, text=True)
            result = run(source)
            self.assertEqual(result.returncode, 0, result.stderr)
            for before, after in mutations:
                self.assertIn(before, source)
                broken = run((FIXTURE / template).read_text().replace('/* DRIVER_FUNCTIONS */', '\n'.join(parts).replace(before, after)))
                self.assertNotEqual(broken.returncode, 0, f'case did not reject mutation: {before}')

    def test_protection_fault_latch_hardware_readback_and_reset(self):
        self.case('protection.c', {'sound/soc/codecs/cs35l45.c': [
            'cs35l45_vendor_prot_regs', 'cs35l45_default_prot_regs',
            'cs35l45_set_prot_regs', 'cs35l45_prot_restore_failed', 'cs35l45_global_en_ev']}, [
                ('if (cs35l45->reset_held)', 'if (false && cs35l45->reset_held)'),
                ('regmap_read_bypassed(', 'regmap_read_cached(')])

    def test_amplifier_readback_register_allowlist(self):
        if self.exact:
            header = (Path(self.exact) / 'sound/soc/codecs/cs35l45.h').read_text()
            for line in (FIXTURE / 'readable-registers.h').read_text().splitlines():
                if line.startswith('#define '):
                    self.assertIn(line, header, 'register address differs from exact source')
        self.case('readable.c', {'sound/soc/codecs/cs35l45-tables.c': [
            'cs35l45_readable_reg']}, [
                ('case CS35L45_BOOST_LPMODE_CFG:', 'case 0xdeadbeef:')])

    def test_lpass_reply_token_payload_and_timeout_state(self):
        self.case('lpass.c', {'sound/soc/qcom/qdsp6/q6afe.c': [
            'q6afe_hw_vote_reply', 'q6afe_hw_vote_send',
            'q6afe_unvote_lpass_core_hw', 'q6afe_vote_lpass_core_hw']}, [
                ('hdr->token != afe->hw_vote_token', 'false'),
                ('if (!handle)', 'if (false && !handle)')])

    def test_pcm_cleanup_independent_of_running_and_quarantine(self):
        self.case('pcm-cleanup.c', {'sound/soc/qcom/qdsp6/q6asm-dai.c': [
            'q6asm_dai_pcm_cleanup', 'q6asm_dai_close']}, [
                ('if (prtd->stream_open)', 'if (prtd->stream_open && prtd->state == Q6ASM_STREAM_RUNNING)'),
                ('substream->dma_buffer.area = NULL;', 'substream->dma_buffer.area = prtd->dma_buffer.area;')])

    def test_framebuffer_flush_target_and_failed_rearm(self):
        self.case('framebuffer.c', {'drivers/gpu/drm/msm/msm_kms.c': [
            'msm_kms_fb_unpin_work', 'msm_kms_fb_unpin_queued', 'msm_kms_fb_unpin_flushed',
            'msm_crtc_fb_unpin_fallback']}, [
                ('if (ret != 0)', 'if (ret > 0)'),
                ('!unpin->target_vbl && unpin->required_seq', 'unpin->required_seq')])

    def test_fastrpc_dma_device_and_exported_channel_lifetime(self):
        self.case('fastrpc.c', {'drivers/misc/fastrpc.c': [
            '__fastrpc_buf_alloc', 'fastrpc_buf_free', 'fastrpc_release']}, [
                ('buf->dev = get_device(dev);', 'buf->dev = dev;')])

    def test_dp_exhaustion_and_phy_initialisation_ownership(self):
        self.case('display.c', {'drivers/gpu/drm/msm/dp/dp_ctrl.c': [
            'msm_dp_ctrl_train_link_downshift', 'msm_dp_ctrl_phy_init', 'msm_dp_ctrl_phy_exit']}, [
                ('if (!rc)\n\t\trc = -ETIMEDOUT;', 'if (false && !rc)\n\t\trc = -ETIMEDOUT;')])

    def test_usb_registration_gate_and_teardown_watchdog(self):
        self.case('usb.c', {
            'drivers/usb/dwc3/gadget.c': ['dwc3_gadget_soft_connect'],
            'drivers/usb/dwc3/dwc3-qcom-legacy.c': [
                'dwc3_qcom_bw_work', 'dwc3_qcom_legacy_post_gadget_stop']}, [
                ('READ_ONCE(dwc->requested_role) != USB_ROLE_DEVICE', 'false')])

    def test_battery_reply_correlation_boost_unknown_and_suspend(self):
        self.case('power.c', {'drivers/power/supply/qcom_battmgr.c': [
            'qcom_battmgr_callback', 'qcom_battmgr_btm_otg_send_locked',
            'qcom_battmgr_btm_otg_is_enabled', 'qcom_battmgr_suspend']}, [
                ('opcode != battmgr->request_opcode', 'false'),
                ('battmgr->btm_otg_confirmed = -EIO;', 'battmgr->btm_otg_confirmed = 0;')])


if __name__ == '__main__':
    # Mutation binaries deliberately assert; do not leave host core dumps.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    unittest.main(verbosity=2)
