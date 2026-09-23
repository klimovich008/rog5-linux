#!/usr/bin/env python3
"""Check that 0043 turns the AMS678 driver into the XBL init sequence.

Rebuilds the 0037 driver file, applies 0043 with git apply, then checks the
resulting callbacks: prepare sends a DCS soft reset, 120 ms, sleep out, 10 ms, the Samsung DSC enable
and PPS registers, the PPS and compression packets, TE on and a 60 ms settle,
and no Samsung level-2 register writes remain in the command paths. The
combined driver then runs through the fault-injection lifecycle harness.
This does not establish physical panel behavior.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / 'patches/linux-7.1.4'
BASE = PATCHES / '0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch'
FIX = PATCHES / '0043-drm-panel-asus-rog5-ams678-use-the-XBL-init-sequence.patch'
DRIVER = 'drivers/gpu/drm/panel/panel-asus-rog5-ams678.c'
LEVEL2 = ('0xf0', '0xfc', '0xb0', '0xd1', '0xd3', '0xd5', '0xe4', '0xec', '0xf7', '0x60')


def function(source, name):
    start = source.index('static int ' + name + '(')
    return source[start:source.index('\n}\n', start) + 3]


def order(body, needles):
    positions = [body.index(needle) for needle in needles]
    assert positions == sorted(positions), 'out of order: %r' % (needles,)


def main():
    with tempfile.TemporaryDirectory(prefix='ams678-xbl-') as work:
        work = Path(work)
        # 0037 also edits Kconfig and the Makefile; rebuild only its new driver file.
        tail = BASE.read_text().split('+++ b/' + DRIVER + '\n', 1)[1]
        (work / DRIVER).parent.mkdir(parents=True)
        (work / DRIVER).write_text('\n'.join(line[1:] for line in tail.splitlines() if line.startswith('+')) + '\n')
        base = (work / DRIVER).read_text()
        subprocess.run(['git', 'init', '-q', str(work)], check=True)
        subprocess.run(['git', 'apply', str(FIX)], cwd=work, check=True)
        source = (work / DRIVER).read_text()

        on = function(source, 'ams678_er2_plus_dsc_on')
        order(on, ['mipi_dsi_dcs_soft_reset_multi(', 'mipi_dsi_msleep(&dsi_ctx, 120)',
                   'mipi_dsi_dcs_exit_sleep_mode_multi(', 'mipi_dsi_usleep_range(&dsi_ctx, 10000, 11000)',
                   'mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x9d, 0x01)',
                   'mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x9e,'])
        off = function(source, 'ams678_er2_plus_dsc_off')
        order(off, ['mipi_dsi_dcs_set_display_off_multi(', 'mipi_dsi_msleep(&dsi_ctx, 20)',
                    'mipi_dsi_dcs_enter_sleep_mode_multi(', 'mipi_dsi_msleep(&dsi_ctx, 120)'])
        for name, body in (('on', on), ('off', off)):
            code = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
            writes = re.findall(r'write_seq_multi\(&dsi_ctx, (0x[0-9a-f]+)', code)
            bad = sorted(set(writes) & set(LEVEL2))
            assert not bad, '%s still writes level-2 registers %s' % (name, bad)
        assert re.findall(r'write_seq_multi\(&dsi_ctx, (0x[0-9a-f]+)', on) == ['0x9d', '0x9e'], on

        prepare = function(source, 'ams678_er2_plus_dsc_prepare')
        order(prepare, ['ams678_er2_plus_dsc_on(ctx)', 'mipi_dsi_picture_parameter_set(',
                        'mipi_dsi_compression_mode(', 'mipi_dsi_dcs_set_tear_on_multi(',
                        'mipi_dsi_msleep(&dsi_ctx, 60)', 'ctx->initialized = true'])
        assert 'msleep(28)' not in prepare

        pps = re.search(r'0x9e,\n(.*?)\);', base, re.S).group(1)
        assert pps in on, 'the 0x9e PPS bytes changed'

        combined = work / 'combined.patch'
        combined.write_text('+++ b/' + DRIVER + '\n' + ''.join('+' + line + '\n' for line in source.splitlines()))
        subprocess.run([sys.executable, str(ROOT / 'scripts/device/test-ams678-lifecycle.py'),
                        '--patch', str(combined)], check=True, timeout=300)
    print('PASS 0043 XBL init sequence and lifecycle harness on 0037+0043')


if __name__ == '__main__':
    main()
