#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/network-root-init
shutdown=$repo/initramfs/network-root-shutdown
initramfs_builder=$repo/scripts/device/build-network-root-initramfs.sh
verifier_builder=$repo/scripts/device/build-persistent-root-verifier-static.sh

for script in "$init" "$shutdown" "$initramfs_builder" \
	"$verifier_builder"; do
	[ -x "$script" ] || {
		echo "FAIL missing executable network-root source: $script" >&2
		exit 1
	}
	sh -n "$script"
done
for text in \
	'usage: build-network-root-initramfs.sh BASE OUTPUT' \
	'build-persistent-root-verifier-static.sh' \
	'NETWORK_ROOT_VERIFIER' \
	'NETWORK_ROOT_DIAGNOSTIC_REPORTER' \
	'reviewed_verifier_hash=bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58' \
	'reviewed_reporter_size=67288' \
	'reviewed_reporter_hash=f0a9a52b42385a5c963230d5c48f152bed2e24e382c22de09acdba529082a1fd' \
	'install -D -m 0755 "$verifier" "$stage/sbin/persistent-root-verify"' \
	'"$stage/sbin/rog5-early-target-diag"' \
	'verify-network-root-initramfs.sh' \
	'accepted_base=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac'; do
	grep -Fq "$text" "$initramfs_builder" || {
		echo "FAIL network-root builder contract missing: $text" >&2
		exit 1
	}
done
if grep -Fq 'STATIC_VERIFIER' "$initramfs_builder"; then
	echo 'FAIL network-root builder still accepts an external verifier' >&2
	exit 1
fi
grep -Fq 'cmp "$root_verifier" "$trusted/persistent-root-verify"' \
	"$repo/scripts/device/verify-network-root-initramfs.sh"
for text in \
	'normal network-root initramfs carries diagnostic reporter' \
	'diagnostic initramfs lacks early-target reporter' \
	'cmp "$reporter" "$reviewed_reporter"'; do
	grep -Fq "$text" \
		"$repo/scripts/device/verify-network-root-initramfs.sh"
done
for text in \
	'aarch64-linux-musl-gcc' \
	'-static -std=c11' \
	'Machine:.*AArch64' \
	'Requesting program interpreter' \
	'Shared library:'; do
	grep -Fq -- "$text" "$verifier_builder" || {
		echo "FAIL static verifier builder contract missing: $text" >&2
		exit 1
	}
done

for text in \
	'rog5.netroot=1' \
	'169.254.77.2/30' \
	'169.254.77.1:/' \
	'rog5-network-root-watchdog.pid' \
	'rog5-network-root-watchdog.lease' \
	'format=rog5-network-root-watchdog-v1' \
	'timer_start_time_ticks=%s' \
	'deadline_boottime_seconds=%s' \
	'watchdog_reset=/proc/sysrq-trigger' \
	'exec 9>"$watchdog_reset"' \
	'echo b >&9' \
	'physical block device appeared with UFS-disabled DTB' \
	'rog5.a660_command_manifest_sha256=' \
	'rog5.root_generation=' \
	'rog5.root_tree_sha256=' \
	'rog5.root_seal_sha256=' \
	'rog5.root_tree_entries=' \
	'rog5.root_subtree=' \
	'/sbin/persistent-root-verify' \
	'verify_network_root_identity || return 1' \
	'format=rog5-network-root-identity-v1' \
	'publish_network_root_identity' \
	'diagnostic_candidate=headless-netroot-early-diag-v1' \
	'ROG5 diagnostic network root' \
	'Diagnostic NFS root over NCM and ACM' \
	'functions/acm.usb0' \
	'rog5-early-target-new-init.service' \
	'rog5-early-target-sshd.service' \
	'ExecStart=/run/initramfs/sbin/rog5-early-target-diag emit 130' \
	'ExecStart=/run/initramfs/sbin/rog5-early-target-diag emit 140' \
	'cp -p "$diagnostic_binary"' \
	'mount -t nfs4' \
	'vers=4.2,proto=tcp,port=2049,ro,nolock' \
	'mount -t tmpfs -o nodev,nosuid' \
		'mount -t overlay overlay' \
		'/run/initramfs' \
		'cp -p /shutdown "$exitrd/shutdown"' \
		'chroot "$exitrd" /bin/sh -n /shutdown' \
		'if ! handoff_network_root; then' \
		'rollback_handoff_mounts || true' \
		'trap switch_root_failure EXIT' \
		'trap - EXIT' \
		'exec switch_root "$handoff_newroot" /sbin/init'; do
	grep -Fq "$text" "$init" || {
		echo "FAIL network-root init contract missing: $text" >&2
		exit 1
	}
