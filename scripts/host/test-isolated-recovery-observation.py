#!/usr/bin/env python3
"""Synthetic negative-health evidence; no phone, service change or boot."""
import copy
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import Mock,patch

SPEC=importlib.util.spec_from_file_location('negative_observation',Path(__file__).with_name('isolated-recovery-observation.py'))
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)
IDENTITY=dict(boot_id='12345678-1234-4abc-8def-1234567890ab',bundle='fixture-negative',release='7.1.4-fixture')
TRIAL='a'*64
INSTALLED=dict(trial_id='b'*64,primary_bundle='fixture-primary',primary_manifest_sha256='c'*64,
               fallback_bundle='fixture-rescue',fallback_manifest_sha256='d'*64)
SEALED={role:hashlib.sha256(role.encode()).hexdigest() for role in M.SEALED}


def file_record(fields,mode=0o444,dev=1):
    return dict(status='present',text=''.join(f'{k}={v}\n' for k,v in fields.items()),
                mode=mode,uid=0,gid=0,nlink=1,dev=dev)


def command(value):
    if isinstance(value,dict):value=''.join(f'{k}={v}\n' for k,v in value.items())
    return dict(returncode=0,stdout=value,stderr='')


def fixture():
    files=dict(descriptor=file_record(dict(format='rog5-persistent-wifi-health-v1',trial_id=TRIAL,
                   primary_bundle=IDENTITY['bundle'],mode='try-once')),
               healthy={'status':'absent'},radio_refused={'status':'absent'},
               pending=file_record(dict(format='rog5-persistent-wifi-trial-v1',**INSTALLED,state='pending'),0o600,os.makedev(259,58)),
               ready=file_record(dict(status='PASS',attested_boot_id=IDENTITY['boot_id'],
                   kernel=IDENTITY['release'],ssh='strict-key-only')),
               ssh=file_record(dict(format='rog5-persistent-ssh-identity-v1',mode='load',
                   fingerprint='SHA256:'+'x'*43,identity_boot_id=IDENTITY['boot_id'])))
    units=dict(health=command(dict(zip(M.SERVICE_PROPERTIES,('loaded','failed','failed','exit-code','1','50000000','60000000')))),
               rollback=command(dict(zip(M.SERVICE_PROPERTIES,('loaded','inactive','dead','success','0','0','0')))),
               timer=command(dict(zip(M.TIMER_PROPERTIES,('loaded','active','waiting','success',M.UNITS['rollback'])))))
    journal=[dict(_BOOT_ID=IDENTITY['boot_id'].replace('-',''),_SYSTEMD_UNIT=M.UNITS['health'],
                  MESSAGE=message,__MONOTONIC_TIMESTAMP=str(55000000+index)) for index,message in enumerate(M.MESSAGES)]
    return dict(identity=IDENTITY,uptime=100,files=files,units=units,
                sealed={role:dict(status='present',sha256=SEALED[role],uid=0,gid=0,nlink=1,mode=mode,dev=1)
                        for role,(_,mode) in M.SEALED.items()},
                journal=command(''.join(json.dumps(row)+'\n' for row in journal)),
                power=dict(health='Good',temp='299',voltage_now='8590000',usb_online='1'),
                thermal={'thermal_zone0':40000},blocks=dict(sda='0',sda23='0',**{f'fixture{x}':'1' for x in range(115)}),
                userdata_device='259:58',userdata_partition=dict(M.USERDATA_GEOMETRY,
                    uevent='MAJOR=259\nMINOR=58\nDEVNAME=sda23\nDEVTYPE=partition\nDISKSEQ=10\nPARTN=23\nPARTNAME=userdata\nPARTUUID='+M.USERDATA_PARTUUID),mountinfo='123 1 259:58 / /.rog5/userdata-rw rw,nosuid,nodev,noexec - ext4 /dev/sda23 rw\n')


