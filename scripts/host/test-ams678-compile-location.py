#!/usr/bin/env python3
"""Actual builder application function must work beneath another Git checkout."""
from pathlib import Path
import subprocess
import os
import tempfile

builder = Path(__file__).with_name('build-ams678-panel-check.sh').read_text()
begin = builder.index('apply_panel_patch() {')
function = builder[builder.index('kernel_git() {'):builder.index('\n}', begin) + 2]
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    foreign = root / 'foreign'
    subprocess.run(['git', 'init', '-q', str(foreign)], check=True)
    source = root / 'build/output/source'
    source.mkdir(parents=True)
    patch = root / 'panel.patch'
    patch.write_text('diff --git a/panel.c b/panel.c\nnew file mode 100644\n'
                     '--- /dev/null\n+++ b/panel.c\n@@ -0,0 +1 @@\n+test\n')
    # Source-level regression: unprotected git apply succeeds without applying.
    subprocess.run(['git', '-C', str(source), 'apply', str(patch)], check=True)
    if (source / 'panel.c').exists():
        raise RuntimeError('fixture no longer reproduces ancestor Git filtering')
    subprocess.run(['bash', '-euc', function + '\napply_panel_patch "$1" "$2"',
                    'fixture', str(source), str(patch)], check=True)
    if (source / 'panel.c').read_text() != 'test\n' or (root / 'panel.c').exists():
        raise RuntimeError('patch did not reach the isolated kernel source')
    second = root / 'build/second/source'
    second.mkdir(parents=True)
    foreign_env = dict(os.environ, GIT_DIR=str(foreign / '.git'),
                       GIT_WORK_TREE=str(foreign), GIT_INDEX_FILE=str(foreign / '.git/index'),
                       GIT_COMMON_DIR=str(foreign / '.git'))
    subprocess.run(['bash', '-euc', function + '\napply_panel_patch "$1" "$2"',
                    'fixture', str(second), str(patch)], env=foreign_env, check=True)
    if (second / 'panel.c').read_text() != 'test\n' or (foreign / 'panel.c').exists():
        raise RuntimeError('inherited Git variables escaped the isolated source')
    # A foreign GIT_DIR does redirect the read-only source/object lookup,
    # even though the write-escape variants above do not reproduce an escape.
    (root / 'base-file').write_text('source identity')
    subprocess.run(['git', '-C', str(root), 'add', 'base-file'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Fixture', '-c',
                    'user.email=fixture@example.invalid', 'commit', '-qm', 'base'], check=True)
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    raw = subprocess.run(['git', '-C', str(root), 'archive', revision],
                         env=foreign_env, capture_output=True)
    if raw.returncode == 0:
        raise RuntimeError('foreign object-store fixture did not reproduce refusal')
    if 'kernel_git() {' in builder:
        clean_begin = builder.index('kernel_git() {')
        functions = builder[clean_begin:builder.index('\n}', begin) + 2]
        subprocess.run(['bash', '-euc', functions + '\nkernel_git "$1" -C "$2" archive "$3" >/dev/null',
                        'fixture', str(root.parent), str(root), revision],
                        env=foreign_env, check=True)
    else:
        # Pre-fix path is exactly the builder's raw git archive invocation.
        subprocess.run(['git', '-C', str(root), 'archive', revision],
                        env=foreign_env, stdout=subprocess.DEVNULL, check=True)
print('PASS actual panel application and source archive with nested/foreign Git metadata')
