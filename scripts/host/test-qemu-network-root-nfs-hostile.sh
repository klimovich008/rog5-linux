#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
contract=$repo/scripts/host/test-qemu-system-smoke-contract.sh
source_file=$repo/tools/qemu-network-root-nfs/init.c
config_file=$repo/tools/qemu-network-root-nfs/ganesha.conf.in
runner_file=$repo/scripts/host/test-qemu-network-root-nfs.sh
production_harness=$repo/tools/qemu-network-root-nfs/production-init.sh
kernel_builder=$repo/scripts/host/build-qemu-smoke-kernel.sh
handoff_source=$repo/tools/qemu-diagnostic-handoff/init.c
for path in "$contract" "$source_file" "$config_file" "$runner_file" \
	"$production_harness" "$kernel_builder" "$handoff_source"; do
	[[ -f $path && ! -L $path ]] || fail "unsafe hostile-test input: $path"
done

test_root=$(mktemp -d)
trap 'find "$test_root" -depth -delete 2>/dev/null || true' EXIT HUP INT TERM

expect_rejection() {
	local expected=$1
	shift
	if "$@" >"$test_root/output" 2>&1; then
		fail "hostile mutation was accepted: $expected"
	fi
	grep -Fq "$expected" "$test_root/output" || {
		sed -n '1,120p' "$test_root/output" >&2
		fail "hostile mutation had the wrong classification: $expected"
	}
}

cp -- "$source_file" "$test_root/init.c"
sed -i 's/vers=4\.2/vers=4.1/' "$test_root/init.c"
expect_rejection 'QEMU NFS mount options differ from production' \
	env QEMU_NFS_SOURCE="$test_root/init.c" "$contract"

cp -- "$config_file" "$test_root/ganesha.conf.in"
sed -i 's/Access_Type = RO/Access_Type = RW/' "$test_root/ganesha.conf.in"
expect_rejection 'QEMU NFS server contract is missing: Access_Type = RO' \
	env QEMU_NFS_CONFIG="$test_root/ganesha.conf.in" "$contract"

cp -- "$config_file" "$test_root/ganesha.conf.in"
sed -i 's/Name = VFS/Name = MEM/' "$test_root/ganesha.conf.in"
expect_rejection 'QEMU NFS server contract is missing: Name = VFS' \
	env QEMU_NFS_CONFIG="$test_root/ganesha.conf.in" "$contract"

cp -- "$config_file" "$test_root/ganesha.conf.in"
sed -i 's|Path = @EXPORT_ROOT@|Path = /|' "$test_root/ganesha.conf.in"
expect_rejection 'QEMU NFS server contract is missing: Path = @EXPORT_ROOT@' \
	env QEMU_NFS_CONFIG="$test_root/ganesha.conf.in" "$contract"

cp -- "$config_file" "$test_root/ganesha.conf.in"
sed -i '/Only_Numeric_Owners = true/d' "$test_root/ganesha.conf.in"
expect_rejection \
	'QEMU NFS server contract is missing: Only_Numeric_Owners = true' \
	env QEMU_NFS_CONFIG="$test_root/ganesha.conf.in" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i 's/,restrict=on//' "$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS contract is missing: host=169.254.77.3,dns=169.254.77.4,restrict=on' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i '/TCP port 2049 is already in use/d' \
	"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS contract is missing: TCP port 2049 is already in use' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i '/pid=\$ganesha_pid,/d' "$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS contract is missing: pid=$ganesha_pid,' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i 's|mktemp -d /dev/shm/rog5-qemu-network-root.XXXXXX|mktemp -d|' \
	"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU production root handoff contract is missing: /dev/shm/rog5-qemu-network-root.XXXXXX' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i '/stat -f -c %T/d' "$test_root/test-qemu-network-root-nfs.sh"
expect_rejection 'QEMU NFS export is not constrained to private tmpfs' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i '/sed "s|@EXPORT_ROOT@|\$export_root|"/d' \
	"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS VFS export path is not bound to the private tmpfs root' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i 's/nfsv4\.directory_delegations=0 //' \
	"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS contract is missing: nfsv4.directory_delegations=0' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i 's/nfs\.nfs4_disable_idmapping=1 //' \
	"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS contract is missing: nfs.nfs4_disable_idmapping=1' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$source_file" "$test_root/init.c"
