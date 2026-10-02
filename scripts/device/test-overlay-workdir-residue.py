#!/usr/bin/env python3
"""OverlayFS work/work crash residue: the init's pre-mount check against the
kernel's own mount-time cleanup.

verify_overlay_workdir_pre_mount (initramfs/persistent-root-init) must accept
exactly the residue that k113's ovl_workdir_cleanup() removes on a read-write
mount, and refuse the rest before anything is mounted.

1. Predicate cases (always): the init functions on directory fixtures under
   `unshare -r` (owner 0 as on the phone). Set ROG5_TEST_BUSYBOX and
   ROG5_TEST_QEMU to run them under the target ARM64 busybox.
2. Kernel cases (optional, private inputs): a networkless QEMU virt guest
   boots the production kernel Image (k113 by default, ROG5_OVERLAY_KERNEL)
   with the target archive's busybox (ROG5_OVERLAY_ARCHIVE) on a disposable
   ext4 disk. Boot 1 mounts a real overlay, makes real whiteouts, adds residue
   of every kernel inode type to work/work and resets the guest with the
   overlay mounted (journal pending). Boot 2 replays the journal, runs the
   check, mounts the overlay and requires a read-write mount, an empty
   work/work and intact upper data; then it shows that each refused shape
   either is refused by the check or makes the kernel mount read-only.
   The host finally runs e2fsck -fn on the disk. Needs podman and the
   localhost/rog5-qemu-gate:ubuntu-24.04 image (qemu-system-aarch64).
No phone, no host block device and no root are used.
"""
import gzip
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
INIT = REPO/'initramfs/persistent-root-init'
FUNCTIONS = ('overlay_scratch_name', 'overlay_scratch_subdirs', 'verify_overlay_workdir_pre_mount')
APPLETS = ('find', 'stat')
STATE = Path.home()/'.local/state'
KERNEL = Path(os.environ.get('ROG5_OVERLAY_KERNEL', STATE/'rog5-kernel-7.2.7-build-r113/objects/arch/arm64/boot/Image'))
ARCHIVE = Path(os.environ.get('ROG5_OVERLAY_ARCHIVE', STATE/'rog5-production-boot-20260923/ramdisk-main-k113-d13-261001a/target.cpio.gz'))
QEMU_IMAGE = 'localhost/rog5-qemu-gate:ubuntu-24.04'


def function(text, name):
    match = re.search(rf'^{name}\(\) \{{\n.*?^\}}\n', text, re.M | re.S)
    assert match, name
    return match.group(0)


LIBRARY = 'set -u\n' + ''.join(function(INIT.read_text(), name) for name in FUNCTIONS)


def unshare_ok():
    return subprocess.run(['unshare', '-r', 'true'], capture_output=True).returncode == 0