done

[ "$(grep -Fc 'network-root watchdog attestation failed' "$init")" -eq 1 ]
grep -Fq 'chmod 0400 "$lease_stage" "$pid_stage"' "$init"
grep -Fq '"$watchdog_run/rog5-network-root-watchdog.lease"' "$init"
grep -Fq 'timer_pid=$(find_watchdog_timer "$watchdog_pid")' "$init"

storage_device_pattern='(^|[^[:alnum:]_./])/dev/(block|disk|mapper|sd[a-z]|mmcblk|nvme|ufs)'
if grep -Eq "blkid|fsck|$storage_device_pattern" "$init"; then
	echo 'FAIL network-root init exposes forbidden storage discovery' >&2
	exit 1
fi
if grep -Eq 'fastboot|flash|mkfs|wipefs' "$init"; then
	echo 'FAIL network-root init exposes destructive device operations' >&2
	exit 1
fi

mode_line=$(grep -n 'invalid network-root command line' "$init" |
	head -n1 | cut -d: -f1)
storage_line=$(grep -n 'physical block device appeared with UFS-disabled DTB' \
	"$init" | tail -n1 | cut -d: -f1)
watchdog_line=$(grep -n '^[[:space:]]*if ! arm_watchdog; then$' "$init" |
	head -n1 | cut -d: -f1)
diagnostic_start_line=$(grep -n \
	'^[[:space:]]*if ! start_diagnostics; then$' "$init" |
	head -n1 | cut -d: -f1)
usb_line=$(grep -n '^[[:space:]]*configure_usb$' "$init" |
	head -n1 | cut -d: -f1)
nfs_line=$(grep -n '^[[:space:]]*mount_network_root$' "$init" |
	head -n1 | cut -d: -f1)
exitrd_line=$(grep -n '^[[:space:]]*if ! prepare_shutdown_root; then$' "$init" |
	head -n1 | cut -d: -f1)
switch_line=$(grep -n 'exec switch_root "\$handoff_newroot" /sbin/init' "$init" |
	tail -n1 | cut -d: -f1)

[ "$mode_line" -lt "$storage_line" ]
[ "$storage_line" -lt "$watchdog_line" ]
[ "$watchdog_line" -lt "$diagnostic_start_line" ]
[ "$diagnostic_start_line" -lt "$usb_line" ]
[ "$usb_line" -lt "$nfs_line" ]
[ "$nfs_line" -lt "$exitrd_line" ]
[ "$exitrd_line" -lt "$switch_line" ]
[ "$nfs_line" -lt "$switch_line" ]
identity_publish_line=$(grep -n \
	'^[[:space:]]*if ! publish_network_root_identity; then$' "$init" |
	head -n1 | cut -d: -f1)
handoff_line=$(grep -n \
	'^[[:space:]]*if ! handoff_network_root; then$' "$init" |
	head -n1 | cut -d: -f1)
[ "$nfs_line" -lt "$identity_publish_line" ]
[ "$identity_publish_line" -lt "$handoff_line" ]

readonly_check_line=$(grep -n \
	'^[[:space:]]*awk .*"/mnt/root-ro".*ro' "$init" |
	head -n1 | cut -d: -f1)
identity_line=$(grep -n \
	'^[[:space:]]*verify_network_root_identity || return 1$' "$init" |
	head -n1 | cut -d: -f1)
overlay_line=$(grep -n \
	'^[[:space:]]*mount -t overlay overlay' "$init" |
	head -n1 | cut -d: -f1)
[ "$readonly_check_line" -lt "$identity_line" ]
[ "$identity_line" -lt "$overlay_line" ]

for stage in 10 20 30 40 50 60 70 80 90 100 110 120; do
	[ "$(grep -Ec "diagnostic_emit[[:space:]]+$stage([[:space:];]|$)" \
		"$init")" -eq 1 ] || {
		echo "FAIL diagnostic stage $stage is absent or duplicated" >&2
		exit 1
	}
done
for fault in \
	gadget-config-failed \
	udc-bind-failed \
	ncm-interface-failed \
	address-failed \
	carrier-timeout \
	nfs-mount-failed \
	seal-verify-failed \
	overlay-failed \
	diagnostic-units-failed \
	identity-publish-failed \
	storage-before-switch \
	exitrd-failed \
	handoff-failed \
	switch-root-returned; do
	grep -Fq "$fault" "$init" || {
		echo "FAIL diagnostic fault is absent: $fault" >&2
		exit 1
	}
