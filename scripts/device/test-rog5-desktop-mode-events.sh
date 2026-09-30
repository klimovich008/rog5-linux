#!/bin/bash
# Offline test of the event-driven rog5-desktop-mode: decisions of check()
# with mocked systemctl/loginctl/clock, the logind signal parser, and one run
# of the real event loop with fake udevadm/gdbus/systemctl/loginctl.
set -u
here=$(cd "$(dirname "$0")" && pwd)
t=$(mktemp -d)
trap 'rm -rf "$t"' EXIT
fail() { echo "FAIL $*"; exit 1; }
pass() { echo "PASS $*"; }

export ROG5_DM_LIB=1 ROG5_DM_STATUS=$t/status ROG5_DM_MODE_FILE=$t/mode ROG5_DM_RUN_DIR=$t/run
mkdir -p "$t/run"
. "$here/rog5-desktop-mode"
set +e

# --- mocks (state in files: command substitutions run in subshells) --------
st() { cat "$t/$1" 2>/dev/null; }
put() { printf '%s\n' "$2" >"$t/$1"; }
systemctl() {
	echo "systemctl $*" >>"$t/calls"
	case "$*" in
	"is-active rog5-gnome.service rog5-phosh.service") st G; st P ;;
	"stop rog5-gnome.service") put G inactive ;;
	"start rog5-phosh.service") put P active; put SESS "$(( $(st SESS) + 1 ))"; put LOCK yes ;;
	"start --no-block rog5-gnome.service") put G activating; put P inactive ;;
	"list-jobs --no-legend") st JOBS ;;
	esac
}
loginctl() {
	local n
	case "$*" in
	list-sessions*) echo "$(st SESS) 1000 phone seat0 tty7"; echo "99 0 root - -" ;;
	*" 99 -p Service"*) echo sshd ;;
	*"-p Service"*) echo phosh ;;
	*"-p State"*) echo active ;;
	*"-p LockedHint -p IdleHint") echo "IdleHint=$(st IDLE)"; echo "LockedHint=$(st LOCK)" ;;
	*"-p Id") [ "$2" = "$(st SESS)" ] || return 1; echo "$2" ;;
	*"-p LockedHint --value")
		n=$(( $(st NREAD) + 1 )); put NREAD "$n"
		# LOCK_AT: the phone locks on this LockedHint read (race tests)
		if [ -n "$(st LOCK_AT)" ] && [ "$n" -ge "$(st LOCK_AT)" ]; then echo yes; else st LOCK; fi ;;
	esac
}
T=1000
now_cs() { now=$((T * 100)); }

