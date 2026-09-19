#!/usr/bin/env python3
"""Test the proc sampler and opt-in ptrace against owned children; no VM access."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/qemu-virtio-drm/app-close-probe.rs'


class AppCloseProbe(unittest.TestCase):
    def test_bounded_stack_reader_and_actual_owned_child(self):
        with tempfile.TemporaryDirectory(prefix='rog5-close-stack-') as temp:
            target = Path(temp)
            fixture = target / 'fixture.c'
            fixture.write_text('''#include <stdint.h>
#include <stdio.h>
#include <sys/mman.h>
#include <unistd.h>
int main(void) {
    _Alignas(16) volatile uint64_t frames[4];
    frames[0]=(uintptr_t)&frames[2]; frames[1]=0x12345678;
    frames[2]=0; frames[3]=0x87654321;
    long page=sysconf(_SC_PAGESIZE);
    if (page<=0) return 1;
    char *p=mmap(0,(size_t)page*2,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if (p==MAP_FAILED || mprotect(p+page,(size_t)page,PROT_NONE)) return 2;
    printf("%lx %lx\\n",(unsigned long)(uintptr_t)frames,(unsigned long)(uintptr_t)(p+page-8));
    fflush(stdout);
    for (;;) pause();
}''')
            subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                            str(fixture), '-o', str(target/'fixture')], check=True, timeout=20)
            source=SOURCE.with_name('app-close-stack.rs')
            subprocess.run(['rustc','--edition=2024','-D','warnings','--test',
                            str(source),'-o',str(target/'tests')],check=True,timeout=30)
            subprocess.run([str(target/'tests'),'--test-threads=1','--skip','ptrace::tests::'],
                           env={**os.environ,'ROG5_STACK_FIXTURE':str(target/'fixture')},check=True,timeout=15)
            subprocess.run(['rustc','--edition=2024','-D','warnings','--crate-type=lib',
                            str(source),'-o',str(target/'stack.rlib')],check=True,timeout=30)

    def test_actual_ptrace_snapshot_and_owned_child_cleanup(self):
        source = SOURCE.with_name('app-close-ptrace.rs')
        with tempfile.TemporaryDirectory(prefix='rog5-close-ptrace-') as temp:
            target = Path(temp)
            subprocess.run(['rustc', '--edition=2024', '-D', 'warnings',
                            '--crate-type=lib', str(source), '-o', str(target / 'probe.rlib')],
                           check=True, timeout=30)

    def test_actual_rust_parser_sampler_and_release_refusal(self):
        with tempfile.TemporaryDirectory(prefix='rog5-app-close-probe-') as temp:
            target = Path(temp)
            for kind, flags in [('tests', ['--test','--cfg','close_ptrace']), ('release', []),
                                ('intrusive', ['--cfg','close_ptrace']),
                                ('stack-tests', ['--test','--cfg','close_ptrace','--cfg','close_stack']),
                                ('stack-release', ['--cfg','close_ptrace','--cfg','close_stack'])]:
                subprocess.run(['rustc', '--edition=2024', '-D', 'warnings', *flags,
                                str(SOURCE), '-o', str(target / kind)], check=True, timeout=30)
            subprocess.run([str(target / 'tests'), '--nocapture', '--test-threads=1'], check=True, timeout=15)
            subprocess.run([str(target / 'stack-tests'), '--test-threads=1', '--skip',
                            'stack::tests::actual_owned_child_stack_and_partial_syscall'], check=True, timeout=15)
            for kind in ['release','intrusive','stack-release']:
                result = subprocess.run([str(target / kind), '1', '1', '2', '1'],
                                    capture_output=True, timeout=3)
                self.assertEqual(result.returncode, 125)
                self.assertEqual(result.stdout, b'')
                self.assertIn(b'requires non-root isolated VM', result.stderr)


if __name__ == '__main__':
    unittest.main()
