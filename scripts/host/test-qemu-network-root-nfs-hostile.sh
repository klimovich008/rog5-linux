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
for path in "$contract" "$source_file" "$config_file" "$runner_file" \
	"$production_harness"; do
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

echo 'PASS hostile QEMU NFS mutations fail closed with exact classifications'
