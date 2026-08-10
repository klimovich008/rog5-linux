#!/usr/bin/env bash
# shellcheck disable=SC2016
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_file=$repo/tools/qemu-smoke/init.c
builder=${QEMU_KERNEL_BUILDER:-$repo/scripts/host/build-qemu-smoke-kernel.sh}
cache_integration=$repo/scripts/host/test-kernel-build-cache-integration.sh
runner=$repo/scripts/host/test-qemu-system-smoke.sh
handoff_source=${QEMU_HANDOFF_SOURCE:-$repo/tools/qemu-diagnostic-handoff/init.c}
handoff_runner=$repo/scripts/host/test-qemu-diagnostic-handoff.sh
nfs_source=${QEMU_NFS_SOURCE:-$repo/tools/qemu-network-root-nfs/init.c}
nfs_production_harness=${QEMU_NFS_PRODUCTION_HARNESS:-$repo/tools/qemu-network-root-nfs/production-init.sh}
nfs_config=${QEMU_NFS_CONFIG:-$repo/tools/qemu-network-root-nfs/ganesha.conf.in}
nfs_runner=${QEMU_NFS_RUNNER:-$repo/scripts/host/test-qemu-network-root-nfs.sh}
nfs_runtime=$repo/artifacts/network-root-v3/rog5-network-root-initramfs.cpio.gz
systemd_runtime=$repo/artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz
systemd_runtime_builder=$repo/scripts/host/build-qemu-systemd-runtime.sh
systemd_runtime_verifier=$repo/scripts/host/verify-qemu-systemd-runtime.sh
workflow=$repo/.github/workflows/offline-smoke.yml
for path in "$source_file" "$builder" "$cache_integration" "$runner" \
	"$handoff_source" "$handoff_runner" "$systemd_runtime" \
	"$systemd_runtime_builder" "$systemd_runtime_verifier" "$nfs_source" \
	"$nfs_config" "$nfs_runner" "$nfs_runtime" \
	"$nfs_production_harness" "$workflow"; do
	[[ -f $path && ! -L $path ]] || fail "missing QEMU smoke source: $path"
done
for command in clang git ld.lld readelf sha256sum stat strings; do
	command -v "$command" >/dev/null ||
		fail "missing QEMU smoke contract command: $command"
done

git -C "$repo" ls-files --error-unmatch -- \
	"${nfs_runtime#"$repo"/}" >/dev/null 2>&1 ||
	fail 'QEMU NFS initramfs is not available in a clean checkout'
[[ $(stat -c %s "$nfs_runtime") == 5840728 ]] ||
	fail 'QEMU NFS initramfs size changed'
[[ $(sha256sum "$nfs_runtime" | cut -d ' ' -f 1) == \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac ]] ||
	fail 'QEMU NFS initramfs hash changed'

test_root=$(mktemp -d)
trap 'find "$test_root" -depth -delete 2>/dev/null || true' EXIT HUP INT TERM
clang --target=aarch64-none-elf -fuse-ld=lld -nostdlib -static -fno-pic \
	-fno-stack-protector -Werror -Wall -Wextra \
	-Wl,--build-id=none,--entry=_start \
	"$source_file" -o "$test_root/init"
readelf -h "$test_root/init" | grep -q 'Machine:.*AArch64'
if readelf -l "$test_root/init" | grep -q INTERP; then
	fail 'QEMU smoke init has a dynamic interpreter'
fi
strings "$test_root/init" |
	grep -qx 'PASS qemu-system arm64 initramfs boot'
grep -Fq '7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' "$builder"
grep -Fq 'LLVM=1 tinyconfig' "$builder"
grep -Fq 'rog5_kernel_prepare_output "$output_root" "$build_state"' "$builder"
grep -Fq 'rog5_kernel_make -s -C "$source_root"' "$builder"
grep -Fq 'KBUILD_BUILD_TIMESTAMP=' "$builder"
grep -Fq 'make bc clang clang++ ld.lld llvm-ar llvm-nm llvm-objcopy llvm-strip' \
	"$builder" || fail 'QEMU kernel state does not bind every build tool'
