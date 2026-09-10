#!/usr/bin/env python3
"""Bound isolated suite concurrency by affinity and inherited cgroup CPU quota."""
import os
from pathlib import Path
import re


def worker_count(affinity, quotas, override=None):
    if affinity < 1:
        raise ValueError('empty CPU affinity')
    requested = 2
    if override is not None:
        if not re.fullmatch(r'[1-9][0-9]*', override) or len(override) > 2:
            raise ValueError('ROG5_TEST_WORKERS must be an integer from 1 to 32')
        requested = int(override)
        if requested > 32:
            raise ValueError('ROG5_TEST_WORKERS must be an integer from 1 to 32')
    available = affinity
    for value in quotas:
        quota, period = value.split()
        if not period.isdigit() or int(period) <= 0:
            raise ValueError('invalid cgroup CPU period')
        if quota == 'max':
            continue
        if not quota.isdigit() or int(quota) <= 0:
            raise ValueError('invalid cgroup CPU quota')
        # Fractional quotas still need one worker; never round up to two.
        available = min(available, max(1, int(quota) // int(period)))
    return min(requested, available)


def quotas_for_process(cgroup=Path('/proc/self/cgroup'), root=Path('/sys/fs/cgroup')):
    rows = cgroup.read_text().splitlines()
    unified = [row[3:] for row in rows if row.startswith('0::')]
    if len(unified) != 1:
        # Unknown/legacy hierarchy: serialize rather than infer unlimited CPU.
        return ['100000 100000']
    relative = unified[0]
    if not relative.startswith('/') or '..' in Path(relative).parts:
        raise ValueError('invalid unified cgroup path')
    current = root / relative.lstrip('/')
    if not current.is_dir():
        return ['100000 100000']
    quotas = []
    while True:
        path = current / 'cpu.max'
        try:
            quotas.append(path.read_text())
        except FileNotFoundError:
            pass  # Root may omit cpu.max; ancestors can still limit descendants.
        if current == root:
            break
        current = current.parent
    return quotas or ['100000 100000']


if __name__ == '__main__':
    try:
        print(worker_count(len(os.sched_getaffinity(0)), quotas_for_process(),
                           os.environ.get('ROG5_TEST_WORKERS')))
    except (OSError, ValueError) as error:
        raise SystemExit('test worker limit: ' + str(error))
