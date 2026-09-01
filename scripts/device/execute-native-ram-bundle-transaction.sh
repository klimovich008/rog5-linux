#!/bin/sh
# Survive loss of SSH while quiescing persistent state before one RAM kexec.
set -eu

PATH=/usr/sbin:/usr/bin:/sbin:/bin
LC_ALL=C
export PATH LC_ALL

[ "$#" -eq 4 ] || exit 2
root=/run/rog5-native-kexec
loader=$root/load-native-ram-bundle.sh
runtime_record=/run/rog5-persistent-state.runtime
block_class=/sys/class/block
rollback_required=0

log() {
	printf 'rog5-native-kexec-transaction: %s\n' "$*" \
		>/dev/kmsg 2>/dev/null || true
}

rollback() {
	status=$?
	trap - EXIT HUP INT TERM
	if [ "$rollback_required" -eq 1 ]; then
		log "transaction failed status=$status; requesting V11 restart"
		systemctl reboot --no-block >/dev/null 2>&1 || true
	fi
	exit "$status"
}
trap rollback EXIT HUP INT TERM

[ "$(id -u)" -eq 0 ]
[ -f "$loader" ] && [ ! -L "$loader" ] && [ -x "$loader" ]
"$loader" check "$@"

# From here onward the management path may disappear. This transient local
# service must either dispatch the already claimed target once or reboot V11.
rollback_required=1
systemctl stop rog5-tailscaled.service
systemctl stop rog5-persistent-state.service
[ ! -e "$runtime_record" ] && [ ! -L "$runtime_record" ]

count=0
for node in "$block_class"/sd*; do
	[ -e "$node/dev" ] || continue
	[ "$(cat "$node/ro")" -eq 1 ]
	count=$((count + 1))
done
[ "$count" -eq 117 ]
log 'persistent state stopped; all 117 UFS nodes read-only'

"$loader" execute "$@"
rollback_required=0
trap - EXIT HUP INT TERM