grep -Fq 'fresh cached and uncached Images differ' "$cache_integration"
grep -Fq 'INCREMENTAL_BUILD=1' "$cache_integration"
grep -Fq "hashFiles('scripts/host/build-qemu-smoke-kernel.sh', 'scripts/device/kernel-build-contract.sh')" \
	"$workflow" ||
	fail 'QEMU cache key does not bind the shared kernel build contract'
[[ $(grep -Fc "key: qemu-linux-arm64-v7.1.4-7a5cef0-\${{ runner.os }}-\${{ hashFiles('scripts/host/build-qemu-smoke-kernel.sh', 'scripts/device/kernel-build-contract.sh') }}" \
	"$workflow") == 2 ]] ||
	fail 'QEMU restore and immediate-save cache keys differ'
grep -Fq 'uses: actions/cache/save@v4' "$workflow" ||
	fail 'QEMU kernel is not cached immediately after a successful build'
for option in BLK_DEV_INITRD BINFMT_ELF CGROUPS EPOLL FHANDLE FILE_LOCKING \
	FUTEX INET INOTIFY_USER IP_PNP MEMFD_CREATE MULTIUSER NET NETDEVICES POSIX_TIMERS PRINTK PROC_FS RD_GZIP \
	NFS_FS NFS_V4 NFS_V4_2 OVERLAY_FS ROOT_NFS SECCOMP SECCOMP_FILTER SERIAL_AMBA_PL011_CONSOLE \
	SHMEM SIGNALFD SUNRPC SYSFS TIMERFD TMPFS TMPFS_XATTR UNIX VIRTIO VIRTIO_CONSOLE \
	VIRTIO_MENU VIRTIO_MMIO VIRTIO_NET; do
	grep -Eq "(^|[[:space:]])$option([[:space:]]|$)" "$builder" ||
		fail "minimal QEMU kernel is missing $option"
done
grep -Fq 'config_arguments+=(--enable "$required_runtime_option")' "$builder" ||
	fail 'minimal QEMU kernel does not derive enable arguments from its required list'
grep -Fq 'disabled_runtime_options=(NFS_V4_2_READ_PLUS)' "$builder" ||
	fail 'minimal QEMU kernel enables Ganesha-unsupported NFSv4.2 READ_PLUS'
grep -Fq 'config_arguments+=(--disable "$disabled_runtime_option")' "$builder" ||
	fail 'minimal QEMU kernel does not apply its disabled option list'
grep -Fq 'QEMU kernel enabled unsupported $disabled_runtime_option' "$builder" ||
	fail 'minimal QEMU kernel does not verify disabled options after resolution'
[[ $(grep -Fc 'for required_runtime_option in "${required_runtime_options[@]}"; do' \
	"$builder") == 2 ]] ||
	fail 'minimal QEMU kernel does not verify the same resolved option list'
grep -Fq 'QEMU kernel lost $required_runtime_option after olddefconfig' \
	"$builder" || fail 'QEMU runtime prerequisites are not checked after resolution'
grep -Fq '/^host_port_probe_(attempts|timeout|interval|output)=/ { print }' \
	"$nfs_runner" ||
	fail 'QEMU NFS readiness constants are not extracted from production'
grep -Fq '/^host_port_timeout_floor_ms=/ { print }' "$nfs_runner" ||
	fail 'QEMU NFS timeout floor is not extracted from production'
grep -Fq 'production readiness variable extraction is ambiguous' "$nfs_runner" ||
	fail 'QEMU NFS readiness extraction is not verified exactly once'
