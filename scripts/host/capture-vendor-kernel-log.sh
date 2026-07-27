#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ $# == 1 ]] ||
	fail 'usage: capture-vendor-kernel-log.sh test-results/private/NAME.log'

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
private_root=$repo/test-results/private
umask 077
mkdir -p "$private_root"
[[ ! -L $private_root ]] || fail 'private result directory must not be a symlink'
chmod 700 "$private_root"
private_root=$(realpath -e "$private_root")

requested=$1
[[ $(basename "$requested") =~ ^[A-Za-z0-9][A-Za-z0-9._-]*\.log$ ]] ||
	fail 'output filename must be a simple .log name'
parent=$(realpath -e "$(dirname "$requested")" 2>/dev/null) ||
	fail 'output parent directory does not exist'
case $parent/ in
	"$private_root"/ | "$private_root"/*/) ;;
	*) fail 'output must be inside test-results/private' ;;
esac
output=$parent/$(basename "$requested")
[[ ! -e $output && ! -L $output ]] ||
	fail 'refusing to overwrite an existing private artifact'

ssh_bin=${ROG5_CAPTURE_SSH:-ssh}
if [[ $ssh_bin == */* ]]; then
	[[ $ssh_bin == /* && -x $ssh_bin ]] ||
		fail 'ROG5_CAPTURE_SSH must be an absolute executable path'
else
	ssh_bin=$(command -v "$ssh_bin") ||
		fail 'ssh is unavailable'
fi
for command in awk basename chmod dirname grep ln mkdir mktemp realpath rm \
	sed sha256sum stat tail timeout wc; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done

tmp=$(mktemp "$parent/.vendor-kernel-log.XXXXXX")
cleanup() {
	[[ -z ${tmp:-} || ! -e $tmp ]] || rm -f -- "$tmp"
}
trap cleanup EXIT HUP INT TERM
chmod 600 "$tmp"

ssh_options=(
	-o BatchMode=yes
	-o StrictHostKeyChecking=yes
	-o IdentitiesOnly=yes
	-o HostKeyAlias=rog5-fallback
	-o ConnectTimeout=8
	-o ConnectionAttempts=1
	-o LogLevel=ERROR
)

set +e
timeout 20 "$ssh_bin" "${ssh_options[@]}" rog5-fallback sh -se \
	>"$tmp" <<'REMOTE'
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

kernel=$(uname -r)
[ "$kernel" = 5.4.134-qgki-perf-00001-g6c308144c23e ] ||
	fail 'unexpected fallback kernel'
[ "$(id -u)" = 0 ] || fail 'fallback capture requires root'
[ "$(readlink /proc/1/exe)" = /bin/busybox ] ||
	fail 'unexpected fallback init'
tr '\000' '\n' </proc/device-tree/compatible |
	grep -Fxq qcom,lahaina-mtp ||
	fail 'unexpected fallback compatible'

printf '%s\n' \
	ROG5_VENDOR_KERNEL_LOG_V1 \
	"kernel_release=$kernel" \
	dmesg_begin
dmesg
printf '%s\n' dmesg_end
REMOTE
ssh_status=$?
set -e
[[ $ssh_status == 0 ]] || fail "SSH capture failed with status $ssh_status"

bytes=$(stat -c %s "$tmp")
(( bytes > 0 && bytes <= 2097152 )) ||
	fail 'captured log is empty or exceeds the 2 MiB safety bound'
[[ $(sed -n '1p' "$tmp") == ROG5_VENDOR_KERNEL_LOG_V1 ]] ||
	fail 'capture header is missing'
[[ $(sed -n '2p' "$tmp") == \
	kernel_release=5.4.134-qgki-perf-00001-g6c308144c23e ]] ||
	fail 'capture kernel identity is missing'
[[ $(grep -Fxc dmesg_begin "$tmp") == 1 ]] ||
	fail 'capture start marker is missing or ambiguous'
[[ $(grep -Fxc dmesg_end "$tmp") == 1 ]] ||
	fail 'capture end marker is missing or ambiguous'
[[ $(tail -n 1 "$tmp") == dmesg_end ]] ||
	fail 'capture is incomplete'
grep -Eq \
	'^\[[^]]*\]( \[[[:space:]]*0\.[0-9]+\])?.*Linux version' "$tmp" ||
	fail 'kernel ring no longer contains the boot origin'

total_lines=$(wc -l <"$tmp")
log_lines=$((total_lines - 4))
(( log_lines > 0 )) || fail 'captured kernel log has no entries'
hash=$(sha256sum "$tmp" | awk '{ print $1 }')

ln -- "$tmp" "$output" ||
	fail 'could not atomically publish the private artifact'
rm -f -- "$tmp"
tmp=

printf 'PASS private vendor-kernel log captured artifact=%s bytes=%s log_lines=%s sha256=%s kernel=%s\n' \
	"${output#"$repo"/}" "$bytes" "$log_lines" "$hash" \
	5.4.134-qgki-perf-00001-g6c308144c23e
