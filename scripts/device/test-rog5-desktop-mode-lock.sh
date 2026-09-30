#!/bin/sh
# Mock test of the proposed lock tracking in rog5-desktop-mode.new.
set -u
here=$(dirname "$0")
sed -n '/^sess_cache= seen_locked=/,/^to_phosh()/p' "$here/rog5-desktop-mode" | sed '$d' >/tmp/ldm.$$
LOCK=no SESS=2 STATE=active
loginctl() {
	case "$1 $*" in
	*list-sessions*) echo "$SESS 1000 phone seat0 tty7" ;;
	*"-p Service"*) echo phosh ;;
	*"-p State"*) echo "$STATE" ;;
	*"-p Id"*) [ "$2" = show-session ] && [ "$3" = "$SESS" ] && echo "$SESS" || return 1 ;;
	*"-p LockedHint"*) echo "$LOCK" ;;
	esac
}
. /tmp/ldm.$$; rm -f /tmp/ldm.$$
ok() { if phosh_unlocked; then r=unlocked; else r=locked; fi; [ "$r" = "$1" ] && echo "PASS $2" || { echo "FAIL $2 (got $r)"; exit 1; }; }
LOCK=no; track_phosh_lock; ok locked 'fresh session with LockedHint=no (never seen locked): fail closed'
LOCK=yes; track_phosh_lock; ok locked 'locked'
LOCK=no; track_phosh_lock; ok unlocked 'locked -> unlocked'
SESS=5 LOCK=no; track_phosh_lock; ok locked 'new session after a handover: fail closed'
LOCK=yes; track_phosh_lock; LOCK=no; track_phosh_lock; ok unlocked 'new session locked -> unlocked'