grep -Fq -- '-M virt' "$runner"
grep -Fq -- '-nic none' "$runner"
grep -Fq -- '-fuse-ld=lld' "$runner"
grep -Fq "rdinit=/init" "$runner"
for token in \
	'tools/early_target_diag/rog5-early-target-diag.c' \
	'verify-qemu-systemd-runtime.sh' \
	'install_diagnostic_units' \
	'ExecStart=/usr/bin/rog5-qemu-diagnostic-handoff sshd-server' \
	'ExecStart=/usr/bin/rog5-qemu-diagnostic-handoff ssh-proof' \
	'-device virtio-serial-device' \
	'-device virtconsole,chardev=diagnostic' \
	'PASS real key-only OpenSSH login completed' \
	'PASS generated diagnostic units ran under ARM64 systemd' \
	'DiagnosticStream("headless-netroot-early-diag-v2")' \
	'reporter_source_sha256=93d09cca8ad8dc573b1aa25c2fba5cc027d1ba901adb6c9e2643f97287387f9a' \
	'for required in (10, 120, 130, 140)'; do
	grep -Fq -- "$token" "$handoff_runner" ||
		fail "QEMU diagnostic handoff contract is missing: $token"
done
grep -Fq 'execl("/usr/bin/sshd", "/usr/bin/sshd", "-D", "-e", "-f"' \
	"$handoff_source" || fail 'QEMU harness does not execute the real OpenSSH daemon'
if grep -Fq 'sshd-stub' "$handoff_runner" ||
	grep -Fq 'SSH ordering stub' "$handoff_runner"; then
	fail 'QEMU diagnostic handoff still substitutes an SSH ordering stub'
fi
actual_reporter_source_sha256=$(
	sha256sum "$repo/tools/early_target_diag/rog5-early-target-diag.c" |
		cut -d ' ' -f 1
)
[[ $actual_reporter_source_sha256 == \
	93d09cca8ad8dc573b1aa25c2fba5cc027d1ba901adb6c9e2643f97287387f9a ]] ||
	fail 'QEMU diagnostic contract reporter source seal is stale'
grep -Fq 'enter_new_root("/newroot", SYSTEMD)' "$handoff_source"
grep -Fq 'strcmp(pid_one, SYSTEMD)' "$handoff_source"
grep -Fq 'bind_file(REPORTER, RETAINED_REPORTER)' "$handoff_source"
grep -Fq '#define PUBLICATION_SETTLE_MS 500' "$handoff_source"
[[ $(grep -Fc 'sleep_milliseconds(PUBLICATION_SETTLE_MS);' \
	"$handoff_source") == 1 ]] ||
	fail 'QEMU harness lost its final reporter publication window'
if grep -Eq 'require_emit\("(130|140)"\)' "$handoff_source"; then
	fail 'QEMU harness directly emits a systemd-owned diagnostic stage'
fi
reporter_start_line=$(grep -n 'reporter_pid = start_reporter();' \
	"$handoff_source" | cut -d: -f1)
tty_alias_line=$(grep -n 'symlink("/dev/hvc0", "/dev/ttyGS0")' \
	"$handoff_source" | cut -d: -f1)
[[ $reporter_start_line -lt $tty_alias_line ]] ||
	fail 'QEMU reporter no longer starts before its transport exists'
grep -Fq 'test-qemu-diagnostic-handoff.sh' "$workflow"
grep -Fq 'test-qemu-network-root-nfs.sh' "$workflow"
grep -Fq 'nfs-ganesha-vfs' "$workflow"
grep -Fq 'iproute2' "$workflow" ||
	fail 'QEMU workflow lacks the ss provider used for listener isolation'
grep -Fq 'libc6-dev-arm64-cross' "$workflow" ||
	fail 'QEMU workflow lacks the ARM64 static libc development package'
ganesha_stop_line=$(grep -n \
	'sudo systemctl stop nfs-ganesha.service' "$workflow" | cut -d: -f1 || true)
port_proof_line=$(grep -n \
	"ss -H -ltn 'sport = :2049'" "$workflow" | cut -d: -f1 || true)
nfs_gate_line=$(grep -n \
	'sudo scripts/host/test-qemu-network-root-nfs.sh' "$workflow" | cut -d: -f1 || true)
[[ -n $ganesha_stop_line && -n $port_proof_line && -n $nfs_gate_line &&
	$ganesha_stop_line -lt $port_proof_line &&
	$port_proof_line -lt $nfs_gate_line ]] ||
	fail 'QEMU workflow does not isolate TCP/2049 before the NFS gate'
