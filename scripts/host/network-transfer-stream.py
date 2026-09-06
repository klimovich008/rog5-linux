#!/usr/bin/env python3
"""Bounded pipe-transfer primitive, NOT device identity or S02 qualification.

The caller owns endpoint authentication, interface binding and release evidence.
No shell, listener, payload file, retry or phone discovery is provided here.
"""
import argparse
import hashlib
import json
import math
import os
import re
import selectors
import signal
import subprocess
import sys
import time

LIMIT = 256 * 1024 * 1024
BLOCK = 65536


class TransferError(RuntimeError):
    pass


def validate(nonce, size):
    if type(size) is not int or not 0 < size <= LIMIT:
        raise ValueError('invalid byte count')
    if not isinstance(nonce, str) or not re.fullmatch('[0-9a-f]{64}', nonce):
        raise ValueError('invalid nonce')


def payload(nonce, size):
    validate(nonce, size)
    seed = bytes.fromhex(nonce)
    for offset in range(0, size, BLOCK):
        # SHAKE avoids compressible repeating blocks, with bounded memory.
        yield hashlib.shake_256(seed + offset.to_bytes(8, 'big')).digest(
            min(BLOCK, size - offset))


def expected_digest(nonce, size):
    digest = hashlib.sha256()
    for block in payload(nonce, size):
        digest.update(block)
    return digest.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate receipt field')
        result[key] = value
    return result


def transfer(argv, direction, nonce, size, timeout):
    """Stream one owned subprocess; deadline includes preparation and exit."""
    validate(nonce, size)
    if (direction not in ('upload', 'download') or
            type(timeout) not in (int, float) or
            not math.isfinite(timeout) or not 0 < timeout <= 180):
        raise ValueError('invalid direction or deadline')
    if not isinstance(argv, (list, tuple)) or not argv or not all(
            isinstance(arg, str) and arg and '\0' not in arg for arg in argv):
        raise ValueError('argv must be explicit nonempty strings')
    start = time.monotonic()
    deadline = start + timeout
    expected = hashlib.sha256()
    for block in payload(nonce, size):
        expected.update(block)
        if time.monotonic() >= deadline:
            raise TransferError('deadline during preparation')
    expected = expected.hexdigest()
    process = subprocess.Popen(argv, start_new_session=True, bufsize=0,
        stdin=subprocess.PIPE if direction == 'upload' else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    receipt = bytearray()
    errors = bytearray()
    digest = hashlib.sha256()
    count = 0
    blocks = iter(payload(nonce, size))
    pending = memoryview(next(blocks)) if direction == 'upload' else None
    try:
        for stream, event in ((process.stdout, selectors.EVENT_READ),
                              (process.stderr, selectors.EVENT_READ),
                              (process.stdin, selectors.EVENT_WRITE)):
            if stream is not None:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, event)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TransferError('transfer deadline exceeded')
            for key, _ in selector.select(remaining):
                stream = key.fileobj
                if stream is process.stdin:
                    try:
                        written = os.write(stream.fileno(), pending)
                    except BlockingIOError:
                        continue
                    pending = pending[written:]
                    if not pending:
                        block = next(blocks, None)
                        if block is None:
                            selector.unregister(stream)
                            stream.close()
                        else:
                            pending = memoryview(block)
                    continue
                try:
                    data = os.read(stream.fileno(), BLOCK)
                except BlockingIOError:
                    continue
                if not data:
                    selector.unregister(stream)
                    stream.close()
                elif stream is process.stderr:
                    if len(errors) + len(data) > 4096:
                        raise TransferError('stderr limit exceeded')
                    errors.extend(data)
                elif direction == 'upload':
                    if len(receipt) + len(data) > 1024:
                        raise TransferError('receipt limit exceeded')
                    receipt.extend(data)
                else:
                    count += len(data)
                    if count > size:
                        raise TransferError('excess payload')
                    digest.update(data)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TransferError('exit deadline exceeded')
        if process.wait(timeout=remaining) != 0:
            raise TransferError('endpoint exited unsuccessfully')
        if direction == 'upload':
            try:
                record = json.loads(receipt, object_pairs_hook=unique_object)
            except (ValueError, UnicodeError) as exc:
                raise TransferError('invalid receipt') from exc
            wanted = dict(format='rog5-transfer-v1', bytes=size, sha256=expected)
            if not isinstance(record, dict) or type(record.get('bytes')) is not int or record != wanted:
                raise TransferError('receipt mismatch')
        elif count != size or digest.hexdigest() != expected:
            raise TransferError('payload length or digest mismatch')
        return dict(bytes=size, sha256=expected, returncode=0,
                    duration_seconds=time.monotonic() - start, s02_qualified=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TransferError('deadline exceeded' if isinstance(exc, subprocess.TimeoutExpired)
                            else 'endpoint I/O failure') from exc
    finally:
        # Also kill descendants retaining pipe FDs; never retry the command.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        selector.close()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def endpoint(action, nonce, size):
    validate(nonce, size)
    if action == 'send':
        for block in payload(nonce, size):
            sys.stdout.buffer.write(block)
        sys.stdout.buffer.flush()
        return
    digest = hashlib.sha256()
    count = 0
    while True:
        block = sys.stdin.buffer.read(min(BLOCK, size - count + 1))
        if not block:
            break
        count += len(block)
        if count > size:
            raise TransferError('excess payload')
        digest.update(block)
    if count != size or digest.hexdigest() != expected_digest(nonce, size):
        raise TransferError('payload length or digest mismatch')
    print(json.dumps(dict(format='rog5-transfer-v1', bytes=count, sha256=digest.hexdigest())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('send', 'receive'))
    parser.add_argument('--bytes', type=int, required=True)
    parser.add_argument('--nonce', required=True)
    args = parser.parse_args()
    # Bound an endpoint even if its supervising connection vanishes.
    def expired(_signum, _frame):
        raise TransferError('endpoint deadline exceeded')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 180)
    try:
        endpoint(args.action, args.nonce, args.bytes)
    except (ValueError, OSError, TransferError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
