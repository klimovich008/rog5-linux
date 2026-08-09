#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

action=${1:-preflight}
case $action in
	preflight) ;;
	retention-preflight) ;;
	reboot)
		[[ ${ALLOW_FALLBACK_BOOTLOADER_REBOOT:-} == 1 ]] ||
			fail 'set ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 for one guarded reboot'
		;;
	*)
		fail 'usage: reboot-fallback-to-fastboot.sh [preflight|retention-preflight|reboot]'
		;;
esac

ssh_key=${SSH_KEY:-}
known_hosts=${KNOWN_HOSTS:-}
[[ -n $ssh_key && -n $known_hosts ]] ||
	fail 'set SSH_KEY and KNOWN_HOSTS to the dedicated phone credentials'
sys_bus_usb=/sys/bus/usb/devices
sys_devices=/sys/devices
fastboot_timeout=45
for command in realpath ssh stat; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
if [[ $action == reboot ]]; then
	for command in date fastboot sleep; do
		command -v "$command" >/dev/null ||
			fail "missing host command: $command"
	done
	fastboot_serial=${FASTBOOT_SERIAL:-}
	[[ $fastboot_serial =~ ^[A-Za-z0-9._:-]{1,128}$ ]] ||
		fail 'set FASTBOOT_SERIAL to the exact expected device'
fi

ssh_key=$(realpath -e "$ssh_key")
known_hosts=$(realpath -e "$known_hosts")
case $ssh_key:$known_hosts in
	*%*|*[[:space:]]*)
		fail 'credential paths must not contain whitespace or OpenSSH percent tokens'
		;;
esac
[[ -f $ssh_key && ! -L $ssh_key && -r $ssh_key ]] ||
	fail 'SSH_KEY is not a readable regular file'
[[ -f $known_hosts && ! -L $known_hosts && -r $known_hosts ]] ||
	fail 'KNOWN_HOSTS is not a readable regular file'
[[ $(stat -c %u "$ssh_key") == "$EUID" &&
	$(stat -c %u "$known_hosts") == "$EUID" ]] ||
	fail 'credential files must be owned by the caller'
key_mode=$(stat -c %a "$ssh_key")
known_hosts_mode=$(stat -c %a "$known_hosts")
[[ $key_mode =~ ^[0-7]{3,4}$ && $known_hosts_mode =~ ^[0-7]{3,4}$ ]] ||
	fail 'credential modes are invalid'