if grep -Eq 'fastboot|/dev/(sd|nvme|ufs)|mount[[:space:]].*root=' \
	"$runner" "$handoff_runner" "$nfs_runner"; then
	fail 'board-neutral QEMU smoke contains a phone or storage action'
fi

for token in \
	'169.254.77.2::169.254.77.1:255.255.255.252' \
	'ganesha.nfsd -F' \
	'net=169.254.77.0/24' \
	'host=169.254.77.3,dns=169.254.77.4,restrict=on' \
	'guestfwd=tcp:169.254.77.1:2049-tcp:127.0.0.1:2049' \
	'PASS Linux 7.1.4 mounted exact NFSv4.2 root read-only' \
	'PASS QEMU NFS server rejected an RW client write' \
	'PASS production network-root shell assembled NFSv4.2 plus OverlayFS root' \
	'nfsv4.directory_delegations=0' \
	'nfs.nfs4_disable_idmapping=1' \
	'artifacts/network-root-v3/rog5-network-root-initramfs.cpio.gz' \
	'4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac' \
	'TCP port 2049 is already in use' \
	'pid=$ganesha_pid,' \
	"/^udc_candidate_count\\(\\) \\{/" \
	'mount_network_root'; do
	grep -Fq -- "$token" "$nfs_runner" "$nfs_source" \
		"$nfs_production_harness" ||
		fail "QEMU NFS contract is missing: $token"
done
grep -Fqx $'\tverify_server_read_only(server_probe_options);' "$nfs_source" ||
	fail 'QEMU NFS client does not prove server-side read-only enforcement'
grep -Fqx $'\tverify_server_probe_client_rw();' "$nfs_source" ||
	fail 'QEMU NFS server-RO probe does not prove the client mount is RW'
[[ $(grep -Fc \
	'timeout --signal=TERM --kill-after=2 60 qemu-system-aarch64 \' \
	"$nfs_runner") == 1 ]] ||
	fail 'QEMU NFS runner duplicates the guest invocation'
if grep -Fq 'vers=4.2' "$nfs_production_harness"; then
	fail 'QEMU production harness copied the NFS mount implementation'
fi
grep -Fqx 'if ! mount_network_root; then' "$nfs_production_harness" ||
	fail 'QEMU production harness does not call mount_network_root'
grep -Fq '[ "$directory_delegations" = N ] || fail directory-delegations-enabled' \
	"$nfs_production_harness" ||
	fail 'QEMU production harness does not verify directory-delegation disablement'
grep -Fq '[ "$nfs4_disable_idmapping" = Y ] || fail idmapping-enabled' \
	"$nfs_production_harness" ||
	fail 'QEMU production harness does not verify numeric owner mapping'
grep -Fq "[ \"\$stages\" = '70 75 80 90 100' ]" \
	"$nfs_production_harness" ||
	fail 'QEMU production harness does not require stage 100'
production_nfs_options=$(
	sed -n 's/^[[:space:]]*-o \([^[:space:]]*\).*/\1/p' \
		"$repo/initramfs/network-root-init" | grep '^vers=4\.2,' | sort -u
)
qemu_nfs_options=$(
	sed -n '/static const char production_options\[\] =/ {
		n
		s/.*"\(vers=4\.2,[^"]*\)";.*/\1/p
		q
	}' "$nfs_source"
)
[[ -n $production_nfs_options && $qemu_nfs_options == "$production_nfs_options" ]] ||
	fail 'QEMU NFS mount options differ from production'
for token in 'Minor_Versions = 2' 'Only_Numeric_Owners = true' \
	'Access_Type = RO' 'Protocols = 4' \
	'Enable_UDP = false' 'Enable_NLM = false' 'Enable_RQUOTA = false' \
	'Transports = TCP' 'Path = @EXPORT_ROOT@' 'Name = VFS'; do
	grep -Fq "$token" "$nfs_config" ||
		fail "QEMU NFS server contract is missing: $token"
