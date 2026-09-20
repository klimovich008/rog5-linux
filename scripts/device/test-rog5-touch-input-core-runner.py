#!/usr/bin/env python3
"""Run the touch harness's process regressions through the board-test interface."""
import os
import sys
if not sys.flags.no_site:
    os.execv(sys.executable, [sys.executable, '-S', '-B', *sys.orig_argv[1:]])
sys.dont_write_bytecode = True

from pathlib import Path
import runpy
import tempfile

root = Path(__file__).resolve().parents[2]
source = os.environ.get('ROG5_LINUX_SOURCE')
if not source or not Path(source).is_dir():
    print('BLOCKED exact kernel source: set ROG5_LINUX_SOURCE', flush=True)
    sys.exit(2)
fixture = root / 'scripts/device/fixtures/fts3658u-input-core'
build = root / 'build'
build.mkdir(exist_ok=True)
runpy.run_path(str(root / 'scripts/device/test-rog5-touch-input-core.py'))['disk_backed'](build)
output = Path(tempfile.mkdtemp(prefix='touch-runner-regression-', dir=build))
output.chmod(0o700)
print('Runner evidence: ' + str(output / 'report'), flush=True)
sys.argv = [str(fixture / 'runner-regression.py'), '--before',
            str(fixture / 'original-runner.py'), '--output', str(output / 'report')]
runpy.run_path(sys.argv[0], run_name='__main__')
