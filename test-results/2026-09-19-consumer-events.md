# Six-consumer udev diagnostic — 2026-09-19

Generic ARM64 VM/offline work only. No phone operation, candidate, signing,
admission, claim consumption or protected-storage mutation. Physical NOT RUN;
ASUS slot A, signed fallback, server/rescue and historical S06/R01 FAIL preserved.

Starting commit1724de965a8681f794f540594634ca5020ddf7d1,
tree2071465f344a5135b639c70a7758829c972ddc19. Previous turn made progress:
original FUSE was late in one VM, inside the wait in the second, which still
failed. A later all-ready snapshot could not distinguish another late consumer
from an undispatched completion event. Pinned systemd source admits the latter
possibility but existing evidence did not establish it.

## Changed layer and checks

Source d655dcde64ee15bce4060ba4516d4cd45dfd658a,
tree1bbf027ad564a08cf4e9abf66746ba0f5409b46b changes only
`tools/qemu-virtio-drm/logind-session.sh` and its executable host regressions
in `scripts/host/test-qemu-logind-runner.py`.

The existing RAM-only debug rule now names the six exact consumers. Database
snapshots carry begin/end boottime observations. A2s pre-wait database-only
capture is retained before the unchanged8s initialization wait, with serialization
deferred until after failure observation. A bounded3s/100-line/16KiB journal
capture retains original consumer database/completion/broadcast/failure records
before the existing diagnostic FUSE retrigger. No property query, retry or
retrigger precedes admission. Diagnostic success never repairs a failed wait.

New debug and pre-wait work perturb scheduling: this is a diagnostic experiment,
not an isolated priority-performance comparison. Snapshot reads are sequential;
journal times are receipt observations and multicast send is not waiter dispatch.

Old source failed the six-consumer rule regression.26 final focused cases PASS
17.196s, including real query argv/filter matching, original wait status despite
journal errors/overflow/deadline, bounds, scratch cleanup and one-use retrigger.
Packaged ARM64 udevadm verify under QEMU user emulation accepted the rule file;
this is parser validation, not live udev or phone proof. Read-only review caught
serial-output delay and omitted error records; both corrected before freezing.

## Integrated and VM result

The one diagnostic VM at d655dcde fails overall in395.897096215s
(wrapper395.965728585s). Pre-wait database snapshot163.59→163.76 has tty1
present-empty and five other entries absent. The unchanged wait164.64→169.52
passes in4.88s. Therefore failure-only original-event capture and FUSE retrigger
are NOT RUN. This success does not explain or supersede earlier readiness FAILs.

PAM authentication, local nonroot session/seat/device access, portal services and
real FUSE mount pass. Portal start takes34s (CLOCK_MONOTONIC237.478373712 to
272.359676448). Both apps visibly render; the retained Mousepad editor and Foot
terminal screenshots were personally inspected. Observer and mapping/focus
protocol PASS, approved teardown true. Text entry and phone touch NOT RUN.

Foot exits0. Mousepad exits137 after the controlled close. Its timeout reports
TERM then KILL; close brackets311.62→314.10 BOOTTIME include transport/reaping,
not exact signal timestamps. Exact PID980 probe shows loaded and APP_RUN_BEGIN,
but no shutdown/sync/run-end/unref/destructor markers. Its last client protocol
messages destroy the toplevel, xdg_surface and wl_surface. This locates the
observed failure before the later probe boundaries, without proving its cause.
The65s app watchdog had not elapsed based on the recorded launch/close interval;
the normal-close path signals its timeout process, whose2s kill grace remains.

The fixture supervisor then exits142, PAM cleanup markers are absent. Source
reveals another independent budget contradiction: the Rust helper arms alarm140
before authentication, despite child190. Exit142 is consistent with SIGALRM;
there is no separately captured signal-delivery receipt. This cannot explain
away Mousepad137, already recorded before the supervisor exits.

Source correction c56abeeaf9ca39da446b351ca5afeab87dfb5eba, tree
0cd94bf97e8713f0e2e2488e42af2ccd84a63f41 changes the full alarm to225s,
inside outer230; child190 plus1s kill grace leaves a shared reserve for
authentication/PAM teardown. Nominal5s between alarm and outer timeout is not
a measured guarantee because their start times differ. Basic40/startup140 remain.
The regression compiles actual child AND alarm expressions with real runner cfg;
old140 fails140>=225.15 focused budget/cleanup cases PASS2.002s. Initial focused
attempts missed the recorded rustc wrapper PATH/TMPDIR and are retained as harness
errors, not pre-fix failures. Compiler stderr now appears in assertion failures.

The complete ARM64 helper compiles with -Dwarnings in6.931170982s,
SHA256 bffcf5eaa028c901de437953ad30f4934578097b9b0814c74305895308bcdddd,
564224B. Corrected alarm runtime and successful PAM/compositor cleanup NOT RUN.
No second VM executed after correction. Independent review found no further
fixed watchdog in the PAM process; seat-probe and app watchdogs remain distinct.

Normal guest poweroff passes the RCU-aware check; /var unmount FAIL retained.
No containers remain; original runtime bytes/metadata and all input hashes pass
post-run verification. Failed-session shutdown is not successful PAM or normal
compositor lifecycle proof. No phone operation or protected-storage mutation.

Next: bounded read-only task/syscall/FD observation during Mousepad close under
the existing2s grace, with owned identity and FIFO reader preservation. Do not
attribute missing shutdown markers to settings sync or unref. Keep the repaired
alarm separate, and avoid another unchanged expensive VM retry.

Frozen active tier111PASS,0FAIL/BLOCKED/SKIPPED,255NOT_SELECTED in185.631240071s; three declared optional historical subchecks SKIPPED. The diagnostic tier passed in186.414162149s, peak501.2MiB, zero swap; final tier resource totals remain in its terminal log. Full commands, source and artifact identities, per-step durations and diagnostic packets are retained in the qualification JSON and private records.
