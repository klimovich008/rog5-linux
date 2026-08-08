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
seed_init=$repo/tools/qemu-network-root-nfs/seed-init.sh
kernel_builder=$repo/scripts/host/build-qemu-smoke-kernel.sh
for path in "$contract" "$source_file" "$config_file" "$runner_file" \
	"$production_harness" "$seed_init" "$kernel_builder"; do
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
sed -i 's/Name = MEM/Name = VFS/' "$test_root/ganesha.conf.in"
expect_rejection 'QEMU NFS server contract is missing: Name = MEM' \
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
sed -i '/Reread exports complete/d' "$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS contract is missing: Reread exports complete' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$seed_init" "$test_root/seed-init.sh"
sed -i 's/,rw,/,ro,/' "$test_root/seed-init.sh"
expect_rejection \
	'QEMU NFS seed does not request an RW setup mount' \
	env QEMU_NFS_SEED="$test_root/seed-init.sh" "$contract"

cp -- "$runner_file" "$test_root/test-qemu-network-root-nfs.sh"
sed -i 's/rog5.qemu_nfs_seed=1/rog5.qemu_nfs_seed=0/' \
	"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS runner does not request the fixture seed mode' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

cp -- "$source_file" "$test_root/init.c"
sed -i '/seed_fixture();/d' "$test_root/init.c"
expect_rejection \
	'QEMU NFS client does not enter the requested fixture seed mode' \
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
sed -i '/cp -- "\$stage\/init" "\$seed_stage\/init"/d' \
	"$test_root/test-qemu-network-root-nfs.sh"
expect_rejection \
	'QEMU NFS seed does not reuse the compiled static init' \
	env QEMU_NFS_RUNNER="$test_root/test-qemu-network-root-nfs.sh" "$contract"

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

echo 'PASS hostile QEMU NFS mutations fail closed with exact classifications'