(( (8#$key_mode & 077) == 0 )) ||
	fail 'SSH_KEY must not be accessible by group or other users'
(( (8#$known_hosts_mode & 022) == 0 )) ||
	fail 'KNOWN_HOSTS must not be writable by group or other users'

target=root@169.254.77.2
ssh_options=(
	-F /dev/null
	-i "$ssh_key"
	-o IdentitiesOnly=yes
	-o BatchMode=yes
	-o StrictHostKeyChecking=yes
	-o UserKnownHostsFile="$known_hosts"
	-o GlobalKnownHostsFile=/dev/null
	-o HostKeyAlias=rog5-fallback
	-o ConnectTimeout=8
	-o ConnectionAttempts=1
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=2
	-o LogLevel=ERROR
)

read_usb_field() {
	local path=$1 value
	[[ -f $path && ! -L $path ]] || return 1
	IFS= read -r value <"$path" || return 1
	[[ $value =~ ^[A-Za-z0-9._:-]{1,128}$ ]] || return 1
	printf '%s\n' "$value"
}

usb_identity_at() {
	local location=$1 raw vendor product
	raw=$sys_devices/$location
	[[ -d $raw ]] || return 1
	vendor=$(read_usb_field "$raw/idVendor") || return 1
	product=$(read_usb_field "$raw/idProduct") || return 1
	vendor=${vendor,,}
	product=${product,,}
	[[ $vendor =~ ^[0-9a-f]{4}$ && $product =~ ^[0-9a-f]{4}$ ]] ||
		return 1
	printf '%s:%s\n' "$vendor" "$product"
}

find_fallback_usb_location() {
	local candidate resolved vendor product serial location=
	local count=0
	for candidate in "$sys_bus_usb"/*; do
		[[ -e $candidate ]] || continue
		vendor=$(read_usb_field "$candidate/idVendor" 2>/dev/null || true)
		product=$(read_usb_field "$candidate/idProduct" 2>/dev/null || true)
		serial=$(read_usb_field "$candidate/serial" 2>/dev/null || true)
		[[ ${vendor,,}:${product,,}:$serial == 1d6b:0104:ROG5LINUX ]] ||
			continue
		resolved=$(realpath -e "$candidate") || continue
		case $resolved in
			"$sys_devices"/*) ;;
			*) continue ;;
		esac
		location=${resolved#"$sys_devices"/}
		[[ -n $location && $location != "$resolved" ]] || continue
		count=$((count + 1))
	done
	[[ $count == 1 ]] ||
		fail "expected one exact fallback USB device, found $count"
	printf '%s\n' "$location"
}

require_fastboot_usb_at() {
	local location=$1 expected_serial=$2 raw serial
	[[ $(usb_identity_at "$location" 2>/dev/null || true) == 0b05:4daf ]] ||
		fail 'fastboot escaped the exact fallback USB device'
	raw=$sys_devices/$location
	serial=$(read_usb_field "$raw/serial" 2>/dev/null || true)
	[[ $serial == "$expected_serial" ]] ||
		fail 'fastboot serial changed at the anchored USB device'
}

if [[ $action == reboot ]]; then
	fallback_usb_location=$(find_fallback_usb_location)
	initial_count=$(fastboot devices 2>/dev/null |
		awk '$2 == "fastboot" { count++ } END { print count + 0 }')
	[[ $initial_count == 0 ]] ||
		fail 'refusing reboot request while a fastboot device already exists'
fi

set +e
output=$(ssh "${ssh_options[@]}" "$target" sh -se -- "$action" <<'REMOTE'
action=$1

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$action" = preflight ] || [ "$action" = retention-preflight ] ||
	[ "$action" = reboot ] ||
	fail 'unexpected remote action'
[ "$(uname -r)" = 5.4.134-qgki-perf-00001-g6c308144c23e ] ||
	fail 'unexpected fallback kernel'
[ "$(readlink /proc/1/exe)" = /bin/busybox ] ||
	fail 'unexpected fallback init'
tr '\000' '\n' </proc/device-tree/compatible |
	grep -Fxq qcom,lahaina-mtp ||
	fail 'unexpected fallback compatible'
awk '$2 == "/" && $3 == "ext4" { found=1 }
	END { exit !found }' /proc/mounts ||
	fail 'fallback root is not ext4'
[ ! -e /run/rog5-gpucc-diagnostic ] ||
	fail 'a diagnostic stage is still present'
awk '$1 ~ /^rog5_/ { found=1 } END { exit found }' /proc/modules ||
	fail 'a project diagnostic module is loaded'

pstore_records=0
for directory in /sys/fs/pstore /mnt/pstore; do
	[ -d "$directory" ] || continue
	for file in "$directory"/*; do
		[ -f "$file" ] || continue
		pstore_records=$((pstore_records + 1))
	done
done
[ "$pstore_records" -eq 0 ] || fail 'fallback pstore is not empty'
fatal_pattern='(^|[^[:alnum:]_])(Kernel panic|Oops:|BUG:|watchdog[[:space:]_-]+bite|Kernel fault|Unable to handle kernel|Synchronous External Abort)([^[:alnum:]_]|$)'
command -v dmesg >/dev/null || fail 'fallback dmesg is unavailable'
dmesg >/dev/null 2>&1 || fail 'fallback kernel log is unreadable'
fatal_lines=$(dmesg 2>/dev/null |
	grep -Eic "$fatal_pattern" || true)
[ "$fatal_lines" -eq 0 ] || fail 'fallback kernel log has a fatal signature'

thermal_zones=0
thermal_max=0
for file in /sys/class/thermal/thermal_zone*/temp; do
	value=$(sed -n '1p' "$file" 2>/dev/null || true)
	case $value in ''|*[!0-9-]*) continue ;; esac
	[ "$value" -ge 0 ] 2>/dev/null || continue
	thermal_zones=$((thermal_zones + 1))
	[ "$value" -le "$thermal_max" ] || thermal_max=$value
done
[ "$thermal_zones" -gt 0 ] || fail 'fallback thermal telemetry is absent'
[ "$thermal_max" -le 60000 ] || fail 'fallback temperature is unsafe'
command -v python3 >/dev/null || fail 'fallback Python is unavailable'

if [ "$action" = retention-preflight ]; then
	python3 -B - / <<'PY'
# BEGIN FALLBACK_RAMOOPS_TRANSITION_VERIFIER
from __future__ import annotations

from contextlib import contextmanager, ExitStack
import errno
import os
from pathlib import Path
import stat
import struct
import sys
from typing import Iterator


RAMOOPS_START = 0x9B800000
RAMOOPS_SIZE = 0x400000
RAMOOPS_END = RAMOOPS_START + RAMOOPS_SIZE
ADDRESS_LIMIT = 1 << 64
DIRECTORY_FLAGS = (
    os.O_RDONLY
    | os.O_CLOEXEC
    | os.O_DIRECTORY
    | getattr(os, "O_NOFOLLOW", 0)
)
REGULAR_FLAGS = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
RAMOOPS_TOKENS = (
    "ramoops.mem_address=0x9b800000",
    "ramoops.mem_size=0x400000",
    "ramoops.record_size=0x100000",
    "ramoops.console_size=0x300000",
    "ramoops.pmsg_size=0",
    "ramoops.ftrace_size=0",
    "ramoops.dump_oops=1",
)


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def same_object(first: os.stat_result, second: os.stat_result) -> bool:
    return first.st_dev == second.st_dev and first.st_ino == second.st_ino


@contextmanager
def opened_root(root: Path) -> Iterator[int]:
    try:
        descriptor = os.open(root, DIRECTORY_FLAGS)
    except OSError:
        fail("fallback runtime root is unsafe or absent")
    try:
        opened = os.fstat(descriptor)
        pathname_before = root.stat(follow_symlinks=False)
        if not stat.S_ISDIR(opened.st_mode) or not same_object(opened, pathname_before):
            fail("fallback runtime root is unsafe or absent")
        yield descriptor
        pathname_after = root.stat(follow_symlinks=False)
        if not stat.S_ISDIR(pathname_after.st_mode) or not same_object(
            opened, pathname_after
        ):
            fail("fallback runtime root changed during verification")
    except OSError:
        fail("fallback runtime root changed during verification")
    finally:
        os.close(descriptor)


@contextmanager
def opened_directory(
    parent: int,
    name: str,
    label: str,
    *,
    optional: bool = False,
) -> Iterator[int | None]:
    try:
        descriptor = os.open(name, DIRECTORY_FLAGS, dir_fd=parent)
    except OSError as error:
        if optional and error.errno == errno.ENOENT:
            yield None
            return
        fail(f"{label} is unsafe or absent")
    try:
        opened = os.fstat(descriptor)
        pathname_before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISDIR(opened.st_mode) or not same_object(
            opened, pathname_before
        ):
            fail(f"{label} is unsafe or absent")
        yield descriptor
        pathname_after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISDIR(pathname_after.st_mode) or not same_object(
            opened, pathname_after
        ):
            fail(f"{label} changed during verification")
    except OSError:
        fail(f"{label} changed during verification")
    finally:
        os.close(descriptor)


@contextmanager
def opened_path(
    root: Path,
    components: tuple[str, ...],
    label: str,
) -> Iterator[int]:
    with ExitStack() as stack:
        current = stack.enter_context(opened_root(root))
        for component in components:
            opened = stack.enter_context(opened_directory(current, component, label))
            if opened is None:
                fail(f"{label} is absent")
            current = opened
        yield current


def read_regular_at(
    directory: int,
    name: str,
    label: str,
    *,
    optional: bool = False,
) -> bytes | None:
    try:
        descriptor = os.open(name, REGULAR_FLAGS, dir_fd=directory)
    except OSError as error:
        if optional and error.errno == errno.ENOENT:
            return None
        fail(f"{label} is unsafe or absent")
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            fail(f"{label} is not regular")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > 1024 * 1024:
                fail(f"{label} is oversized")
        after = os.fstat(descriptor)
        try:
            pathname_after = os.stat(
                name,
                dir_fd=directory,
                follow_symlinks=False,
            )
        except OSError:
            fail(f"{label} changed during verification")
        if (
            not same_object(before, after)
            or before.st_size != after.st_size
            or not same_object(before, pathname_after)
            or not stat.S_ISREG(pathname_after.st_mode)
        ):
            fail(f"{label} changed during verification")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def directory_names(directory: int, label: str) -> tuple[str, ...]:
    try:
        return tuple(sorted(os.listdir(directory)))
    except OSError:
        fail(f"{label} changed during verification")


def revalidate_names(
    directory: int,
    expected: tuple[str, ...],
    label: str,
) -> None:
    if directory_names(directory, label) != expected:
        fail(f"{label} changed during verification")


def exact_command_line(root: Path) -> None:
    with opened_path(root, ("proc",), "fallback procfs") as proc:
        raw = read_regular_at(proc, "cmdline", "fallback command line")
    if raw is None:
        fail("fallback ramoops command line is not exact")
    try:
        command_line = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        fail("fallback ramoops command line is not exact")
    tokens = command_line.split()
    if (
        any(tokens.count(token) != 1 for token in RAMOOPS_TOKENS)
        or any(
            token.startswith("ramoops.") and token not in RAMOOPS_TOKENS
            for token in tokens
        )
    ):
        fail("fallback ramoops command line is not exact")


def ramoops_compatible(payload: bytes | None) -> bool:
    if payload is None:
        return False
    values = payload.rstrip(b"\0").split(b"\0")
    return any(value == b"ramoops" or value.endswith(b",ramoops") for value in values)


def inspect_reserved_child(
    reserved: int,
    name: str,
) -> tuple[bool, bytes | None]:
    with opened_directory(
        reserved,
        name,
        "fallback reserved-memory child",
    ) as child:
        if child is None:
            fail("fallback reserved-memory child is absent")
        names = directory_names(child, "fallback reserved-memory child")
        compatible = read_regular_at(
            child,
            "compatible",
            "fallback reserved-memory compatible",
            optional=True,
        )
        if ramoops_compatible(compatible):
            fail("fallback ramoops consumer is present")
        reg = read_regular_at(
            child,
            "reg",
            "fallback reserved-memory reg",
            optional=True,
        )
        revalidate_names(child, names, "fallback reserved-memory child")
        return name == "memory@9b800000", reg


def exact_reserved_memory(root: Path) -> None:
    path = ("sys", "firmware", "devicetree", "base", "reserved-memory")
    with opened_path(root, path, "fallback reserved-memory contract") as reserved:
        names = directory_names(reserved, "fallback reserved-memory contract")
        if read_regular_at(
            reserved,
            "#address-cells",
            "fallback reserved-memory address cells",
        ) != struct.pack(">I", 2):
            fail("fallback ramoops reserved-memory contract has wrong address cells")
        if read_regular_at(
            reserved,
            "#size-cells",
            "fallback reserved-memory size cells",
        ) != struct.pack(">I", 2):
            fail("fallback ramoops reserved-memory contract has wrong size cells")
        if read_regular_at(
            reserved,
            "ranges",
            "fallback reserved-memory ranges",
        ) != b"":
            fail("fallback ramoops reserved-memory contract has nonempty ranges")

        target_seen = False
        for name in names:
            metadata = os.stat(name, dir_fd=reserved, follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode):
                fail("fallback reserved-memory child is malformed")
            if not stat.S_ISDIR(metadata.st_mode):
                continue
            is_target, payload = inspect_reserved_child(reserved, name)
            if is_target:
                if target_seen or payload != struct.pack(
                    ">QQ", RAMOOPS_START, RAMOOPS_SIZE
                ):
                    fail("fallback ramoops reserved-memory contract has the wrong tuple")
                target_seen = True
                continue
            if payload is None:
                continue
            if not payload or len(payload) % 16:
                fail("fallback reserved-memory child is malformed")
            for offset in range(0, len(payload), 16):
                start, size = struct.unpack(">QQ", payload[offset : offset + 16])
                end = start + size
                if size == 0 or end >= ADDRESS_LIMIT:
                    fail("fallback reserved-memory child is malformed")
                if start < RAMOOPS_END and end > RAMOOPS_START:
                    fail("fallback reserved-memory node overlaps ramoops")
        if not target_seen:
            fail("fallback ramoops reserved-memory contract is absent")
        revalidate_names(reserved, names, "fallback reserved-memory contract")


def name_is_ramoops(name: str) -> bool:
    return "ramoops" in name.lower()


def no_ramoops_consumer(root: Path) -> None:
    for components in (
        ("sys", "bus", "platform", "devices"),
        ("sys", "devices", "platform"),
    ):
        with opened_path(root, components, "fallback platform devices") as devices:
            names = directory_names(devices, "fallback platform devices")
            for name in names:
                if name_is_ramoops(name):
                    fail("fallback ramoops consumer is present")
            revalidate_names(devices, names, "fallback platform devices")

    drivers_path = ("sys", "bus", "platform", "drivers")
    with opened_path(root, drivers_path, "fallback platform drivers") as drivers:
        driver_names = directory_names(drivers, "fallback platform drivers")
        with opened_directory(
            drivers,
            "ramoops",
            "fallback ramoops driver",
            optional=True,
        ) as driver:
            if driver is not None:
                names = directory_names(driver, "fallback ramoops driver")
                for name in names:
                    if name not in {"bind", "unbind", "uevent", "module"}:
                        fail("fallback ramoops consumer is present")
                revalidate_names(driver, names, "fallback ramoops driver")
        revalidate_names(drivers, driver_names, "fallback platform drivers")


def empty_pstore(root: Path) -> None:
    with opened_path(root, ("sys", "fs", "pstore"), "fallback pstore") as pstore:
        names = directory_names(pstore, "fallback pstore")
        if names:
            fail("fallback pstore is not empty")
        revalidate_names(pstore, names, "fallback pstore")
    with opened_path(root, ("mnt",), "fallback mount root") as mount_root:
        mount_names = directory_names(mount_root, "fallback mount root")
        with opened_directory(
            mount_root,
            "pstore",
            "fallback mounted pstore",
            optional=True,
        ) as mounted_pstore:
            if mounted_pstore is not None:
                names = directory_names(mounted_pstore, "fallback mounted pstore")
                if names:
                    fail("fallback pstore is not empty")
                revalidate_names(
                    mounted_pstore,
                    names,
                    "fallback mounted pstore",
                )
        revalidate_names(mount_root, mount_names, "fallback mount root")


def main(arguments: list[str]) -> int:
    if len(arguments) != 1:
        fail("fallback ramoops verifier requires one absolute root")
    root = Path(arguments[0])
    if not root.is_absolute():
        fail("fallback ramoops verifier root is not absolute")
    exact_command_line(root)
    exact_reserved_memory(root)
    no_ramoops_consumer(root)
    empty_pstore(root)
    print(
        "PASS fallback ramoops transition reservation is exact, "
        "unconsumed, and empty"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
# END FALLBACK_RAMOOPS_TRANSITION_VERIFIER
PY
	echo 'PASS exact fallback ramoops retention preflight'
	exit 0
fi

if [ "$action" = preflight ]; then
	echo 'PASS exact persistent fallback ready for guarded bootloader reboot'
	exit 0
fi

[ "$action" = reboot ] || fail 'non-reboot action reached reboot boundary'
echo 'PASS authenticated fallback reboot session'
python3 - <<'PY'
import ctypes
import os
import platform

LINUX_REBOOT_MAGIC1 = 0xFEE1DEAD
LINUX_REBOOT_MAGIC2 = 672274793
LINUX_REBOOT_CMD_RESTART2 = 0xA1B2C3D4
SYS_REBOOT = 142

if os.geteuid() != 0:
    raise SystemExit("FAIL reboot syscall requires root")
if platform.machine() != "aarch64":
    raise SystemExit("FAIL reboot syscall is pinned to aarch64")

libc = ctypes.CDLL(None, use_errno=True)
syscall = libc.syscall
syscall.restype = ctypes.c_long
os.sync()
print("PASS guarded fallback RESTART2 bootloader request sent", flush=True)
result = syscall(
    ctypes.c_long(SYS_REBOOT),
    ctypes.c_ulong(LINUX_REBOOT_MAGIC1),
    ctypes.c_ulong(LINUX_REBOOT_MAGIC2),
    ctypes.c_ulong(LINUX_REBOOT_CMD_RESTART2),
    ctypes.c_char_p(b"bootloader"),
)
error = ctypes.get_errno()
raise SystemExit(f"FAIL reboot syscall returned result={result} errno={error}")
PY
REMOTE
)
ssh_status=$?
set -e
printf '%s\n' "$output"

if [[ $action == preflight ]]; then
	[[ $ssh_status == 0 ]] || fail 'fallback preflight SSH failed'
	grep -Fxq \
		'PASS exact persistent fallback ready for guarded bootloader reboot' \
		<<<"$output" ||
		fail 'fallback preflight marker is absent'
	exit 0
fi

if [[ $action == retention-preflight ]]; then
	[[ $ssh_status == 0 ]] || fail 'fallback ramoops retention SSH failed'
	grep -Fxq \
		'PASS fallback ramoops transition reservation is exact, unconsumed, and empty' \
		<<<"$output" ||
		fail 'fallback ramoops transition marker is absent'
	grep -Fxq 'PASS exact fallback ramoops retention preflight' \
		<<<"$output" ||
		fail 'fallback ramoops retention preflight marker is absent'
	exit 0
fi

restart_marker=0
authenticated_marker=0
if grep -Fxq 'PASS authenticated fallback reboot session' \
	<<<"$output"; then
	authenticated_marker=1
fi
[[ $authenticated_marker == 1 ]] ||
	fail 'authenticated fallback reboot-session marker is absent'
if grep -Fxq 'PASS guarded fallback RESTART2 bootloader request sent' \
	<<<"$output"; then
	restart_marker=1
	[[ $ssh_status == 0 || $ssh_status == 255 ]] ||
		fail "fallback restart2 SSH failed with status $ssh_status"
fi
if [[ $restart_marker == 0 && $ssh_status != 255 ]]; then
	fail "fallback restart2 acknowledgement is absent and SSH exited with status $ssh_status"
fi

fallback_identity=1d6b:0104
fastboot_identity=0b05:4daf
saw_disconnect=0
saw_reenumeration=0
saw_fastboot_usb=0
saw_fallback_return=0
deadline=$(( $(date +%s) + fastboot_timeout ))
while (( $(date +%s) < deadline )); do
	usb_identity=$(usb_identity_at "$fallback_usb_location" 2>/dev/null || true)
	if [[ -z $usb_identity ]]; then
		saw_disconnect=1
	elif [[ $usb_identity != "$fallback_identity" ]]; then
		saw_disconnect=1
		saw_reenumeration=1
		if [[ $usb_identity == "$fastboot_identity" ]]; then
			saw_fastboot_usb=1
			observed_usb_serial=$(read_usb_field \
				"$sys_devices/$fallback_usb_location/serial" \
				2>/dev/null || true)
			if [[ -n $observed_usb_serial &&
				$observed_usb_serial != "$fastboot_serial" ]]; then
				fail 'fastboot serial changed at the anchored USB device'
			fi
		fi
	elif [[ $saw_disconnect == 1 ]]; then
		observed_usb_serial=$(read_usb_field \
			"$sys_devices/$fallback_usb_location/serial" \
			2>/dev/null || true)
		[[ $observed_usb_serial == ROG5LINUX ]] ||
			fail 'fallback serial changed at the anchored USB device'
		saw_reenumeration=1
		saw_fallback_return=1
	fi
	devices=$(fastboot devices 2>/dev/null || true)
	device_count=$(awk 'NF { count++ } END { print count + 0 }' \
		<<<"$devices")
	fastboot_count=$(awk '$2 == "fastboot" { count++ }
		END { print count + 0 }' <<<"$devices")
	if [[ $device_count == 1 && $fastboot_count == 1 ]]; then
		read -r observed_serial observed_state <<<"$devices"
		[[ $observed_serial == "$fastboot_serial" &&
			$observed_state == fastboot ]] ||
			fail 'fastboot device identity does not match the expected serial'
		require_fastboot_usb_at "$fallback_usb_location" "$fastboot_serial"
		set +e
		product_output=$(fastboot -s "$fastboot_serial" \
			getvar product 2>&1)
		product_status=$?
		set -e
		[[ $product_status == 0 ]] ||
			fail 'cannot verify the expected fastboot product'
		product_count=$(grep -Ec \
			'^[[:space:]]*product:[[:space:]]*lahaina[[:space:]]*$' \
			<<<"$product_output" || true)
		product_lines=$(grep -Ec \
			'^[[:space:]]*product:' <<<"$product_output" || true)
		[[ $product_count == 1 && $product_lines == 1 ]] ||
			fail 'fastboot product is not exactly lahaina'
		if [[ $restart_marker == 1 ]]; then
			echo 'PASS exact lahaina fastboot device reached after acknowledged restart2'
		else
			echo 'PASS exact lahaina fastboot device proves restart2 despite SSH disconnect before acknowledgement'
		fi
		exit 0
		fi
	if (( device_count == 1 )); then
		fail 'one fastboot device is present in an unexpected state'
	fi
	(( device_count == 0 )) ||
		fail "expected at most one fastboot device, found $device_count"
	sleep 1
done

[[ $restart_marker == 1 ]] ||
	fail 'fallback restart2 marker was absent and exact fastboot did not appear'
if [[ $saw_disconnect == 0 ]]; then
	fail 'fallback USB never disconnected after the acknowledged bootloader reboot'
fi
if [[ $saw_reenumeration == 0 ]]; then
	fail 'fallback USB disconnected but no anchored-port USB re-enumeration was observed'
fi
if [[ $saw_fallback_return == 1 ]]; then
	fail 'fallback Linux USB returned at the anchored port instead of fastboot'
fi
if [[ $saw_fastboot_usb == 1 ]]; then
	fail 'exact fastboot USB re-enumerated but fastboot userspace discovery did not succeed'
fi
fail 'a non-fastboot USB mode was observed at the anchored port'