reset() {       # G P dp mode
	rm -f "$t"/calls "$t"/NREAD "$t"/LOCK_AT "$t"/run/*
	put G "$1"; put P "$2"; put status "$3"; put mode "$4"
	put SESS 2; put LOCK no; put IDLE no; put JOBS ""
	auto_done=0 nosess_since= dp_state= dp_since=0 sess_cache= seen_locked= EV=
	T=1000
}
called() { grep -qxF "systemctl $1" "$t/calls" 2>/dev/null; }
started_gnome() { called "start --no-block rog5-gnome.service"; }
unlock_cycle() { put LOCK yes; check; put LOCK no; }

# --- idle is not counted twice ----------------------------------------------
reset active inactive connected auto
check; called "stop rog5-gnome.service" && fail "idle: switched while active"
[ "$wait_s" = 60 ] || fail "idle: safety wait is $wait_s"
put IDLE yes; T=1001; check
called "stop rog5-gnome.service" && called "start rog5-phosh.service" || fail "idle: no hand-back on IdleHint=yes"
[ "$auto_done" = 0 ] || fail "idle: latch not cleared"
pass "IdleHint=yes hands back at once (GNOME's idle-delay is the only wait)"

# --- GNOME lock ---------------------------------------------------------------
reset active inactive connected auto
put LOCK yes; check
called "start rog5-phosh.service" && [ "$auto_done" = 0 ] || fail "GNOME locked"
pass "GNOME LockedHint=yes hands back"

# --- unplug and mode=off while GNOME is starting ------------------------------
reset activating inactive disconnected auto
check; T=1010; check
called "stop rog5-gnome.service" && fail "unplug: acted before OFF_AFTER"
[ "$wait_s" = 2 ] || fail "unplug: activating GNOME should be re-checked soon (wait $wait_s)"
T=1021; check
called "stop rog5-gnome.service" || fail "unplug ignored while GNOME is activating"
pass "unplug cancels an activating GNOME after OFF_AFTER"

reset active inactive disconnected auto
check; T=1005; check
[ "$wait_s" = 16 ] || fail "unplug: expected a wake-up at the deadline (16 s), got $wait_s"
pass "unplug debounce sleeps until its deadline"

reset activating inactive connected off
check
called "stop rog5-gnome.service" || fail "mode=off ignored while GNOME is activating"
pass "mode=off cancels an activating GNOME"

# --- manual start sets the once-per-plug latch --------------------------------
reset active inactive connected auto
check
[ "$auto_done" = 1 ] && [ -e "$t/run/auto-done" ] || fail "manual GNOME start did not set the latch"
put G inactive; put P active; put SESS 3; put LOCK yes; T=1100; check
put LOCK no; T=1200; check
started_gnome && fail "auto start after Phone mode without a replug"
put status disconnected; T=1201; check; T=1222; check
[ "$auto_done" = 0 ] && [ ! -e "$t/run/auto-done" ] || fail "latch not cleared after OFF_AFTER unplugged"
put status connected; T=1230; check; T=1236; check
started_gnome || fail "no auto start after a replug"
pass "manual start latches; replug re-arms"

# --- automatic start: lock/unlock, debounce, bounce ---------------------------
reset inactive active connected auto
check; started_gnome && fail "fresh session (never locked) started GNOME"
unlock_cycle; T=1003
handle_event D; check
started_gnome && fail "started before ON_AFTER"
[ "$wait_s" = 6 ] || fail "debounce wait is $wait_s, expected 6"
T=1007; handle_event D; T=1012; check
started_gnome && fail "HPD bounce did not restart the debounce"
T=1013; check
started_gnome || fail "no start after ON_AFTER of stable connection"
pass "locked -> unlocked + ON_AFTER stable connection starts GNOME; a bounce restarts the debounce"

reset inactive active connected auto
put LOCK yes; check; put LOCK no; put LOCK_AT 2; T=1100; check
started_gnome && fail "locked between the check and the start, GNOME started anyway"
pass "LockedHint is re-read right before the start (race closed)"

reset inactive active connected auto
unlock_cycle; T=1100
exec {EV}<>"$t/fifo" 2>/dev/null || { mkfifo "$t/fifo"; exec {EV}<>"$t/fifo"; }
echo "L 2 yes" >&"$EV"
check
started_gnome && fail "started with an unread event queued"
[ "$wait_s" = 1 ] || fail "queued events: wait $wait_s"
IFS= read -r -u "$EV" ev; exec {EV}>&-; EV=
pass "queued events are handled before a start"

reset inactive active connected auto
check
handle_event "L 2 yes"      # the lock was over before the state was read
T=1100; check
started_gnome || fail "a lock seen only as a logind signal did not count"
pass "a LockedHint=yes signal counts even if missed by the state read"

reset inactive active connected auto
check; handle_event "L 99 yes"; put SESS 99; T=1100; check
started_gnome && fail "a lock of a non-phosh session vouched for a switch"
pass "locks of other sessions are ignored"

reset inactive active connected manual
unlock_cycle; T=1100; check
started_gnome && fail "manual mode switched automatically"
printf manual >"$t/mode"; T=1200; check
started_gnome && fail "a mode file without a newline was read as auto"
pass "manual mode never switches automatically"

# --- no session ----------------------------------------------------------------
reset inactive failed connected auto
check; T=1005; check
called "start rog5-phosh.service" && fail "no session: acted early"
put JOBS "12 rog5-gnome.service start waiting"; T=1011; check
called "start rog5-phosh.service" && fail "no session: acted with a queued job"
put JOBS ""; T=1012; check; T=1022; check
called "start rog5-phosh.service" || fail "no session: Phosh not started after NOSESS_AFTER"
pass "no session for NOSESS_AFTER starts Phosh; queued jobs defer it"

# --- event parsing -------------------------------------------------------------
out=$(awk "$LOGIND_AWK" <<'EOF'
Monitoring signals from all objects owned by org.freedesktop.login1
The name org.freedesktop.login1 is owned by :1.5
/org/freedesktop/login1/session/_37: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.Session', {'LockedHint': <true>}, @as [])
/org/freedesktop/login1/session/_312: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.Session', {'LockedHint': <false>}, @as [])
/org/freedesktop/login1/session/c1: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.Session', {'IdleHint': <true>, 'IdleSinceHint': <uint64 1790737432357959>, 'IdleSinceHintMonotonic': <uint64 5000000>}, @as [])
/org/freedesktop/login1: org.freedesktop.login1.Manager.SessionNew ('8', objectpath '/org/freedesktop/login1/session/_38')
/org/freedesktop/login1/user/_1000: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.User', {'Display': <('7', objectpath '/org/freedesktop/login1/session/_37')>}, @as [])
EOF
)
exp=$(printf '%s\n' "R logind" "L 7 yes" "L 12 no" "E" "S")
[ "$out" = "$exp" ] || fail "logind parser: got [$out]"
handle_event "X gdbus monitor" 2>/dev/null && fail "a dead event source was not fatal"
pass "logind signal parser and dead-source handling"

# --- the real loop with fake tools ----------------------------------------------
b=$t/bin; mkdir -p "$b"; : >"$t/calls"
reset inactive active connected auto
put LOCK yes; put NREAD 0
cat >"$b/stdbuf" <<'EOF'
#!/bin/sh
shift; exec "$@"
EOF
cat >"$b/udevadm" <<'EOF'
#!/bin/sh
echo 'monitor will print the received events for:'
echo 'UDEV - the event which udev sends out after rule processing'
exec sleep 60
EOF
cat >"$b/gdbus" <<EOF
#!/bin/sh
echo 'The name org.freedesktop.login1 is owned by :1.5'
sleep 1; echo 'no' >"$t/LOCK"
echo "/org/freedesktop/login1/session/_32: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.Session', {'LockedHint': <false>}, @as [])"
exec sleep 60
EOF
{ echo '#!/bin/bash'; echo "t=$t"; declare -f st put systemctl loginctl
  echo 'n=${0##*/}; "$n" "$@"'; } >"$b/systemctl"
