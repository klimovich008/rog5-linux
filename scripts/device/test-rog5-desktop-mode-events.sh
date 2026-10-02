#!/bin/bash
# Offline test of the event-driven rog5-desktop-mode: decisions of check()
# with mocked systemctl/loginctl/clock, the logind signal parser, and one run
# of the real event loop with fake udevadm/gdbus/systemctl/loginctl.
set -u
here=$(cd "$(dirname "$0")" && pwd)
t=$(mktemp -d)
# a forked child killed before it execs runs the EXIT trap too: only the test shell cleans up
trap '[ "$BASHPID" = "$$" ] || exit 0; inhibit_stop 2>/dev/null; rm -rf "$t"' EXIT
fail() { echo "FAIL $*"; exit 1; }
pass() { echo "PASS $*"; }

export ROG5_DM_LIB=1 ROG5_DM_STATUS=$t/status ROG5_DM_MODE_FILE=$t/mode ROG5_DM_RUN_DIR=$t/run
export ROG5_DM_ASOUND=$t/asound ROG5_DM_INHIBITORS_CMD=mock_inhibitors
mkdir -p "$t/run" "$t/asound/card0/pcm0p/sub0"
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
	# Conflicts=: starting Phosh stops GNOME in the same transaction
	"start rog5-phosh.service") put G inactive; put P active; put SESS "$(( $(st SESS) + 1 ))"; put LOCK yes ;;
	"reload rog5-desktop-mode.service") ;;
	"show -p MainPID --value rog5-desktop-mode.service") echo "${SWITCHER_PID:-$$}" ;;
	"start --no-block rog5-phosh.service") put G inactive; put P active ;;
	"start --no-block rog5-gnome.service") put G activating; put P inactive ;;
	"list-jobs --no-legend") st JOBS ;;
	"show -p MainPID --value rog5-phosh.service")
		# rog5-phosh's main process leads the current phone session
		if [ "$(st P)" = active ]; then echo "${PHOSH_PID:-100$(st SESS)}"; else echo 0; fi ;;
	"show -p MainPID --value rog5-gnome.service")
		# rog5-gnome's main process leads GNOME's session (GNOME_PID: another)
		if [ "$(st G)" = active ]; then echo "$(st GNOME_PID || true)" | grep . || echo "100$(st SESS)"; else echo 0; fi ;;
	esac
}
loginctl() {
	local n
	case "$*" in
	list-sessions*) [ -z "$(st EXTRA)" ] || echo "$(st EXTRA) 1000 phone seat0 tty7"
		echo "$(st SESS) 1000 phone seat0 tty7"; echo "99 0 root - -" ;;
	*" 99 -p Service"*) echo sshd ;;
	*"-p Service"*) echo phosh ;;
	*"-p Leader --value") echo "100$2" ;;
	*"-p State"*) echo active ;;
	*"-p LockedHint -p IdleHint") [ -z "$(st PROPFAIL)" ] || return 1
		echo "IdleHint=$(st IDLE)"; echo "LockedHint=$(st LOCK)" ;;
	*"-p Id") [ "$2" = "$(st SESS)" ] || return 1; echo "$2" ;;
	*"-p LockedHint --value")
		n=$(( $(st NREAD) + 1 )); put NREAD "$n"
		# LOCK_AT: the phone locks on this LockedHint read (race tests)
		# FAIL_AT: this LockedHint read fails (logind busy, bus error)
		[ "$n" != "$(st FAIL_AT)" ] || return 1
		if [ -n "$(st LOCK_AT)" ] && [ "$n" -ge "$(st LOCK_AT)" ]; then echo yes; else st LOCK; fi ;;
	esac
}
T=1000
now_cs() { now=$((T * 100)); }
# work in progress: PROCS (pgrep -l lines), SINKS (pactl list short sinks),
# INH (busctl ListInhibitors reply), FULL (fullscreen window), GINH (GNOME
# idle inhibitor app id), asound status file
pgrep() { echo "pgrep $*" >>"$t/calls"; [ -s "$t/PROCS" ] && cat "$t/PROCS"; }
user_cmd() { case $1 in pactl) [ -s "$t/SINKS" ] && cat "$t/SINKS" ;; *) return 1 ;; esac; }
mock_inhibitors() { if [ -s "$t/INH" ]; then cat "$t/INH"; else echo 'a(ssssuu) 0'; fi; }
x11_fullscreen() { [ -s "$t/FULL" ] && cat "$t/FULL"; }
gnome_idle_inhibitor() { [ -s "$t/GINH" ] && cat "$t/GINH"; }
gnome_idle_left() { [ -s "$t/LEFT" ] && cat "$t/LEFT"; }
spawn_inhibitor() { echo "inhibit $1" >>"$t/calls"; (exec sleep 300) </dev/null >/dev/null 2>&1 & inhibit_pid=$!; }
inhibiting() { [ -n "$inhibit_pid" ] && kill -0 "$inhibit_pid" 2>/dev/null; }