done
[ "$(grep -Ec 'diagnostic_emit[[:space:]]+200([[:space:];]|$)' \
	"$init")" -eq 1 ]

[ "$(grep -Fc 'rog5.netroot=1' "$init")" -eq 1 ]
grep -Fq '[ "$physical_count" -eq 0 ]' "$init"
grep -Fq '[ -x /newroot/sbin/init ]' "$init"
grep -Fq 'move_handoff_mount "$handoff_dev" "$handoff_newroot/dev"' "$init"
grep -Fq 'move_handoff_mount "$handoff_proc" "$handoff_newroot/proc"' "$init"
grep -Fq 'move_handoff_mount "$handoff_sys" "$handoff_newroot/sys"' "$init"
grep -Fq 'move_handoff_mount "$handoff_run" "$handoff_newroot/run"' "$init"

for text in \
	'mount --move "$source" "$target"' \
	'move_mount /oldroot/.rog5/root-ro /oldsys/root-ro' \
	'move_mount /oldroot/.rog5/state /oldsys/state' \
	'unmount_mount /oldroot' \
	'umount -l "$target"' \
	'reboot -f -n' \
	'printf b >/proc/sysrq-trigger'; do
	grep -Fq "$text" "$shutdown" || {
		echo "FAIL network-root shutdown contract missing: $text" >&2
		exit 1
	}
done
if grep -Eq \
	"mkfs|wipefs|blkdiscard|fastboot|flash|$storage_device_pattern" \
	"$shutdown"; then
	echo 'FAIL network-root shutdown exposes destructive operations' >&2
	exit 1
fi

