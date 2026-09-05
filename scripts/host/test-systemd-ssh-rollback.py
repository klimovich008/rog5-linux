#!/usr/bin/env python3
"""C02: real user-systemd timer/sshd restart, sealed shell, simulated reboot.

No phone, login, root privileges, persistent units or host reboot. /proc and
healthy acceptance are fixtures. Rollback executes in a network/PID/mount/user
isolated BusyBox root with no host system bus or block devices.
"""
import argparse
import gzip
import importlib.util
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[2]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,REPO/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


FIXTURE=load('healthy_fixture','scripts/device/test-native-wifi-healthy.py')
SEALED=load('sealed_shell','scripts/host/run-sealed-busybox.py')
ACCEPTANCE=load('acceptance','scripts/host/release-acceptance.py')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    for executable in ('systemctl','sshd','ssh-keygen','ssh-keyscan','bwrap','qemu-aarch64-static'):
        if not shutil.which(executable):
            print('BLOCKED: missing '+executable); return 77
    if subprocess.run(['systemctl','--user','show-environment'],stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,timeout=3).returncode:
        print('BLOCKED: no available user systemd manager'); return 77
    output=args.output.resolve()
    if output.exists() or output.is_relative_to(REPO):
        parser.error('output must be new and outside repository')
    output.mkdir(mode=0o700)
    source=ACCEPTANCE.source_identity()
    started=time.monotonic()
    events=[]; owned=[]; links={}; case=FIXTURE.PersistentWifiHealthy()
    work_temp=tempfile.TemporaryDirectory(prefix='rog5-c02-')
    report={'source':source,'status':'FAIL','scope':__doc__,
            'archive_sha256':ACCEPTANCE.sha_file(args.target_archive),'events':events}

    def command(argv, *, check=True):
        result=subprocess.run(argv,capture_output=True,text=True,timeout=10)
        events.append(dict(command=argv,returncode=result.returncode,
                           stdout=result.stdout[-4096:],stderr=result.stderr[-4096:],
                           seconds=round(time.monotonic()-started,3)))
        if check and result.returncode: raise RuntimeError('command failed: '+shlex.join(argv))
        return result.stdout.strip()

    def wait_for(predicate,description):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            if predicate(): return
            time.sleep(.1)
        raise RuntimeError('deadline: '+description)

    try:
        def exercise(temp):
            nonlocal owned
            work=Path(temp)
            root,_=case.fixture('already-healthy-missing-timers')
            # Reuse the existing safe fixture's exact production ExecStart and
            # shell code. Capture its invocation rather than execute it here.
            invocations=[]
            def capture(argv,**kwargs):
                invocations.append(argv)
                return SimpleNamespace(returncode=0,stderr='',stdout='')
            with patch.object(FIXTURE.subprocess,'run',side_effect=capture):
                case.fire_boot_timer(root)
            if len(invocations)!=1 or invocations[0][:2]!=['sh','-c']:
                raise RuntimeError('unexpected rollback fixture invocation')
            archive_root=work/'archive'; archive_root.mkdir()
            SEALED.extract(SEALED.ARCHIVE.entries(gzip.decompress(args.target_archive.read_bytes())),archive_root)
            (archive_root/'rog5-qemu').touch()
            entered=root/'invocations'
            safe_argv=['bwrap','--unshare-all','--die-with-parent','--new-session',
                '--uid','0','--gid','0','--ro-bind',str(archive_root),'/', '--dev','/dev',
                '--tmpfs','/tmp','--bind',str(root),str(root),
                '--ro-bind','/usr/bin/qemu-aarch64-static','/rog5-qemu','--clearenv',
                '--setenv','PATH','/bin:/sbin:/usr/bin:/usr/sbin',
                '/rog5-qemu','/bin/busybox',*invocations[0]]
            runner=work/'rollback'
            runner.write_text('#!/bin/sh\nset -eu\n'+shlex.join(safe_argv)+
                '\nprintf "completed\\n" >>'+shlex.quote(str(entered))+'\n')
            runner.chmod(0o700)

            key=work/'host-key'
            command(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)])
            public=key.with_suffix('.pub').read_text().split()[:2]
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1',0)); port=reservation.getsockname()[1]
            config=work/'sshd.conf'
            config.write_text(f'ListenAddress 127.0.0.1\nPort {port}\nHostKey {key}\n'
                f'PidFile {work}/sshd.pid\nPasswordAuthentication no\n'
                'KbdInteractiveAuthentication no\nUsePAM no\nPermitRootLogin no\n'
                'PubkeyAuthentication no\nPermitUserRC no\nLogLevel ERROR\n')
            command(['sshd','-t','-f',str(config)])
            prefix='rog5-c02-'+work.name.removeprefix('rog5-c02-')
            rollback=prefix+'-rollback'; ssh=prefix+'-ssh.service'
            timer=rollback+'.timer'
            owned=[ssh,timer,rollback+'.service']
            # Names/paths and the short OnBootSec are fixture substitutions;
            # keep the production timer and SSH Requires/After relationship.
            timer_source=(REPO/'initramfs/native-wifi/units/rog5-wifi-boot-rollback.timer').read_text()
            dependency=(REPO/'initramfs/native-wifi/units/before-ssh.conf').read_text()
            if 'OnBootSec=@OUTER_SECONDS@s' not in timer_source or dependency != '[Unit]\nRequires=rog5-wifi-boot-rollback.timer\nAfter=rog5-wifi-boot-rollback.timer\n':
                raise RuntimeError('timer/dependency contract changed; update exact integration')
            service_source=(REPO/'initramfs/native-wifi/units/rog5-wifi-boot-rollback.service').read_text()
            service_source='\n'.join('ExecStart='+str(runner) if line.startswith('ExecStart=') else line
                                     for line in service_source.splitlines())+'\n'
            timer_deadline=math.ceil(time.monotonic()+5)
            definitions={timer:timer_source.replace('@OUTER_SECONDS@',str(timer_deadline)).replace(
                    'Unit=rog5-wifi-boot-rollback.service','Unit='+rollback+'.service'),
                rollback+'.service':service_source,
                ssh:'[Unit]\nDefaultDependencies=no\nRequires='+timer+'\nAfter='+timer+
                    '\n[Service]\nType=exec\nExecStart='+shlex.join([shutil.which('sshd'),'-D','-e','-f',str(config)])+
                    '\nRuntimeMaxSec=60s\nTimeoutStopSec=3s\n'}
            runtime_units=Path('/run/user')/str(os.getuid())/'systemd/user'
            for name,text in definitions.items():
                path=work/name;path.write_text(text)
                link=runtime_units/name
                if link.exists() or link.is_symlink(): raise RuntimeError('test unit already exists')
                links[link]=path
            command(['systemctl','--user','link','--runtime',*[str(p) for p in links.values()]])
            command(['systemctl','--user','start',ssh])
            command(['systemctl','--user','show',ssh,'-p','Requires','-p','After','-p','FragmentPath'])

            def count(): return len(entered.read_text().splitlines()) if entered.exists() else 0
            def listener():
                scan=command(['ssh-keyscan','-T','1','-t','ed25519','-p',str(port),'127.0.0.1'],check=False)
                return any(line.split()[1:]==public for line in scan.splitlines() if not line.startswith('#'))
            wait_for(listener,'initial exact fixture SSH listener')
            if count() or (root/'reboots').exists():
                raise RuntimeError('timer fired before healthy disarm')
            for stale in (False,True):
                if stale:
                    # A new deadline represents another trial, not replay of
                    # an already-fired OnBootSec timestamp. The production
                    # health gate stops its timer BEFORE the first expiry.
                    command(['systemctl','--user','--job-mode=ignore-dependencies','stop',timer])
                    timer_deadline=math.ceil(time.monotonic()+3)
                    (work/timer).write_text(timer_source.replace('@OUTER_SECONDS@',str(timer_deadline)).replace(
                        'Unit=rog5-wifi-boot-rollback.service','Unit='+rollback+'.service'))
                    command(['systemctl','--user','daemon-reload'])
                    command(['systemctl','--user','start',timer])
                state=command(['systemctl','--user','show',timer,'-p','SubState','--value'])
                if state!='waiting' or time.monotonic()>=timer_deadline:
                    raise RuntimeError('fixture missed pre-expiry health disarm')
                command(['systemctl','--user','--job-mode=ignore-dependencies','stop',timer])
                command(['systemctl','--user','is-active','--quiet',ssh])
                if stale:
                    ack=root/'run/rog5-native-wifi/healthy.record'
                    ack.chmod(0o644)
                    ack.write_text(ack.read_text().replace('000000000001','000000000002'))
                    ack.chmod(0o444)
                previous=command(['systemctl','--user','show','-p','MainPID','--value',ssh])
                before=count()
                wait_for(lambda:time.monotonic()>timer_deadline+.2,'original deadline elapsed while disarmed')
                if count()!=before: raise RuntimeError('disarmed timer executed')
                command(['systemctl','--user','restart',ssh])
                wait_for(listener,'restarted exact fixture SSH listener')
                wait_for(lambda:count()>before,'reactivated elapsed timer callback')
                current=command(['systemctl','--user','show','-p','MainPID','--value',ssh])
                if previous==current or current=='0': raise RuntimeError('SSH process did not actually restart')
                requested=(root/'reboots').exists()
                if requested!=stale: raise RuntimeError('incorrect reboot outcome after SSH restart')
                events.append(dict(test='stale' if stale else 'healthy',old_pid=previous,new_pid=current,
                                   callback_count=count(),reboot_requested=requested))
            report['status']='PASS'
        exercise(work_temp.name)
    except Exception as error:
        report['error']=str(error)
    finally:
        # Only this invocation's runtime links/user units; no persistent install.
        if owned:
            try:
                command(['systemctl','--user','stop',*owned])
                command(['systemctl','--user','reset-failed',*owned],check=False)
            except Exception as error:
                report.update(status='FAIL',cleanup_error=str(error))
        for link,path in links.items():
            if link.is_symlink() and link.resolve()==path:
                link.unlink()
            elif link.exists() or link.is_symlink():
                report.update(status='FAIL',cleanup_error='owned unit link changed; preserved')
        if links: command(['systemctl','--user','daemon-reload'])
        case.doCleanups()
        work_temp.cleanup()
        if source!=ACCEPTANCE.source_identity(): report.update(status='FAIL',error='source changed during test')
        report.update(duration_seconds=round(time.monotonic()-started,3),
                      systemd_version=command(['systemctl','--version']).splitlines()[0])
        (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','duration_seconds','scope')}))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__': raise SystemExit(main())