sed -i '/verify_seeded_systemd();/d' "$test_root/init.c"
expect_rejection \
	'QEMU NFS client does not prove the staged systemd payload is readable' \
	env QEMU_NFS_SOURCE="$test_root/init.c" "$contract"

cp -- "$source_file" "$test_root/init.c"
sed -i '/verify_server_read_only(server_probe_options);/d' "$test_root/init.c"
expect_rejection \
	'QEMU NFS client does not prove server-side read-only enforcement' \
	env QEMU_NFS_SOURCE="$test_root/init.c" "$contract"

cp -- "$source_file" "$test_root/init.c"
sed -i '/verify_server_probe_client_rw();/d' "$test_root/init.c"
expect_rejection \
	'QEMU NFS server-RO probe does not prove the client mount is RW' \
	env QEMU_NFS_SOURCE="$test_root/init.c" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -n '/run_qemu_guest()/,/^}/p' "$runner_file" \
	>>"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS runner duplicates the guest invocation' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$source_file" "$test_root/init.c"
sed -i '/verify_read_only_enforcement();/d' "$test_root/init.c"
expect_rejection 'QEMU NFS client does not test read-only enforcement' \
	env QEMU_NFS_SOURCE="$test_root/init.c" "$contract"

cp -- "$source_file" "$test_root/init.c"
sed -i '/execl("\/bin\/sh", "sh", "\/production-init"/d' "$test_root/init.c"
expect_rejection 'direct QEMU probe does not enter the production shell probe' \
	env QEMU_NFS_SOURCE="$test_root/init.c" "$contract"

cp -- "$production_harness" "$test_root/production-init.sh"
sed -i 's/mount_network_root/mount_network_root_copy/' \
	"$test_root/production-init.sh"
expect_rejection 'QEMU production harness does not call mount_network_root' \
	env QEMU_NFS_PRODUCTION_HARNESS="$test_root/production-init.sh" "$contract"

cp -- "$production_harness" "$test_root/production-init.sh"
sed -i '/directory_delegations" = N/d' "$test_root/production-init.sh"
expect_rejection \
	'QEMU production harness does not verify directory-delegation disablement' \
	env QEMU_NFS_PRODUCTION_HARNESS="$test_root/production-init.sh" "$contract"

cp -- "$production_harness" "$test_root/production-init.sh"
sed -i '/nfs4_disable_idmapping" = Y/d' "$test_root/production-init.sh"
expect_rejection \
	'QEMU production harness does not verify numeric owner mapping' \
	env QEMU_NFS_PRODUCTION_HARNESS="$test_root/production-init.sh" "$contract"

cp -- "$production_harness" "$test_root/production-init.sh"
printf '\n# copied implementation: vers=4.2\n' >>"$test_root/production-init.sh"
expect_rejection 'QEMU production harness copied the NFS mount implementation' \
	env QEMU_NFS_PRODUCTION_HARNESS="$test_root/production-init.sh" "$contract"

cp -- "$production_harness" "$test_root/production-init.sh"
sed -i 's/70 75 80 90 100/70 75 80 90/' "$test_root/production-init.sh"
expect_rejection 'QEMU production harness does not require stage 100' \
	env QEMU_NFS_PRODUCTION_HARNESS="$test_root/production-init.sh" "$contract"

cp -- "$kernel_builder" "$test_root/build-qemu-smoke-kernel.sh"
sed -i '/OVERLAY_FS ROOT_NFS/s/OVERLAY_FS //' \
	"$test_root/build-qemu-smoke-kernel.sh"
expect_rejection 'minimal QEMU kernel is missing OVERLAY_FS' \
	env QEMU_KERNEL_BUILDER="$test_root/build-qemu-smoke-kernel.sh" "$contract"

cp -- "$kernel_builder" "$test_root/build-qemu-smoke-kernel.sh"
sed -i '/TMPFS_XATTR TTY/s/TMPFS_XATTR //' \
	"$test_root/build-qemu-smoke-kernel.sh"
expect_rejection 'minimal QEMU kernel is missing TMPFS_XATTR' \
	env QEMU_KERNEL_BUILDER="$test_root/build-qemu-smoke-kernel.sh" "$contract"