reset() {       # G P dp mode
	inhibit_stop
	rm -f "$t"/calls "$t"/NREAD "$t"/LOCK_AT "$t"/FAIL_AT "$t"/EXTRA "$t"/run/* "$t"/GNOME_PID "$t"/PROPFAIL \
		"$t"/PROCS "$t"/SINKS "$t"/INH "$t"/FULL "$t"/GINH "$t"/LEFT
	echo closed >"$t/asound/card0/pcm0p/sub0/status"
	busy= eval_at=
	put G "$1"; put P "$2"; put status "$3"; put mode "$4"
	put SESS 2; put LOCK no; put IDLE no; put JOBS ""
	auto_done=0 nosess_since= dp_state= dp_since=0 sess_cache= seen_locked= EV=
	lock_sess= locked_at=0 lock_ready= unlock_ok= PHOSH_PID= req= sup_bad= grant_sess= SWITCHER_PID=
	T=1000
}
called() { grep -qxF "systemctl $1" "$t/calls" 2>/dev/null; }
started_gnome() { called "start --no-block rog5-gnome.service"; }
# a hand-back is one start of Phosh (no separate stop of GNOME)
handed_back() { called "start rog5-phosh.service"; }
# lock, confirm the lock LOCKED_MIN later, unlock (T advances by 2 s)
unlock_cycle() { put LOCK yes; check; T=$((T + 2)); check; put LOCK no; }

# --- idle is not counted twice ----------------------------------------------
reset active inactive connected auto
check; handed_back && fail "idle: switched while active"
[ "$wait_s" = 60 ] || fail "idle: safety wait is $wait_s"
put IDLE yes; T=1001; check
handed_back || fail "idle: no hand-back on IdleHint=yes"
[ "$auto_done" = 0 ] || fail "idle: latch not cleared"
pass "IdleHint=yes hands back at once (GNOME's idle-delay is the only wait)"

# --- work in progress keeps GNOME from idling (2026-10-01 13:32 regression) ---
# Steam's shader pre-compilation ran 10 min without input; the idle hand-back
# killed it with the session. The switcher must hold GNOME awake instead.
reset active inactive connected auto
put PROCS "4711 fossilize_replay"; check
inhibiting || fail "work: no GNOME idle inhibitor while fossilize_replay runs"
grep -q "^inhibit running: fossilize_replay" "$t/calls" || fail "work: inhibitor reason"
[ "$wait_s" = 60 ] || fail "work: re-check in $wait_s s, expected BUSY_POLL"
put IDLE yes; T=1001; check
handed_back && fail "work: GNOME idle while fossilize_replay runs was handed back"
inhibiting || fail "work: inhibitor dropped while idle and busy"
[ "$(grep -c '^inhibit ' "$t/calls")" = 1 ] || fail "work: inhibitor spawned more than once"
rm -f "$t/PROCS"; T=1002; check
handed_back || fail "work: no hand-back once the work ended"
inhibiting && fail "work: inhibitor left running after the hand-back"
pass "fossilize_replay keeps GNOME from idling; an idle GNOME is handed back only once it ends"

reset active inactive connected auto
put PROCS "9001 reaper"; put IDLE yes; check
handed_back && fail "a Steam game (reaper SteamLaunch) was handed back"
grep -q "pgrep -u phone -l -f -- fossilize_replay|SteamLaunch" "$t/calls" || fail "work: pgrep pattern"
pass "a game under Steam (SteamLaunch) keeps GNOME"

# not idle: the work is re-evaluated only every BUSY_POLL seconds
reset active inactive connected auto
echo "state: RUNNING" >"$t/asound/card0/pcm0p/sub0/status"
check; inhibiting || fail "audio: no inhibitor while ALSA playback runs"
echo closed >"$t/asound/card0/pcm0p/sub0/status"
T=1030; check; inhibiting || fail "audio: re-evaluated before BUSY_POLL"
T=1061; check; inhibiting && fail "audio: inhibitor kept after playback stopped"
handed_back && fail "audio: switched while GNOME was not idle"
pass "audio playback holds the inhibitor; it is dropped after BUSY_POLL without work"

# work that starts after a check is still seen PRE_IDLE s before GNOME idles
reset active inactive connected auto
put LEFT 35; check
[ "$wait_s" = 25 ] || fail "pre-idle: next look in $wait_s s, expected 25 (35 - PRE_IDLE)"
put PROCS "4711 fossilize_replay"; T=1010; check
inhibiting && fail "pre-idle: evaluated before its time"
T=1025; check
inhibiting || fail "pre-idle: work that started after the last look got no inhibitor before the idle-delay"
pass "work is checked again PRE_IDLE s before GNOME's idle-delay runs out"

reset active inactive connected auto
put SINKS "57	bluez_output.00_11_22.1	PipeWire	s16le 2ch 48000Hz	RUNNING"; put IDLE yes; check
handed_back && fail "Bluetooth playback (RUNNING sink) was handed back"
put SINKS "57	bluez_output.00_11_22.1	PipeWire	s16le 2ch 48000Hz	SUSPENDED"; T=1001; check
handed_back || fail "a suspended sink counted as playback"
pass "a RUNNING PipeWire sink (Bluetooth too) counts as audio playing"

reset active inactive connected auto
put FULL "steam_app_1493710 0x1a00003"; put IDLE yes; check
handed_back && fail "a fullscreen window was handed back"
pass "a focused fullscreen X11 window keeps GNOME"

reset active inactive connected auto
put GINH "org.mozilla.firefox"; check
inhibiting && fail "GNOME's own inhibitors are GNOME's business while it is not idle"
put IDLE yes; T=1001; check
handed_back && fail "an idle GNOME with an app idle inhibitor was handed back"
pass "GNOME app idle inhibitors are honoured when GNOME reports idle"

# logind idle inhibitors: block or block-weak, never the switcher's own
reset active inactive connected auto
put INH 'a(ssssuu) 3 "sleep" "rog5-server" "keep-server-workloads-running" "block" 0 8398 "idle" "rog5-desktop-mode" "rog5-desktop-mode: running: fossilize_replay" "block" 1000 77 "idle:sleep" "phone" "rog5-desktop-mode: audio" "block-weak" 1000 78'
put IDLE yes; check
handed_back || fail "the switcher's own (mirrored) inhibitor or a sleep inhibitor kept GNOME"
reset active inactive connected auto
put INH 'a(ssssuu) 2 "sleep" "rog5-server" "x" "block" 0 1 "handle-lid-switch:idle" "mpv" "Playing \"a b\"" "block-weak" 1000 2'
put IDLE yes; check
handed_back && fail "a logind idle inhibitor (block-weak) was ignored"
[ "$busy" = 'idle inhibitor: mpv: Playing "a b"' ] || fail "logind inhibitor reason: [$busy]"
put INH 'a(ssssuu) 1 "idle" "mpv" "x" "delay" 1000 2'; T=1001; check
handed_back || fail "a delay-mode idle inhibitor kept GNOME"
pass "logind idle inhibitors (block, block-weak) keep GNOME; delay mode and the own one do not"

# a lock still hands back at once (GNOME has no unlock), work or not
reset active inactive connected auto
put PROCS "4711 fossilize_replay"; check; inhibiting || fail "setup"
put LOCK yes; T=1001; check
called "start rog5-phosh.service" || fail "GNOME lock with work running was not handed back"
inhibiting && fail "inhibitor left after the lock hand-back"
pass "a GNOME lock hands back even with work running; the inhibitor goes with it"

# GNOME stopping or gone (Phone mode, unplug) drops the inhibitor
reset active inactive connected auto
put PROCS "4711 fossilize_replay"; check; inhibiting || fail "setup"
put G deactivating; T=1001; check
inhibiting && fail "inhibitor left while GNOME stops"
put G active; T=1002; check; inhibiting || fail "setup 2"
put G inactive; put P active; T=1003; check
inhibiting && fail "inhibitor left after GNOME ended"
pass "the inhibitor ends with GNOME"

# --- GNOME lock ---------------------------------------------------------------
reset active inactive connected auto
put LOCK yes; check
called "start rog5-phosh.service" && [ "$auto_done" = 0 ] || fail "GNOME locked"
called "stop rog5-gnome.service" || fail "GNOME locked: the desktop was not stopped first"
pass "GNOME LockedHint=yes hands back, stopping GNOME first (no carry delay on screen)"

reset active inactive connected auto
put IDLE yes; check
called "start rog5-phosh.service" || fail "idle: no hand-back"
called "stop rog5-gnome.service" && fail "idle: separate stop (rog5-session-carry would see no switch)"
pass "the idle hand-back is one start of Phosh (apps are carried)"

# --- unplug and mode=off while GNOME is starting ------------------------------
reset activating inactive disconnected auto
check; T=1010; check
handed_back && fail "unplug: acted before OFF_AFTER"
[ "$wait_s" = 2 ] || fail "unplug: activating GNOME should be re-checked soon (wait $wait_s)"
T=1021; check
handed_back || fail "unplug ignored while GNOME is activating"
pass "unplug cancels an activating GNOME after OFF_AFTER"

reset active inactive disconnected auto
check; T=1005; check
[ "$wait_s" = 16 ] || fail "unplug: expected a wake-up at the deadline (16 s), got $wait_s"
pass "unplug debounce sleeps until its deadline"

reset activating inactive connected off
check
handed_back || fail "mode=off ignored while GNOME is activating"
pass "mode=off cancels an activating GNOME"

# --- manual start sets the once-per-plug latch --------------------------------
reset active inactive connected auto
check
[ "$auto_done" = 1 ] && [ -e "$t/run/auto-done" ] || fail "manual GNOME start did not set the latch"
put G inactive; put P active; put SESS 3; put LOCK yes; T=1100; check; T=1102; check
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
put LOCK yes; check; T=1002; check; put LOCK no; put LOCK_AT 4; T=1100; check
started_gnome && fail "locked between the check and the start, GNOME started anyway"
pass "a relock seen by the re-read right before the start stops it"

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
started_gnome && fail "a lock seen only as a logind signal (never confirmed) counted"
pass "a lock seen only as a signal, never confirmed by a read, does not count"

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

# --- regression 2026-09-30 11:34 (r200 boot): locked at boot, USB/DP rebind --
# Replay of the boot: Phosh session 2 starts with LockedHint=no, phosh 0002
# publishes the lock, the reconnect helper's rebind sends drm uevents, logind
# adds/removes sessions, a reload arrives. Nobody unlocks: GNOME must not start.
reset inactive active connected auto
check                                   # fresh session, LockedHint=no
T=1001; put LOCK yes; handle_event "L 2 yes"; check
for i in 1 2 3 4 5 6 7 8 9 10; do T=$((1001 + i)); handle_event D; handle_event S; handle_event E; check; done
handle_event M; T=1030; check; T=1100; check; T=1500; check
handle_event "L 7 no"; handle_event "L 99 no"; T=1501; check   # other sessions' unlocks
started_gnome && fail "r200 replay: GNOME started from a locked phone"
pass "r200 boot replay (locked, rebind uevents, session churn, reload, other sessions' unlocks): no GNOME"

# a shell that publishes yes and then a wrong "no" right away (startup bug):
# the flip is ignored until the session is locked again
reset inactive active connected auto
check
T=1001; handle_event "L 2 yes"; handle_event "L 2 no"; put LOCK no
T=1100; check; T=1200; check
started_gnome && fail "a yes->no flip faster than LOCKED_MIN started GNOME"
T=1300; put LOCK yes; handle_event "L 2 yes"; check; T=1302; check
T=1310; put LOCK no; handle_event "L 2 no"; check
started_gnome || fail "a real lock/unlock after an ignored flip did not start GNOME"
pass "an unlock faster than LOCKED_MIN after the lock is ignored; a real one later counts"

# only one unlock per lock period: after a start and a hand-back, the new
# Phosh session must be locked and unlocked again
reset inactive active connected auto
unlock_cycle; T=1010; check
started_gnome || fail "setup: no start"
rm -f "$t/calls"; put G inactive; put P active; put SESS 3; put LOCK no; latch 0
T=1100; handle_event "L 2 no"; check; T=1200; check
started_gnome && fail "an old session's unlock vouched for the new session"
pass "an unlock is not reused for a later session"

# the session must be rog5-phosh's (its leader is the unit's main process):
# GNOME's session has Service=phosh too
reset inactive active connected auto
PHOSH_PID=4242; unlock_cycle; T=1100; check
started_gnome && fail "an unlock of a session that is not rog5-phosh's started GNOME"
PHOSH_PID=
pass "only rog5-phosh's own session can authorise a start"

# another Service=phosh session listed first (e.g. GNOME's, not closing yet)
# must not hide rog5-phosh's own session: its unlock still counts
reset inactive active connected auto
put EXTRA 5
unlock_cycle; T=1100; check
started_gnome || fail "a second Service=phosh session hid rog5-phosh's session"
rm -f "$t/EXTRA"
pass "rog5-phosh's session is found by its leader even with another phosh session listed first"

# an unreadable final re-read drops the lock history (no invented lock)
reset inactive active connected auto
unlock_cycle; put FAIL_AT 4; T=1100; check
started_gnome && fail "started although the final re-read failed"
T=1200; check; T=1300; check
started_gnome && fail "a failed re-read left an unlock that counted later"
pass "a failed lock-state read drops the history; the next start needs a new lock"

# a removed session forgets its history (the id must not carry it)
reset inactive active connected auto
unlock_cycle; handle_event "Q 2"; T=1100; check
started_gnome && fail "the history of a removed session id counted"
pass "a removed session forgets its lock history"

# --- no session ----------------------------------------------------------------
reset inactive failed connected auto
check; T=1005; check
called "start rog5-phosh.service" && fail "no session: acted early"
put JOBS "12 rog5-gnome.service start waiting"; T=1011; check
called "start rog5-phosh.service" && fail "no session: acted with a queued job"
put JOBS ""; T=1012; check; T=1022; check
called "start rog5-phosh.service" || fail "no session: Phosh not started after NOSESS_AFTER"
pass "no session for NOSESS_AFTER starts Phosh; queued jobs defer it"

# --- "Desktop mode" requests (the launcher) and the start grant -----------------
request() { now_cs; printf '%s\n' "$now" >"$t/run/request"; }
granted() { [ -f "$t/run/gnome-grant" ]; }

reset inactive active connected manual
unlock_cycle; T=1100; request; check
started_gnome && granted || fail "request: an unlocked phone's request did not start GNOME with a grant"
[ ! -e "$t/run/request" ] || fail "request: not consumed"
called "stop rog5-gnome.service" && fail "request: stopped GNOME"
pass "a Desktop mode request on an unlocked phone starts GNOME with a one-use grant (manual mode too)"

reset inactive active connected manual
put LOCK yes; check; T=1002; check; T=1100; request; check 2>"$t/err"
started_gnome && fail "request: a locked phone's request started GNOME"
granted && fail "request: grant written for a locked phone"
[ ! -e "$t/run/request" ] && grep -q "refused: the phone is not unlocked" "$t/err" || fail "request: locked refusal"
put LOCK no; T=1103; check
started_gnome && fail "request: a refused request was kept and honoured after the unlock"
pass "a request on a locked phone is refused and dropped (not kept for the unlock)"

reset inactive active connected manual
check; T=1100; request; check 2>/dev/null
started_gnome && fail "request: a never-locked session (LockedHint=no from the start) started GNOME"
pass "a request from a session that was never seen locked is refused"

reset inactive active connected manual
unlock_cycle; put LOCK_AT 4; T=1100; request; check 2>/dev/null
started_gnome && fail "request: a relock seen by the final re-read did not stop the start"
pass "a request meets the same LockedHint re-read right before the start"

reset inactive active connected off
unlock_cycle; T=1100; request; check 2>/dev/null
started_gnome && fail "request: honoured with desktop mode off"
reset inactive active disconnected auto
unlock_cycle; T=1100; request; check 2>/dev/null
started_gnome && fail "request: honoured without a display"
reset inactive active connected manual
unlock_cycle; T=1100; request; T=1111; check 2>/dev/null
started_gnome && fail "request: an expired request was honoured"
[ ! -e "$t/run/request" ] || fail "request: expired request kept"
reset inactive active connected manual
unlock_cycle; T=1100; echo 'x y' >"$t/run/request"; check 2>/dev/null
started_gnome && fail "request: a malformed request was honoured"
pass "requests are refused with mode off, without a display, after REQUEST_TTL and when malformed"

reset inactive active connected manual
( ROG5_DM_RUN_DIR=$t/run; REQUEST=$t/run/request; request_main ) || fail "request_main failed"
[ -s "$t/run/request" ] && called "reload rog5-desktop-mode.service" || fail "request_main: no request or reload"
pass "the launcher's request unit leaves a request and wakes the switcher"

# the gate in rog5-gnome.service: one fresh grant, one start
reset inactive active connected manual
gate() { ( gate_main ) >/dev/null 2>&1; }
gate && fail "gate: started without a grant"
now_cs; grant_write 2; gate || fail "gate: refused a fresh grant"
gate && fail "gate: a grant served two starts"
now_cs; grant_write 2; T=$((T + 61)); gate && fail "gate: accepted a stale grant"
T=1000; now_cs; printf '%s 2\n' "$((now + 500))" >"$t/run/gnome-grant"; gate && fail "gate: accepted a grant from the future"
ln -s /dev/null "$t/run/gnome-grant"; gate && fail "gate: accepted a symlink"
rm -f "$t/run/gnome-grant"
now_cs; grant_write 2; SWITCHER_PID=1; gate && fail "gate: accepted a grant from another (earlier) switcher"
SWITCHER_PID=
pass "rog5-gnome's gate needs a fresh grant from the running switcher and consumes it"

# a relock after the grant was written (Phosh still stopping) voids it
reset inactive active connected manual
unlock_cycle; T=1100; request; check
granted && started_gnome || fail "relock: setup"
handle_event "L 2 yes"
granted && fail "relock: the grant survived a lock signal of its session"
called "start --no-block rog5-phosh.service" || fail "relock: Phosh not put back"
reset inactive active connected manual
unlock_cycle; T=1100; request; check
put G activating; put P deactivating; put LOCK yes; T=1102; check 2>/dev/null
granted && fail "relock: the grant survived a locked re-read while GNOME was activating"
reset inactive active connected manual
unlock_cycle; T=1100; request; check
put G activating; put P deactivating; T=1102; check
granted || fail "relock: an unlocked session lost its grant"
pass "a relock between the grant and the gate voids the grant and puts Phosh back"

# supervision fails closed: GNOME without a readable lock state goes back
reset active inactive connected auto
put GNOME_PID 4242; check; T=1005; check
handed_back && fail "supervision: handed back before SUP_GRACE"
T=1010; check
handed_back || fail "supervision: GNOME kept without its own session for SUP_GRACE"
called "stop rog5-gnome.service" || fail "supervision: the desktop was not stopped first"
reset active inactive connected auto
put PROPFAIL 1; check; T=1009; check
handed_back && fail "supervision: handed back early on unreadable hints"
rm -f "$t/PROPFAIL"; T=1010; check; put PROPFAIL 1; T=1015; check
handed_back && fail "supervision: a good read did not reset the grace period"
T=1025; check
handed_back || fail "supervision: unreadable LockedHint/IdleHint kept GNOME"
pass "GNOME without its own session or readable hints for SUP_GRACE is handed back"

# --- event parsing -------------------------------------------------------------
out=$(awk "$LOGIND_AWK" <<'EOF'
Monitoring signals from all objects owned by org.freedesktop.login1
The name org.freedesktop.login1 is owned by :1.5
/org/freedesktop/login1/session/_37: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.Session', {'LockedHint': <true>}, @as [])
/org/freedesktop/login1/session/_312: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.Session', {'LockedHint': <false>}, @as [])
/org/freedesktop/login1/session/c1: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.Session', {'IdleHint': <true>, 'IdleSinceHint': <uint64 1790737432357959>, 'IdleSinceHintMonotonic': <uint64 5000000>}, @as [])
/org/freedesktop/login1: org.freedesktop.login1.Manager.SessionNew ('8', objectpath '/org/freedesktop/login1/session/_38')
/org/freedesktop/login1: org.freedesktop.login1.Manager.SessionRemoved ('7', objectpath '/org/freedesktop/login1/session/_37')
/org/freedesktop/login1/user/_1000: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.User', {'Display': <('7', objectpath '/org/freedesktop/login1/session/_37')>}, @as [])
EOF
)
exp=$(printf '%s\n' "R logind" "L 7 yes" "L 12 no" "E" "S" "Q 7")
[ "$out" = "$exp" ] || fail "logind parser: got [$out]"
handle_event "X gdbus monitor" 2>/dev/null && fail "a dead event source was not fatal"
[ "$(echo "The name org.freedesktop.login1 does not have an owner" | awk "$LOGIND_AWK")" = "X logind lost its bus name" ] ||
	fail "logind losing its name is not fatal"
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
sleep 3; echo 'no' >"$t/LOCK"
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
grep -q "phone unlocked (session 2) -> GNOME" "$t/out" || fail "event loop: no log line"
put mode off; kill -USR1 "$pid"
for _ in $(seq 1 20); do handed_back && break; sleep 0.5; done
handed_back || { cat "$t/out"; fail "event loop: reload (mode off) not handled"; }
kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
pass "event loop: unlock signal -> GNOME after ON_AFTER; reload -> mode off -> Phosh"

# real loop, r200-like boot: fresh session, lock published, a flip to "no"
# right after it, uevents from a rebind, nobody unlocks: no GNOME in 10 s
reset inactive active connected auto
cat >"$b/udevadm" <<'EOF'
#!/bin/sh
echo 'UDEV - the event which udev sends out after rule processing'
for i in 1 2 3 4 5; do sleep 0.3; echo 'UDEV  [45.0] change   /devices/platform/soc@0/ae00000.display-subsystem/drm/card1 (drm)'; done
exec sleep 60
EOF
cat >"$b/gdbus" <<EOF
#!/bin/sh
echo 'The name org.freedesktop.login1 is owned by :1.5'
sleep 1; echo yes >"$t/LOCK"
echo "/org/freedesktop/login1/session/_32: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.Session', {'LockedHint': <true>}, @as [])"
echo no >"$t/LOCK"
echo "/org/freedesktop/login1/session/_32: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.login1.Session', {'LockedHint': <false>}, @as [])"
exec sleep 60
EOF
chmod +x "$b/udevadm" "$b/gdbus"
PATH=$b:$PATH ROG5_DM_LIB= timeout 10 bash "$here/rog5-desktop-mode" >"$t/out" 2>&1; rc=$?
[ "$rc" = 124 ] || { cat "$t/out"; fail "event loop ended early: rc $rc"; }
started_gnome && { cat "$t/out"; fail "event loop: GNOME started after a yes->no flip nobody made"; }
grep -q "ignored, needs a new lock" "$t/out" || { cat "$t/out"; fail "event loop: the flip was not reported"; }
pass "event loop: a published lock followed at once by a stale unlock does not start GNOME"

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
inhibit_stop
echo PASS rog5-desktop-mode events
