#!/usr/bin/python3 -S
"""Owned-process regressions only: fake compiler; NEVER compile/run touch C.

--before is the byte-preserved original harness, not a previous runner rewrite.
Each scenario uses an owned private repository, a real compiler/child/grandchild
process tree, a separate sentinel, disk logs and independent subreaper cleanup.
"""
import os
import sys
if not sys.flags.no_site:
    os.execv(sys.executable, [sys.executable, '-S', '-B', *sys.orig_argv[1:]])
sys.dont_write_bytecode = True
import argparse
import ctypes
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[4]
REL = 'scripts/device/test-rog5-touch-input-core.py'
FIX = 'scripts/device/fixtures/fts3658u-input-core'
BEFORE_SHA = '0961c7fc4aac0b454ab525d826106e2332484a6be5df427925b597e1bcc29b83'
UNIT_SHA = '9a4aff51520f8ace82384a26711608dab245250c79c35e97f6ad525c1a5061ad'
CANCEL = 0


def need(test, message):
    if not test:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def stat(pid):
    try:
        f = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return dict(pid=pid, state=f[0], ppid=int(f[1]), pgid=int(f[2]), start_ticks=f[19])
    except (FileNotFoundError, ProcessLookupError):
        return None


def same(record):
    now = stat(record['pid'])
    return now is not None and now['start_ticks'] == record['start_ticks']


def direct():
    # Independent fixture cleanup: PPID discovery, then waitid validation.
    return [int(p.name) for p in Path('/proc').iterdir() if p.name.isdigit()
            and (r := stat(int(p.name))) is not None and r['ppid'] == os.getpid()]


def observe(pid):
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)


def no_children():
    try:
        os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        return True
    return False


def sweep():
    """Only this fixture's unreaped direct/adopted children can be signalled."""
    end = time.monotonic() + 2
    while not no_children():
        owned = direct()
        for pid in owned:
            observe(pid)  # Fail closed if not our waitable child; pins PID.
            if os.getpgid(pid) == pid:
                os.killpg(pid, signal.SIGKILL)
            else:
                os.kill(pid, signal.SIGKILL)
        for pid in owned:
            if observe(pid) is not None:
                os.waitpid(pid, 0)
        need(time.monotonic() < end, 'independent fixture cleanup deadline')
        time.sleep(.005)


def interrupt(signum, frame):
    global CANCEL
    CANCEL = CANCEL or signum


def tick(end):
    need(not CANCEL, f'fixture cancelled by signal {CANCEL}')
    need(time.monotonic() < end, 'fixture deadline')
    time.sleep(.005)


def wait_json(path, end, pid=None):
    while not path.exists():
        if pid is not None:
            need(observe(pid) is None, 'process exited before fixture READY')
        tick(end)
    return json.loads(path.read_text())


def wait_exit(proc, end):
    while observe(proc.pid) is None:
        tick(end)
    return proc.wait()


