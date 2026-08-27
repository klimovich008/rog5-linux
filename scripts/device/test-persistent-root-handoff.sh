#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-init

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk bash chmod cmp cp grep mkdir mktemp; do
	command -v "$command" >/dev/null ||
		fail "missing persistent-root handoff test command: $command"
done
[ -x "$init" ] || fail 'persistent-root init is absent'

for contract in \
	'handoff_persistent_root() {' \
	'rollback_handoff_mounts() {' \
	'switch_root_failure() {' \
	'publish_stage switch-root PASS' \
	'trap switch_root_failure EXIT'; do
	grep -Fq "$contract" "$init" ||
		fail "persistent-root handoff contract is absent: $contract"
done
[ "$(grep -Ec '^[[:space:]]*mount --move ' "$init")" -eq 1 ] ||
	fail 'persistent-root handoff has a direct or missing mount move'

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
functions=$work/handoff-functions.sh
awk '
	/^move_handoff_mount\(\) \{/ { copy=1 }
	/^recovery_timeout=/ { copy=0 }
	copy { print }
' "$init" >"$functions"
grep -Fq 'handoff_persistent_root() {' "$functions" ||
	fail 'persistent-root handoff functions could not be isolated'
expected_native_root_mode=0
# shellcheck disable=SC1090
. "$functions"

handoff_tree=$work/handoff
handoff_newroot=$handoff_tree/newroot
handoff_userdata=$handoff_tree/userdata
handoff_root=$handoff_tree/root-ro
handoff_state=$handoff_tree/state
handoff_dev=$handoff_tree/dev
handoff_proc=$handoff_tree/proc
handoff_sys=$handoff_tree/sys
handoff_run=$handoff_tree/run
mkdir -p "$handoff_userdata" "$handoff_root" "$handoff_state" "$handoff_dev" \
	"$handoff_proc" "$handoff_sys" "$handoff_run"

handoff_move_count=0
handoff_fail_at=0
move_handoff_mount() {
	handoff_move_count=$((handoff_move_count + 1))
	[ "$handoff_move_count" -ne "$handoff_fail_at" ]
}
for handoff_fail_at in 1 2 3 4 5 6 7; do
	handoff_move_count=0
	if handoff_persistent_root; then
		fail "persistent-root handoff accepted failed move $handoff_fail_at"
	fi
	[ "$handoff_move_count" -eq "$((handoff_fail_at * 2 - 1))" ] ||
		fail "persistent-root handoff did not roll back move $handoff_fail_at"
done
handoff_fail_at=0
handoff_move_count=0
handoff_persistent_root || fail 'complete persistent-root handoff was rejected'
[ "$handoff_move_count" -eq 7 ] ||
	fail 'complete persistent-root handoff did not move seven mounts'
expected_native_root_mode=1
handoff_move_count=0
handoff_persistent_root || fail 'complete native-root handoff was rejected'
[ "$handoff_move_count" -eq 6 ] ||
	fail 'complete native-root handoff did not move six mounts'
expected_native_root_mode=0

failure_log=$work/switch-root-failure
probe=$work/switch-root-failure-probe.sh
cp "$functions" "$probe"
cat >>"$probe" <<'EOF'
rollback_handoff_mounts() {
	printf 'rollback\n' >>"$SWITCH_ROOT_FAILURE_LOG"
}
publish_stage() {
	[ "$1:$2" = switch-root:FAIL ] || exit 76
	printf 'failed\n' >>"$SWITCH_ROOT_FAILURE_LOG"
}
log() { :; }
force_rollback() {
	printf 'forced\n' >>"$SWITCH_ROOT_FAILURE_LOG"
	exit 77
}
sleep() { :; }
trap switch_root_failure EXIT
if exec /rog5-definitely-missing-switch-root; then
	exit 0
else
	exit $?
fi
EOF
chmod 0755 "$probe"
if SWITCH_ROOT_FAILURE_LOG="$failure_log" \
	bash -O execfail "$probe" 2>/dev/null; then
	fail 'failed switch_root exec bypassed the rollback trap'
else
	failure_status=$?
fi
[ "$failure_status" -eq 77 ] ||
	fail 'failed switch_root exec did not force rollback'
printf 'rollback\nfailed\nforced\n' >"$work/expected-failure"
cmp "$failure_log" "$work/expected-failure" ||
	fail 'failed switch_root exec produced the wrong rollback sequence'

echo 'PASS persistent-root handoff rejects and rolls back every failed move and returned switch_root'
