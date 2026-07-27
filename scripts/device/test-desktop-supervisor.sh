#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/desktop-supervisor.sh}
installer=$repo/scripts/device/install-runtime-tools.sh
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT HUP INT TERM

[ -x "$target" ] || {
	echo 'FAIL missing desktop supervisor' >&2
	exit 1
}

mkdir -p "$fixture/bin"
cat >"$fixture/bin/pgrep" <<'EOF'
#!/bin/sh
case "$*" in
	*chromium*) [ -e "$ROG5_TEST_HEALTHY" ] ;;
	*) exit 0 ;;
esac
EOF
cat >"$fixture/bin/sleep" <<'EOF'
#!/bin/sh
exit 0
EOF
cat >"$fixture/desktop-start" <<'EOF'
#!/bin/sh
count=0
[ ! -r "$ROG5_TEST_COUNT" ] || count=$(cat "$ROG5_TEST_COUNT")
count=$((count + 1))
printf '%s\n' "$count" >"$ROG5_TEST_COUNT"
[ "${ROG5_TEST_MODE:-heal}" != heal ] || : >"$ROG5_TEST_HEALTHY"
EOF
chmod +x "$fixture/bin/pgrep" "$fixture/bin/sleep" "$fixture/desktop-start"

run_supervisor() {
	PATH=$fixture/bin:$PATH \
	ROG5_DESKTOP_START=$fixture/desktop-start \
	ROG5_DESKTOP_SUPERVISOR_INTERVAL=1 \
	ROG5_DESKTOP_SUPERVISOR_MAX_CYCLES=3 \
	ROG5_TEST_COUNT=$fixture/count \
	ROG5_TEST_HEALTHY=$fixture/healthy \
	ROG5_TEST_MODE=$1 \
		"$target"
}

: >"$fixture/healthy"
run_supervisor heal
[ ! -e "$fixture/count" ] || {
	echo 'FAIL healthy desktop was restarted' >&2
	exit 1
}

rm -f "$fixture/healthy" "$fixture/count"
run_supervisor heal
[ "$(cat "$fixture/count")" -eq 1 ] || {
	echo 'FAIL recovered desktop was restarted more than once' >&2
	exit 1
}

rm -f "$fixture/healthy" "$fixture/count"
run_supervisor fail
[ "$(cat "$fixture/count")" -eq 3 ] || {
	echo 'FAIL unhealthy desktop was not retried once per cycle' >&2
	exit 1
}

if PATH=$fixture/bin:$PATH \
	ROG5_DESKTOP_START=$fixture/desktop-start \
	ROG5_DESKTOP_SUPERVISOR_INTERVAL=0 \
	ROG5_DESKTOP_SUPERVISOR_MAX_CYCLES=1 \
		"$target" >/dev/null 2>&1; then
	echo 'FAIL zero supervisor interval was accepted' >&2
	exit 1
fi

grep -Fq \
	'desktop-supervisor.sh /usr/local/sbin/rog5-desktop-supervisor' \
	"$installer"

if grep -Eq \
	'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|rm[[:space:]]+-rf|0[.]0[.]0[.]0:' \
	"$target"
then
	echo 'FAIL desktop supervisor contains a destructive or public-exposure path' >&2
	exit 1
fi

echo 'PASS desktop supervisor leaves healthy services alone and retries a missing browser without touching boot state'
