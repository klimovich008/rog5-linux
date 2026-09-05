#!/usr/bin/env python3
"""Offline user-systemd keyring ordering; all GPG/storage/SSH endpoints are fixtures.

Extracts the dirty init's drop-in; does not execute init or qualify ARM GPG.
Only uniquely owned runtime links are removed; artifacts remain under --output.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
R = Path(__file__).resolve().parents[2]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    if output.exists() or output.is_relative_to(R):
        parser.error('output must be new and outside the repository')
    os.umask(0o077)
    output.mkdir(mode=0o700)
    started = time.monotonic()
    report = dict(status='FAIL', scope=__doc__, cases=[], commands=[], cleanup=[])
    links = {}; owned = []; sources = {}

    def ctl(*args, check=True):
        p = subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True, timeout=10)
        report['commands'].append(dict(args=args, returncode=p.returncode, stdout=p.stdout,
                                       stderr=p.stderr, seconds=round(time.monotonic()-started, 6)))
        require(not check or p.returncode == 0, 'systemctl failed: '+shlex.join(args))
        return p

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def identity(names):
        result = {}
        for name in names:
            values = dict(line.split('=', 1) for line in ctl('show', name, '-p', 'ActiveState',
                          '-p', 'InvocationID', '-p', 'MainPID').stdout.splitlines())
            require(values['ActiveState'] == 'active' and values['InvocationID'], 'inactive core: '+name)
            result[name] = values
        return result

    try:
        try:
            available = ctl('show', '--property=Version', check=False).returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            available = False
        if not available:
            report['status'] = 'BLOCKED'
            raise RuntimeError('no available user systemd manager')
        spec = importlib.util.spec_from_file_location('keyring_core', R/'scripts/host/test-systemd-ssh-rollback.py')
        core_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(core_module)
        inputs = {Path(__file__).resolve(), R/'initramfs/persistent-root-init',
                  Path(core_module.__file__), R/'configs/systemd/rog5-package-keyring.service'}
        sources = {str(p.relative_to(R)): digest(p) for p in sorted(inputs)}
        report['source_sha256'] = sources
        report['head'] = subprocess.check_output(['git', '-C', str(R), 'rev-parse', 'HEAD'], text=True, timeout=5).strip()
        source = (R/'initramfs/persistent-root-init').read_text()
        prepare = source.split('prepare_package_keyring() {\n', 1)[1].split('\n}\n', 1)[0]
        matches = re.findall(r"\tprintf (.*?)>/run/systemd/system/archlinux-keyring-wkd-sync.service.d/10-package-trust.conf", prepare, re.S)
        require(len(matches) == 1, 'ambiguous production drop-in')
        words = shlex.split(matches[0].replace('\\\n', ''))
        require(words[:1] == ['%s\\n'] and words[1:2] == ['[Unit]'], 'unexpected drop-in generator')
        dropin = '\n'.join(words[1:])+'\n'
        (output/'production-dropin.conf').write_text(dropin)
        unit = (R/'configs/systemd/rog5-package-keyring.service').read_text()
        (output/'production-keyring.service').write_text(unit)
        prefix = 'rog5-keyring-test-'+uuid.uuid4().hex
        ssh = prefix+'-ssh.service'
        definitions, mapping = core_module.core_units(output, prefix, ssh)
        definitions[ssh] = '[Service]\nType=exec\nExecStart=/usr/bin/sleep 60\nTimeoutStopSec=2s\n'
        core_names = list(definitions)
        bootstrap, refresh, clock = (prefix+'-'+n+'.service' for n in ('bootstrap', 'refresh', 'clock'))
        mapping.update({'rog5-package-keyring.service': bootstrap,
                        'archlinux-keyring-wkd-sync.service': refresh, 'systemd-timesyncd.service': clock})
        fixture = output/'endpoint'
        fixture.write_text('#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\n'+'''mode=$(cat mode)
printf '%s:%s\\n' "$mode" "$1" >>events
case $1 in
  start)
    case $mode in
      failure) exit 42 ;;
      timeout) exec sleep 30 ;;
    esac
    sleep .05
    printf '%s:ready\\n' "$mode" >>events ;;
  stop|refresh) : ;;
  *) exit 99 ;;
esac
''')
        fixture.chmod(0o700)
        definitions[bootstrap] = unit.replace('/run/rog5-persistent-keyring', shlex.quote(str(fixture)))
        definitions[bootstrap] += '\n[Service]\nTimeoutStartSec=1s\nTimeoutStopSec=2s\n'
        definitions[refresh] = '[Service]\nType=oneshot\nExecStart='+shlex.join([str(fixture), 'refresh'])+'\n'+dropin
        definitions[clock] = '[Service]\nType=oneshot\nExecStart=/usr/bin/true\nRemainAfterExit=yes\n'
        report['fixture_overrides'] = dict(TimeoutStartSec='1s', TimeoutStopSec='2s',
            source_timeouts=re.findall(r'^Timeout.*$', unit, re.M), dropin='extracted, appended verbatim before name mapping')
        runtime = Path('/run/user')/str(os.getuid())/'systemd/user'
        for name, content in definitions.items():
            path = output/name
            path.write_text(re.sub(r'[\w-]+\.service', lambda m: mapping.get(m[0], m[0]), content))
            link = runtime/name
            require(not link.exists() and not link.is_symlink(), 'runtime unit collision')
            links[link] = path
        report['artifact_sha256'] = {p.name: digest(p) for p in output.iterdir() if p.is_file()}
        owned = list(definitions)
        ctl('link', '--runtime', *map(str, links.values()))
        ctl('start', mapping['rog5-persistent-ssh-identity.service'], mapping['rog5-tailscaled.service'])
        baseline = identity(core_names)
        report['core_identity'] = baseline
        report['state_sha256'] = {n: digest(output/n) for n in ('p2-accepted', 'state-events')}
        ctl('show', refresh, bootstrap, '-p', 'Requires', '-p', 'After', '-p', 'Before', '-p', 'TimeoutStartUSec')
        for scenario in ('success', 'failure', 'timeout'):
            (output/'mode').write_text(scenario)
            (output/'events').write_text('')
            begin = time.monotonic()
            p = ctl('start', refresh, check=False)
            expected = [scenario+':start'] + (['success:ready', 'success:refresh'] if scenario == 'success' else [scenario+':stop'])
            require((p.returncode == 0) == (scenario == 'success'), 'incorrect refresh job outcome')
            outcome = ctl('show', bootstrap, '-p', 'Result', '-p', 'ExecMainStatus').stdout
            require(('Result='+{'success': 'success', 'failure': 'exit-code', 'timeout': 'timeout'}[scenario]+'\n') in outcome, 'wrong bootstrap result')
            require(scenario != 'failure' or 'ExecMainStatus=42\n' in outcome, 'wrong failure exit code')
            if scenario == 'success':
                before = identity([bootstrap])
                ctl('start', bootstrap)  # RemainAfterExit must not replay initialization.
                ctl('restart', refresh)
                expected.append('success:refresh')
                require(identity([bootstrap]) == before, 'refresh restart reran bootstrap')
            events = (output/'events').read_text().splitlines()
            require(events == expected, 'incorrect exact endpoint events: '+repr(events))
            require(identity(core_names) == baseline, 'keyring operation changed core identity')
            require(all(digest(output/n) == h for n, h in report['state_sha256'].items()), 'core state changed')
            require((output/'state-events').read_text() == 'start\n' and not (output/'network-events').exists(), 'core teardown occurred')
            report['cases'].append(dict(scenario=scenario, status='PASS', events=events,
                                        result=outcome, seconds=round(time.monotonic()-begin, 6)))
            ctl('stop', bootstrap)
            ctl('reset-failed', bootstrap, refresh, check=False)
        report['status'] = 'PASS'
    except Exception as error:
        report['error'] = str(error)
    finally:
        try:
            if owned:
                ctl('stop', *owned)
                ctl('reset-failed', *owned, check=False)
        except Exception as error:
            report.update(status='FAIL', cleanup_error=str(error))
        try:
            for link, path in links.items():
                if link.is_symlink() and link.resolve() == path:
                    link.unlink(); report['cleanup'].append(str(link))
                else:
                    require(not link.exists() and not link.is_symlink(), 'changed link preserved: '+str(link))
            if links:
                ctl('daemon-reload')
                for name in owned:
                    require(ctl('show', name, '-p', 'LoadState', '--value', check=False).stdout.strip() == 'not-found', 'unit still attached: '+name)
        except Exception as error:
            report.update(status='FAIL', cleanup_error=str(error))
        if any(digest(R/p) != value for p, value in sources.items()):
            report.update(status='FAIL', error='test input changed during run')
        report['duration_seconds'] = round(time.monotonic()-started, 6)
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('status', 'duration_seconds')} | {'output': str(output)}))
    return {'PASS': 0, 'BLOCKED': 77}.get(report['status'], 1)


if __name__ == '__main__':
    raise SystemExit(main())
