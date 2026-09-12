#!/usr/bin/env python3
"""Compile pinned Linux7.1.4 GENI probe/DMA extracts; never access hardware."""
import argparse
import hashlib
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'scripts/device/fixtures/geni-mode'
I2C = 'drivers/i2c/busses/i2c-qcom-geni.c'
SPECS = {
    'setup.inc': (I2C, 'static int setup_gpi_dma(', None),
    'protocol.inc': (I2C, '\tproto = geni_se_read_proto(&gi2c->se);',
                     '\n\tclk_disable_unprepare(gi2c->core_clk);'),
    'buffer-select.inc': (I2C, '\tdma_buf = gi2c->no_dma ? NULL : i2c_get_dma_safe_msg_buf(msg, 32);',
                          '\n\twritel_relaxed(len, se->base + SE_I2C_RX_TRANS_LEN);'),
    'firmware.inc': ('drivers/soc/qcom/qcom-geni-se.c', 'int geni_load_se_firmware(', None),
    'buffer.inc': ('drivers/i2c/i2c-core-base.c', 'u8 *i2c_get_dma_safe_msg_buf(', None),
}


def extract(source, begin, end):
    start = source.index(begin)
    stop = source.index(end, start) if end else source.index('\n}', start) + 2
    return source[start:stop] + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linux-source', type=Path, default=os.environ.get('ROG5_LINUX_SOURCE'))
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    started = time.monotonic()
    files = sorted(FIXTURE.iterdir())
    pins = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    if args.linux_source:
        for name, (relative, begin, end) in SPECS.items():
            expected = extract((args.linux_source / relative).read_text(), begin, end)
            actual = (FIXTURE / name).read_text().split('/* BEGIN EXACT EXTRACT */\n', 1)[1]
            if actual != expected:
                raise ValueError('pinned kernel extract differs: ' + name)
        print('PASS exact Linux source comparison: five extracts')
    else:
        print('NOT RUN external kernel-source comparison; pinned extracts compiled')
    scratch = ROOT / 'build'
    scratch.mkdir(exist_ok=True)
    mutations = (
        ('wrong-protocol', 'protocol.inc', 'proto != GENI_SE_I2C', 'false'),
        ('dma-required', 'protocol.inc', 'if (fifo_disable)', 'if (false && fifo_disable)'),
        ('rx-unwind', 'setup.inc', 'dma_release_channel(gi2c->tx_c);', 'if (false) dma_release_channel(gi2c->tx_c);'),
        ('firmware-required', 'firmware.inc', '\t\treturn -EINVAL;\n\t}\n\n\tif (of_property', '\t\treturn 0;\n\t}\n\n\tif (of_property'),
        ('small-id-fifo', 'buffer-select.inc', 'msg, 32)', 'msg, 1)'),
    )
    with tempfile.TemporaryDirectory(prefix='geni-mode-', dir=scratch) as directory:
        tmp = Path(directory)
        for label, target, old, new in [('kernel', None, None, None), *mutations]:
            for path in files:
                contents = path.read_text()
                if path.name == target:
                    if old not in contents:
                        raise ValueError('mutation target changed: ' + label)
                    contents = contents.replace(old, new, 1)
                (tmp / path.name).write_text(contents)
            binary = tmp / label
            subprocess.run([os.environ.get('CC', 'cc'), '-std=gnu11', '-O1', '-Wall',
                            '-Wextra', '-Werror', '-Wno-unused-parameter',
                            '-fsanitize=undefined', '-fno-sanitize-recover=all',
                            str(tmp / 'cases.c'), '-o', str(binary)], check=True, timeout=20)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=5)
            if label == 'kernel':
                if result.returncode:
                    raise RuntimeError(result.stderr)
                print(result.stdout.strip())
            elif result.returncode == 0 or 'FAIL ' not in result.stderr:
                raise ValueError('mutation escaped behavioral checks: ' + label)
            else:
                print('PASS rejected mutation ' + label + ': ' + result.stderr.strip())
    if pins != {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:
        raise ValueError('test inputs changed during execution')
    print('fixture_sha256=' + hashlib.sha256(str(sorted(pins.items())).encode()).hexdigest())
    print(f'PASS actual GENI mode fixtures; elapsed={time.monotonic() - started:.6f}s')
    print('NOT RUN adapter registration, hardware protocol/FIFO state, firmware loading, DMA, IRQ or touch')


if __name__ == '__main__':
    main()
