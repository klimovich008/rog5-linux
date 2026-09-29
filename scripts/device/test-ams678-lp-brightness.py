#!/usr/bin/env python3
"""Check that 0043 sends the AMS678 brightness in LP mode and nothing else.

Rebuilds the 0037 driver file, applies 0043 with git apply, then checks that
the backlight callback sets MIPI_DSI_MODE_LPM around the DBV write and never
clears it, and that every other line of the driver is unchanged. The combined
driver then runs through the fault-injection lifecycle harness. This does not
establish physical panel behavior.
"""
from pathlib import Path
import difflib
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / 'patches/linux-7.2.7'
BASE = PATCHES / '0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch'
FIX = PATCHES / '0043-drm-panel-asus-rog5-ams678-send-brightness-in-LP-mode.patch'
DRIVER = 'drivers/gpu/drm/panel/panel-asus-rog5-ams678.c'


def function(source, name):
    start = source.index('static int ' + name + '(')
    return source[start:source.index('\n}\n', start) + 3]


def main():
    with tempfile.TemporaryDirectory(prefix='ams678-lp-') as work:
        work = Path(work)
        # 0037 also edits Kconfig and the Makefile; rebuild only its new driver file.
        tail = BASE.read_text().split('+++ b/' + DRIVER + '\n', 1)[1]
        (work / DRIVER).parent.mkdir(parents=True)
        (work / DRIVER).write_text('\n'.join(line[1:] for line in tail.splitlines() if line.startswith('+')) + '\n')
        base = (work / DRIVER).read_text()
        subprocess.run(['git', 'init', '-q', str(work)], check=True)
        subprocess.run(['git', 'apply', str(FIX)], cwd=work, check=True)
        source = (work / DRIVER).read_text()

        update = function(source, 'ams678_er2_plus_dsc_bl_update_status')
        assert '&= ~MIPI_DSI_MODE_LPM' not in update, 'brightness still switches to HS'
        set_lp = update.index('dsi->mode_flags |= MIPI_DSI_MODE_LPM;')
        write = update.index('mipi_dsi_dcs_set_display_brightness_large(dsi, brightness)')
        restore = update.index('dsi->mode_flags = mode_flags;')
        assert set_lp < write < restore, update

        changed = [line for line in difflib.unified_diff(base.splitlines(), source.splitlines(), lineterm='', n=0)
                   if line[:1] in '+-' and not line.startswith(('+++', '---'))]
        code = [line for line in changed if not line[1:].strip().startswith(('/*', '*', '*/'))]
        assert code == ['-\tdsi->mode_flags &= ~MIPI_DSI_MODE_LPM;', '+\tdsi->mode_flags |= MIPI_DSI_MODE_LPM;'], code

        combined = work / 'combined.patch'
        combined.write_text('+++ b/' + DRIVER + '\n' + ''.join('+' + line + '\n' for line in source.splitlines()))
        subprocess.run([sys.executable, str(ROOT / 'scripts/device/test-ams678-lifecycle.py'),
                        '--patch', str(combined)], check=True, timeout=300)
    print('PASS 0043 LP-mode brightness and lifecycle harness on 0037+0043')


if __name__ == '__main__':
    main()