done
grep -Fq 'verify_read_only_enforcement();' "$nfs_source" ||
	fail 'QEMU NFS client does not test read-only enforcement'
grep -Fq 'verify_seeded_systemd();' "$nfs_source" ||
	fail 'QEMU NFS client does not prove the staged systemd payload is readable'
grep -Fq 'execl("/bin/sh", "sh", "/production-init", NULL);' "$nfs_source" ||
	fail 'direct QEMU probe does not enter the production shell probe'
for token in \
	'artifacts/qemu-systemd-arm64-v1/runtime.cpio.gz' \
	'verify-qemu-systemd-runtime.sh' \
	'/dev/shm/rog5-qemu-network-root.XXXXXX' \
	'rog5-qemu-diagnostic-handoff network-root-success' \
	'PASS production NFS/OverlayFS root reached ARM64 systemd and key-only OpenSSH'; do
	grep -Fq -- "$token" "$nfs_runner" \
		"$nfs_production_harness" ||
		fail "QEMU production root handoff contract is missing: $token"
done
grep -Fq '[[ $(stat -f -c %T "$test_root") == tmpfs ]]' "$nfs_runner" ||
	fail 'QEMU NFS export is not constrained to private tmpfs'
grep -Fq 'sed "s|@EXPORT_ROOT@|$export_root|"' "$nfs_runner" ||
	fail 'QEMU NFS VFS export path is not bound to the private tmpfs root'
grep -Fqx 'prepare_shutdown_root || fail exitrd' "$nfs_production_harness" ||
	fail 'QEMU production root handoff contract is missing: prepare_shutdown_root'
grep -Fqx 'handoff_network_root || fail handoff' "$nfs_production_harness" ||
	fail 'QEMU production root handoff contract is missing: handoff_network_root'
grep -Fqx 'exec switch_root "$handoff_newroot" /sbin/init' \
	"$nfs_production_harness" ||
	fail 'QEMU production root handoff contract is missing: exec switch_root "$handoff_newroot" /sbin/init'
grep -Fq 'strcmp(argv[1], "network-root-success")' "$handoff_source" ||
	fail 'QEMU systemd helper lacks the network-root success mode'
grep -Fq 'require_network_root_state();' "$handoff_source" ||
	fail 'QEMU systemd helper skips the production-root topology proof'
grep -Fq 'require_no_block_devices();' "$handoff_source" ||
	fail 'QEMU systemd helper skips the live zero-storage proof'
grep -Fq 'opendir("/sys/class/block")' "$handoff_source" ||
	fail 'QEMU live zero-storage proof does not inspect block topology'
grep -Fq 'directory == NULL && errno == ENOENT' "$handoff_source" ||
	fail 'QEMU zero-storage proof does not distinguish absent block class'
grep -Fq 'mountinfo_has("/.rog5/root-ro", "nfs4", "169.254.77.1:/"' \
	"$handoff_source" ||
	fail 'QEMU systemd helper does not verify the exact NFS lower topology'
grep -Fq \
	'PASS production NFS/OverlayFS root reached ARM64 systemd and key-only OpenSSH' \
	"$handoff_source" ||
	fail 'QEMU systemd helper lacks the production-root terminal proof'
[[ $(grep -Fc 'verify_sha256 ' "$nfs_production_harness") == 3 ]] ||
	fail 'QEMU production harness does not verify the exact systemd runtime hashes'
grep -Fq '[[ $qemu_status -eq 0 ]] ||' "$nfs_runner" ||
	fail 'QEMU NFS runner does not reject failure after terminal proof'
grep -Fq 'PasswordAuthentication no' "$nfs_runner" ||
	fail 'QEMU OpenSSH fixture permits password authentication'
grep -Fq 'PreferredAuthentications=password' "$handoff_source" ||
	fail 'QEMU OpenSSH proof does not attempt password-only rejection'
grep -Fq 'SSH_ASKPASS_REQUIRE' "$handoff_source" ||
	fail 'QEMU OpenSSH password probe cannot supply its test credential'

echo 'PASS board-neutral full-system QEMU smoke contract'
