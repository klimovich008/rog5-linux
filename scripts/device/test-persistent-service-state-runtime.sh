#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper=$repo/initramfs/persistent-service-state
init=$repo/initramfs/persistent-root-init
builder=$repo/scripts/device/build-persistent-root-standalone-initramfs.sh
shutdown=$repo/initramfs/persistent-root-shutdown-standalone
ssh_identity=$repo/initramfs/persistent-ssh-identity

fail() { echo "FAIL $*" >&2; exit 1; }

for path in "$helper" "$init" "$builder" "$shutdown" "$ssh_identity"; do
	[ -x "$path" ]
	sh -n "$path"
done

for contract in \
	'expected_physical_count=117' \
	'expected_userdata_partition=23' \
	'expected_userdata_start=18821440' \
	'expected_userdata_sectors=408997568' \
	'expected_userdata_partuuid=8d82ef11-4d42-60e9-24e8-4d6ebf20491b' \
	'expected_userdata_uuid=0892bacf-3e02-41b0-84a4-5f05c2df7ce5' \
	'expected_state_uuid=52037413-561a-48f4-92c4-8ad45b748a6f' \
	'expected_manifest_sha256=2c93224d74394876d1617f193f7ec7c3c1cac4575c95da1dfb233557d0819ea6' \
	'state_relative=rog5/state/server-state-v1.ext4' \
	'preflight_state() {' \
	'verify_empty_mountpoint() {' \
	'format=rog5-persistent-service-state-preflight-v1' \
	'verify_storage_read_only' \
	'verify_root_storage_mounts' \
	'verify_write_window' \
	'bb blockdev --setrw "$userdata"' \
	'bb blockdev --setrw "$userdata_disk"' \
	'bb mount -t ext4 -o rw,nodev,nosuid,noexec,noatime' \
	'bb losetup -d "$recorded_loop"' \
	'bb umount "$state_mount" || status=1' \
	'bb losetup -d "$recorded_loop" || status=1' \
	'bb umount "$userdata_mount" || status=1' \
	'relock_storage || status=1'; do
	grep -Fq "$contract" "$helper" || fail "missing helper contract: $contract"
done

for forbidden in fastboot adb sgdisk parted fdisk mkfs blkdiscard wipefs \
	'/dev/sda23' 'rm -rf'; do
	! grep -Fq "$forbidden" "$helper" || fail "forbidden helper surface: $forbidden"
done

[ "$(grep -Fc 'blockdev --setrw' "$helper")" -eq 2 ]
[ "$(grep -Fc 'mount -t ext4 -o rw,nodev,nosuid,noexec,noatime' "$helper")" -eq 2 ]
[ "$(grep -Fc 'trap cleanup_start EXIT HUP INT TERM' "$helper")" -eq 1 ]
! grep -Eq '^[[:space:]]*\[ .* =$' "$helper"
! grep -Eq '^[[:space:]]*\[ .* =$' "$ssh_identity"

for contract in \
	'persist_identity=$persist_root/host-ed25519-v1' \
	'identity_record=/run/rog5-persistent-ssh-identity.record' \
	'verify_key_pair() {' \
	'verify_sshd_listener() {' \
	'ssh-keygen -y -f "$private"' \
	'PPid:[[:space:]]*' \
	'kill -HUP "$sshd_pid"' \
	'format=rog5-persistent-ssh-identity-v1' \
	'format=rog5-persistent-ssh-preflight-v1'; do
	grep -Fq "$contract" "$ssh_identity" ||
		fail "missing persistent SSH contract: $contract"
done
[ "$(grep -Fc 'identity_record=/run/rog5-persistent-ssh-identity.record' \
	"$ssh_identity")" -eq 1 ]
! grep -Fxq 'identity_record=/run/rog5-persistent-ssh-identity' "$ssh_identity"
grep -Fq '[ "$identity_record" != "$0" ]' "$ssh_identity"
for forbidden in fastboot adb sgdisk parted fdisk mkfs blkdiscard wipefs \
	'/dev/sda' 'rm -rf'; do
	! grep -Fq "$forbidden" "$ssh_identity" ||
		fail "forbidden persistent SSH surface: $forbidden"
done

