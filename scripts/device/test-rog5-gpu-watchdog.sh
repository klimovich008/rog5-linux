#!/bin/bash
# Offline test of rog5-gpu-watchdog: a fake kernel log (a regular file in
# /dev/kmsg record format), fake msm parameters, sysrq and reboot command.
set -u
here=$(cd "$(dirname "$0")" && pwd)
t=$(mktemp -d)
pid=
trap '[ -z "$pid" ] || kill -- -"$pid" 2>/dev/null; rm -rf "$t"' EXIT
fail() { echo "FAIL $*"; [ -f "$t/out" ] && sed 's/^/  | /' "$t/out"; exit 1; }
pass() { echo "PASS $*"; }

seq_n=100
rec() {                 # append one kernel record
	seq_n=$((seq_n + 1))
	printf '3,%s,%s,-;%s\n SUBSYSTEM=platform\n' "$seq_n" "$((seq_n * 1000))" "$1" >>"$t/kmsg"
}
params() {             # failures recovering [recoveries] [inits_ok]
	printf '%s\n' "$1" >"$t/p/gpu_init_failures"; printf '%s\n' "$2" >"$t/p/gpu_recovering"
	printf '%s\n' "${3:-0}" >"$t/p/gpu_recoveries"; printf '%s\n' "${4:-100}" >"$t/p/gpu_inits_ok"
}
setup() {
	rm -rf "$t/p" "$t/kmsg" "$t/sysrq" "$t/rebooted" "$t/out"
	mkdir -p "$t/p"; : >"$t/kmsg"; : >"$t/sysrq"
	params 0 N
}
run() {                 # run the daemon in the background
	setsid env ROG5_GPUWD_PARAMS=$t/p ROG5_GPUWD_KMSG=$t/kmsg ROG5_GPUWD_SYSRQ=$t/sysrq \
	ROG5_GPUWD_GRACE=2 ROG5_GPUWD_CONFIRM=1 ROG5_GPUWD_FORCE_AFTER=1 \
	ROG5_GPUWD_REBOOT_CMD="touch $t/rebooted" ROG5_GPUWD_FALLBACK=inline "$@" \
		bash "$here/rog5-gpu-watchdog" >"$t/out" 2>&1 &
	pid=$!
	sleep 1.5
}
stop() { kill -- -"$pid" 2>/dev/null; wait "$pid" 2>/dev/null; }
waitfor() {             # $1 = seconds, then a test command
	local n=$(( $1 * 4 )); shift
	while [ "$n" -gt 0 ]; do "$@" && return 0; sleep 0.25; n=$((n - 1)); done
	return 1
}

# --- a kernel without 0152: nothing to watch -----------------------------------
setup; rm -rf "$t/p"
ROG5_GPUWD_PARAMS=$t/p ROG5_GPUWD_KMSG=$t/kmsg timeout 10 bash "$here/rog5-gpu-watchdog" >"$t/out" 2>&1; rc=$?
[ "$rc" = 0 ] && grep -q "kernel without patch 0152" "$t/out" || fail "no parameters: rc $rc"
pass "without the 0152 parameters the daemon exits 0"

# --- the 2026-10-01 13:32 sequence: GMU dead, GPU never back -> reboot ---------
setup
rec "adreno 3d00000.gpu: [drm:a6xx_irq [msm]] *ERROR* old hang before start"
run
grep -q "GPU error" "$t/out" && fail "a record from before the start counted"
rec "rog5-gmu-bind 3d6a000.gmu: [drm:a6xx_gmu_set_oob [msm]] *ERROR* Timeout waiting for GMU OOB set GPU_SET: 0x0"
params 1 Y 1 100
rec "adreno 3d00000.gpu: [drm:recover_worker [msm]] *ERROR* 06060001: hangcheck recover!"
rec "rog5-gmu-bind 3d6a000.gmu: GMU watchdog expired"
waitfor 12 test -e "$t/rebooted" || fail "dead GPU: no reboot"
[ "$(grep -c "GPU error" "$t/out")" = 1 ] || fail "one health check per incident expected"
grep -q "Timeout waiting for GMU OOB" "$t/out" || fail "the first error is not logged"
waitfor 10 grep -qx wsub "$t/sysrq" || fail "sysrq sequence: $(cat "$t/sysrq")"
stop
pass "GMU OOB timeout + watchdog, GPU still dead after GRACE+CONFIRM: sysrq w, reboot, then s/u/b"

# --- a recovered GPU (normal app hang) only logs -----------------------------------
setup; run
params 0 Y
rec "adreno 3d00000.gpu: [drm:recover_worker [msm]] *ERROR* 06060001: hangcheck recover!"
sleep 1; params 0 N
waitfor 8 grep -q "GPU recovered" "$t/out" || fail "recovery not reported"
sleep 2
[ -e "$t/rebooted" ] && fail "rebooted although the GPU recovered"
stop
pass "a GPU that recovers within GRACE is only logged"