def make_tree(scratch):
    """Two genuine descendant generations, ignoring TERM/INT to require KILL."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    ready = Path(os.environ['CANCELLATION_READY'])
    mode = os.environ['RUNNER_REGRESSION_MODE']
    child_ready = ready.with_name('child.json')
    child = subprocess.Popen([sys.executable, '-S', '-B', __file__, '--descendant',
                              str(child_ready)], start_new_session=(mode == 'escaped'))
    records = wait_json(child_ready, time.monotonic() + 3, child.pid)
    value = dict(scratch=str(scratch), records=[stat(os.getpid()), *records])
    save(ready, value)
    print('READY synthetic process tree; no C compilation or device access', flush=True)
    return value


def descendant(ready):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    leaf_ready = ready.with_name('leaf.json')
    leaf = subprocess.Popen([sys.executable, '-S', '-B', __file__, '--leaf', str(leaf_ready)],
                            start_new_session=os.environ['RUNNER_REGRESSION_MODE'] == 'escaped')
    record = wait_json(leaf_ready, time.monotonic() + 3, leaf.pid)
    save(ready, [stat(os.getpid()), record])
    time.sleep(60)


def fake_compile():
    if sys.argv[1:] == ['--version']:
        print('runner regression fake compiler; NEVER compiled touch C')
        return 0
    mode = os.environ['RUNNER_REGRESSION_MODE']
    unit = next(Path(a) for a in sys.argv[1:] if a.endswith('.c'))
    if mode == 'compile-failure':
        print('FAIL synthetic compiler infrastructure error', flush=True)
        return 86
    if mode.startswith('mutant-') or mode == 'semantic-control':
        binary = Path(sys.argv[sys.argv.index('-o') + 1])
        binary.write_text('#!/usr/bin/python3 -S\nimport os\nos.execv(' + repr(sys.executable) +
                          ', ' + repr([sys.executable, '-S', '-B', __file__, '--fake-binary',
                                      str(binary)]) + ')\n')
        binary.chmod(0o700)
        return 0
    make_tree(unit.parent)
    if mode == 'background':
        return 0
    time.sleep(60)
    return 0


def fake_binary(binary):
    if binary.name == 'baseline':
        return 0
    mode = os.environ['RUNNER_REGRESSION_MODE']
    print('FAIL synthetic CHECK for runner-classification control only', flush=True)
    if mode == 'mutant-signal':
        os.kill(os.getpid(), signal.SIGTERM)
    if mode == 'mutant-ubsan':
        print('runtime error: synthetic UBSan infrastructure control', flush=True)
    if mode in ('mutant-background', 'mutant-timeout'):
        make_tree(binary.parent)
        if mode == 'mutant-timeout':
            time.sleep(60)
    return 1


# Test-only monkeypatches. The real harness and ownership helper are imported,
# not edited. No production test flags, sleep knobs or synthetic-success mode.
ADAPTER = r'''
import sys, os, time, json, signal, subprocess, importlib.util
from pathlib import Path
sys.dont_write_bytecode = True
path, mode = Path(sys.argv[1]), sys.argv[2]
spec = importlib.util.spec_from_file_location('actual_harness', path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
sys.argv = [str(path)]
ready = Path(os.environ['CANCELLATION_READY'])

def wait_ready():
    end = time.monotonic() + 3
    while not ready.exists():
        if time.monotonic() >= end:
            raise RuntimeError('injection READY timeout')
        time.sleep(.005)

def target(proc):
    return '-std=gnu11' in proc.args or Path(str(proc.args[0])).name == 'no-abs-suppression'

if mode in ('timeout', 'wait-error', 'mutant-timeout'):
    original = m.OwnedCommands._await
    def await_injected(self, proc, end):
        if target(proc) and (mode != 'mutant-timeout' or '-std=gnu11' not in proc.args):
            wait_ready()
            if mode == 'wait-error':
                raise RuntimeError('injected unexpected wait exception')
            end = time.monotonic() + .03
        return original(self, proc, end)
    m.OwnedCommands._await = await_injected
if mode in ('launch-signal', 'launch-exception'):
    original_popen = subprocess.Popen
    held = []
    def popen_injected(argv, *a, **kw):
        proc = original_popen(argv, *a, **kw)
        if '-std=gnu11' in argv:
            held.append(proc)
            wait_ready()
            ready.with_name('launch-gap.json').write_text(json.dumps({'pid':proc.pid}))
            if mode == 'launch-exception':
                raise RuntimeError('injected exception before Popen return/registration')
            os.kill(os.getpid(), signal.SIGTERM)
            os.kill(os.getpid(), signal.SIGINT)
        return proc
    subprocess.Popen = popen_injected
if mode in ('repeat', 'cleanup-refusal'):
    original_signal = m.OwnedCommands._signal_child
    def injected_signal(self, pid):
        if ready.exists():
            if mode == 'cleanup-refusal':
                return  # A controlled infrastructure failure, never a kill credit.
            os.kill(os.getpid(), signal.SIGINT)
            os.kill(os.getpid(), signal.SIGTERM)
            ready.with_name('repeated.json').write_text('true\n')
        return original_signal(self, pid)
    m.OwnedCommands._signal_child = injected_signal
if mode == 'stale-inventory':
    # Deterministically expose a real adoption AFTER an earlier child snapshot.
    # Signal suppression/delayed delivery is test-only, not production behavior.
    import owned_process
    original_children = owned_process.children
    original_signal = m.OwnedCommands._signal_child
    delayed = {'owner': None, 'done': False}
    def delayed_signal(self, pid):
        if ready.exists() and not delayed['done']:
            root = json.loads(ready.read_text())['records'][0]['pid']
            if pid == root:
                delayed['owner'] = self
                return
        return original_signal(self, pid)
    def stale_children():
        snapshot = original_children()
        if delayed['owner'] is not None and not delayed['done']:
            delayed['done'] = True
            root = json.loads(ready.read_text())['records'][0]['pid']
            original_signal(delayed['owner'], root)
            end = time.monotonic() + 2
            while owned_process.exited(root) is None:
                if time.monotonic() >= end:
                    raise RuntimeError('delayed exit did not finish')
                time.sleep(.005)
            ready.with_name('stale-inventory.json').write_text(json.dumps(snapshot))
        return snapshot
    m.OwnedCommands._signal_child = delayed_signal
    owned_process.children = stale_children
if mode.startswith('mutant-') or mode == 'semantic-control':
    # Exercise ONLY the orchestration gate with fake executables, not touch C.
    m.CASES = ('unchanged-empty',)
    m.CORE_MUTANTS = m.CORE_MUTANTS[:1]
    m.DRIVER_MT_MUTANTS = ()

original_rmtree = m.shutil.rmtree
def checked_rmtree(path, *a, **kw):
    path = Path(path)
    if path.name.startswith('fts3658u-input-core-'):
        import owned_process
        if not owned_process.no_children():
            raise RuntimeError('scratch deletion preceded owned child reaping')
        if ready.exists():
            for row in json.loads(ready.read_text())['records']:
                p = Path('/proc') / str(row['pid']) / 'stat'
                if p.exists() and p.read_text().rsplit(')',1)[1].split()[19] == row['start_ticks']:
                    raise RuntimeError('scratch deletion preceded descendant disappearance')
        ready.with_name('delete-order.json').write_text('"all owned children reaped first"\n')
    return original_rmtree(path, *a, **kw)
m.shutil.rmtree = checked_rmtree
raise SystemExit(m.entrypoint())
'''


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row():
    return dict(path=REL, interpreter='python3', tiers=['board'], mandatory=True,
                deadline_seconds=90, prerequisites=['cc'], resource_class='high-memory',
                exclusivity_group='repository', python_optimized=True, exact_source=True,
                required_inputs=[e['label'][5:] for e in json.loads(
                    (ROOT / FIX / 'source-pins.json').read_text())['sources']
                    if e['label'].startswith('repo/')] + [FIX + '/' + n for n in
                                 ('source-pins.json', 'types.h.in', 'boundary.h', 'cases.c',
                                  'owned_process.py')], optional_subchecks=[])


def private_repo(target, before=None):
    pins = json.loads((ROOT / FIX / 'source-pins.json').read_text())
    paths = [e['label'][5:] for e in pins['sources'] if e['label'].startswith('repo/')]
    paths += [str(f.relative_to(ROOT)) for f in (ROOT / FIX).iterdir() if f.is_file()]
    paths += [REL, 'scripts/host/repository-test-report.py']
    for rel in paths:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dest)
    if before:
        shutil.copyfile(before, target / REL)
    config = target / 'configs/repository-tests.json'
    config.parent.mkdir(exist_ok=True)
    config.write_text(json.dumps(dict(tests=[row()]), indent=2) + '\n')
    fake = target / FIX / 'runner-regression.py'
    fake.chmod(0o700)
    return fake


def scenario(out, name, mode, linux, before=None, reporter=False, missing=False, batch_end=None):
    directory = out / name
    directory.mkdir()
    repo = directory / 'repo'
    fake = private_repo(repo, before)
    ready = directory / 'ready.json'
    report = directory / 'report'
    env = dict(os.environ, CC=str(fake), ROG5_LINUX_SOURCE=str(linux),
               CANCELLATION_READY=str(ready), RUNNER_REGRESSION_MODE=mode)
    if missing:
        env.pop('ROG5_LINUX_SOURCE')
    if reporter:
        report.mkdir()
        argv = [sys.executable, '-S', '-B', '-O', str(repo / 'scripts/host/repository-test-report.py'),
                'run', str(repo), str(report), REL]
    elif before:
        argv = [sys.executable, '-S', '-B', '-O', str(repo / REL), '--linux-source', str(linux)]
    elif mode in ('term', 'int', 'escaped', 'compile-failure', 'background') or missing:
        argv = [sys.executable, '-O', str(repo / REL)]  # EXACT repository child interface.
    else:
        adapter = directory / 'adapter.py'
        adapter.write_text(ADAPTER)
        argv = [sys.executable, '-S', '-B', '-O', str(adapter), str(repo / REL), mode]
    result = dict(name=name, command=argv, mode=mode, real_C_compilation=False,
                  physical='NOT RUN', expected_negative=bool(before), input_sha256=digest(repo / REL))
    proc = sentinel = None
    started = time.monotonic()
    end = min(started + 12, batch_end) if batch_end is not None else started + 12
    try:
        with (directory / 'sentinel.log').open('wb') as f:
            sentinel = subprocess.Popen([sys.executable, '-S', '-B', '-c', 'import time; time.sleep(60)'],
                                        stdout=f, stderr=f, start_new_session=True)
        sentinel_id = stat(sentinel.pid)
        with (directory / 'harness.log').open('wb') as f:
            proc = subprocess.Popen(argv, env=env, cwd=repo, stdout=f, stderr=f, start_new_session=True)
        if mode in ('term', 'int', 'repeat', 'escaped', 'cleanup-refusal', 'stale-inventory') and not missing:
            value = wait_json(ready, min(started + 7, end), proc.pid)
            need(value['records'][0]['ppid'] == proc.pid, 'fixture root is not actual harness child')
            need(all(same(r) for r in value['records']), 'fixture tree not live before cancellation')
            os.kill(proc.pid, signal.SIGINT if mode == 'int' else signal.SIGTERM)  # Runner ONLY.
        rc = wait_exit(proc, end)
        result['exit'] = rc
        log = (directory / 'harness.log').read_text()
        result['log_sha256'] = digest(directory / 'harness.log')
        value = json.loads(ready.read_text()) if ready.exists() else None
        if value:
            records = value['records']
            need(len(records) == 3 and len({r['pid'] for r in records}) == 3, 'need three genuine processes')
            need(records[1]['ppid'] == records[0]['pid'] and records[2]['ppid'] == records[1]['pid'],
                 'compiler/child/grandchild ancestry differs')
            need(all(r['pgid'] == (r['pid'] if mode == 'escaped' else records[0]['pid'])
                     for r in records), 'fixture session/group shape differs')
        surviving = [r for r in value['records'] if same(r)] if value else []
        scratch = Path(value['scratch']) if value else None
        result.update(fixture=value, survivors_before_fixture_cleanup=surviving,
                      scratch_before_fixture_cleanup=scratch.exists() if scratch else None,
                      sentinel_untouched=same(sentinel_id) and observe(sentinel.pid) is None)
        need(result['sentinel_untouched'], 'unrelated-to-harness sentinel was signalled')
        if before:
            need(rc == -signal.SIGTERM and surviving and scratch.is_dir(), 'original negative not reproduced')
        elif mode == 'cleanup-refusal':
            need(rc == 1 and surviving and scratch.is_dir() and 'scratch retained:' in log,
                 'unproven drain must fail and retain scratch')
        else:
            need(not surviving, 'owned compiler/descendant remains (including zombies)')
            need(scratch is None or not scratch.exists(), 'scratch remains after proven cleanup')
            need(not list((repo / 'build').glob('fts3658u-input-core-*')),
                 'scratch remains without a READY record')
            expected = 0 if mode == 'semantic-control' else 2 if missing and not reporter else 1
            need(rc == expected, f'wrong runner exit {rc}, expected {expected}: {log[-1600:]}')
        if not before and not missing:
            need('PASS applicability: 32 exact function bodies' in log, 'source comparisons not executed')
            need('python_no_site=1' in log, 'no-site re-exec missing')
            need(('PASS behavioral: rejects ' in log) == (mode == 'semantic-control'),
                 'infrastructure failure was credited as a semantic mutant kill')
        if mode in ('term', 'int', 'repeat', 'escaped', 'launch-signal', 'stale-inventory') and not before:
            need(f'cancelled by signal {2 if mode == "int" else 15}' in log, 'first cancellation cause lost')
        if mode.startswith('launch-'):
            need((directory / 'launch-gap.json').is_file(), 'launch/registration gap not exercised')
        if mode == 'stale-inventory':
            need((directory / 'stale-inventory.json').is_file(), 'stale inventory window not exercised')
        if mode == 'repeat':
            need((directory / 'repeated.json').is_file(), 'repeat signal during cleanup not injected')
        if not before and not missing and not reporter and mode not in (
                'term', 'int', 'escaped', 'compile-failure', 'background', 'cleanup-refusal'):
            need((directory / 'delete-order.json').is_file(), 'deletion ordering not observed')
            result['deletion_order'] = json.loads((directory / 'delete-order.json').read_text())
        if mode in ('timeout', 'mutant-timeout'):
            need('command timeout (not a mutation kill)' in log, 'internal timeout not exercised')
        if mode == 'wait-error':
            need('injected unexpected wait exception' in log, 'wait exception not exercised')
        if mode in ('background', 'mutant-background'):
            need('background descendants' in log, 'background descendants not refused')
        if reporter:
            key = hashlib.sha256(REL.encode()).hexdigest()[:20]
            r = json.loads((report / (key + '.json')).read_text())
            need(r['status'] == ('BLOCKED' if missing else 'FAIL'), 'reporter classification changed')
            if not missing:
                need(r['command'] == ['python3', '-O', str(repo / REL)], 'reporter argv contract changed')
                need(any(x.startswith('PASS applicability: 32') for x in r['source_sections']),
                     'reporter lost source applicability section')
            result['repository_result'] = r
        result['status'] = 'PASS expected original failure' if before else 'PASS runner regression'
    except BaseException as error:
        result.update(status='FAIL fixture/regression', error=repr(error))
        raise
    finally:
        # Independent rescue handles the original leak and injected cleanup failure.
        # The sentinel is ours, too, but was asserted untouched before this cleanup.
        sweep()
        if proc is not None and proc.returncode is None:
            proc.returncode = -signal.SIGKILL  # Already reaped by independent rescue.
        if sentinel is not None:
            sentinel.returncode = -signal.SIGKILL
        for path in (repo / 'build').glob('fts3658u-input-core-*') if (repo / 'build').exists() else ():
            need(path.parent == repo / 'build' and not path.is_symlink(), 'unsafe fixture scratch path')
            shutil.rmtree(path)
        result.update(fixture_cleanup_complete=no_children(), elapsed_seconds=time.monotonic() - started)
        save(directory / 'result.json', result)
    print('PASS runner regression: ' + name, flush=True)
    return result


def late_cancellation():
    """A first SIGINT during handler restoration must not become success."""
    from unittest.mock import patch
    helper = load(ROOT / FIX / 'owned_process.py', 'late_cancel_owner')
    original_signal = signal.signal
    original_int = signal.getsignal(signal.SIGINT)
    sent = []
    def restoring(signum, handler):
        if signum == signal.SIGINT and handler is original_int and not sent:
            sent.append(signum)
            signal.raise_signal(signal.SIGINT)
        return original_signal(signum, handler)
    owner = helper.OwnedCommands()
    caught = None
    try:
        with patch.object(signal, 'signal', restoring):
            with owner:
                pass
    except helper.Cancelled as error:
        caught = error
    need(sent == [signal.SIGINT] and caught is not None and owner.cancelled == signal.SIGINT,
         'late cancellation incorrectly returned success')
    need(signal.getsignal(signal.SIGINT) is original_int and no_children(),
         'late cancellation did not restore clean ownership')
    print('PASS runner cleanup: first SIGINT during handler restoration', flush=True)
    return dict(status='PASS', signal='SIGINT', cancellation_raised=True,
                handlers_restored=True, no_children=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before', required=True, type=Path)
    p.add_argument('--linux-source', type=Path, default=os.environ.get('ROG5_LINUX_SOURCE'))
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    need(os.geteuid() != 0, 'run unprivileged')
    need(args.linux_source is not None and args.linux_source.is_dir(), 'supply retained exact Linux source')
    need(digest(args.before) == BEFORE_SHA, 'before file is not the preserved supplied original')
    need(no_children(), 'fixture must start with no children')
    need(ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0, 'fixture subreaper setup')
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupt)
    m = load(ROOT / REL, 'source_comparison_only')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    m.disk_backed(args.output.parent)
    args.output.mkdir(exist_ok=False)
    out = args.output.resolve()
    watched = [ROOT / REL, *(ROOT / FIX).glob('*'), ROOT / 'scripts/host/repository-test-report.py']
    before = {str(f):digest(f) for f in watched if f.is_file()}
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (384 * 1024**2, 384 * 1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024**2, 8 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    started = time.monotonic()
    linux = m.sources(argparse.Namespace(packet=None, packet_manifest=None, linux_source=args.linux_source),
                      json.loads((ROOT / FIX / 'source-pins.json').read_text()))
    parts, audit = m.compose(linux)
    original = load(args.before, 'preserved_original_constants')
    for name in ('CASES', 'CORE_MUTANTS', 'DRIVER_MT_MUTANTS', 'OLD_FUNCS', 'CORE_FUNCS'):
        need(getattr(m, name) == getattr(original, name), 'original scope changed: ' + name)
    need(len(m.CASES) == 13 and len(m.CORE_MUTANTS) + len(m.DRIVER_MT_MUTANTS) == 18,
         'semantic scope changed')
    unit = '\n'.join(parts.values()).encode()
    need(len(audit) == 32 and hashlib.sha256(unit).hexdigest() == UNIT_SHA, 'compiled unit changed')
    save(out / 'source-comparisons.json', audit)
    (out / 'composed-unit.c').write_bytes(unit)
    save(out / 'manifest-row.json', row())
    report = load(ROOT / 'scripts/host/repository-test-report.py', 'unchanged_reporter')
    probe = dict(status='PASS')
    sections = ['PASS applicability: source', 'PASS compilation: baseline',
                'PASS behavioral: synthetic parser probe', 'NOT RUN physical']
    report.classify_output(row(), probe, sections)
    need(probe['status'] == 'PASS' and probe['source_sections'] == sections, 'report section interface')
    blocked = dict(status='PASS')
    report.classify_output(row(), blocked, ['BLOCKED exact source'])
    need(blocked['status'] == 'BLOCKED', 'BLOCKED interface')
    save(out / 'report-parser.json', dict(pass_probe=probe, blocked_probe=blocked))
    late = late_cancellation()
    save(out / 'late-cancellation.json', late)
    results = []
    tests = [('before-term', 'term', True, False, False),
             ('after-term-no-argv', 'term', False, False, False),
             ('after-int', 'int', False, False, False),
             ('after-repeat', 'repeat', False, False, False),
             ('after-launch-signal', 'launch-signal', False, False, False),
             ('after-launch-exception', 'launch-exception', False, False, False),
             ('after-stale-inventory', 'stale-inventory', False, False, False),
             ('after-timeout', 'timeout', False, False, False),
             ('after-wait-exception', 'wait-error', False, False, False),
             ('after-background', 'background', False, False, False),
             ('after-escaped-descendants', 'escaped', False, False, False),
             ('cleanup-unproven-retains-scratch', 'cleanup-refusal', False, False, False),
             ('semantic-gate-positive-synthetic', 'semantic-control', False, False, False),
             ('mutant-signal-not-kill', 'mutant-signal', False, False, False),
             ('mutant-ubsan-not-kill', 'mutant-ubsan', False, False, False),
             ('mutant-background-not-kill', 'mutant-background', False, False, False),
             ('mutant-timeout-not-kill', 'mutant-timeout', False, False, False),
             ('direct-missing-source', 'compile-failure', False, False, True),
             ('reporter-no-argv', 'compile-failure', False, True, False),
             ('reporter-missing-source', 'compile-failure', False, True, True)]
    for name, mode, negative, reporter, missing in tests:
        tick(started + 80)
        results.append(scenario(out, name, mode, args.linux_source.resolve(),
                                args.before if negative else None, reporter, missing, started + 80))
    need(before == {str(f):digest(f) for f in watched if f.is_file()}, 'source changed')
    save(out / 'results.json', dict(status='PASS', scenarios=results, inputs=before,
         python=sys.version, uid=os.geteuid(), elapsed_seconds=time.monotonic()-started,
         source_comparisons=32, unit_sha256=UNIT_SHA, real_C_compilation=False,
         semantic_13_18='NOT RERUN; unchanged unit and lists verified', legacy_27_8='NOT RUN',
         physical='NOT RUN'))
    print(f'PASS runner regression: {len(results)} scenarios; 32 source comparisons; unchanged unit')
    print('NOT RUN actual 13/18 or legacy 27/8 semantics; compiler and binaries here are fixtures')
    print('NOT RUN kernel concurrency, evdev/libinput, physical touch or phone operations')
    return 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--version'] or '-std=gnu11' in sys.argv:
        sys.exit(fake_compile())
    if sys.argv[1:2] == ['--descendant']:
        descendant(Path(sys.argv[2])); sys.exit(0)
    if sys.argv[1:2] == ['--leaf']:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        save(Path(sys.argv[2]), stat(os.getpid()))
        time.sleep(60); sys.exit(0)
    if sys.argv[1:2] == ['--fake-binary']:
        sys.exit(fake_binary(Path(sys.argv[2])))
    try:
        sys.exit(main())
    except (Exception, KeyboardInterrupt) as error:
        print('FAIL runner regression: ' + repr(error), file=sys.stderr, flush=True)
        sys.exit(1)