grep -Fq 'cp -p /usr/local/sbin/rog5-persistent-state' "$init"
grep -Fq 'find_exact_userdata /sys/class/block /dev' "$init"
grep -Fq 'Requires=rog5-p2-ready.service' "$init"
grep -Fq 'After=rog5-p2-ready.service' "$init"
grep -Fq 'ExecStart=/run/rog5-persistent-state start' "$init"
grep -Fq 'ExecStop=/run/rog5-persistent-state stop' "$init"
grep -Fq 'sysinit.target.wants/rog5-persistent-state.service' "$init"
grep -Fq 'Requires=rog5-persistent-state.service rog5-early-sshd.service' "$init"
grep -Fq 'ExecStart=/run/rog5-persistent-ssh-identity apply' "$init"
grep -Fq 'sysinit.target.wants/rog5-persistent-ssh-identity.service' "$init"
grep -Fq 'install -D -m 0755 "$state_helper"' "$builder"
grep -Fq 'detach_persistent_state || mark_unclean detach' "$shutdown"
grep -Fq 'clean=0' "$shutdown"
grep -Fq 'losetup -d "$loop_device"' "$shutdown"
grep -Fq 'loop_device=/oldsys/dev/${loop_device#/dev/}' "$shutdown"
persist_lazy=$(grep -n 'lazy_unmount /oldroot/persist' "$shutdown" | cut -d: -f1)
root_lazy=$(grep -n 'lazy_unmount /oldroot$' "$shutdown" | cut -d: -f1)
[ "$persist_lazy" -lt "$root_lazy" ]

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
awk '
	/^verify_key_pair\(\) \{/ { copy=1 }
	/^verify_sshd_listener\(\) \{/ { copy=0 }
	copy { print }
' "$ssh_identity" >"$work/verify-key-pair.sh"
ssh-keygen -q -t ed25519 -N '' -C root@alarm -f "$work/key-a"
ssh-keygen -q -t ed25519 -N '' -C other@alarm -f "$work/key-b"
chmod 0600 "$work/key-a" "$work/key-b"
chmod 0644 "$work/key-a.pub" "$work/key-b.pub"
bb() {
	applet=$1
	shift
	if [ "$applet:$1" = stat:-c ]; then
		# Only fixture ownership is mapped; preserve real size/mode/link count.
		command stat "$@" | sed "s/^$(id -u):$(id -g):/0:0:/"
		return 0
	fi
	command "$applet" "$@"
}
# shellcheck disable=SC1090
. "$work/verify-key-pair.sh"
verify_key_pair "$work/key-a" "$work/key-a.pub"
cp "$work/key-b.pub" "$work/key-a.pub"
! verify_key_pair "$work/key-a" "$work/key-a.pub"

manifest=$work/rog5-state.manifest
printf '%s\n' \
	'format=rog5-persistent-service-state-v1' \
	'image_bytes=4294967296' \
	'image_uuid=52037413-561a-48f4-92c4-8ad45b748a6f' \
	'layout=home,root,var-lib,var-log,etc-ssh,secrets' >"$manifest"
[ "$(stat -c %s "$manifest")" -eq 160 ]
[ "$(sha256sum "$manifest" | cut -d ' ' -f 1)" = \
	2c93224d74394876d1617f193f7ec7c3c1cac4575c95da1dfb233557d0819ea6 ]
printf x >>"$manifest"
[ "$(sha256sum "$manifest" | cut -d ' ' -f 1)" != \
	2c93224d74394876d1617f193f7ec7c3c1cac4575c95da1dfb233557d0819ea6 ]

awk '
	/^stop_state\(\) \{/ { copy=1 }
	/^case \$action in/ { copy=0 }
	copy { print }
' "$helper" >"$work/stop-state.sh"
# shellcheck disable=SC1090
. "$work/stop-state.sh"
runtime_record=$work/state.runtime
state_mount=/persist
userdata_mount=/userdata
mock_log=$work/stop.log
mock_owner=
mock_state_mounted=1
mock_userdata_mounted=1
resolve_exact_devices() {
	userdata=/dev/sdz23
	userdata_disk=/dev/sdz
}
resolve_userdata_owner() { userdata_owner=$mock_owner; }
verify_write_window() { printf 'verify-write-window\n' >>"$mock_log"; }
relock_storage() { printf 'relock\n' >>"$mock_log"; }
verify_empty_mountpoint() { printf 'verify-empty %s\n' "$1" >>"$mock_log"; }
bb() {
	applet=$1
	shift
	case $applet in
		stat) printf '0:0:400:1\n' ;;
		grep|sed|rm) command "$applet" "$@" ;;
		sync) printf 'sync\n' >>"$mock_log" ;;
		umount)
			printf 'umount %s\n' "$1" >>"$mock_log"
			case $1 in "$state_mount") mock_state_mounted=0 ;; "$userdata_mount") mock_userdata_mounted=0 ;; esac
			;;
		mountpoint)
			case $2 in "$state_mount") [ "$mock_state_mounted" = 1 ] ;; "$userdata_mount") [ "$mock_userdata_mounted" = 1 ] ;; *) return 1 ;; esac
			;;
		losetup) printf 'losetup %s %s\n' "$1" "$2" >>"$mock_log" ;;
		rmdir) : ;;
		*) return 1 ;;
	esac
}
run_stop_case() {
	mock_owner=$1
	mock_state_mounted=1
	mock_userdata_mounted=1
	printf '%s\n' \
		'format=rog5-persistent-service-state-runtime-v1' \
		'userdata=/dev/sdz23' \
		'loop=/dev/loop7' \
		"userdata_owner=$mock_owner" >"$runtime_record"
	: >"$mock_log"
	stop_state 2>/dev/null
}
run_stop_case overlay
grep -Fxq 'umount /persist' "$mock_log"
grep -Fxq 'losetup -d /dev/loop7' "$mock_log"
grep -Fxq 'verify-write-window' "$mock_log"
grep -Fxq 'verify-empty /persist' "$mock_log"
! grep -Fq 'umount /userdata' "$mock_log"
! grep -Fxq relock "$mock_log"
run_stop_case state
grep -Fxq 'umount /persist' "$mock_log"
grep -Fxq 'losetup -d /dev/loop7' "$mock_log"
grep -Fxq 'umount /userdata' "$mock_log"
grep -Fxq relock "$mock_log"