work=$(mktemp -d)
watchdog_pid=
timer_pid=
cleanup() {
	[ -z "$timer_pid" ] ||
		kill "$timer_pid" 2>/dev/null || true
	[ -z "$watchdog_pid" ] ||
		kill "$watchdog_pid" 2>/dev/null || true
	[ -z "$watchdog_pid" ] ||
		wait "$watchdog_pid" 2>/dev/null || true
	rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM
mkdir "$work/run"

diagnostic_functions=$work/diagnostic-functions.sh
awk '
	/^diagnostic_emit\(\) \{/ { copy=1 }
	/^physical_topology_count\(\) \{/ { copy=0 }
	copy { print }
' "$init" >"$diagnostic_functions"
(
# shellcheck disable=SC1090
. "$diagnostic_functions"
diagnostic_log=$work/diagnostic-rollback
diagnostic_binary=$work/fake-diagnostic-reporter
: >"$diagnostic_binary"
chmod 0755 "$diagnostic_binary"
diagnostic_mode=1
deadline_boottime=
if start_diagnostics; then
	echo 'FAIL reporter started without a watchdog deadline' >&2
	exit 1
fi
deadline_boottime=not-a-number
if start_diagnostics; then
	echo 'FAIL reporter started with a nonnumeric watchdog deadline' >&2
	exit 1
fi
diagnostic_emit() {
	printf 'emit %s %s\n' "$1" "${2:-none}" >>"$diagnostic_log"
}
sleep() {
	printf 'sleep %s\n' "$1" >>"$diagnostic_log"
}
force_rollback() {
	printf 'rollback\n' >>"$diagnostic_log"
	return 77
}
diagnostic_mode=1
: >"$diagnostic_log"
if diagnostic_rollback seal-verify-failed; then
	echo 'FAIL diagnostic rollback unexpectedly returned success' >&2
	exit 1
else
	diagnostic_status=$?
fi
[ "$diagnostic_status" -eq 77 ]
printf 'emit 200 seal-verify-failed\nsleep 5\nrollback\n' \
	>"$work/expected-diagnostic-rollback"
cmp "$diagnostic_log" "$work/expected-diagnostic-rollback"
diagnostic_mode=0
: >"$diagnostic_log"
if diagnostic_rollback ignored-in-normal-mode; then
	exit 1
else
	diagnostic_status=$?
fi
[ "$diagnostic_status" -eq 77 ]
printf 'rollback\n' >"$work/expected-normal-rollback"
cmp "$diagnostic_log" "$work/expected-normal-rollback"
)

unit_functions=$work/diagnostic-unit-functions.sh
awk '
	/^install_diagnostic_units\(\) \{/ { copy=1 }
	/^prepare_shutdown_root\(\) \{/ { copy=0 }
	copy { print }
' "$init" >"$unit_functions"
# shellcheck disable=SC1090
. "$unit_functions"
handoff_newroot=$work/unit-root
diagnostic_mode=0
install_diagnostic_units
[ ! -e "$handoff_newroot/etc" ]
diagnostic_mode=1
install_diagnostic_units
unit_root=$handoff_newroot/etc/systemd/system
[ -f "$unit_root/rog5-early-target-new-init.service" ]
[ -f "$unit_root/rog5-early-target-sshd.service" ]
[ "$(stat -c %a "$unit_root/rog5-early-target-new-init.service")" = 644 ]
[ "$(readlink "$unit_root/basic.target.wants/rog5-early-target-new-init.service")" = \
	../rog5-early-target-new-init.service ]
[ "$(readlink "$unit_root/multi-user.target.wants/rog5-early-target-sshd.service")" = \
	../rog5-early-target-sshd.service ]
grep -Fxq 'ExecStart=/run/initramfs/sbin/rog5-early-target-diag emit 130' \
	"$unit_root/rog5-early-target-new-init.service"
grep -Fxq 'Requires=sshd.service' \
	"$unit_root/rog5-early-target-sshd.service"
grep -Fxq 'After=sshd.service' \
	"$unit_root/rog5-early-target-sshd.service"
grep -Fxq 'ExecStart=/run/initramfs/sbin/rog5-early-target-diag emit 140' \
	"$unit_root/rog5-early-target-sshd.service"
(
	handoff_newroot=$work/unit-write-failure
	diagnostic_mode=1
	cat() {
		return 1
	}
	if install_diagnostic_units; then
		echo 'FAIL partial diagnostic unit write was accepted' >&2
		exit 1
	fi
	[ ! -e "$handoff_newroot/etc/systemd/system/rog5-early-target-new-init.service" ]
	[ ! -e "$handoff_newroot/etc/systemd/system/rog5-early-target-sshd.service" ]
)
handoff_newroot=$work/unit-link-refusal
mkdir -p "$handoff_newroot/etc/systemd/system"
ln -s /dev/null \
	"$handoff_newroot/etc/systemd/system/rog5-early-target-new-init.service"
if install_diagnostic_units; then
	echo 'FAIL linked diagnostic unit destination was accepted' >&2
	exit 1
fi

canonical_elf=$work/canonical-persistent-root-verify
substitute_elf=$work/substitute-persistent-root-verify
printf '\177ELF\002\001\001\000\000\000\000\000\000\000\000\000\002\000\267\000\001\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\100\000\070\000\000\000\100\000\000\000\000\000' \
	>"$canonical_elf"
cp "$canonical_elf" "$substitute_elf"
printf '\001' >>"$substitute_elf"
chmod 0755 "$canonical_elf" "$substitute_elf"
if NETWORK_ROOT_VERIFIER="$canonical_elf" \
	"$initramfs_builder" "$work/absent-base" "$work/refused-output" \
	>"$work/reviewed-verifier-refusal.log" 2>&1; then
	echo 'FAIL unreviewed verifier artifact was accepted' >&2
	exit 1
fi
grep -Fq 'reviewed static verifier artifact hash changed' \
	"$work/reviewed-verifier-refusal.log"
for candidate in "$canonical_elf" "$substitute_elf"; do
	readelf -h "$candidate" | grep -q 'Machine:.*AArch64'
	if readelf -l "$candidate" | grep -q 'Requesting program interpreter'; then
		echo 'FAIL substitution fixture is not static' >&2
		exit 1
	fi
done

substitution_root=$work/substitution-root
mkdir -p "$substitution_root/sbin" "$substitution_root/etc/ssh" \
	"$substitution_root/root/.ssh"
cp "$init" "$substitution_root/init"
cp "$shutdown" "$substitution_root/shutdown"
cp "$substitute_elf" \
	"$substitution_root/sbin/persistent-root-verify"
for path in \
	bin/sh \
	bin/mount \
	bin/mountpoint \
	bin/sleep \
	sbin/ip \
	sbin/mdev \
	sbin/reboot \
	sbin/switch_root \
	usr/bin/awk \
	usr/bin/find \
	usr/bin/readlink \
	usr/bin/sha256sum \
	usr/bin/setsid \
	usr/sbin/chroot; do
	mkdir -p "$substitution_root/$(dirname "$path")"
	ln -s /bin/true "$substitution_root/$path"
done
substitution_archive=$work/substitution.cpio.gz
(cd "$substitution_root" &&
	find . -mindepth 1 -print0 | LC_ALL=C sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0) |
	gzip -n >"$substitution_archive"
if "$repo/scripts/device/verify-network-root-initramfs.sh" \
	"$substitution_archive" >"$work/substitution.log" 2>&1; then
	echo 'FAIL valid static verifier substitution was accepted' >&2
	exit 1
fi
grep -Fq 'embedded persistent-root verifier hash changed' \
	"$work/substitution.log"

handoff_functions=$work/handoff-functions.sh
awk '
	/^move_handoff_mount\(\) \{/ { copy=1 }
	/^if ! parse_network_root_command_line; then$/ { copy=0 }
	copy { print }
' "$init" >"$handoff_functions"
grep -Fq 'handoff_network_root() {' "$handoff_functions"
# shellcheck disable=SC1090
. "$handoff_functions"
handoff_tree=$work/handoff
handoff_newroot=$handoff_tree/newroot
handoff_root_ro=$handoff_tree/root-ro
handoff_state=$handoff_tree/state
handoff_dev=$handoff_tree/dev
handoff_proc=$handoff_tree/proc
handoff_sys=$handoff_tree/sys
handoff_run=$handoff_tree/run
mkdir -p "$handoff_root_ro" "$handoff_state" "$handoff_dev" \
	"$handoff_proc" "$handoff_sys" "$handoff_run"
handoff_move_count=0
handoff_fail_at=0
handoff_log=$work/handoff-moves
move_handoff_mount() {
	handoff_move_count=$((handoff_move_count + 1))
	printf '%s -> %s\n' "$1" "$2" >>"$handoff_log"
	[ "$handoff_move_count" -ne "$handoff_fail_at" ]
}
for handoff_fail_at in 1 2 3 4 5 6; do
	handoff_move_count=0
	: >"$handoff_log"
	if handoff_network_root; then
		echo "FAIL handoff move $handoff_fail_at was accepted" >&2
		exit 1
	fi
	[ "$handoff_move_count" -eq "$((handoff_fail_at * 2 - 1))" ]
	if [ "$handoff_fail_at" -eq 6 ]; then
		cat >"$work/expected-handoff-rollback" <<EOF
$handoff_root_ro -> $handoff_newroot/.rog5/root-ro
$handoff_state -> $handoff_newroot/.rog5/state
$handoff_dev -> $handoff_newroot/dev
$handoff_sys -> $handoff_newroot/sys
$handoff_proc -> $handoff_newroot/proc
$handoff_run -> $handoff_newroot/run
$handoff_newroot/proc -> $handoff_proc
$handoff_newroot/sys -> $handoff_sys
$handoff_newroot/dev -> $handoff_dev
$handoff_newroot/.rog5/state -> $handoff_state
$handoff_newroot/.rog5/root-ro -> $handoff_root_ro
EOF
		cmp "$handoff_log" "$work/expected-handoff-rollback"
	fi
done
handoff_fail_at=0
handoff_move_count=0
: >"$handoff_log"
handoff_network_root
[ "$handoff_move_count" -eq 6 ]

handoff_move_count=0
handoff_newroot=$work/not-a-directory
: >"$handoff_newroot"
if handoff_network_root 2>/dev/null; then
	echo 'FAIL handoff directory failure was accepted' >&2
	exit 1
fi
[ "$handoff_move_count" -eq 0 ]
handoff_newroot=$handoff_tree/newroot

handoff_move_count=0
handoff_run=$work/not-a-run-directory
: >"$handoff_run"
if handoff_network_root 2>/dev/null; then
	echo 'FAIL handoff marker write failure was accepted' >&2
	exit 1
fi
[ "$handoff_move_count" -eq 0 ]
handoff_run=$handoff_tree/run-second-marker
mkdir "$handoff_run"
mkdir "$handoff_run/rog5-network-root-source"
if handoff_network_root 2>/dev/null; then
	echo 'FAIL second handoff marker write failure was accepted' >&2
	exit 1
fi
[ "$handoff_move_count" -eq 0 ]
handoff_run=$handoff_tree/run-touch
mkdir "$handoff_run"
(
	# shellcheck disable=SC2329 # resolved dynamically by the sourced function
	touch() {
		return 1
	}
	if handoff_network_root; then
		exit 1
	fi
	[ "$handoff_move_count" -eq 0 ]
)
handoff_run=$handoff_tree/run
switch_root_failure_log=$work/switch-root-failure
switch_root_failure_probe=$work/switch-root-failure-probe.sh
cp "$handoff_functions" "$switch_root_failure_probe"
cat >>"$switch_root_failure_probe" <<'EOF'
rollback_handoff_mounts() {
	printf 'rollback\n' >>"$SWITCH_ROOT_FAILURE_LOG"
}
diagnostic_rollback() {
	[ "$1" = switch-root-returned ] || exit 76
	printf 'forced\n' >>"$SWITCH_ROOT_FAILURE_LOG"
	exit 77
}
trap switch_root_failure EXIT
if exec /rog5-definitely-missing-switch-root; then
	exit 0
else
	exit $?
fi
EOF
chmod 0755 "$switch_root_failure_probe"
switch_root_shell=bash
busybox_candidate=
if command -v qemu-aarch64-static >/dev/null 2>&1 &&
	[ -d "$repo/artifacts" ]; then
	busybox_candidate=$(find "$repo/artifacts" -type f \
		-path '*/bin/busybox' -print -quit 2>/dev/null)
fi
if [ -n "$busybox_candidate" ] &&
	[ -f "${busybox_candidate%/bin/busybox}/lib/ld-musl-aarch64.so.1" ]; then
	set -- qemu-aarch64-static -L "${busybox_candidate%/bin/busybox}" \
		"$busybox_candidate" sh "$switch_root_failure_probe"
	switch_root_shell='AArch64 BusyBox ash'
elif command -v busybox >/dev/null 2>&1; then
	set -- busybox sh "$switch_root_failure_probe"
	switch_root_shell='host BusyBox ash'
else
	set -- bash -O execfail "$switch_root_failure_probe"
fi
if SWITCH_ROOT_FAILURE_LOG="$switch_root_failure_log" \
	"$@" 2>/dev/null; then
	echo 'FAIL failed exec bypassed the switch-root failure trap' >&2
	exit 1
else
	switch_root_failure_status=$?
fi
[ "$switch_root_failure_status" -eq 77 ]
printf 'rollback\nforced\n' >"$work/expected-switch-root-failure"
cmp "$switch_root_failure_log" "$work/expected-switch-root-failure"
printf 'switch_root_failure_shell=%s\n' "$switch_root_shell" \
	>"$work/switch-root-failure-shell"

identity_functions=$work/identity-functions.sh
awk '
	/^mount_id_for_path\(\) \{/ { copy=1 }
	/^is_nonzero_sha256\(\) \{/ { copy=0 }
	copy { print }
' "$init" >"$identity_functions"
grep -Fq 'publish_network_root_identity() {' "$identity_functions"
mount_inventory=$work/mountinfo
network_root_identity=$work/run/rog5-network-root-identity
cat >"$mount_inventory" <<'EOF'
20 1 0:20 / /newroot rw - overlay overlay rw
21 1 0:21 / /mnt/root-ro ro - nfs 169.254.77.1:/ ro
22 1 0:22 / /mnt/state rw - tmpfs tmpfs rw
EOF
command_manifest_sha256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
root_generation=arch-a
root_tree_sha256=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
root_seal_sha256=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
root_tree_entries=42
root_subtree=/
export root_generation root_subtree
# shellcheck disable=SC1090
. "$identity_functions"
identity_umask=$(umask)
publish_network_root_identity
[ "$(umask)" = "$identity_umask" ]
[ -f "$network_root_identity" ] && [ ! -L "$network_root_identity" ]
[ "$(stat -c %a "$network_root_identity")" = 400 ]
[ "$(wc -l <"$network_root_identity")" -eq 11 ]
cat >"$work/expected-identity" <<EOF
format=rog5-network-root-identity-v1
overlay_mount_id=20
overlay_lower_mount_id=21
state_mount_id=22
overlay_lower_path=/mnt/root-ro
command_manifest_sha256=$command_manifest_sha256
root_generation=arch-a
root_tree_sha256=$root_tree_sha256
root_seal_sha256=$root_seal_sha256
root_tree_entries=42
root_subtree=/
EOF
cmp "$network_root_identity" "$work/expected-identity"
cp "$mount_inventory" "$work/mountinfo.valid"
cat >>"$mount_inventory" <<'EOF'
31 1 0:31 / /mnt/root-ro ro - nfs 169.254.77.1:/ ro
EOF
if publish_network_root_identity; then
	echo 'FAIL duplicate lower mount ID was accepted' >&2
	exit 1
fi
cmp "$network_root_identity" "$work/expected-identity"
grep -v ' /mnt/state ' "$work/mountinfo.valid" >"$mount_inventory"
if publish_network_root_identity; then
	echo 'FAIL absent state mount ID was accepted' >&2
	exit 1
fi
cmp "$network_root_identity" "$work/expected-identity"
cp "$work/mountinfo.valid" "$mount_inventory"

parser_functions=$work/parser-functions.sh
awk '
	/^is_nonzero_sha256\(\) \{/ { copy=1 }
	/^process_start_time_ticks\(\) \(/ { copy=0 }
	copy { print }
' "$init" >"$parser_functions"
grep -Fq 'parse_network_root_command_line() {' "$parser_functions"
command_manifest_sha256=
root_tree_sha256=
root_seal_sha256=
root_tree_entries=
# shellcheck disable=SC1090
. "$parser_functions"

hash_a=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
hash_b=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
hash_c=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
valid_cmdline="console=ttyMSM0,115200n8
rog5.netroot=1
rog5.bundle=headless-network-root-v3-r2
rog5.recovery_timeout=900
rog5.a660_command_manifest_sha256=$hash_a
rog5.root_generation=arch-a
rog5.root_tree_sha256=$hash_b
rog5.root_seal_sha256=$hash_c
rog5.root_tree_entries=42
rog5.root_subtree=/"
kernel_cmdline=$work/cmdline
diagnostic_candidate=headless-netroot-early-diag-v1
printf '%s\n' "$valid_cmdline" >"$kernel_cmdline"
parse_network_root_command_line
[ "$diagnostic_mode" -eq 0 ]
[ "$recovery_timeout" -eq 900 ]
[ "$command_manifest_sha256" = "$hash_a" ]
[ "$root_tree_sha256" = "$hash_b" ]
[ "$root_seal_sha256" = "$hash_c" ]
[ "$root_tree_entries" -eq 42 ]

expect_cmdline_rejection() {
	label=$1
	candidate=$2
	printf '%s\n' "$candidate" >"$kernel_cmdline"
	if parse_network_root_command_line; then
		echo "FAIL command line parser accepted $label" >&2
		exit 1
	fi
}

for family in \
		rog5.netroot \
		rog5.bundle \
		rog5.recovery_timeout \
	rog5.a660_command_manifest_sha256 \
	rog5.root_generation \
	rog5.root_tree_sha256 \
	rog5.root_seal_sha256 \
	rog5.root_tree_entries \
	rog5.root_subtree; do
	expect_cmdline_rejection "bare $family" \
		"$valid_cmdline $family"
	value=$(printf '%s\n' "$valid_cmdline" |
		sed -n "s/^$family=//p")
	expect_cmdline_rejection "duplicate $family" \
		"$valid_cmdline $family=$value"
	expect_cmdline_rejection "missing $family" \
		"$(printf '%s\n' "$valid_cmdline" |
			sed "/^$family=/d")"
done

diagnostic_cmdline=$(printf '%s\n' "$valid_cmdline" |
	sed 's/rog5.bundle=headless-network-root-v3-r2/rog5.bundle=headless-netroot-early-diag-v1/')
diagnostic_cmdline="$diagnostic_cmdline
rog5.diagnostic=1"
printf '%s\n' "$diagnostic_cmdline" >"$kernel_cmdline"
parse_network_root_command_line
[ "$diagnostic_mode" -eq 1 ]
expect_cmdline_rejection 'bare diagnostic mode' \
	"$diagnostic_cmdline rog5.diagnostic"
expect_cmdline_rejection 'duplicate diagnostic mode' \
	"$diagnostic_cmdline rog5.diagnostic=1"
expect_cmdline_rejection 'wrong diagnostic mode' \
	"$(printf '%s\n' "$diagnostic_cmdline" |
		sed 's/rog5.diagnostic=1/rog5.diagnostic=2/')"
expect_cmdline_rejection 'diagnostic identity without mode' \
	"$(printf '%s\n' "$diagnostic_cmdline" |
		sed '/rog5.diagnostic=1/d')"
expect_cmdline_rejection 'diagnostic mode with runtime identity' \
	"$valid_cmdline rog5.diagnostic=1"
expect_cmdline_rejection 'leading-dot bundle identity' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's/rog5.bundle=headless-network-root-v3-r2/rog5.bundle=.hidden/')"
expect_cmdline_rejection 'double-dot bundle identity' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's/rog5.bundle=headless-network-root-v3-r2/rog5.bundle=a..b/')"
expect_cmdline_rejection 'slash in bundle identity' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's|rog5.bundle=headless-network-root-v3-r2|rog5.bundle=a/b|')"
expect_cmdline_rejection 'uppercase bundle identity' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's/rog5.bundle=headless-network-root-v3-r2/rog5.bundle=Upper/')"
long_bundle=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
expect_cmdline_rejection 'overlong bundle identity' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed "s/rog5.bundle=headless-network-root-v3-r2/rog5.bundle=$long_bundle/")"

expect_cmdline_rejection 'wrong netroot mode' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's/^rog5.netroot=1$/rog5.netroot=0/')"
expect_cmdline_rejection 'timeout below floor' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's/^rog5.recovery_timeout=900$/rog5.recovery_timeout=59/')"
expect_cmdline_rejection 'timeout above ceiling' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's/^rog5.recovery_timeout=900$/rog5.recovery_timeout=901/')"
expect_cmdline_rejection 'uppercase hash' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed "s/^rog5.root_tree_sha256=$hash_b$/rog5.root_tree_sha256=B${hash_b#?}/")"
expect_cmdline_rejection 'punctuated hash' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed "s/^rog5.root_tree_sha256=$hash_b$/rog5.root_tree_sha256=:${hash_b#?}/")"
expect_cmdline_rejection 'zero hash' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed "s/^rog5.root_tree_sha256=$hash_b$/rog5.root_tree_sha256=$(printf '%064d' 0)/")"
expect_cmdline_rejection 'noncanonical entry count' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's/^rog5.root_tree_entries=42$/rog5.root_tree_entries=042/')"
expect_cmdline_rejection 'wrong generation' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's/^rog5.root_generation=arch-a$/rog5.root_generation=arch-b/')"
expect_cmdline_rejection 'wrong subtree' \
	"$(printf '%s\n' "$valid_cmdline" |
		sed 's|^rog5.root_subtree=/$|rog5.root_subtree=/usr|')"

