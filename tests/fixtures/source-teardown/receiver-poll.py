"""Exact sender/Receiver.poll integration inside the replay's fresh namespace."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,'/repo/scripts/host')
spec=importlib.util.spec_from_file_location('fixture_receiver','/repo/scripts/host/headless-stage-receiver.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
expected=json.loads(Path('/expected.json').read_text())
subprocess.run(['/bin/busybox','fixture-network'],check=True,timeout=2)
events=[];started=time.monotonic();child=None
with Path('/receiver-events.jsonl').open('x') as log:
    def emit(event):
        events.append(event)
        log.write(json.dumps(dict(event,monotonic=time.monotonic()))+'\n');log.flush()
        if event['event'] in ('source-teardown','source-teardown-diagnostic'):os.fsync(log.fileno())
    with M.Receiver(expected['identity']['release'],emit,source_boot_id=expected['identity']['boot_id'],
                    source_teardown=expected) as receiver:
        receiver.transport('source',None)
        original=receiver.record;raw_count=0
        def record(raw,peer):
            global raw_count
            name='/receipt'
            if raw.startswith(('format='+M.TEARDOWN.DIAGNOSTIC_FORMAT+'\n').encode()):
                name=f'/diagnostic-{raw_count}';raw_count+=1
            with Path(name).open('xb') as f:f.write(raw)
            original(raw,peer)
        receiver.record=record
        with Path('/sender.stdout').open('xb') as stdout,Path('/sender.stderr').open('xb') as stderr:
            child=subprocess.Popen(['/qemu','/lib/ld-musl-aarch64.so.1','/sealed/busybox','sh','/shutdown','reboot'],
                                   stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
            try:
                while child.poll() is None or receiver.clients:
                    if time.monotonic()-started>10:raise TimeoutError('assembled receiver fixture bound')
                    receiver.poll(.01)
            finally:
                if child.poll() is None:
                    child.kill();child.wait(timeout=2)
        passed=(not receiver.failed and receiver.teardown.receipt is not None
                and Path('/fallback').is_file() and Path('/fallback').read_text()=='requested\n'
                and child.returncode in (-15,143))
        result=dict(status='PASS' if passed else 'FAIL',seconds=time.monotonic()-started,
                    sender_returncode=child.returncode,receipt=receiver.teardown.receipt,
                    diagnostics=receiver.teardown.diagnostics,
                    receiver_sha256=hashlib.sha256(Path(M.__file__).read_bytes()).hexdigest(),
                    receiver_failed=receiver.failed,phone_action=False,
                    scope='real sealed sender and Receiver.poll on isolated loopback; synthetic kernel/USB')
Path('/receiver-poll.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(not passed)
