#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/collect-component-pss.sh}

[ -x "$target" ] || {
	echo "FAIL missing executable component PSS collector: $target" >&2
	exit 1
}
sh -n "$target"

fixture=$(mktemp -d)
trap 'rm -rf -- "$fixture"' EXIT HUP INT TERM
root=$fixture/root

add_process() {
	pid=$1
	name=$2
	pss=${3:-}
	mkdir -p "$root/proc/$pid"
	printf 'Name:\t%s\n' "$name" >"$root/proc/$pid/status"
	if [ -n "$pss" ]; then
		printf 'Pss:                %s kB\n' "$pss" \
			>"$root/proc/$pid/smaps_rollup"
	fi
}

add_process 101 kwin_wayland 100
add_process 102 plasmashell 200
add_process 103 kactivitymanage 30
add_process 201 chromium 300
add_process 202 chrome_crashpad 10
add_process 301 Xvnc 40
add_process 302 ttyd 20
add_process 401 unrelated 999

output=$(ROG5_METRICS_ROOT=$root "$target")
for expected in \
	'desktop_process_count=3' \
	'desktop_pss_readable_count=3' \
	'desktop_pss_kib=330' \
	'browser_process_count=2' \
	'browser_pss_readable_count=2' \
	'browser_pss_kib=310' \
	'remote_process_count=2' \
	'remote_pss_readable_count=2' \
	'remote_pss_kib=60' \
	'managed_process_count=7' \
	'managed_pss_readable_count=7' \
	'managed_pss_kib=700'
do
	printf '%s\n' "$output" | grep -Fqx "$expected" || {
		echo "FAIL component PSS collector omits: $expected" >&2
		exit 1
	}
done

add_process 303 websockify
output=$(ROG5_METRICS_ROOT=$root "$target")
printf '%s\n' "$output" | grep -Fqx 'remote_process_count=3'
printf '%s\n' "$output" | grep -Fqx 'remote_pss_readable_count=2'
printf '%s\n' "$output" | grep -Fqx 'remote_pss_kib=unavailable'
printf '%s\n' "$output" | grep -Fqx 'managed_pss_kib=unavailable'

set +e
ROG5_METRICS_ROOT=relative "$target" >/dev/null 2>&1
relative_status=$?
set -e
[ "$relative_status" -eq 2 ]

if grep -Eq \
	'/proc/(cmdline|[0-9*?{[]+/cmdline)|/proc/[0-9*?{[]+/(environ|fd)|ip[[:space:]]+-brief|nmcli|iwgetid' \
	"$target"
then
	echo 'FAIL component PSS collector reads a forbidden identifier source' >&2
	exit 1
fi

echo 'PASS redacted component PSS collector attributes desktop, browser, and remote-stack memory without process arguments'