# Exercise the real stop/EXIT-cleanup callers together with the real relock
# implementation. Only hardware I/O and the sysfs inventory are fixtures.
python3 -B - "$helper" "$repo" <<'PY'
import os
from pathlib import Path
import subprocess
import sys
import time

source = Path(sys.argv[1]).read_text()


def function(name, indent=""):
    start = source.index(indent + name + "() {\n")
    end = source.index("\n" + indent + "}\n", start)
    return source[start:end + len(indent) + 3]


nodes = " ".join(["/fixture/sdz"] + [f"/fixture/sdz{i}" for i in range(1, 117)])
functions = "\n".join(
    function(name).replace("/sys/class/block/sd*", nodes)
    for name in ("verify_storage_read_only", "relock_storage", "stop_state")
).replace("/dev/kmsg", "/dev/null")
functions += "\n" + function("cleanup_start", "\t")
fixture = r'''
set -eu
expected_physical_count=117
runtime_record=/fixture/state.runtime
runtime_next=/fixture/state.runtime.next
state_mount=/persist
userdata_mount=/userdata
userdata_owner=state
state_mounted=1
userdata_mounted=1
state_mount_created=1
loop_device=/dev/loop7
resolve_exact_devices() { userdata=/dev/sdz23; userdata_disk=/dev/sdz; }
resolve_userdata_owner() { userdata_owner=state; }
[() {
    if command [ "$1" = '!' ]; then
        shift
        if [ "$@"; then return 1; else return 0; fi
    fi
    case "$1" in
        -e|-b|-f) case "$2" in /fixture/*|/dev/sdz*) return 0 ;; *) return 1 ;; esac ;;
        -L) return 1 ;;
        *) command [ "$@" ;;
    esac
}
bb() {
    case "$1" in
        basename) printf '%s\n' "${2##*/}" ;;
        cat) printf '1\n' ;;
        stat) printf '0:0:400:1\n' ;;
        grep) printf '1\n' ;;
        sed) case "$3" in
            's/^userdata=//p') printf '/dev/sdz23\n' ;;
            's/^loop=//p') printf '/dev/loop7\n' ;;
            's/^userdata_owner=//p') printf 'state\n' ;;
            *) return 98 ;;
        esac ;;
        blockdev)
            printf 'blockdev %s %s\n' "$2" "$3" >&2
            case "$2" in
                --setro) [ "$injected_failure:$3" != relock:/dev/sdz23 ] ;;
                --getro) if [ "$injected_failure:$3" = readonly:/dev/sdz23 ]; then printf '0\n'; else printf '1\n'; fi ;;
                *) return 98 ;;
            esac ;;
        umount) printf 'umount %s\n' "$2" >&2; [ "$injected_failure:$2" != umount:/persist ] ;;
        losetup) printf 'losetup %s %s\n' "$2" "$3" >&2; [ "$injected_failure" != detach ] ;;
        mountpoint) return 0 ;;
        sync|rmdir) return 0 ;;
        rm) printf 'rm %s %s\n' "$2" "$3" >&2 ;;
        *) printf 'UNEXPECTED_IO %s\n' "$1" >&2; return 98 ;;
    esac
}
'''
cases = [
    ("stop", "none", 0, 0),
    ("stop", "umount", 0, 1),
    ("stop", "detach", 0, 1),
    ("stop", "relock", 0, 1),
    ("stop", "readonly", 0, 1),
    ("cleanup", "none", 0, 0),
    ("cleanup", "none", 1, 1),
    ("cleanup", "none", 7, 7),
    ("cleanup", "umount", 0, 1),
    ("cleanup", "detach", 0, 1),
    ("cleanup", "relock", 0, 1),
]
lifecycle_functions = "\n".join(
    function(name).replace("/sys/class/block/sd*", nodes)
    for name in ("verify_storage_read_only", "verify_write_window",
                 "verify_mount", "resolve_userdata_owner", "relock_storage", "stop_state")
).replace("/dev/kmsg", "/dev/null")
lifecycle_fixture = fixture.replace("bb() {", "base_bb() {").replace(
    "/fixture/*|/dev/sdz*)", "/fixture/*|/dev/sdz*|/dev/loop7)") + r'''
overlay_record=/absent-overlay
locked=0
fixture_ro() {
    if [ "$locked" = 1 ] || [ "$window" = ro ]; then printf '1\n'; return; fi
    case "$window:$1" in
        *:/dev/sdz|rw:/dev/sdz23|extra:/dev/sdz23|extra:/dev/sdz24) printf '0\n' ;;
        *) printf '1\n' ;;
    esac
}
bb() {
    case "$1:${2-}" in
        blockdev:--getro) fixture_ro "$3" ;;
        blockdev:--setro) base_bb "$@"; locked=1 ;;
        cat:*)
            fixture_node=${2%/ro}
            fixture_ro "/dev/${fixture_node##*/}"
            ;;
        sed:*) case "$3" in
            's/^userdata=//p') printf '%s\n' "$recorded_device" ;;
            's/^disk=//p') printf '/dev/sdz\n' ;;
            's/^image=//p') printf 'rog5/root/root-overlay-v1.ext4\n' ;;
            's/^mount=//p') printf '/mnt/state\n' ;;
            's/^userdata_mount=//p') printf '/mnt/userdata\n' ;;
            *) base_bb "$@" ;;
        esac ;;
        awk:*) printf 'verify-mount\n' >&2 ;;
        *) base_bb "$@" ;;
    esac
}
'''
# Real owner resolution and both real storage guards must agree with lifecycle.
lifecycle_cases = [
    ("default-ro", "ro", "resolve_userdata_owner", 0, False),
    ("default-rw", "rw", "resolve_userdata_owner", 1, False),
    ("preflight-ro", "ro", "resolve_userdata_owner preflight", 0, False),
    ("preflight-rw", "rw", "resolve_userdata_owner preflight", 1, False),
    ("stop-rw", "rw", "stop_state", 0, True),
    ("stop-ro", "ro", "stop_state", 1, False),
    ("stop-extra-writer", "extra", "stop_state", 1, False),
    ("stop-missing-writer", "one", "stop_state", 1, False),
    ("stop-count", "rw", "expected_physical_count=118; stop_state", 1, False),
    ("stop-wrong-record", "rw", "recorded_device=/dev/sdz22; stop_state", 1, False),
    ("unknown-mode", "ro", "resolve_userdata_owner invalid", 1, False),
    ("extra-mode", "ro", "resolve_userdata_owner startup extra", 1, False),
    ("empty-mode", "ro", "resolve_userdata_owner ''", 1, False),
    ("overlay-start", "rw", "overlay_record=/fixture/overlay; resolve_userdata_owner", 0, False),
    ("overlay-stop", "rw", "overlay_record=/fixture/overlay; resolve_userdata_owner stop", 0, False),
]
runners = [("host-sh", ["sh"], ())]
fds = []
archive = os.environ.get("ROG5_STATE_TEST_ARM64_ARCHIVE")
try:
    if archive:
        # Anonymous RAM files avoid mounts, extraction directories and device I/O.
        for member in ("lib/ld-musl-aarch64.so.1", "bin/busybox"):
            data = subprocess.run(
                ["bsdtar", "-xOf", archive, "./" + member],
                check=True, capture_output=True, timeout=10,
            ).stdout
            fd = os.memfd_create("rog5-state-relock-test", 0)
            fds.append(fd)
            with os.fdopen(os.dup(fd), "wb") as stream:
                stream.write(data)
            os.lseek(fd, 0, os.SEEK_SET)
        qemu = str(Path(sys.argv[2]) / "artifacts/host-tools/qemu-aarch64-static")
        runners.append(("sealed-arm-ash", [
            qemu, f"/proc/self/fd/{fds[0]}", "--argv0", "busybox",
            f"/proc/self/fd/{fds[1]}", "ash",
        ], tuple(fds)))
    failures = []
    for label, runner, inherited in runners:
        started = time.monotonic()
        for action, failure, initial, expected in cases:
            call = "if stop_state; then exit 0; else exit $?; fi"
            if action == "cleanup":
                call = "trap cleanup_start EXIT HUP INT TERM\nexit " + str(initial)
            result = subprocess.run(
                runner + ["-c", fixture + "\n" + functions +
                          f"\ninjected_failure={failure}\n" + call],
                capture_output=True, text=True, timeout=10, pass_fds=inherited,
            )
            checks = (
                result.returncode == expected,
                "UNEXPECTED_IO" not in result.stderr,
                result.stderr.count("blockdev --setro ") == 117,
                failure == "readonly" or result.stderr.count("blockdev --getro ") == 117,
                action != "stop" or expected == 0 or
                "rm -f /fixture/state.runtime\n" not in result.stderr,
            )
            if not all(checks):
                failures.append(f"{label} {action}/{failure}/exit{initial}: "
                                f"expected {expected}, got {result.returncode}; checks={checks}")
        print(f"{label}: {len(cases)} relock caller cases in {time.monotonic() - started:.3f}s", flush=True)
        started = time.monotonic()
        for name, window, call, expected, cleanup in lifecycle_cases:
            result = subprocess.run(
                runner + ["-c", lifecycle_fixture + "\n" + lifecycle_functions +
                          f"\ninjected_failure=none\nwindow={window}\nrecorded_device=/dev/sdz23\n"
                          "resolve_exact_devices\n" +
                          "if { " + call + "; }; then exit 0; else exit $?; fi"],
                capture_output=True, text=True, timeout=10, pass_fds=inherited,
            )
            mutations = ("umount ", "losetup ", "blockdev --setro ", "rm -f ")
            cleanup_ok = (
                all(token in result.stderr for token in
                    ("umount /persist\n", "losetup -d /dev/loop7\n",
                     "umount /userdata\n", "rm -f /fixture/state.runtime\n")) and
                result.stderr.count("blockdev --setro ") == 117
            ) if cleanup else not any(token in result.stderr for token in mutations)
            if result.returncode != expected or not cleanup_ok or "UNEXPECTED_IO" in result.stderr:
                failures.append(f"{label} lifecycle/{name}: expected {expected}, "
                                f"got {result.returncode}; cleanup_ok={cleanup_ok}")
        print(f"{label}: {len(lifecycle_cases)} lifecycle cases in {time.monotonic() - started:.3f}s", flush=True)
    if failures:
        raise SystemExit("\n".join(failures))
finally:
    for fd in fds:
        os.close(fd)
PY

echo 'PASS persistent state mounts only exact p23/image after P2 and relocks on stop'
