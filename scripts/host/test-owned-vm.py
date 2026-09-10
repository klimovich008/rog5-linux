#!/usr/bin/env -S -i /usr/bin/python3 -I -S
"""Exercise actual A01 ownership/cleanup flow with mocked Podman and clock."""
import importlib.util
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('owned_vm', Path(__file__).with_name('rog5_owned_vm.py'))
VM = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VM)
IMAGE = 'a' * 64
CID = 'b' * 64
COMMAND = ['podman', 'run', '--rm', '--pull=never', '--network=none',
           '--cap-drop=ALL', '--security-opt=no-new-privileges', '--cpus=2',
           '--memory=1g', '--memory-swap=1g', '-v', '/kernel:/Image:ro', IMAGE,
           'timeout', '--kill-after=2', '60', 'qemu-system-aarch64', '-M', 'virt',
           '-m', '512', '-smp', '2', '-nic', 'none']


class FakeProcess:
    pid = 123456789

    def __init__(self, transport):
        self.transport = transport
        self.returncode = None if transport.mode in ('timeout', 'stop-fail', 'reap-kill') else 0
        if transport.mode == 'killed':
            self.returncode = -9
        self.alive = self.returncode is None
        self.reaped = False

    def poll(self):
        return None if self.alive else self.returncode

    def wait(self, timeout):
        if self.alive:
            raise subprocess.TimeoutExpired('attach', timeout)
        self.reaped = True
        return self.returncode


class Transport:
    def __init__(self, mode='success'):
        self.mode = mode
        self.clock = 0.0
        self.commands = []
        self.info = None
        self.process = None
        self.started = False
        self.inspections = 0
        self.post_inspections = 0
        self.removed = False
        self.signals = []
        self.group_alive = False

    def sleep(self, duration):
        self.clock += duration

    def call(self, argv, timeout):
        self.commands.append(argv)
        action = argv[1]
        if action == 'create':
            name = argv[argv.index('--name') + 1]
            owner = argv[argv.index('--label') + 1].split('=', 1)[1]
            self.info = dict(Id=CID, Name='/' + name, Image=IMAGE,
                             Config={'Labels': {VM.LABEL: owner}},
                             State=dict(Running=False, OOMKilled=False, ExitCode=0))
            Path(argv[argv.index('--cidfile') + 1]).write_text(CID + '\n')
            if self.mode == 'late-create':
                raise subprocess.TimeoutExpired('create', timeout)
            if self.mode == 'create-fail':
                self.info = None
                return 125, '', 'create refused'
            return 0, ('bad' if self.mode == 'bad-cid' else CID) + '\n', ''
        if action == 'inspect':
            self.inspections += 1
            if self.mode == 'late-create' and self.inspections == 1:
                return 125, '', 'not yet visible'
            if self.info is None:
                return 125, '', 'absent'
            if self.started:
                self.post_inspections += 1
                if self.mode == 'inspect-timeout' and self.post_inspections == 1:
                    raise subprocess.TimeoutExpired('inspect', timeout)
            if self.mode == 'bad-json':
                return 0, '{broken', ''
            observed = json.loads(json.dumps(self.info))
            if self.mode == 'wrong-owner':
                observed['Config']['Labels'][VM.LABEL] = 'foreign'
            return 0, json.dumps([observed]), ''
        if action == 'stop':
            if self.mode == 'stop-fail':
                return 125, '', 'stop failed'
            self.info['State'].update(Running=False, ExitCode=143)
            return 0, CID, ''
        if action == 'kill':
            self.info['State'].update(Running=False, ExitCode=137)
            return 0, CID, ''
        if action == 'rm':
            if self.mode == 'remove-fail':
                return 125, '', 'remove failed'
            self.removed = True
            return 0, CID, ''
        if argv[1:3] == ['container', 'exists']:
            return (1 if self.removed else 0), '', ''
        raise AssertionError(argv)

    def popen(self, argv, **kwargs):
        self.commands.append(argv)
        assert argv == ['podman', 'start', '--attach', CID]
        assert kwargs['start_new_session'] is True
        self.started = True
        self.info['State']['Running'] = True
        if self.mode == 'start-ambiguous':
            raise OSError('attach failed after start')
        self.process = FakeProcess(self)
        self.group_alive = self.process.alive or self.mode == 'exited-descendants'
        if not self.process.alive:
            self.info['State'].update(Running=False,
                                      ExitCode=137 if self.mode == 'killed' else 0,
                                      OOMKilled=self.mode == 'oom')
        if self.mode == 'log-overflow':
            kwargs['stdout'].write(b'x' * (VM.LOG_LIMIT + 1))
            kwargs['stdout'].flush()
        if self.mode == 'missing-log':
            Path(kwargs['stdout'].name).unlink()
        return self.process

    def killpg(self, pid, number):
        assert pid == self.process.pid
        if number == 0:
            if not self.group_alive:
                raise ProcessLookupError()
            return
        self.signals.append(number)
        if self.mode != 'reap-kill' or number == signal.SIGKILL:
            self.group_alive = False
            self.process.alive = False
            self.process.returncode = -number