cp -- "$kernel_builder" "$test_root/build-qemu-smoke-kernel.sh"
sed -i 's/disabled_runtime_options=(NFS_V4_2_READ_PLUS)/disabled_runtime_options=()/' \
	"$test_root/build-qemu-smoke-kernel.sh"
expect_rejection \
	'minimal QEMU kernel enables Ganesha-unsupported NFSv4.2 READ_PLUS' \
	env QEMU_KERNEL_BUILDER="$test_root/build-qemu-smoke-kernel.sh" "$contract"

cp -- "$production_harness" "$test_root/production-init.sh"
sed -i '/prepare_shutdown_root/d' "$test_root/production-init.sh"
expect_rejection \
	'QEMU production root handoff contract is missing: prepare_shutdown_root' \
	env QEMU_NFS_PRODUCTION_HARNESS="$test_root/production-init.sh" "$contract"

cp -- "$production_harness" "$test_root/production-init.sh"
sed -i '/handoff_network_root/d' "$test_root/production-init.sh"
expect_rejection \
	'QEMU production root handoff contract is missing: handoff_network_root' \
	env QEMU_NFS_PRODUCTION_HARNESS="$test_root/production-init.sh" "$contract"

cp -- "$production_harness" "$test_root/production-init.sh"
sed -i '/exec switch_root/d' "$test_root/production-init.sh"
expect_rejection \
	'QEMU production root handoff contract is missing: exec switch_root "$handoff_newroot" /sbin/init' \
	env QEMU_NFS_PRODUCTION_HARNESS="$test_root/production-init.sh" "$contract"

cp -- "$handoff_source" "$test_root/handoff-init.c"
sed -i '/strcmp(argv\[1\], "network-root-success")/d' \
	"$test_root/handoff-init.c"
expect_rejection 'QEMU systemd helper lacks the network-root success mode' \
	env QEMU_HANDOFF_SOURCE="$test_root/handoff-init.c" "$contract"

cp -- "$handoff_source" "$test_root/handoff-init.c"
sed -i '/require_network_root_state();/d' "$test_root/handoff-init.c"
expect_rejection \
	'QEMU systemd helper skips the production-root topology proof' \
	env QEMU_HANDOFF_SOURCE="$test_root/handoff-init.c" "$contract"

cp -- "$production_harness" "$test_root/production-init.sh"
sed -i '/verify_sha256 dad2b133/d' "$test_root/production-init.sh"
expect_rejection \
	'QEMU production harness does not verify the exact systemd runtime hashes' \
	env QEMU_NFS_PRODUCTION_HARNESS="$test_root/production-init.sh" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i '/\[\[ \$qemu_status -eq 0 \]\]/d' \
	"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS runner does not reject failure after terminal proof' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$handoff_source" "$test_root/handoff-init.c"
sed -i '/require_no_block_devices();/d' "$test_root/handoff-init.c"
expect_rejection 'QEMU systemd helper skips the live zero-storage proof' \
	env QEMU_HANDOFF_SOURCE="$test_root/handoff-init.c" "$contract"

cp -- "$handoff_source" "$test_root/handoff-init.c"
sed -i 's/directory == NULL && errno == ENOENT/directory == NULL \&\& errno == EACCES/' \
	"$test_root/handoff-init.c"
expect_rejection \
	'QEMU zero-storage proof does not distinguish absent block class' \
	env QEMU_HANDOFF_SOURCE="$test_root/handoff-init.c" "$contract"

cp -- "$handoff_source" "$test_root/handoff-init.c"
sed -i 's|mountinfo_has("/.rog5/root-ro"|mountinfo_has("/.rog5/root-weak"|' \
	"$test_root/handoff-init.c"
expect_rejection \
	'QEMU systemd helper does not verify the exact NFS lower topology' \
	env QEMU_HANDOFF_SOURCE="$test_root/handoff-init.c" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' \
	"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection 'QEMU OpenSSH fixture permits password authentication' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$handoff_source" "$test_root/handoff-init.c"
sed -i 's/PreferredAuthentications=password/PreferredAuthentications=none/' \
	"$test_root/handoff-init.c"
expect_rejection \
	'QEMU OpenSSH proof does not attempt password-only rejection' \
	env QEMU_HANDOFF_SOURCE="$test_root/handoff-init.c" "$contract"

echo 'PASS hostile QEMU NFS mutations fail closed with exact classifications'
