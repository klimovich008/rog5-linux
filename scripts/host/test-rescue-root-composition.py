#!/usr/bin/env python3
"""Offline fixture/gate checks. Actual Arch execution is a separate artifact run."""
import copy
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
import struct
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('composition', Path(__file__).with_name('check-rescue-root-composition.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class CompositionTest(unittest.TestCase):
    def test_external_primary_and_fallback_use_root_bytes_and_sealed_verifier(self):
        final=M.load('external_composition_test','scripts/host/check-release-composition.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root.ext4'; root.write_bytes(b'root')
            record=dict(execution='fastboot-boot-selector-trial',target_bundle='primary',
                        fallback_bundle='fallback',manifest_sha256=M.hashlib.sha256(b'primary').hexdigest(),
                        fallback_manifest_sha256=M.hashlib.sha256(b'fallback').hexdigest(),selector_sha256='a'*64)
            reads=[]; verified=[]; original={}
            def read(image,path,limit,*,directory=False):
                self.assertEqual(image,root); reads.append(path)
                if directory:
                    return b'/1/040700/0/0/.//\n/2/040755/0/0/..//\n\n'+b''.join(
                        b'/3/100644/0/0/'+name.encode()+b'/1/\n' for name in
                        ('manifest','manifest.sig','Image','board.dtb','initramfs.cpio.gz'))
                parts=path.split('/'); return parts[-2].encode() if parts[-1]=='manifest' else b'payload'
            def verify(members,bundle,digest):
                verified.append((bundle,digest))
                self.assertEqual(members['usr/share/rog5/ram-bundles/'+bundle+'/Image'][1],b'payload')
                return dict(bundle=bundle,manifest_sha256=digest)
            with patch.object(final,'local_selector_identity',return_value={}), \
                    patch.object(final,'root_member',side_effect=read), \
                    patch.object(final.C,'sealed_bundle_plan',side_effect=verify):
                members,plan,evidence=final.external_bundle_plan(root,record,original)
            self.assertEqual(original,{})
            self.assertEqual(plan['bundle'],'primary')
            self.assertEqual([x[0] for x in verified],['primary','fallback'])
            self.assertEqual(evidence['source'],'retained-root-only')
            self.assertTrue(all(p.startswith('/boot/rog5-linux/bundles/') for p in reads))
            self.assertIn('usr/share/rog5/ram-bundles/fallback/manifest',members)
            for fault in ('manifest','extra-entry','signature','mixed','unsafe-name','source-change'):
                def bad_read(image,path,limit,*,directory=False):
                    data=read(image,path,limit,directory=directory)
                    if fault=='manifest' and path.endswith('/manifest'): return b'changed'
                    if fault=='extra-entry' and directory: return data+b'/4/100644/0/0/extra/1/\n'
                    if fault=='source-change' and path.endswith('/manifest'): root.write_bytes(root.read_bytes()+b'changed')
                    return data
                bad_record=dict(record)
                if fault=='unsafe-name': bad_record['target_bundle']='../primary'
                initial={'usr/share/rog5/ram-bundles/primary/Image':([],b'embedded')} if fault=='mixed' else {}
                with patch.object(final,'local_selector_identity',return_value={}), \
                        patch.object(final,'root_member',side_effect=bad_read), \
                        patch.object(final.C,'sealed_bundle_plan',side_effect=ValueError('invalid signature')
                                     if fault=='signature' else verify):
                    with self.assertRaises(ValueError,msg=fault): final.external_bundle_plan(root,bad_record,initial)

    def test_root_bundle_reads_are_bounded_nofollow_and_read_only(self):
        final=M.load('root_bundle_reader_test','scripts/host/check-release-composition.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root'; root.write_bytes(b'root')
            faults=['none','symlink-parent','symlink-file','group-write','hardlink','oversize','short','change']
            for fault in faults:
                def run(command,**kwargs):
                    self.assertNotIn('-w',command); self.assertEqual(command[-1],str(root))
                    self.assertEqual(kwargs['timeout'],5); self.assertTrue(callable(kwargs['preexec_fn']))
                    query=command[2]; last=query.endswith('/manifest')
                    if query.startswith('stat '):
                        kind='regular' if last else 'directory'; size=3 if last else 4096; mode='0400' if last else '0700'
                        if (fault=='symlink-parent' and not last) or (fault=='symlink-file' and last): kind='symlink'
                        if fault=='group-write': mode='0664'
                        if fault=='oversize' and last: size=10000
                        links=2 if fault=='hardlink' and last else 1
                        data=f'Inode: 42 Type: {kind} Mode: {mode}\nUser: 0 Group: 0 Project: 0 Size: {size}\nLinks: {links}\n'.encode()
                    else:
                        self.assertEqual(query,'cat /boot/rog5-linux/bundles/fixture/manifest')
                        data=b'x' if fault=='short' else b'abc'
                        if fault=='change': root.write_bytes(root.read_bytes()+b'change')
                    kwargs['stdout'].write(data)
                    return subprocess.CompletedProcess(command,0)
                with patch.object(final.shutil,'which',return_value='/usr/bin/debugfs'), \
                        patch.object(final.subprocess,'run',side_effect=run):
                    if fault=='none':
                        self.assertEqual(final.root_member(root,'/boot/rog5-linux/bundles/fixture/manifest',4096),b'abc')
                    else:
                        with self.assertRaises(ValueError,msg=fault): final.root_member(root,'/boot/rog5-linux/bundles/fixture/manifest',4096)
            for path in ('/etc/passwd','/boot/rog5-linux/bundles/../manifest','/boot/rog5-linux/bundles/fixture/evil;write'):
                with self.assertRaises(ValueError): final.root_member(root,path,4096)

    def test_external_bundle_rejects_stale_selector_before_payload_read(self):
        final=M.load('external_stale_test','scripts/host/check-release-composition.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root'; root.write_bytes(b'root')
            record=dict(execution='fastboot-boot-selector-trial',target_bundle='primary',fallback_bundle='fallback',
                        manifest_sha256='a'*64,fallback_manifest_sha256='b'*64,selector_sha256='c'*64)
            with patch.object(final,'local_selector_identity',side_effect=ValueError('stale selector')), \
                    patch.object(final,'root_member') as read:
                with self.assertRaisesRegex(ValueError,'stale selector'):
                    final.external_bundle_plan(root,record,{})
                read.assert_not_called()

    def test_server_snapshot_rejects_captured_old_selector_without_writes(self):
        final=M.load('a01_selector_test','scripts/host/check-release-composition.py')
        # Retained P24 snapshot predates the current selector-v2 staging.
        old=(b'format=rog5-slotb-selector-v1\nbundle=persistent-native-root-v11\n'
             b'manifest_sha256=a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2\n')
        metadata=b'Inode: 393292   Type: regular    Mode:  0600\nUser: 0 Group: 0 Project: 0 Size: 145\nLinks: 1\n'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'retained.ext4'; root.write_bytes(b'fixture')
            def run(command,**kwargs):
                self.assertNotIn('-w',command)
                self.assertEqual(command[-1],str(root))
                data=metadata if command[2].startswith('stat ') else old
                return subprocess.CompletedProcess(command,0,stdout=data,stderr=b'')
            with patch.object(final.subprocess,'run',side_effect=run), \
                    patch.object(final.shutil,'which',return_value='/usr/bin/debugfs'):
                with self.assertRaisesRegex(ValueError,'retained root selector mismatch'):
                    final.local_selector_identity(root,'c15c77824e3cecf128288f2c273c6bd7f93825e837568c669d8288145541d904')
                digest=M.hashlib.sha256(old).hexdigest()
                self.assertEqual(final.local_selector_identity(root,digest)['sha256'],digest)
            self.assertEqual(root.read_bytes(),b'fixture')

    def test_selector_metadata_refuses_missing_linked_and_oversize_before_cat(self):
        final=M.load('a01_selector_metadata','scripts/host/check-release-composition.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'retained.ext4'; root.write_bytes(b'fixture')
            for data in (b'',b'Type: symlink\nUser: 0 Group: 0 Project: 0 Size: 145\nLinks: 1\n',
                         b'Type: regular\nUser: 0 Group: 0 Project: 0 Size: 9000\nLinks: 1\n'):
                with patch.object(final.subprocess,'run',return_value=subprocess.CompletedProcess([],0,data,b'')) as run, \
                        patch.object(final.shutil,'which',return_value='/usr/bin/debugfs'):
                    with self.assertRaises(ValueError): final.local_selector_identity(root,'a'*64)
                    self.assertEqual(run.call_count,1)

    def test_timing_binds_signed_values_and_host_receiver(self):
        final=M.load('a01_timing_test','scripts/host/check-release-composition.py')
        manifest=dict(bundle='fixture',target_id='fixture',target_timeout='600',rollback_timeout='900')
        plan=dict(target_id='fixture',target_timeout='600',cmdline=
                  'rdinit=/init rog5.bundle=fixture rog5.target_timeout=600 rog5.recovery_timeout=900')
        wrapper=dict(cmdline='init=/init rog5.recovery_timeout=300')
        members=self.members()
        result=final.timing_contract(manifest,plan,wrapper,members)
        self.assertEqual(result['capture_seconds'],1380)
        self.assertEqual(result['rollback_seconds'],900)
        for wrong in (plan['cmdline']+' rog5.recovery_timeout=900',
                      plan['cmdline'].replace('900','600'),
                      plan['cmdline'].replace('600','870')):
            with self.assertRaises(ValueError):
                final.timing_contract(manifest,dict(plan,cmdline=wrong),wrapper,members)
        changed=copy.deepcopy(members)
        fields,data=changed['init']
        changed['init']=(fields,data.replace(b'169.254.77.1 8079',b'169.254.77.1 8080'))
        with self.assertRaises(ValueError): final.timing_contract(manifest,plan,wrapper,changed)

    def test_firmware_tree_checks_content_inventory_and_metadata(self):
        members={}
        for name,data in [('adsp.mdt',b'firmware'),('adsp.b00',b'')]:
            M.SEALED.ARCHIVE.add(members,'opt/rog5-charge-firmware/'+name,data,stat.S_IFREG|0o644)
        rows=''.join(M.hashlib.sha256(data).hexdigest()+'  '+name+'\n'
                     for name,data in [('adsp.b00',b''),('adsp.mdt',b'firmware')])
        digest=M.hashlib.sha256(rows.encode()).hexdigest()
        self.assertEqual(M.firmware_composition(members,digest,2)['tree_sha256'],digest)
        for bad in ('0'*64,digest):
            changed=copy.deepcopy(members)
            if bad==digest:
                fields,data=changed['opt/rog5-charge-firmware/adsp.mdt']
                fields[1]=stat.S_IFLNK|0o777
            with self.assertRaises(ValueError): M.firmware_composition(changed,bad,2)
        with self.assertRaises(ValueError): M.firmware_composition(members,digest,3)

    def test_signed_runtime_timeout_replaces_only_the_fixture(self):
        source=''.join(name+'() {\n :\n}\n' for name in M.FUNCTIONS)
        script=M.driver(source,recovery_timeout=900)
        self.assertIn('recovery_timeout=900\n',script)
        self.assertNotIn('recovery_timeout=1\n',script)
        for bad in (True,299,901,'900'):
            with self.assertRaises(ValueError): M.driver(source,recovery_timeout=bad)

    def test_vm_reuses_archive_without_duplicate_members_or_writable_root(self):
        source=''.join(name+'() {\n :\n}\n' for name in M.FUNCTIONS)
        members={}
        M.SEALED.ARCHIVE.add(members,'init',source.encode(),stat.S_IFREG|0o755)
        M.SEALED.ARCHIVE.add(members,'proc',b'',stat.S_IFDIR|0o755)
        original=copy.deepcopy(members)
        log=''.join('COMPOSITION_'+name+'_PASS\n' for name in M.MARKERS)+'COMPOSITION_VM_COMPLETE\n'
        def run(command, **kwargs):
            kwargs['stdout'].write(log.encode())
            self.assertIn('file=/arch.ext4,format=raw,if=none,id=root,readonly=on',command)
            self.assertIn('--network=none',command)
            self.assertNotIn('--privileged',command)
            self.assertNotIn('-dtb',command)
            return subprocess.CompletedProcess(command,0)
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(M.subprocess,'check_output',return_value='a'*64+'\n'), \
                patch.object(M.subprocess,'run',side_effect=run):
            result=M.vm_runtime(members,[],Path(tmp)/'kernel',Path(tmp)/'root',Path(tmp),profile='rescue')
            self.assertEqual(result['status'],'PASS')
        self.assertEqual(members,original)

    def test_combined_vm_refuses_missing_duplicate_or_failed_evidence(self):
        rows = [dict(name='fixture')]
        log = 'COMPOSITION_MODULE_fixture\n' + ''.join(
            'COMPOSITION_'+name+'_PASS\n' for name in M.MARKERS)
        log += 'COMPOSITION_VM_COMPLETE\n'
        self.assertTrue(M.vm_runtime_passed(log, 0, rows))
        for bad in (log.replace('COMPOSITION_EXITRD_PASS\n',''),
                    log+'COMPOSITION_VM_FAILURE\n', log+'WARNING: fixture\n',
                    log+'COMPOSITION_MODULE_fixture\n',
                    log.replace('COMPOSITION_MODULE_fixture','echo COMPOSITION_MODULE_fixture')):
            with self.subTest(log=bad):
                self.assertFalse(M.vm_runtime_passed(bad,0,rows))
        self.assertFalse(M.vm_runtime_passed(log,124,rows))

    def test_verified_plan_requires_exact_record_and_command_hash(self):
        command = 'rdinit=/init rog5.bundle=fixture'
        record = dict(format='rog5-verified-plan-v1', bundle='fixture',
                      manifest_sha256='a'*64, profile='persistent-root-ro-v1',
                      kernel_file='Image', dtb_file='board.dtb', initramfs_file='initramfs.cpio.gz',
                      target_id='fixture', target_release='7.1.4-g123456789abc',
                      target_timeout='600', cmdline_sha256=M.hashlib.sha256(command.encode()).hexdigest(),
                      cmdline=command)
        encode = lambda r: ''.join(k+'='+v+'\n' for k,v in r.items()).encode()
        self.assertEqual(M.verified_plan(encode(record),'fixture','a'*64), record)
        for raw in (encode(record)+b'bundle=fixture\n', encode(record).rstrip(b'\n'),
                    encode(dict(record, bundle='other')), encode(dict(record, manifest_sha256='b'*64)),
                    encode(dict(record, cmdline_sha256='0'*64)), encode(dict(record, extra='value')),
                    encode(dict(record, kernel_file='../Image')), b'not a plan\n'):
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                M.verified_plan(raw,'fixture','a'*64)

    def test_sealed_verifier_refuses_unsafe_input_before_process(self):
        with patch.object(M.subprocess,'run') as run:
            for bundle, digest in (('../bad','a'*64),('fixture','bad'),('fixture','a'*64)):
                with self.subTest(bundle=bundle), self.assertRaises(ValueError):
                    M.sealed_bundle_plan({},bundle,digest)
            run.assert_not_called()

    def test_wrapper_pairs_exact_payloads_and_full_command_line(self):
        kernel, recovery = b'fixture kernel', b'fixture recovery'
        cmdline = 'init=/init rog5.recovery_timeout=300'
        header = b'ANDROID!' + struct.pack('<9I', len(kernel), len(recovery),
                                            0, 1580, 0, 0, 0, 0, 3)
        header += cmdline.encode().ljust(1536, b'\0')
        boot = header.ljust(4096, b'\0') + kernel.ljust(4096, b'\0') + recovery
        result = M.wrapper_composition(boot, kernel, recovery, cmdline)
        self.assertFalse(result['avb_verified'])
        self.assertFalse(result['release_qualified'])
        for bad_boot, bad_kernel, bad_recovery, bad_cmdline in (
            (boot, kernel+b'x', recovery, cmdline),
            (boot, kernel, recovery+b'x', cmdline),
            (boot, kernel, recovery, cmdline+' rog5.recovery_timeout=900'),
            (boot[:-1], kernel, recovery, cmdline),
            (b'WRONG!!!'+boot[8:], kernel, recovery, cmdline),
            (boot[:40]+struct.pack('<I',4)+boot[44:], kernel, recovery, cmdline),
            (boot[:20]+struct.pack('<I',0)+boot[24:], kernel, recovery, cmdline),
            (boot[:24]+struct.pack('<I',1)+boot[28:], kernel, recovery, cmdline),
            (boot[:12]+struct.pack('<I',len(recovery)+1)+boot[16:], kernel, recovery, cmdline),
        ):
            with self.subTest(size=len(bad_boot), cmdline=bad_cmdline), self.assertRaises(ValueError):
                M.wrapper_composition(bad_boot, bad_kernel, bad_recovery, bad_cmdline)

    def test_shutdown_is_required_and_bound_to_reviewed_source(self):
        members = self.members()
        item = ([0, stat.S_IFREG | 0o755, 0, 0, 1],
                (M.REPO/'initramfs/persistent-root-shutdown-standalone').read_bytes())
        members['shutdown'] = item
        M.archive_parameters(members)
        for value in (None, (item[0], b'#!/bin/sh\nexit 0\n'),
                      ([0, stat.S_IFLNK | 0o777, 0, 0, 1], item[1])):
            altered = copy.deepcopy(members)
            if value is None:
                del altered['shutdown']
            else:
                altered['shutdown'] = value
            with self.subTest(value=value is None), self.assertRaises(ValueError):
                M.archive_parameters(altered)

    def test_exitrd_is_checked_from_the_arch_root_without_execution(self):
        sealed = ''.join(name+'() {\n :\n}\n' for name in M.FUNCTIONS)
        script = M.driver(sealed, profile='server-runtime')
        self.assertIn('chroot /newroot /usr/bin/chroot /run/initramfs /bin/sh -n /shutdown', script)
        self.assertIn('COMPOSITION_EXITRD_PASS', script)
        self.assertIn('EXITRD', M.MARKERS)
        self.assertNotIn('chroot /newroot /usr/bin/chroot /run/initramfs /bin/sh /shutdown', script)

    def test_sealed_module_load_order_and_dependency_refusals(self):
        item = lambda data: ([0, stat.S_IFREG | 0o644, 0, 0, 1], data)
        elf = bytearray(64)
        elf[:6] = b'\x7fELF\x02\x01'
        elf[16:20] = b'\x01\x00\xb7\x00'
        members = {
            'init': item(b'insmod /rog5-ufs-modules/core.ko || return 1\n'
                         b'if ! power_usb_failure=$(/sbin/rog5-load-persistent-power-usb); then\n'
                         b' :\nfi\nload_deferred_ufs_modules\n'),
            'sbin/rog5-load-persistent-power-usb': item(
                b'load_module power.ko power power\n'),
            'rog5-ufs-modules/core.ko': item(bytes(elf)),
            'rog5-power-usb-modules/power.ko': item(bytes(elf)),
        }
        release='7.1.4-g359318de534f'
        invalid_dependency=''
        def inspect(argv, **kwargs):
            name=Path(argv[-1]).stem
            return {'name':name, 'vermagic':release+' SMP preempt mod_unload aarch64',
                    'depends':invalid_dependency or ('power' if name=='core' else '')}[argv[2]]+'\n'
        with patch.object(M.subprocess,'check_output',side_effect=inspect):
            result=M.module_closure(members,release)
            self.assertEqual([row['name'] for row in result],['power','core'])
            for mutation in ('missing','extra','alias','wrong-arch','wrong-release','order'):
                changed=copy.deepcopy(members)
                expected=release
                if mutation=='missing': del changed['rog5-ufs-modules/core.ko']
                if mutation=='extra': changed['rog5-ufs-modules/extra.ko']=item(bytes(elf))
                if mutation=='alias': changed['rog5-ufs-modules/core.ko'][0][1]=stat.S_IFLNK|0o777
                if mutation=='wrong-arch': changed['rog5-ufs-modules/core.ko']=item(b'not ARM ELF')
                if mutation=='wrong-release': expected=release+'wrong'
                if mutation=='order':
                    changed['init']=item(b'insmod /rog5-power-usb-modules/power.ko || return 1\n')
                    changed['sbin/rog5-load-persistent-power-usb']=item(b'load_module core.ko core core\n')
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    M.module_closure(changed,expected)
            for invalid_dependency in ('missing', 'core', '../power', 'power\ncore'):
                with self.subTest(dependency=invalid_dependency), self.assertRaisesRegex(
                        ValueError,'dependency absent or loaded too late'):
                    M.module_closure(members,release)
            with patch.object(M.time,'monotonic',side_effect=[0,11]), self.assertRaisesRegex(
                    ValueError,'metadata deadline exceeded'):
                M.module_closure(members,release)

    def members(self, overlay='0'):
        values = dict(KERNEL_RELEASE='7.1.4-g359318de534f', UFS_STORAGE_MODE='read-only',
                      PROBE_BOOT_ID='staged-seal', NATIVE_ROOT_MODE='1',
                      SSH_DIAGNOSTIC_MODE='0', PERSISTENT_OVERLAY_MODE=overlay)
        item = lambda data: ([0, stat.S_IFREG | 0o755, 0, 0, 1], data)
        return {
            'shutdown': ([0, stat.S_IFREG | 0o755, 0, 0, 1],
                         (M.REPO/'initramfs/persistent-root-shutdown-standalone').read_bytes()),
            'init': item(M.SEALED.ARCHIVE.render_boot_template(M.REPO/'initramfs/persistent-root-init', values)),
            'usr/local/sbin/rog5-p2-attest': item(M.SEALED.ARCHIVE.render_boot_template(
                M.REPO/'initramfs/persistent-root-attest', {k: values[k] for k in (
                    'UFS_STORAGE_MODE', 'PROBE_BOOT_ID', 'NATIVE_ROOT_MODE', 'PERSISTENT_OVERLAY_MODE')})),
            'sbin/rog5-load-persistent-power-usb': item((M.REPO/'scripts/device/load-persistent-root-power-usb.sh').read_bytes()),
            'usr/local/sbin/rog5-persistent-state': item((M.REPO/'initramfs/persistent-service-state').read_bytes()),
            'usr/local/sbin/rog5-persistent-ssh-identity': item((M.REPO/'initramfs/persistent-ssh-identity').read_bytes()),
            'usr/local/sbin/rog5-persistent-keyring': item((M.REPO/'initramfs/persistent-package-keyring').read_bytes()),
            'usr/local/share/rog5/rog5-package-keyring.service': (
                [0, stat.S_IFREG | 0o644, 0, 0, 1],
                (M.REPO/'configs/systemd/rog5-package-keyring.service').read_bytes()),
        }

    def test_matching_startup_bytes_require_safe_executable_metadata(self):
        members = self.members()
        members['usr/local/sbin/rog5-startup-observer'] = (
            [0, stat.S_IFREG | 0o755, 0, 0, 1],
            (M.REPO/'initramfs/persistent-startup-observer').read_bytes())
        M.archive_parameters(members)
        for name in members:
            mutations = ((1, stat.S_IFLNK | 0o777), (1, stat.S_IFREG | 0o666),
                         (2, 1000), (3, 1000), (4, 2))
            if name != 'usr/local/share/rog5/rog5-package-keyring.service':
                mutations += ((1, stat.S_IFREG | 0o644),)
            for index, value in mutations:
                changed = copy.deepcopy(members)
                changed[name][0][index] = value
                with self.subTest(member=name, field=index, value=value), self.assertRaises(ValueError):
                    M.archive_parameters(changed)

    def server_members(self):
        members = self.members('1')
        prefix = 'rog5-native-wifi/'
        for directory in ('native-wifi', 'native-wifi-persistent'):
            for path in (M.REPO/'initramfs'/directory).rglob('*'):
                if path.is_file():
                    data = path.read_bytes().replace(b'@OUTER_SECONDS@', b'900')
                    mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                    members[prefix+str(path.relative_to(M.REPO/'initramfs'/directory))] = (
                        [0, stat.S_IFREG | mode, 0, 0, 1], data)
        members[prefix+'automatic'] = ([0, stat.S_IFREG | 0o444, 0, 0, 1],
                                       b'rog5-native-wifi-boot-v1\n')
        return members

    def test_server_runtime_requires_explicit_profile_and_current_radio_userspace(self):
        members = self.server_members()
        with self.assertRaises(ValueError):
            M.archive_parameters(members)
        self.assertEqual(M.archive_parameters(members, profile='server-runtime')['PERSISTENT_OVERLAY_MODE'], '1')
        for name in ('runtime', 'timing', 'units/before-state.conf', 'automatic'):
            altered = copy.deepcopy(members)
            fields, data = altered['rog5-native-wifi/'+name]
            altered['rog5-native-wifi/'+name] = fields, data+b'\n'
            with self.subTest(name=name), self.assertRaises(ValueError):
                M.archive_parameters(altered, profile='server-runtime')
        with self.assertRaises(ValueError):
            M.archive_parameters(self.members(), profile='server-runtime')
        with self.assertRaises(ValueError):
            M.archive_parameters(members, profile='typo')

    def test_server_driver_installs_but_never_activates_radio(self):
        sealed = ''.join(name+'() {\n :\n}\n' for name in M.FUNCTIONS)
        script = M.driver(sealed, profile='server-runtime')
        self.assertIn('expected_persistent_overlay_mode=1', script)
        self.assertIn('native_wifi_boot=1', script)
        self.assertLess(script.index('cp -a /rog5-native-wifi /run/'), script.index('\nprepare_runtime\n'))
        self.assertIn('/run/systemd/system/rog5-wifi-radio.service', script)
        self.assertIn('/run/systemd/system/rog5-wifi-healthy.service', script)
        self.assertNotIn('systemctl start', script)
        self.assertNotIn('runtime radio', script)

    def test_server_module_component_does_not_silently_qualify_radio_or_extra_modules(self):
        item = ([0, stat.S_IFREG | 0o644, 0, 0, 1], b'fixture')
        names = ('rog5-pmic-pon-readonly.ko', 'rog5-s12-ufs-vote.ko',
                 'rog5-wifi-activate.ko', 'module-root-complete.tar.gz')
        members = {'rog5-native-wifi/'+name: item for name in names}
        members['unexpected.ko'] = item
        core, pending = M.core_module_members(members, 'server-runtime')
        self.assertIn('unexpected.ko', core)  # Existing inventory guard must refuse it.
        self.assertEqual(len(pending), 4)
        self.assertTrue(all(row['status'] == 'NOT RUN' for row in pending))
        self.assertEqual(M.core_module_members(members, 'rescue'), (members, []))
        del members['rog5-native-wifi/'+names[0]]
        with self.assertRaises(ValueError):
            M.core_module_members(members, 'server-runtime')

    def test_server_driver_provides_prior_overlay_stage_input(self):
        sealed = ''.join(name+'() {\n :\n}\n' for name in M.FUNCTIONS if name != 'prepare_runtime')
        sealed += '''prepare_runtime() {
test -f /run/rog5-persistent-state-userdata-device
test "$(cat /run/rog5-persistent-state-userdata-device)" = "$overlay_userdata"
test "$(stat -c %a /run/rog5-persistent-state-userdata-device)" = 444
}
'''
        script = M.driver(sealed, profile='server-runtime').split('echo COMPOSITION_PREPARE_PASS')[0]
        with tempfile.TemporaryDirectory() as tmp:
            script = script.replace('/run/rog5-persistent-state-userdata-device', tmp+'/userdata')
            script = script.replace('cp -a /rog5-native-wifi /run/', ': # no radio in this fixture')
            result = subprocess.run(['sh','-c',script],capture_output=True,text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_paired_archive_and_stale_producer_consumer(self):
        members = self.members()
        self.assertEqual(M.archive_parameters(members)['NATIVE_ROOT_MODE'], '1')
        for name in members:
            changed = copy.deepcopy(members)
            changed[name] = (changed[name][0], changed[name][1] + b'\n# stale\n')
            with self.subTest(member=name), self.assertRaises(ValueError):
                M.archive_parameters(changed)
        for name in ('usr/local/sbin/rog5-persistent-state',
                     'usr/local/sbin/rog5-persistent-ssh-identity',
                     'usr/local/sbin/rog5-persistent-keyring',
                     'usr/local/share/rog5/rog5-package-keyring.service'):
            changed = copy.deepcopy(members)
            del changed[name]
            with self.subTest(missing=name), self.assertRaises(ValueError):
                M.archive_parameters(changed)

    def test_unresolved_parameter_optional_radio_and_wrong_profile(self):
        for name, data in (('extra', b'@OUTER_SECONDS@'),
                           ('rog5-native-wifi/init', b'activation')):
            members = self.members()
            members[name] = ([0, stat.S_IFREG | 0o755], data)
            with self.subTest(name=name), self.assertRaises(ValueError):
                M.archive_parameters(members)
        members = self.members()
        fields, data = members['init']
        members['init'] = fields, data.replace(b'expected_native_root_mode=1', b'expected_native_root_mode=0')
        with self.assertRaises(ValueError):
            M.archive_parameters(members)

    def test_driver_uses_sealed_functions_and_rejects_missing_or_duplicate(self):
        sealed = ''.join(name+'() {\n echo sealed-'+name+'\n}\n' for name in M.FUNCTIONS)
        result = M.driver(sealed)
        for name in M.FUNCTIONS:
            self.assertIn('echo sealed-'+name, result)
        self.assertNotIn('switch_root', result)
        for broken in ('', sealed + sealed):
            with self.assertRaises(ValueError):
                M.driver(broken)

    def test_driver_supplies_observer_lifetime_without_claiming_deployed_timing(self):
        sealed = ''.join(name+'() {\n :\n}\n' for name in M.FUNCTIONS if name != 'prepare_runtime')
        sealed += 'prepare_runtime() {\n test "$recovery_timeout" -gt 0\n}\n'
        script = M.driver(sealed).split('echo COMPOSITION_PREPARE_PASS')[0]
        result = subprocess.run(['sh','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('fixture, not deployed timing',script)

    def test_driver_verifies_present_observer_and_rejects_stale_observer_bytes(self):
        members=self.members()
        fields=[0, stat.S_IFREG | 0o755, 0, 0, 1]
        members['usr/local/sbin/rog5-startup-observer']=(fields,b'#!/bin/sh\nexit 0\n')
        with self.assertRaisesRegex(ValueError, 'stale startup observer'):
            M.archive_parameters(members)
        self.assertIn('/run/systemd/system/rog5-startup-observer.service',
                      M.driver(members['init'][1].decode()))

    def test_mount_requires_exact_ro_loop_backing_and_no_recovery(self):
        entry = dict(target='/private/root', source='/dev/loop7', fstype='ext4',
                     options='ro,nodev,nosuid,noexec,norecovery')
        def check(record=entry, backing='/private/root.ext4\n', ro='1\n'):
            outputs = [json.dumps({'filesystems': [record]}), backing, ro]
            with patch.object(M.subprocess, 'check_output', side_effect=outputs):
                return M.verify_mount(Path('/private/root'), Path('/private/root.ext4'))
        self.assertEqual(check(), entry)
        for field, value in (('source', '/dev/sda'), ('target', '/private'),
                             ('fstype', 'overlay'), ('options', 'rw,nodev,nosuid,norecovery'),
                             ('options', 'ro,nodev,nosuid'), ('options', 'ro,nosuid,norecovery')):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                check(dict(entry, **{field: value}))
        for backing, ro in (('/wrong/image\n', '1\n'), ('/private/root.ext4\n', '0\n')):
            with self.assertRaises(ValueError):
                check(backing=backing, ro=ro)

    def test_component_receipt_cannot_qualify_full_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp)/'artifact'
            artifact.write_bytes(b'fixture')
            roles = M.ACCEPTANCE.ARTIFACT_ROLES - {'boot_bundle'}
            record = dict(format='rog5-release-inputs-v1', candidate_id='component-only',
                          source_revision='a'*40, artifacts={role: dict(path=str(artifact),
                          size=7, sha256=M.ACCEPTANCE.sha_file(artifact)) for role in roles})
            receipt = Path(tmp)/'receipt.json'; receipt.write_text(json.dumps(record))
            self.assertEqual(set(M.ACCEPTANCE.verify_release(receipt, required_roles=roles)['artifacts']), roles)
            for required in (None, set(), {'unknown'}):
                with self.assertRaises(ValueError):
                    M.ACCEPTANCE.verify_release(receipt, required_roles=required)


if __name__ == '__main__':
    unittest.main(verbosity=2)