class Tests(unittest.TestCase):
    def exercise(self, mode='success', command=None):
        transport = Transport(mode)
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'runtime.log'
            with patch.object(VM, 'call', transport.call), \
                 patch.object(VM.subprocess, 'Popen', transport.popen), \
                 patch.object(VM.os, 'killpg', transport.killpg), \
                 patch.object(VM.time, 'monotonic', lambda: transport.clock), \
                 patch.object(VM.time, 'sleep', transport.sleep):
                result = VM.run(COMMAND if command is None else command, log,
                                deadline_seconds=0.1)
            if 'ownership_path' in result:
                initial = json.loads(Path(result['ownership_path']).read_text())
                self.assertFalse(initial['cleanup_confirmed'])
                final = Path(result['ownership_path']).with_suffix('.result.json')
                self.assertEqual(json.loads(final.read_text()), result)
        return result, transport

    def test_normal_terminal_evidence_and_argv_preservation(self):
        result, transport = self.exercise()
        self.assertTrue(result['passed'])
        self.assertTrue(result['cleanup']['confirmed'])
        self.assertEqual(result['container_id'], CID)
        create = transport.commands[0]
        self.assertNotIn('--rm', create)
        self.assertEqual(create[create.index(IMAGE):], COMMAND[COMMAND.index(IMAGE):])
        self.assertTrue(transport.process.reaped)

    def test_timeout_stops_owned_container_and_reaps(self):
        result, transport = self.exercise('timeout')
        self.assertFalse(result['passed'])
        self.assertEqual(result['exit_code'], 124)
        self.assertTrue(result['container_removed'])
        self.assertTrue(transport.process.reaped)
        self.assertIn('stop', [a[1] for a in transport.commands])

    def test_stop_failure_still_kills_inspects_removes_and_reaps(self):
        result, transport = self.exercise('stop-fail')
        self.assertFalse(result['passed'])
        self.assertTrue(result['cleanup']['errors'])
        self.assertIn('kill', [a[1] for a in transport.commands])
        self.assertTrue(result['container_removed'])
        self.assertTrue(transport.process.reaped)

    def test_failed_create_never_starts_and_stays_unconfirmed(self):
        result, transport = self.exercise('create-fail')
        self.assertFalse(result['passed'])
        self.assertFalse(transport.started)
        self.assertFalse(result['cleanup']['confirmed'])

    def test_late_create_reconciles_by_uuid_without_start(self):
        result, transport = self.exercise('late-create')
        self.assertFalse(result['passed'])
        self.assertFalse(transport.started)
        self.assertTrue(result['container_removed'])
        self.assertGreaterEqual(transport.inspections, 2)

    def test_malformed_cid_still_reconciles_name_without_start(self):
        result, transport = self.exercise('bad-cid')
        self.assertFalse(result['passed'])
        self.assertFalse(transport.started)
        self.assertTrue(result['container_removed'])

    def test_ownership_mismatch_never_starts_or_mutates_foreign_container(self):
        result, transport = self.exercise('wrong-owner')
        self.assertFalse(result['passed'])
        self.assertFalse(transport.started)
        self.assertTrue(all(a[1] in ('create', 'inspect') for a in transport.commands))

    def test_inspect_timeout_reconciles_but_cannot_pass(self):
        result, transport = self.exercise('inspect-timeout')
        self.assertFalse(result['passed'])
        self.assertTrue(result['cleanup']['errors'])
        self.assertTrue(result['container_removed'])
        self.assertTrue(transport.process.reaped)

    def test_malformed_inspect_never_starts_or_claims_cleanup(self):
        result, transport = self.exercise('bad-json')
        self.assertFalse(result['passed'])
        self.assertFalse(transport.started)
        self.assertFalse(result['cleanup']['confirmed'])

    def test_killed_or_oom_guest_cannot_pass(self):
        for mode in ('killed', 'oom'):
            with self.subTest(mode=mode):
                result, _ = self.exercise(mode)
                self.assertFalse(result['passed'])
                self.assertTrue(result['container_removed'])

    def test_ambiguous_start_still_stops_exact_owned_container(self):
        result, transport = self.exercise('start-ambiguous')
        self.assertFalse(result['passed'])
        self.assertTrue(result['container_removed'])
        self.assertIn('stop', [a[1] for a in transport.commands])

    def test_remove_failure_does_not_skip_client_reap(self):
        result, transport = self.exercise('remove-fail')
        self.assertFalse(result['passed'])
        self.assertFalse(result['container_removed'])
        self.assertTrue(transport.process.reaped)

    def test_attach_term_failure_escalates_and_stays_failed(self):
        result, transport = self.exercise('reap-kill')
        self.assertFalse(result['passed'])
        self.assertEqual(transport.signals, [signal.SIGTERM, signal.SIGKILL])
        self.assertTrue(transport.process.reaped)

    def test_final_log_bound_refuses_output_burst(self):
        result, _ = self.exercise('log-overflow')
        self.assertFalse(result['passed'])
        self.assertIn('console limit', result['error'])

    def test_exited_leader_surviving_descendants_are_closed_and_fail(self):
        result, transport = self.exercise('exited-descendants')
        self.assertFalse(result['passed'])
        self.assertEqual(transport.signals, [signal.SIGTERM])
        self.assertTrue(result['cleanup']['leader_reaped'])
        self.assertTrue(result['cleanup']['attach_group_closed'])
        self.assertTrue(result['cleanup']['confirmed'])

    def test_missing_log_returns_failure_after_owned_cleanup(self):
        result, transport = self.exercise('missing-log')
        self.assertFalse(result['passed'])
        self.assertIn('FileNotFoundError', result['error'])
        self.assertTrue(result['cleanup']['confirmed'])

    def test_actual_exited_process_group_leader_with_live_child(self):
        # Become the orphan's temporary reaper so this test does not depend on
        # the host PID1 promptly collecting zombies. No container is launched.
        libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(previous), 0, 0, 0), 0)
        self.assertEqual(libc.prctl(36, 1, 0, 0, 0), 0)
        leader = None
        reaper = None
        try:
            source = ('import os,signal\n'
                      'pid=os.fork()\n'
                      'if pid:\n'
                      ' os.write(1,(str(pid)+"\\n").encode());os._exit(0)\n'
                      'while True: signal.pause()\n')
            leader = subprocess.Popen([sys.executable, '-I', '-c', source],
                                      stdout=subprocess.PIPE, start_new_session=True)
            child = int(leader.stdout.readline())
            leader.stdout.close()
            self.assertEqual(leader.wait(timeout=2), 0)
            self.assertTrue(VM.group_exists(leader.pid))
            reaper = threading.Thread(target=lambda: os.waitpid(child, 0), daemon=True)
            reaper.start()
            record = dict(name='fixture', owner='nonce', image=IMAGE)
            transport = Transport()
            transport.info = dict(Id=CID, Name='/fixture', Image=IMAGE,
                                 Config={'Labels': {VM.LABEL: 'nonce'}},
                                 State=dict(Running=False, OOMKilled=False, ExitCode=0))
            result = dict(container_id=CID, container_state=None, container_removed=False,
                          cleanup=dict(errors=[], actions=[], forced_stop=False))
            with patch.object(VM, 'call', transport.call):
                VM.cleanup(record, result, leader)
            reaper.join(timeout=2)
            self.assertFalse(reaper.is_alive())
            self.assertEqual(result['cleanup']['errors'], [])
            self.assertTrue(result['cleanup']['forced_stop'])
            self.assertTrue(result['cleanup']['client_reaped'])
            self.assertTrue(result['cleanup']['attach_group_closed'])
            self.assertFalse(VM.group_exists(leader.pid))
        finally:
            if leader is not None:
                VM.signal_group(leader.pid, signal.SIGKILL)
                leader.wait(timeout=2)
            if reaper is not None:
                reaper.join(timeout=2)
            libc.prctl(36, previous.value, 0, 0, 0)

    def test_missing_swap_mutable_mount_and_unpinned_image_refuse_before_create(self):
        for old, new in (('--memory-swap=1g', '--memory-swap=2g'),
                         ('/kernel:/Image:ro', '/kernel:/Image:rw'),
                         (IMAGE, 'latest')):
            with self.subTest(old=old):
                command = [new if a == old else a for a in COMMAND]
                result, transport = self.exercise(command=command)
                self.assertFalse(result['passed'])
                self.assertEqual(transport.commands, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