functions=$work/watchdog-functions.sh
awk '
	/^process_start_time_ticks\(\) \(/ { copy=1 }
	/^configure_usb\(\) \{/ { copy=0 }
	copy { print }
' "$init" >"$functions"
grep -Fq 'arm_watchdog() {' "$functions"

watchdog_proc=/proc
watchdog_run=$work/run
watchdog_log=/dev/null
watchdog_reset=/dev/null
recovery_timeout=60
export watchdog_proc watchdog_run watchdog_log watchdog_reset
export recovery_timeout
log() {
	:
}
# shellcheck disable=SC1090
. "$functions"
watchdog_umask=$(umask)
arm_watchdog
[ "$(umask)" = "$watchdog_umask" ]

pid_file=$watchdog_run/rog5-network-root-watchdog.pid
lease_file=$watchdog_run/rog5-network-root-watchdog.lease
[ -f "$pid_file" ] && [ ! -L "$pid_file" ]
[ -f "$lease_file" ] && [ ! -L "$lease_file" ]
[ "$(stat -c %a "$pid_file")" = 400 ]
[ "$(stat -c %a "$lease_file")" = 400 ]
[ "$(wc -l <"$lease_file")" -eq 8 ]
[ "$(cat "$pid_file")" = "$watchdog_pid" ]

lease_value() {
	lease_name=$1
	lease_matches=$(grep -c "^$lease_name=" "$lease_file")
	[ "$lease_matches" -eq 1 ]
	sed -n "s/^$lease_name=//p" "$lease_file"
}

[ "$(lease_value format)" = rog5-network-root-watchdog-v1 ]
[ "$(lease_value pid)" = "$watchdog_pid" ]
[ "$(lease_value start_time_ticks)" = \
	"$(process_start_time_ticks "$watchdog_pid")" ]
[ "$(lease_value timer_pid)" = "$timer_pid" ]
[ "$(lease_value timer_start_time_ticks)" = \
	"$(process_start_time_ticks "$timer_pid")" ]
[ "$(cat "$watchdog_proc/$timer_pid/comm")" = sleep ]
armed=$(lease_value armed_boottime_seconds)
deadline=$(lease_value deadline_boottime_seconds)
[ "$(lease_value timeout_seconds)" = "$recovery_timeout" ]
[ "$((deadline - armed))" -eq "$recovery_timeout" ]
case $armed:$deadline in
	*[!0-9:]*|:*) exit 1 ;;
esac

echo 'PASS network-root init keeps UFS absent, retains an exitrd, tears down overlay backing mounts, and preserves rollback'