class NegativeTest(unittest.TestCase):
    def evaluate(self,value):return M.negative(value,IDENTITY,TRIAL,INSTALLED,SEALED)

    def test_runtime_allocation_is_bound_to_partition_mount_and_record(self):
        for major,minor in ((8,23),(259,58),(259,4096),(4095,1048575)):
            with self.subTest(device=(major,minor)):
                value=fixture();device=f'{major}:{minor}'
                value['userdata_device']=device
                value['mountinfo']=value['mountinfo'].replace('259:58',device)
                value['userdata_partition']['uevent']=value['userdata_partition']['uevent'].replace(
                    'MAJOR=259',f'MAJOR={major}').replace('MINOR=58',f'MINOR={minor}')
                value['files']['pending']['dev']=os.makedev(major,minor)
                self.assertEqual(self.evaluate(value)['status'],'COMPONENT_PASS')
                value['files']['pending']['dev']+=1
                with self.assertRaises(ValueError):self.evaluate(value)

    def test_unbound_partition_or_malformed_device_is_refused(self):
        for device in (None,True,'','0:58','259:058','0259:58','4096:58','259:1048576','259:58\n','259:58:1'):
            value=fixture();value['userdata_device']=device
            with self.subTest(device=device),self.assertRaises(ValueError):self.evaluate(value)
        for field,changed in (('partition','24'),('start','0'),('size','1'),('uevent','bad'),
                              ('uevent',fixture()['userdata_partition']['uevent']+'\nMINOR=58')):
            value=fixture();value['userdata_partition'][field]=changed
            with self.subTest(field=field),self.assertRaises(ValueError):self.evaluate(value)
        for key in ('MAJOR','MINOR','DEVNAME','DEVTYPE','PARTN','PARTNAME','PARTUUID'):
            value=fixture();rows=value['userdata_partition']['uevent'].splitlines()
            value['userdata_partition']['uevent']='\n'.join(
                key+'=changed' if line.startswith(key+'=') else line for line in rows)
            with self.subTest(event=key),self.assertRaises(ValueError):self.evaluate(value)
        for change in ('missing-partition','extra-field','missing-mount-binding'):
            value=fixture()
            if change=='missing-partition':del value['userdata_partition']
            elif change=='extra-field':value['userdata_partition']['unexpected']='value'
            else:value['mountinfo']=value['mountinfo'].replace('259:58','259:59')
            with self.subTest(change=change),self.assertRaises(ValueError):self.evaluate(value)

    def test_pending_health_wait_validates_actual_safety_without_inventing_failure(self):
        value=fixture()
        value['units']['health']=command(dict(zip(M.SERVICE_PROPERTIES,
            ('loaded','activating','start','success','0','50000000','0'))))
        value['journal']=command('')
        self.assertTrue(M.pending(value,IDENTITY,TRIAL,INSTALLED,SEALED))
        with self.assertRaises(ValueError):self.evaluate(value)
        self.assertFalse(M.pending(fixture(),IDENTITY,TRIAL,INSTALLED,SEALED))
        for change in ('power','state','timer','healthy','unexpected-state'):
            with self.subTest(change=change):
                changed=copy.deepcopy(value)
                if change=='power':changed['power']['temp']='401'
                if change=='state':changed['blocks']['sda24']='0'
                if change=='timer':changed['units']['timer']['stdout']=changed['units']['timer']['stdout'].replace('waiting','dead')
                if change=='healthy':changed['files']['healthy']={'status':'present'}
                if change=='unexpected-state':changed['units']['health']['stdout']=changed['units']['health']['stdout'].replace('activating','active')
                with self.assertRaises(ValueError):M.pending(changed,IDENTITY,TRIAL,INSTALLED,SEALED)

    def test_specific_refusal_with_armed_fallback_is_only_a_component(self):
        value=fixture();before=copy.deepcopy(value)
        result=self.evaluate(M.decode(json.dumps(value).encode()))
        self.assertEqual(result['status'],'COMPONENT_PASS')
        self.assertTrue(result['timer_armed'])
        self.assertFalse(result['autonomous_recovery_proven'])
        self.assertFalse(result['release_qualified'])
        self.assertEqual(value,before)

    def test_wrong_or_late_identity_and_healthy_branch_fail(self):
        for case in ('boot','release','bundle','late','nan','negative-uptime','healthy','radio-refused','pending-state','pending-device'):
            value=fixture()
            if case in ('boot','release','bundle'):
                value['identity']=dict(IDENTITY,**{'boot_id' if case=='boot' else case:'different'})
            elif case in ('late','nan','negative-uptime'):
                value['uptime']={'late':900,'nan':float('nan'),'negative-uptime':-1}[case]
            elif case in ('healthy','radio-refused'):
                value['files'][case.replace('-','_')]={'status':'error'}
            elif case=='pending-state':value['files']['pending']['text']=value['files']['pending']['text'].replace('state=pending','state=healthy')
            else:value['files']['pending']['dev']=1
            with self.subTest(case=case),self.assertRaises(ValueError):self.evaluate(value)

    def test_file_identity_guards_and_missing_markers(self):
        for role in ('descriptor','pending','ready','ssh'):
            for field,changed in (('status','absent'),('mode',0o666),('uid',1),('nlink',2),('dev',True),('text','bad\n')):
                value=fixture();value['files'][role][field]=changed
                with self.subTest(role=role,field=field),self.assertRaises(ValueError):self.evaluate(value)
        value=fixture();value['files']['descriptor']['text']+='trial_id='+TRIAL+'\n'
        with self.assertRaisesRegex(ValueError,'duplicate'):self.evaluate(value)
        for role in M.SEALED:
            value=fixture();value['sealed'][role]['sha256']='f'*64
            with self.subTest(role=role),self.assertRaisesRegex(ValueError,'deployed'):self.evaluate(value)

    def test_unrelated_health_failure_or_disarmed_timer_fails(self):
        for role,old,new in (('health','exit-code','timeout'),('health','ExecMainStatus=1','ExecMainStatus=0'),
            ('health','60000000','100000001'),('health','50000000','0'),
            ('timer','ActiveState=active','ActiveState=inactive'),('timer','SubState=waiting','SubState=elapsed'),
            ('timer',M.UNITS['rollback'],'other.service'),('rollback','ExecMainStatus=0','ExecMainStatus=1'),
            ('rollback','ExecMainStartTimestampMonotonic=0','ExecMainStartTimestampMonotonic=1')):
            value=fixture();value['units'][role]['stdout']=value['units'][role]['stdout'].replace(old,new)
            with self.subTest(role=role,new=new),self.assertRaises(ValueError):self.evaluate(value)
        for role in ('health','timer','rollback'):
            value=fixture();value['units'][role]['stderr']='read failed'
            with self.subTest(role=role),self.assertRaisesRegex(ValueError,'command'):self.evaluate(value)

    def test_journal_requires_exact_order_unit_boot_and_execution_window(self):
        for case in ('empty','unrelated','wrong-boot','wrong-unit','early','late','reverse','duplicate','read-failure'):
            value=fixture();rows=[json.loads(line) for line in value['journal']['stdout'].splitlines()]
            if case=='empty':rows=[]
            elif case=='unrelated':rows[0]['MESSAGE']='FAIL native-wifi-healthy: healthy startup deadline'
            elif case=='wrong-boot':rows[0]['_BOOT_ID']='0'*32
            elif case=='wrong-unit':rows[0]['_SYSTEMD_UNIT']='other.service'
            elif case=='early':rows[0]['__MONOTONIC_TIMESTAMP']='1'
            elif case=='late':rows[0]['__MONOTONIC_TIMESTAMP']='99999999'
            elif case=='reverse':rows.reverse()
            elif case=='duplicate':rows.append(rows[-1])
            elif case=='read-failure':value['journal']['returncode']=1
            value['journal']['stdout']=''.join(json.dumps(row)+'\n' for row in rows)
            with self.subTest(case=case),self.assertRaises(ValueError):self.evaluate(value)

    def test_power_storage_and_mount_guards_remain_required(self):
        for case in ('voltage','temperature','usb','thermal','empty-thermal','extra-writable','missing-block',
                     'wrong-device','missing-mount','stacked-mount','wrong-mount-source','readonly-mount'):
            value=fixture()
            if case=='voltage':value['power']['voltage_now']='8300000'
            elif case=='temperature':value['power']['temp']='400'
            elif case=='usb':value['power']['usb_online']='0'
            elif case=='thermal':value['thermal']['thermal_zone0']=60000
            elif case=='empty-thermal':value['thermal']={}
            elif case=='extra-writable':value['blocks']['fixture0']='0'
            elif case=='missing-block':del value['blocks']['fixture0']
            elif case=='wrong-device':value['userdata_device']='8:24'
            elif case=='missing-mount':value['mountinfo']=''
            elif case=='stacked-mount':value['mountinfo']*=2
            elif case=='wrong-mount-source':value['mountinfo']=value['mountinfo'].replace('/dev/sda23','/dev/sda24')
            elif case=='readonly-mount':value['mountinfo']=value['mountinfo'].replace('rw,nosuid','ro,nosuid')
            with self.subTest(case=case),self.assertRaises(ValueError):self.evaluate(value)

    def test_raw_duplicates_and_oversize_are_refused(self):
        for raw in (b'',b'x'*262145,b'{"identity":{},"identity":{}}'):
            with self.assertRaises(ValueError):M.decode(raw)
        for identity in (dict(IDENTITY,boot_id='bad'),dict(IDENTITY,bundle='bad;command')):
            with self.assertRaises(ValueError):M.script(identity)
        compile(M.script(IDENTITY),'<negative probe>','exec')

    def test_host_gates_precede_credentials_and_raw_reply_precedes_post_gate(self):
        reply=subprocess.CompletedProcess([],0,b'raw fixture reply',b'')
        retained=[]
        with patch.object(M.D,'host_gate',side_effect=[None,ValueError('post-read USB mismatch')]), \
             patch.object(M.D,'credential') as credential,patch.object(M.subprocess,'run',return_value=reply) as run:
            with self.assertRaisesRegex(ValueError,'post-read'):
                M.collect(IDENTITY,'fixture',Path('/private/key'),Path('/private/hosts'),
                          lambda result,digest:retained.append((result,digest)))
            self.assertEqual(len(retained),1)
            self.assertIs(retained[0][0],reply)
            self.assertEqual(retained[0][1],hashlib.sha256(M.script(IDENTITY).encode()).hexdigest())
            self.assertEqual(credential.call_count,2)
            self.assertEqual(run.call_args.kwargs['timeout'],20)
        with patch.object(M.D,'host_gate',side_effect=ValueError('wrong USB')), \
             patch.object(M.D,'credential') as credential,patch.object(M.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'wrong USB'):
                M.collect(IDENTITY,'fixture',Path('/private/key'),Path('/private/hosts'),Mock())
            credential.assert_not_called();run.assert_not_called()
        timeout=subprocess.TimeoutExpired(['fixture'],20,output=b'partial raw observation',stderr=b'partial error')
        retained.clear()
        with patch.object(M.D,'host_gate'),patch.object(M.D,'credential'), \
             patch.object(M.subprocess,'run',side_effect=timeout),self.assertRaises(subprocess.TimeoutExpired):
            M.collect(IDENTITY,'fixture',Path('/private/key'),Path('/private/hosts'),
                      lambda result,digest:retained.append(result))
        self.assertEqual(retained,[timeout])
        self.assertEqual(retained[0].stdout,b'partial raw observation')

    def test_actual_probe_reader_rejects_aliases_bounds_and_read_races(self):
        # Exercise the actual embedded reader against real files. Physical
        # boot/sysfs/device numbers remain synthetic in the evaluator tests.
        nodes=[node for node in ast.parse(M.PROBE).body if isinstance(node,ast.FunctionDef)
               and node.name in ('need','signature','observed')]
        namespace=dict(os=os,stat=stat,Path=Path,hashlib=hashlib)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual probe reader>','exec'),namespace)
        observed=namespace['observed']
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'record';path.write_text('key=value\n');path.chmod(0o444)
            value=observed(str(path),True)
            self.assertEqual(value['text'],'key=value\n')
            self.assertEqual(value['mode'],0o444)
            self.assertEqual(value['uid'],os.getuid())
            self.assertEqual(observed(str(root/'absent'),True),{'status':'absent'})
            link=root/'link';link.symlink_to(path)
            with self.assertRaises(OSError):observed(str(link),True)
            parent=root/'parent';parent.symlink_to(root,target_is_directory=True)
            with self.assertRaises(OSError):observed(str(parent/'record'),True)
            missing=root/'missing-link';missing.symlink_to(root/'missing')
            with self.assertRaises(OSError):observed(str(missing),True)
            with self.assertRaises(OSError):observed(str(root/'missing-parent/record'),True)
            hard=root/'hard';os.link(path,hard)
            self.assertEqual(observed(str(hard),True)['nlink'],2)
            with self.assertRaisesRegex(ValueError,'metadata'):M.record(observed(str(hard),True),0o444)
            hard.unlink()
            for raw in (b'',b'x'*16385):
                path.chmod(0o600);path.write_bytes(raw)
                with self.assertRaisesRegex(ValueError,'type/size'):observed(str(path),True)
            path.write_text('key=value\n')
            original=os.read
            def replace(fd,limit):
                block=original(fd,limit)
                if block:
                    path.unlink();path.write_text('key=value\n')
                return block
            with patch.object(os,'read',side_effect=replace),self.assertRaisesRegex(ValueError,'changed'):
                observed(str(path),True)


if __name__=='__main__':unittest.main()