cp "$b/systemctl" "$b/loginctl"
chmod +x "$b"/*
PATH=$b:$PATH ROG5_DM_LIB= timeout 20 bash "$here/rog5-desktop-mode" >"$t/out" 2>&1 &
pid=$!
for _ in $(seq 1 40); do started_gnome && break; sleep 0.5; done
started_gnome || { cat "$t/out"; fail "event loop: no GNOME start after the unlock signal"; }
grep -q "phone unlocked -> GNOME" "$t/out" || fail "event loop: no log line"
put mode off; kill -USR1 "$pid"
for _ in $(seq 1 20); do called "stop rog5-gnome.service" && break; sleep 0.5; done
called "stop rog5-gnome.service" || { cat "$t/out"; fail "event loop: reload (mode off) not handled"; }
kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
pass "event loop: unlock signal -> GNOME after ON_AFTER; reload -> mode off -> Phosh"

# a dead event source ends the switcher (systemd restarts it) at once
cat >"$b/gdbus" <<'EOF'
#!/bin/sh
echo 'The name org.freedesktop.login1 is owned by :1.5'
EOF
chmod +x "$b/gdbus"
PATH=$b:$PATH ROG5_DM_LIB= timeout 20 bash "$here/rog5-desktop-mode" >"$t/out" 2>&1; rc=$?
[ "$rc" = 1 ] && grep -q "gdbus monitor ended" "$t/out" || { cat "$t/out"; fail "dead source: rc $rc"; }
pass "a dead event source ends the switcher"

# the reload trap never blocks on a full event pipe
mkfifo "$t/full"; exec {EV}<>"$t/full"
head -c 70000 /dev/zero >&"$EV" 2>/dev/null & filler=$!
sleep 0.5
eval "$(sed -n "s/^\ttrap '\(.*\)' USR1$/trap_cmd() { \1; }/p" "$here/rog5-desktop-mode")"
declare -f trap_cmd >/dev/null || fail "trap command not found"
timeout 5 bash -c "EV=$EV; $(declare -f trap_cmd); trap_cmd"; rc=$?
[ "$rc" != 124 ] || fail "reload trap blocked on a full pipe"
kill "$filler" 2>/dev/null; exec {EV}>&-; EV=
pass "the reload trap does not block on a full pipe"
echo PASS rog5-desktop-mode events
