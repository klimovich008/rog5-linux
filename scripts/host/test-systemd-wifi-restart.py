#!/usr/bin/env python3
"""Real systemd WPA/DHCP restart graph; hardware and network daemons are fixtures.

Checks dependency propagation, not actual association, lease or SSH recovery.
Only unique user-runtime units and a new private output directory are changed.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
import uuid

R = Path(__file__).resolve().parents[2]


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    if output.exists() or output.is_relative_to(R):
        parser.error('output must be new and outside repository')
    os.umask(0o077)
    output.mkdir(mode=0o700)
    started = time.monotonic()
    report = dict(status='FAIL', scope=__doc__, commands=[], cases=[])
    links = {}; owned = []; source = None
    spec = importlib.util.spec_from_file_location('wifi_restart_core', R/'scripts/host/test-systemd-ssh-rollback.py')
    core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)

    def ctl(*args, check=True):
        p = subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True, timeout=10)
        report['commands'].append(dict(args=args, status=p.returncode, stdout=p.stdout, stderr=p.stderr))
        require(not check or p.returncode == 0, 'systemctl failed: '+shlex.join(args))
        return p.stdout.strip()

    def identity(names):
        result = {}
        for name in names:
            fields = dict(s.split('=', 1) for s in ctl('show', name, '-p', 'ActiveState', '-p', 'InvocationID', '-p', 'MainPID').splitlines())
            require(fields['ActiveState'] == 'active' and fields['InvocationID'], 'inactive service: '+name)
            result[name] = fields
        return result

    try:
        try:
            ctl('show', '--property=Version')
        except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired):
            report['status'] = 'BLOCKED'
            raise RuntimeError('no available user systemd manager')
        source = core.ACCEPTANCE.source_identity()
        report['source'] = source
        prefix = 'rog5-wifi-restart-'+uuid.uuid4().hex
        ssh = prefix+'-ssh.service'
        definitions, mapping = core.core_units(output, prefix, ssh)
        definitions[ssh] = '[Service]\nType=exec\nExecStart=/usr/bin/sleep 60\n'
        stable_names = list(definitions)
        for name in ('rog5-wifi-radio', 'rog5-wifi-wpa', 'rog5-wifi-dhcp', 'systemd-resolved', 'rog5-wifi-failure'):
            mapping[name+'.service'] = prefix+'-'+name+'.service'
        endpoint = output/'endpoint'
        endpoint.write_text('#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\n'
            'printf "%s\\n" "$1" >>events\n'
            'case $1 in radio) exit 0 ;; wpa|dhcp) exec sleep 60 ;; *) exit 99 ;; esac\n')
        endpoint.chmod(0o700)
        report['unit_sha256'] = {}
        for name in ('radio', 'wpa', 'dhcp'):
            path = R/'initramfs/native-wifi/units'/('rog5-wifi-'+name+'.service')
            report['unit_sha256'][path.name] = core.ACCEPTANCE.sha_file(path)
            lines = []
            for line in path.read_text().replace('@OUTER_SECONDS@', '10').splitlines():
                if line.startswith(('ExecCondition=', 'ExecStartPre=')):
                    continue  # Qualified activation/preparation; separate sealed-runtime tests.
                if line.startswith('ExecStart='):
                    line = 'ExecStart='+shlex.join([str(endpoint), name])
                if line == 'Before=basic.target':
                    continue
                line = line.replace(' basic.target', '')
                line = re.sub(r'[\w-]+\.service', lambda m: mapping.get(m[0], m[0]), line)
                lines.append(line)
            definitions[mapping['rog5-wifi-'+name+'.service']] = '\n'.join(lines)+'\n'
        for name in ('systemd-resolved', 'rog5-wifi-failure'):
            definitions[mapping[name+'.service']] = '[Service]\nType=oneshot\nExecStart=/usr/bin/true\nRemainAfterExit=yes\n'
        runtime = Path('/run/user')/str(os.getuid())/'systemd/user'
        for name, content in definitions.items():
            path = output/name; path.write_text(content)
            link = runtime/name
            require(not link.exists() and not link.is_symlink(), 'unit collision')
            links[link] = path
        owned = list(definitions)
        ctl('link', '--runtime', *map(str, links.values()))
        radio, wpa, dhcp = [mapping['rog5-wifi-'+n+'.service'] for n in ('radio', 'wpa', 'dhcp')]
        ctl('start', dhcp, mapping['rog5-tailscaled.service'])
        stable = identity(stable_names+[radio])
        previous = identity([wpa, dhcp])
        for service in (wpa, dhcp):
            begin = time.monotonic()
            ctl('restart', service)
            now = identity([wpa, dhcp])
            require(identity(stable_names+[radio]) == stable, 'network restart changed core/radio identity')
            require(now[dhcp]['InvocationID'] != previous[dhcp]['InvocationID'], 'DHCP was not restarted')
            require((now[wpa] != previous[wpa]) == (service == wpa), 'unexpected WPA invocation change')
            # Wait only for fixture entry, never repair a failed unit in the test.
            deadline = time.monotonic()+2
            expected_dhcp = 2 if service == wpa else 3
            while time.monotonic() < deadline:
                events = (output/'events').read_text().splitlines()
                if events.count('dhcp') == expected_dhcp:
                    break
                time.sleep(.02)
            require(events.count('radio') == 1 and events.count('wpa') == 2 and events.count('dhcp') == expected_dhcp, 'unexpected hardware/daemon execution count')
            require((output/'state-events').read_text() == 'start\n' and not (output/'network-events').exists(), 'core teardown occurred')
            report['cases'].append(dict(action=service, status='PASS', duration_seconds=time.monotonic()-begin, events=events))
            previous = now
        report['status'] = 'PASS'
    except Exception as error:
        report['error'] = str(error)
    finally:
        try:
            if owned:
                ctl('stop', *owned)
                ctl('reset-failed', *owned, check=False)
            for link, path in links.items():
                if link.is_symlink() and link.resolve() == path:
                    link.unlink()
                else:
                    require(not link.exists() and not link.is_symlink(), 'changed link preserved')
            if links:
                ctl('daemon-reload')
                for name in owned:
                    require(ctl('show', name, '-p', 'LoadState', '--value', check=False) == 'not-found', 'unit remains attached')
            report['cleanup'] = 'PASS'
        except Exception as error:
            report.update(status='FAIL', cleanup_error=str(error))
        if source and source != core.ACCEPTANCE.source_identity():
            report.update(status='FAIL', error='source changed during test')
        report['duration_seconds'] = time.monotonic()-started
        (output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: report[key] for key in ('status', 'duration_seconds')} | {'error': report.get('error')}))
    return {'PASS': 0, 'BLOCKED': 77}.get(report['status'], 1)


if __name__ == '__main__':
    raise SystemExit(main())
