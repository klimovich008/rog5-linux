#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=$repo/scripts/host/capture-vendor-kernel-log.sh
[[ -x $target ]] || fail "missing executable vendor-kernel log capture: $target"

private_root=$repo/test-results/private
mkdir -p "$private_root"
fixture=$(mktemp -d "$private_root/.capture-test.XXXXXX")
scratch=$(mktemp -d)
trap 'rm -rf "$fixture" "$scratch"' EXIT HUP INT TERM

fake_ssh=$scratch/ssh
trace_args=$scratch/args
trace_stdin=$scratch/stdin
cat >"$fake_ssh" <<'EOF'
#!/bin/sh
set -eu
printf '%s\n' "$@" >"$TRACE_ARGS"
cat >"$TRACE_STDIN"
case ${FAKE_MODE:-good} in
	good)
		cat <<'LOG'
ROG5_VENDOR_KERNEL_LOG_V1
kernel_release=5.4.134-qgki-perf-00001-g6c308144c23e
dmesg_begin
[    0.000000] Linux version fixture
[    1.000000] qcom fixture driver ready
dmesg_end
LOG
		;;
	malformed)
		printf '%s\n' ROG5_VENDOR_KERNEL_LOG_V1 dmesg_begin
		;;
	fail)
		exit 255
		;;
	*)
		exit 2
		;;
esac
EOF
chmod +x "$fake_ssh"

output=$fixture/vendor-kernel.log
export TRACE_ARGS="$trace_args" TRACE_STDIN="$trace_stdin"
result=$(ROG5_CAPTURE_SSH=$fake_ssh "$target" "$output")

expected=$scratch/expected
cat >"$expected" <<'EOF'
ROG5_VENDOR_KERNEL_LOG_V1
kernel_release=5.4.134-qgki-perf-00001-g6c308144c23e
dmesg_begin
[    0.000000] Linux version fixture
[    1.000000] qcom fixture driver ready
dmesg_end
EOF
cmp "$expected" "$output" || fail 'capture did not preserve the complete framed log'
[[ $(stat -c %a "$output") == 600 ]] ||
	fail 'private capture mode is not 0600'
hash=$(sha256sum "$output" | awk '{ print $1 }')
grep -Fq "sha256=$hash" <<<"$result" ||
	fail 'capture result omits the artifact hash'
grep -Fq 'log_lines=2' <<<"$result" ||
	fail 'capture result omits the complete dmesg line count'

for option in \
	BatchMode=yes StrictHostKeyChecking=yes IdentitiesOnly=yes \
	HostKeyAlias=rog5-fallback ConnectTimeout=8 ConnectionAttempts=1 \
	LogLevel=ERROR rog5-fallback
do
	grep -Fqx "$option" "$trace_args" ||
		fail "SSH invocation omits: $option"
done
grep -Fq '5.4.134-qgki-perf-00001-g6c308144c23e' "$trace_stdin" ||
	fail 'remote capture does not pin the fallback kernel'
grep -Fq 'qcom,lahaina-mtp' "$trace_stdin" ||
	fail 'remote capture does not pin the device compatible'
grep -Fq 'dmesg' "$trace_stdin" ||
	fail 'remote capture omits the complete kernel log'
if grep -Eq '(^|[[:space:]])(reboot|kexec|insmod|rmmod|modprobe|mount|umount|dd)([[:space:]]|$)' \
	"$trace_stdin"; then
	fail 'remote capture contains a phone mutation command'
fi

before_hash=$hash
if ROG5_CAPTURE_SSH=$fake_ssh "$target" "$output" >/dev/null 2>&1; then
	fail 'capture overwrote an existing private artifact'
fi
[[ $(sha256sum "$output" | awk '{ print $1 }') == "$before_hash" ]] ||
	fail 'existing private artifact changed after overwrite rejection'

outside=$scratch/outside.log
if ROG5_CAPTURE_SSH=$fake_ssh "$target" "$outside" >/dev/null 2>&1; then
	fail 'capture accepted an output outside the ignored private directory'
fi
[[ ! -e $outside ]] || fail 'outside-path rejection left an artifact'

failed=$fixture/failed.log
if FAKE_MODE=fail ROG5_CAPTURE_SSH=$fake_ssh \
	"$target" "$failed" >/dev/null 2>&1; then
	fail 'capture accepted an SSH failure'
fi
[[ ! -e $failed ]] || fail 'SSH failure left a partial artifact'

malformed=$fixture/malformed.log
if FAKE_MODE=malformed ROG5_CAPTURE_SSH=$fake_ssh \
	"$target" "$malformed" >/dev/null 2>&1; then
	fail 'capture accepted an incomplete framed log'
fi
[[ ! -e $malformed ]] || fail 'malformed capture left a partial artifact'

echo 'PASS complete vendor-kernel log capture is read-only, private, atomic, and fail-closed'