# recovered between the two reads
setup; run
params 2 N
rec "adreno 3d00000.gpu: [drm:msm_gpu_hw_init [msm]] *ERROR* gpu: hardware init failed: -110 (2 in a row)"
waitfor 8 grep -q "checking again" "$t/out" || fail "no second read"
params 0 N
waitfor 5 grep -q "GPU recovered" "$t/out" || fail "late recovery not seen"
[ -e "$t/rebooted" ] && fail "rebooted although the GPU recovered before the second read"
stop
pass "a GPU back by the confirming read is not rebooted"

# two short recoveries that happen to overlap both samples are not one dead GPU
setup; run
params 0 Y 5 100
rec "adreno 3d00000.gpu: [drm:recover_worker [msm]] *ERROR* 06060001: hangcheck recover!"
waitfor 8 grep -q "checking again" "$t/out" || fail "no second read"
params 0 Y 6 101
waitfor 5 grep -q "recovering again" "$t/out" || fail "a second recovery was taken for the same one"
[ -e "$t/rebooted" ] && fail "rebooted on two separate recoveries"
stop
pass "two separate recoveries at the two samples do not count as a dead GPU"

# inits that failed at both samples with a success in between do not count
setup; run
params 3 N 2 100
rec "adreno 3d00000.gpu: [drm:msm_gpu_hw_init [msm]] *ERROR* gpu: hardware init failed: -110 (3 in a row)"
waitfor 8 grep -q "checking again" "$t/out" || fail "no second read"
params 1 N 3 101
waitfor 5 grep -q "recovering again" "$t/out" || fail "an init success between the samples was missed"
[ -e "$t/rebooted" ] && fail "rebooted although an init succeeded between the samples"
stop
pass "an init success between the samples is not a dead GPU"

# a recovery that never ends (the 13:32 deadlock without 0152's fix) is
setup; run
params 0 Y 7 100
rec "rog5-gmu-bind 3d6a000.gmu: GMU watchdog expired"
waitfor 12 test -e "$t/rebooted" || fail "stuck recovery: no reboot"
stop
pass "one recovery running at both samples reboots"

# an unreadable kernel log ends the daemon (systemd restarts it)
setup; rm -f "$t/kmsg"
ROG5_GPUWD_PARAMS=$t/p ROG5_GPUWD_KMSG=$t/kmsg timeout 10 bash "$here/rog5-gpu-watchdog" >"$t/out" 2>&1; rc=$?
[ "$rc" = 1 ] || fail "unreadable kmsg: rc $rc"
pass "an unreadable kernel log is an error, not a silent stop"

# a log that exists but cannot be read (cat fails at once every time) ends it too
setup; rm -f "$t/kmsg"; mkdir "$t/kmsg"
ROG5_GPUWD_PARAMS=$t/p ROG5_GPUWD_KMSG=$t/kmsg timeout 30 bash "$here/rog5-gpu-watchdog" >"$t/out" 2>&1; rc=$?
[ "$rc" = 1 ] && grep -q "reader ended" "$t/out" || fail "permanently failing kmsg read: rc $rc"
pass "a kernel log that keeps failing to read ends the daemon"

# odd configuration values: leading zeros, junk; a SYSRQ path with a space
setup; mkdir -p "$t/sys rq"; : >"$t/sys rq/trigger"; params 1 N 1 5
setsid env ROG5_GPUWD_PARAMS=$t/p ROG5_GPUWD_KMSG=$t/kmsg ROG5_GPUWD_SYSRQ="$t/sys rq/trigger" \
	ROG5_GPUWD_GRACE=02 ROG5_GPUWD_CONFIRM=x ROG5_GPUWD_FORCE_AFTER=01 ROG5_GPUWD_FALLBACK=inline \
	ROG5_GPUWD_REBOOT_CMD="touch $t/rebooted" bash "$here/rog5-gpu-watchdog" >"$t/out" 2>&1 &
pid=$!
waitfor 20 grep -qx wsub "$t/sys rq/trigger" || fail "odd values / spaced path: $(cat "$t/sys rq/trigger" 2>&1)"
grep -q "checking again in 10 s" "$t/out" || fail "junk CONFIRM did not fall back to 10"
stop
pass "durations with leading zeros or junk and a SYSRQ path with a space work"

# --- log-only mode and a dead GPU at start ------------------------------------------
setup; params 4 N 1 10; run ROG5_GPUWD_ACTION=log
waitfor 8 grep -q "not rebooting" "$t/out" || fail "log mode: no report"
grep -q "GPU unhealthy at start" "$t/out" || fail "dead at start not noticed"
[ -e "$t/rebooted" ] && fail "log mode rebooted"
stop
pass "a GPU dead at start is checked; ROG5_GPUWD_ACTION=log never reboots"

# unrelated kernel messages are ignored
setup; run
rec "msm_dpu ae01000.display-controller: [drm] DP sink @20ms: 200:41"
rec "usb 1-1: new high-speed USB device number 3 using xhci-hcd"
sleep 1
grep -q "GPU error" "$t/out" && fail "an unrelated message started a check"
stop
pass "unrelated kernel messages are ignored"
echo PASS rog5-gpu-watchdog
