#!/usr/bin/env python3
"""E01 real user-systemd ordering with shipped scripts and fake hardware.

No phone or kernel operation; P2/state/SSH executables are fixtures. Does not
qualify actual target SSH or substitute for final archive composition.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time

R=Path(__file__).resolve().parents[2]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,R/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

FIXTURE=load('radio_fixture','scripts/device/test-native-wifi-radio-refusal.py')
CORE=load('core_fixture','scripts/host/test-systemd-ssh-rollback.py')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if (not shutil.which('systemctl') or
        subprocess.run(['systemctl','--user','show','--property=Version'],
                       capture_output=True,timeout=5).returncode):
        print('BLOCKED: no available user systemd manager')
        return 77
    if args.output.resolve().is_relative_to(R):
        parser.error('output must be outside the repository')
    os.umask(0o077)
    args.output.mkdir(mode=0o700)
    started=time.monotonic()
    revision=CORE.ACCEPTANCE.source_identity()
    report=dict(status='FAIL',scope=__doc__,source=revision,cases=[])
    commands=[]
    def command(argv,check=True):
        p=subprocess.run(argv,capture_output=True,text=True,timeout=15)
        commands.append(dict(argv=argv,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if check and p.returncode:
            raise RuntimeError('fixture command failed: '+shlex.join(argv)+' '+p.stderr)
        return p
    try:
        command(['systemctl','--user','show','--property=Version'])
        for scenario in ('safe-refusal','unsafe-power','activation-entered'):
            fixture=FIXTURE.RadioRefusal()
            fixture.setUp()
            work=fixture.root
            prefix='rog5-e01-'+work.name
            names=('rog5-wifi-radio','rog5-wifi-wpa','rog5-wifi-dhcp','rog5-wifi-healthy',
                   'rog5-wifi-failure','systemd-resolved')
            mapping={name+'.service':prefix+'-'+name+'.service' for name in names}
            ssh=prefix+'-ssh.service'
            core,core_mapping=CORE.core_units(work,prefix,ssh)
            mapping.update(core_mapping)
            if scenario=='unsafe-power':
                (work/'sys/class/power_supply/qcom-battmgr-bat/temp').write_text('400')
            elif scenario=='activation-entered':
                (work/'sys/class/power_supply/qcom-battmgr-bat/voltage_now').write_text('8400000')
            runner=work/'radio-run'
            runner.write_text('#!/bin/sh\n'+fixture.script(R/'initramfs/native-wifi/radio',radio=True))
            runner.chmod(0o700)
            condition=work/'radio-condition'
            condition.write_text('#!/bin/sh\nset -- radio-enabled\n'+fixture.script(R/'initramfs/native-wifi/runtime'))
            condition.chmod(0o700)
            must_not_run=work/'optional-started'
            optional=work/'optional-run'
            optional.write_text('#!/bin/sh\nprintf "started\\n" >>'+shlex.quote(str(must_not_run))+'\nexit 97\n')
            optional.chmod(0o700)
            definitions=dict(core)
            definitions[ssh]='[Service]\nType=exec\nExecStart=/usr/bin/sleep 120\n'
            definitions[mapping['systemd-resolved.service']]='[Service]\nType=oneshot\nExecStart=/usr/bin/true\nRemainAfterExit=yes\n'
            definitions[mapping['rog5-wifi-failure.service']]='[Service]\nType=oneshot\nExecStart=/usr/bin/true\n'
            for name in names[:4]:
                condition_record=work/(name+'-condition-status')
                condition_runner=work/(name+'-condition')
                condition_runner.write_text('#!/bin/sh\n'+shlex.quote(str(condition))+
                    '\nstatus=$?\nprintf "%s\\n" "$status" >'+shlex.quote(str(condition_record))+
                    '\nexit "$status"\n')
                condition_runner.chmod(0o700)
                path=(R/'initramfs/native-wifi-persistent/units' if name=='rog5-wifi-healthy'
                      else R/'initramfs/native-wifi/units')/(name+'.service')
                unit=path.read_text().replace('@OUTER_SECONDS@','10')
                lines=[]
                for line in unit.splitlines():
                    if line=='Before=basic.target':continue
                    line=line.replace(' basic.target','')
                    if line.startswith('ExecCondition='):line='ExecCondition='+str(condition_runner)
                    elif line.startswith('ExecStartPre='):continue
                    elif line.startswith('ExecStart='):
                        line='ExecStart='+str(runner if name=='rog5-wifi-radio' else optional)
                    line=re.sub(r'(?:rog5|systemd)-[a-z0-9-]+\.service',
                                lambda m:mapping.get(m[0],m[0]),line)
                    lines.append(line)
                definitions[mapping[name+'.service']]='\n'.join(lines)+'\n'
            # Apply the actual additional ordering/requirement edge on state.
            state_name=mapping['rog5-persistent-state.service']
            dropin=(R/'initramfs/native-wifi/units/before-state.conf').read_text()
            dropin=dropin.replace('rog5-wifi-radio.service',mapping['rog5-wifi-radio.service'])
            definitions[state_name]+='\n'+dropin
            links={}
            owned=list(definitions)
            try:
                runtime=Path('/run/user')/str(os.getuid())/'systemd/user'
                for name,content in definitions.items():
                    file=work/name;file.write_text(content)
                    link=runtime/name
                    if link.exists() or link.is_symlink():raise RuntimeError('unit collision')
                    links[link]=file
                command(['systemctl','--user','link','--runtime',*[str(p) for p in links.values()]])
                command(['systemctl','--user','start',mapping['rog5-wifi-healthy.service']],check=False)
                state=command(['systemctl','--user','is-active',state_name],check=False)
                radio=command(['systemctl','--user','show',mapping['rog5-wifi-radio.service'],
                               '-p','Result','-p','ExecMainStatus','-p','ActiveState'])
                if scenario=='safe-refusal':
                    if state.returncode or not (work/'state-events').exists():
                        raise RuntimeError('safe refusal blocked state')
                    if 'ExecMainStatus=77' not in radio.stdout or 'Result=success' not in radio.stdout:
                        raise RuntimeError('radio refusal was not successful oneshot')
                    for name in names[1:4]:
                        outcome=command(['systemctl','--user','show',mapping[name+'.service'],
                                         '-p','Result','-p','ActiveState'])
                        # Inactive skipped units may be garbage-collected and
                        # reloaded by show, resetting Result to success. Prove
                        # the actual condition ran and returned the skip code;
                        # absence of optional-started proves ExecStart did not.
                        record=work/(name+'-condition-status')
                        if (not record.is_file() or record.read_text()!='1\n' or
                            'ActiveState=inactive' not in outcome.stdout or
                            not any('Result='+value+'\n' in outcome.stdout
                                    for value in ('success','exec-condition'))):
                            raise RuntimeError('optional service did not skip on exact refusal')
                    command(['systemctl','--user','is-active','--quiet',ssh])
                elif (work/'state-events').exists() or state.returncode==0:
                    raise RuntimeError('failed radio opened service state')
                if must_not_run.exists():raise RuntimeError('optional service executed')
                report['cases'].append(dict(scenario=scenario,status='PASS',radio=radio.stdout))
            finally:
                command(['systemctl','--user','stop',*owned])
                command(['systemctl','--user','reset-failed',*owned],check=False)
                for link,path in links.items():
                    if link.is_symlink() and link.resolve()==path:link.unlink()
                    elif link.exists() or link.is_symlink():raise RuntimeError('unit link changed')
                command(['systemctl','--user','daemon-reload'])
                fixture.doCleanups()
        report['status']='PASS'
    except Exception as error:
        report['error']=str(error)
    finally:
        if revision!=CORE.ACCEPTANCE.source_identity():
            report.update(status='FAIL',error='source changed during test')
        report['duration_seconds']=time.monotonic()-started
        (args.output/'commands.json').write_text(json.dumps(commands,indent=2))
        (args.output/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