@unittest.skipUnless(unshare_ok(), 'unshare -r unavailable')
class Predicate(unittest.TestCase):
    """Fixture trees built inside one user namespace, so every node is 0:0."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix='rog5-overlay-work-'))
        (self.dir/'lib.sh').write_text(LIBRARY)
        self.shell, self.env = 'sh', dict(os.environ)
        if os.environ.get('ROG5_TEST_BUSYBOX'):
            qemu, busybox = os.environ['ROG5_TEST_QEMU'], os.environ['ROG5_TEST_BUSYBOX']
            applets = self.dir/'applets'
            applets.mkdir()
            for name in APPLETS:
                (applets/name).write_text(f'#!/bin/sh\nexec {qemu} {busybox} {name} "$@"\n')
                (applets/name).chmod(0o755)
            self.shell = f'{qemu} {busybox} sh'
            self.env['PATH'] = f'{applets}:{os.environ["PATH"]}'

    def tearDown(self):
        subprocess.run(['unshare', '-r', 'chmod', '-R', 'u+rwx', str(self.dir)])
        shutil.rmtree(self.dir)

    def check(self, build, expected):
        """Run shell `build` in $S (the state root) and then the check."""
        state = self.dir/'state'
        if state.exists():
            subprocess.run(['unshare', '-r', 'chmod', '-R', 'u+rwx', str(state)])
            shutil.rmtree(state)
        script = (f'set -eu\nS={state}\nmkdir -p "$S/upper" "$S/work"\nchmod 0700 "$S/work"\n'
                  f'cd "$S"\n{build}\ncd /\n'
                  f'if {self.shell} -c \'. {self.dir}/lib.sh; verify_overlay_workdir_pre_mount "$1"\' sh "$S"\n'
                  'then echo CHECK=PASS; else echo CHECK=FAIL; fi\n')
        result = subprocess.run(['unshare', '-r', 'sh', '-c', script], env=self.env,
                                capture_output=True, text=True, timeout=60)
        # A fixture that could not be built must not pass as a refusal.
        self.assertEqual(result.returncode, 0, build + '\n' + result.stderr)
        self.assertEqual(result.stdout.strip().splitlines()[-1:],
                         ['CHECK=' + ('PASS' if expected else 'FAIL')], build + '\n' + result.stderr)

    def sock(self, path):
        """A socket node (copy-up of a socket creates one with mknod)."""
        return (f"python3 -c 'import socket,sys; socket.socket(socket.AF_UNIX).bind(sys.argv[1])' "
                f"'{path}'\n")

    def test_empty_states_pass(self):
        self.check(':', True)
        self.check('mkdir -m 0 work/work', True)

    def test_every_kernel_residue_type_passes(self):
        build = '''mkdir -m 0 work/work
W=work/work
mknod "$W/#1" c 0 0
ln "$W/#1" upper/whiteout-a
ln "$W/#1" upper/whiteout-b
mkdir -m 0755 "$W/#2"
mkdir -m 0700 "$W/#3"
mknod "$W/#3/name with space" c 0 0
mknod "$W/#3/.hidden" c 0 0
mknod "$W/#3/..dots" c 0 0
mknod "$W/#3/$(printf 'new\\nline')" c 0 0
mknod "$W/#3/*" c 0 0
mkdir "$W/#3/#e"
ln -s /etc/passwd "$W/#4"
ln -s ../../upper "$W/#5"
mkfifo "$W/#6"
: >"$W/#7"
echo data >upper/file
ln upper/file "$W/#8"
mknod "$W/#ffffffff" c 0 0
mkdir "$W/#a0"
ln -s dangling "$W/#a0/link"
: >"$W/#a0/file"
'''
        build += self.sock('work/work/#9')
        self.check(build, True)

    def test_names_that_are_not_kernel_temporaries_fail(self):
        for name in ('foo', '#', '#A', '#01', '#00', '#123456789', '#g', '#1 ', '.#1', '#-1'):
            with self.subTest(name=name):
                self.check(f'mkdir -m 0 work/work\nmknod "work/work/{name}" c 0 0', False)
        self.check('mkdir -m 0 work/work\nmkdir "work/work/x1"', False)
        self.check('mkdir -m 0 work/work\nln -s /etc "work/work/etc"', False)

    def test_deeper_trees_fail(self):
        self.check('mkdir -m 0 work/work\nmkdir -p "work/work/#2/sub"\n: >"work/work/#2/sub/f"', False)
        self.check('mkdir -m 0 work/work\nmkdir -p "work/work/#2/sub/sub2"', False)
        self.check('mkdir -m 0 work/work\nmkdir -p "work/work/#2/.sub"\nmknod "work/work/#2/.sub/w" c 0 0',
                   False)

    def test_work_itself_must_be_exact(self):
        self.check('mkdir -m 0 work/work\nmkdir work/index', False)
        self.check(': >work/stray', False)
        self.check('mkdir -m 0755 work/work', False)
        self.check('mkdir -m 0 work/other\nln -s other work/work', False)
        self.check('mkdir -m 0 work/work\nmkdir -m 0 work/work2', False)

    def test_a_level_one_symlink_to_a_directory_is_not_entered(self):
        # The kernel unlinks a symlink without following it; the check must
        # not follow it either (the target here holds a non-empty directory).
        self.check('mkdir -m 0 work/work\nmkdir -p elsewhere/sub\n: >elsewhere/sub/f\n'
                   'ln -s "$S/elsewhere" "work/work/#4"', True)


GUEST = r'''#!/bin/busybox sh
/bin/busybox --install -s /bin
export PATH=/bin
mkdir -p /proc /sys /dev /state /lower /merged
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
trap 'echo "RESULT guest-exit $?"; poweroff -f' EXIT
. /lib.sh
phase=$(sed -n 's/.*rog5test.phase=\([0-9]\).*/\1/p' /proc/cmdline)
i=0
while [ ! -b /dev/vda ]; do i=$((i + 1)); [ "$i" -le 20 ] || exit 1; sleep 0.5; done
result() { echo "RESULT $1 $2"; }
lower() {
	mount -t tmpfs -o size=4m tmpfs /lower
	echo gone >/lower/gone1
	echo gone >/lower/gone2
	echo kept >/lower/kept
	mkdir /lower/d1
	echo x >/lower/d1/f
	mount -o remount,ro /lower
}
overlay_mode() {
	mount -t overlay overlay \
		-o lowerdir=/lower,upperdir=/state/upper,workdir=/state/work /merged || {
		echo failed; return 0; }
	awk '$2 == "/merged" && $3 == "overlay" { split($4, o, ","); print o[1] }' /proc/mounts
}
mount -t ext4 -o rw,nodev,nosuid,noatime /dev/vda /state
if [ "$phase" = 1 ]; then
	set -e
	mkdir -m 0755 /state/upper
	mkdir -m 0700 /state/work
	lower
	result phase1-overlay "$(overlay_mode)"
	rm /merged/gone1 /merged/gone2
	rm -r /merged/d1
	echo data >/merged/newfile
	echo sentinel >/state/sentinel
	W=/state/work/work
	mkdir -m 0755 "$W/#10"
	chown 1000:1000 "$W/#10"
	mkdir -m 0700 "$W/#11"
	mknod "$W/#11/name with space" c 0 0
	mknod "$W/#11/.hidden" c 0 0
	mknod "$W/#11/$(printf 'nl\nx')" c 0 0
	mkdir "$W/#11/#e"
	ln -s /state/sentinel "$W/#12"
	mkfifo "$W/#13"
	: >"$W/#14"
	ln /state/upper/newfile "$W/#15"
	mknod "$W/#16" b 7 0
	mknod "$W/#17" c 1 3
	mknod "$W/#ffffffff" c 0 0
	ln -s /state "$W/#18"
	result residue-count "$(find "$W" -mindepth 1 | wc -l)"
	result shared-whiteout "$(find "$W" -maxdepth 1 -type c -links +1 | wc -l)"
	sync
	echo b >/proc/sysrq-trigger
	sleep 10
	exit 1
fi
result journal-replay "$(dmesg | grep -c 'EXT4-fs (vda): recovery complete')"
result residue-before "$(find /state/work/work -mindepth 1 | wc -l)"
if verify_overlay_workdir_pre_mount /state; then result precheck PASS; else result precheck FAIL; fi
lower
result overlay "$(overlay_mode)"
result residue-after "$(find /state/work/work -mindepth 1 | wc -l)"
result newfile "$(cat /state/upper/newfile):$(stat -c %h /state/upper/newfile)"
result sentinel "$(cat /state/sentinel)"
result merged "$(ls /merged | tr '\n' ,)"
umount /merged
# Refused shapes: the check must refuse each, and the ones the kernel would
# not clean must make it mount read-only.
W=/state/work/work
refused() {
	name=$1
	shift
	"$@"
	if verify_overlay_workdir_pre_mount /state; then check=PASS; else check=FAIL; fi
	result "refused-$name" "$check:$(overlay_mode)"
	umount /merged 2>/dev/null
	rm -rf /state/work/work /state/work/other
	mkdir -m 0 /state/work/work
}
nonempty() { mkdir -p "$W/#20/sub"; : >"$W/#20/sub/f"; }
nested() { mkdir -p "$W/#21/sub/sub2"; }
plainname() { mknod "$W/foo" c 0 0; }
upperhex() { mknod "$W/#A" c 0 0; }
extra() { mkdir -m 0 /state/work/other; }
wrongmode() { chmod 0755 "$W"; }
wrongowner() { chown 1000:0 "$W"; }
refused level2-nonempty nonempty
refused level2-nested nested
refused plain-name plainname
refused upper-hex upperhex
refused extra-work-entry extra
refused work-mode wrongmode
refused work-owner wrongowner
rm -rf /state/work/work
if verify_overlay_workdir_pre_mount /state; then result clean-absent PASS; else result clean-absent FAIL; fi
result clean-absent-overlay "$(overlay_mode)"
umount /merged
umount /lower
umount /state
result done 1
'''


def newc(members):
    """members: (name, mode, data); every node 0:0."""
    out = io.BytesIO()
    for ino, (name, mode, data) in enumerate(members + [('TRAILER!!!', 0, b'')], 1):
        raw = name.encode() + b'\0'
        out.write(b'070701' + b''.join(b'%08X' % v for v in (
            ino, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(raw), 0)))
        out.write(raw + b'\0' * ((-(110 + len(raw))) % 4))
        out.write(data + b'\0' * ((-len(data)) % 4))
    return out.getvalue()


def archive_member(archive, wanted):
    data = gzip.decompress(archive.read_bytes())
    offset = 0
    while True:
        fields = [int(data[offset + 6 + 8*i:offset + 14 + 8*i], 16) for i in range(13)]
        size, namesize = fields[6], fields[11]
        start = offset + 110
        name = data[start:start + namesize - 1].decode()
        body = start + namesize + ((-(110 + namesize)) % 4)
        if name == 'TRAILER!!!':
            raise KeyError(wanted)
        if name == wanted:
            return data[body:body + size]
        offset = body + size + ((-size) % 4)


def qemu_ready():
    if not (KERNEL.is_file() and ARCHIVE.is_file()):
        return 'private kernel Image or target archive not present'
    for tool in ('podman', 'mkfs.ext4', 'e2fsck'):
        if shutil.which(tool) is None:
            return f'{tool} not installed'
    image = subprocess.run(['podman', 'image', 'exists', QEMU_IMAGE], capture_output=True)
    if image.returncode != 0:
        return f'{QEMU_IMAGE} not installed'
    return None


class Kernel(unittest.TestCase):
    """Real ext4 + OverlayFS under the production kernel in a QEMU guest."""

    def setUp(self):
        reason = qemu_ready()
        if reason:
            print('kernel cases skipped:', reason, file=sys.stderr)
            self.skipTest('kernel cases need private inputs')

    def boot(self, work, phase):
        argv = ['podman', 'run', '--rm', '--network=none', '-v', f'{work}:/w',
                QEMU_IMAGE, 'qemu-system-aarch64', '-M', 'virt', '-cpu', 'cortex-a76', '-smp', '2',
                '-m', '1024', '-nographic', '-no-reboot', '-nic', 'none',
                '-kernel', '/w/Image', '-initrd', '/w/initrd.gz',
                '-append', f'console=ttyAMA0 rdinit=/init panic=-1 loglevel=4 rog5test.phase={phase}',
                '-drive', 'file=/w/disk.ext4,if=virtio,format=raw']
        run = subprocess.run(argv, capture_output=True, text=True, errors='replace', timeout=240)
        results = dict(line.split(' ', 2)[1:] for line in run.stdout.splitlines()
                       if line.startswith('RESULT ') and line.count(' ') >= 2)
        return results, run.stdout[-4000:]

    def test_kernel_cleans_accepted_residue_and_refuses_the_rest(self):
        work = Path(tempfile.mkdtemp(prefix='rog5-overlay-qemu-'))
        try:
            shutil.copyfile(KERNEL, work/'Image')
            busybox = archive_member(ARCHIVE, 'bin/busybox')
            musl = archive_member(ARCHIVE, 'lib/ld-musl-aarch64.so.1')
            members = [('bin', 0o40755, b''), ('lib', 0o40755, b''),
                       ('bin/busybox', 0o100755, busybox),
                       ('lib/ld-musl-aarch64.so.1', 0o100755, musl),
                       ('lib.sh', 0o100644, LIBRARY.encode()),
                       ('init', 0o100755, GUEST.encode())]
            (work/'initrd.gz').write_bytes(gzip.compress(newc(members), 1))
            disk = work/'disk.ext4'
            with disk.open('xb') as stream:
                stream.truncate(64 * 1024 * 1024)
            subprocess.run(['mkfs.ext4', '-q', '-F', str(disk)], check=True)

            first, log1 = self.boot(work, 1)
            self.assertEqual(first.get('phase1-overlay'), 'rw', log1)
            self.assertEqual(first.get('shared-whiteout'), '1', log1)
            self.assertNotIn('guest-exit', first, log1)  # reset, not a clean exit

            second, log2 = self.boot(work, 2)
            expected = {
                'journal-replay': '1',
                'precheck': 'PASS',
                'overlay': 'rw',
                'residue-after': '0',
                'newfile': 'data:1',
                'sentinel': 'sentinel',
                'merged': 'kept,newfile,',
                'refused-level2-nonempty': 'FAIL:ro',
                'refused-level2-nested': 'FAIL:ro',
                'refused-plain-name': 'FAIL:rw',
                'refused-upper-hex': 'FAIL:rw',
                'refused-extra-work-entry': 'FAIL:rw',
                'refused-work-mode': 'FAIL:rw',
                'refused-work-owner': 'FAIL:rw',
                'clean-absent': 'PASS',
                'clean-absent-overlay': 'rw',
                'done': '1',
            }
            for key, value in expected.items():
                self.assertEqual(second.get(key), value, f'{key}\n{log2}')
            self.assertGreaterEqual(int(second['residue-before']), 13, log2)
            fsck = subprocess.run(['e2fsck', '-fn', str(disk)], capture_output=True, text=True)
            self.assertEqual(fsck.returncode, 0, fsck.stdout + fsck.stderr)
        finally:
            shutil.rmtree(work)


if __name__ == '__main__':
    unittest.main(verbosity=2)
