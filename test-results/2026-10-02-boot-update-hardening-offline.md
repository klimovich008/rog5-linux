# Boot and update robustness: offline continuation, 2026-10-02

Branch: `agent/fix-boot-261002`. Continued from `3c39fcf9`, after reading
`git log --stat db5b9d4f..HEAD`, CLAUDE.md, development guidance and the six
supplied Sol audits. Implementation commit: `571d92731eabaca654842a54783e416cb088481c`.
No phone, network transport, partition, installed bundle or PIN-file access.
No push, rebase, or update of another branch/ref. This is source qualification,
not evidence that the installed main/fallback contain these changes.

## Already committed at handoff

| Commits | Finding addressed |
|---|---|
| `1eca6d90`, `3c39fcf9` | Overlay workdir crash residue predicate; watchdog backstop created before switch_root, retained SysRq FD and bounded restart2; module-publication and shell health checks; failed transactions always retain restore; download before snapshot, owned pacman-lock recovery, previous-snapshot retention and last-good rollback selection. |
| `65dd20a3` | Trial-state file fsync, atomic renameat2 initial publication, directory fsync; recovery of safe abandoned temporaries and legacy two-link publication; canonical record bytes; v4 ARM64 helper pin. |
| `8f29cf7f`, `c66425e0` | Durable RAM-trial claims and stage-setup cleanup; selected module provenance and build-output hashes, checked private package copy; structured DTB `requires` inheritance and enforced patch/config/module requirements, including --plan. `kernel_requires` remains explanatory text. |
| `64fe1206` | Ordered Requires+After suspend admission, marker-before-lock, failed admission veto, no pre-suspend xHCI unbind, s2idle and unsupported sleep-mode restrictions. |
| `38f872d8` | Full-charge precedence, Wi-Fi power-save retry/cache, USB-storage ExecStopPost, memory-mask error ownership and measurement cleanup status. |
| `863b128a`, `39bf65a3` | Persistent-state startup/publication failure propagation, wrong-root mount refusal, unreadable module-list refusal, target publication fixture corrections. |

Those were substantive implementations, with three important boot gaps still
present: module-copy failure was only logged; a fast startup unlock could beat
the health poll; RAM execution could commit a matching installed descriptor.
Update commitment also relied on ordering without propagating failed phone
health, and last-good publication could fail before pruning continued.

## Finished in 571d9273

- Module publication failure refuses init handoff through the bounded rollback
  path. Removed the diagnostic before force_rollback's reset work.
- The trusted embedded RAM loader appends `rog5.boot_origin=ram` after signature
  verification. Trial commitment skips before any trial-state call, including
  when its descriptor matches the installed pending primary. Wrapper result
  metadata records the actual appended command line.
- Phosh health observes the matching session locked, an enabled DSI connector
  with DPMS On, and nonzero actual backlight brightness. An early unlocked
  session gets one lock request, then must acknowledge LockedHint=yes. There
  can be one extra unlock during startup. The current-boot latch survives
  subsequent unlocks and a unit restart; malformed/hardlinked latches fail.
  Existing explicit headless and GNOME Mobile paths remain.
- A successful trial commit publishes root-owned current-boot health. The
  updater requires it when the trial kit exists, so an After-only dependency
  cannot discard package rollback after failed display/lock readiness.
- last-good must publish durably before pending is cleared and older snapshots
  are pruned. An injected publication failure preserves all recovery inputs.
- GMU insertion failure stops its consumers. Before msm, the loader waits up
  to about two seconds for the actual 3d6a000.gmu driver binding; modprobe
  success without that binding does not pass.
- Init now rejects root crypt passwords consistently with P2 and verify-root;
  removed obsolete Denial support. The phone user's Phosh PIN is separate.
- Source-repository registries, as well as bundle-inputs, must match the HEAD
  snapshot before packaging. Registry hashes also record external overrides.
- Extended the existing regression suites; registered the previously omitted
  power-measurement suite. Only the two actual local-TCP receiver tests declare
  a sandbox skip; claim fsync and partial stage-setup cleanup still execute.

## Validation

29 affected/support suites passed. Their logs and machine-readable inventory
are in `build/boot-audit-evidence/summary.json`. They report 435 unittest cases
(including two declared skips), plus the shell case matrices. Changed suites
were rerun after fixes; unrelated passing suites were retained.

| Check | Result |
|---|---|
| `python3 scripts/host/check-repository-static.py`, `git diff --check`, generated status/index checks | PASS |
| Real k113 ext4 + OverlayFS guest | 7 tests PASS, no skips; reset with overlay mounted, journal replay, writable recovery, intact upper and symlink target, whiteouts/directories/symlinks/FIFO/socket/device/hardlink residue, rejected deep trees and final `e2fsck -fn` PASS. |
| Trial commit under sealed ARM64 BusyBox | 24 tests PASS, 61.456 s; matching RAM descriptor, early unlock/re-lock acknowledgement, dark display, failed modules and stale/malformed latch cases. |
| Watchdog under sealed ARM64 BusyBox | 14 tests PASS, 37.708 s; blocked restart helper, blocking logger and missing old-root /dev/null after handoff. |
| Update under sealed ARM64 BusyBox | 79 tests PASS, 175.741 s; unchanged-package failure, owned-lock signal recovery, restore interruptions, failed phone health and failed last-good publication. Host run also PASS (42.722 s). |
| Real module-tree loader/publication replay | 16 tests PASS; failed copy/chmod/rename never publishes module readiness. |
| Platform, RAM launcher, bundle tool | 23, 17 and 23 tests respectively PASS; RAM launcher skips only its two loopback receiver tests because socket creation is prohibited. |
| Unsigned standalone archive composition | 9 tests PASS, 94.492 s, using retained V9 base and modules-7.2.7-r110 override; exact trial/update kit modes, current init, reproducible twin archive, hostile-package refusal and labelled-release composition. |
| Persistent state/slot-B/profile/recovery and other affected suites | PASS; includes root-account contract, publication cleanup and RAM-origin command-line behavior. |
| Full CI integration | BLOCKED at scratch socket preflight; all 114 selected suites marked BLOCKED. `build/boot-audit-ci-sandbox/summary.json` is not a passing CI report. |

The sandbox cannot run podman using its read-only /run/user directory. QEMU
8.2.2 and its libraries were instead read from the already retained Ubuntu
image layers, with a launcher written only in writable scratch. No container
storage was modified. The guest had `-nic none`; only a disposable regular-file
ext4 disk was written. Reproduce here with:

```sh
ROG5_OVERLAY_QEMU="$PWD/build/boot-audit-evidence/qemu-system-aarch64" \
  python3 scripts/device/test-overlay-workdir-residue.py
QEMU_LD_PREFIX=/tmp/rog5-audit-target \
ROG5_TEST_QEMU=/usr/bin/qemu-aarch64-static \
ROG5_TEST_BUSYBOX=/tmp/rog5-audit-target/bin/busybox \
  python3 scripts/device/test-production-trial-commit.py
ROG5_TEST_MODULE_TREE=/home/deck/.local/state/rog5-production-boot-20260923/modules-7.2.7-r110/module-root-complete.tar.gz \
  python3 scripts/device/test-standalone-production-tree.py
```

The BusyBox/musl files were extracted from the retained main-k113-d13 target
archive. No live init or module insertion ran on the host.

## Final self-review

Reviewed every initramfs delta from db5b9d4f, including inherited changes:
residue traversal does not follow symlinks or remove data and matches the
retained kernel's cleanup depth; post-mount writable verification stays intact;
the watchdog's independent process and descriptors survive handoff; reset
precedes diagnostics; publication failure cannot attest a partial module tree;
state cleanup remains armed through record publication; identity mismatches and
RAM origin cannot change persistent trial state; health evidence is boot-bound;
failed package transactions retain a durable restore; last-good failure cannot
prune the former root. Root credentials and GMU predecessor ordering were
cross-checked against their consumers. No new kernel/DT rebuild was necessary.

The original worktree admin directory/index is mounted read-only despite the
shared Git common directory being writable. Normal git add/commit failed.
Commits use a writable alternate index (`build/boot-audit-index`), commit-tree,
and a compare-and-swap update of **only** refs/heads/agent/fix-boot-261002. The
protected admin index was untouched. To inspect accurate status in this
sandbox, use `GIT_INDEX_FILE="$PWD/build/boot-audit-index" git status --short`.
After leaving the sandbox, `git read-tree HEAD` refreshes only the stale normal
index; do not use a worktree-destructive reset.

## Remaining native-phone verification (future session, not run here)

1. Rerun `bash scripts/host/test-repository-linux.sh ci` in the documented
   environment with Unix sockets and writable scratch. Refresh the normal Git
   index as above, then package new main and safe bundles from committed source,
   preserving existing accepted bundles. Start with compatible retained pairs:
   `python3 scripts/host/rog5-make-bundle.py --role main --kernel k113 --dtb d13 --plan` and
   `--role safe --kernel k111 --dtb d10 --plan`, then the same commands without
   --plan. Require all module-provenance/selection checks; do not relax a gate
   if an older build cannot provide the current selection. Rebuild the RAM
   wrapper too: an old wrapper does not append the origin marker.
2. Run one newly admitted RAM wrapper through production-ram-trial.py with a
   fresh claim/evidence directory. Require `rog5.boot_origin=ram` in
   /proc/cmdline and `SKIP RAM boot` in trial-commit logs. Record the installed
   trial helper's `state <trial_id> <primary_bundle>` before and after. A
   dedicated matching-pending case must also remain pending; obtain that state
   through an ordinary primary boot with commitment masked, not by editing the
   state record by hand. Never replay a consumed wrapper.

   The host controller commands are `python3 scripts/host/production-ram-trial.py
   to-fastboot --address 10.77.0.2 --mode helper` and then
   `ROG5_ALLOW_RAM_TRIAL=1 python3 scripts/host/production-ram-trial.py boot
   --wrapper <result.wrapper.path> --wrapper-sha256 <result.wrapper.sha256>
   --evidence <fresh-private-directory> --stage-receiver`. First confirm the
   reviewed `/run/initramfs/usr/libexec/rog5-reboot-bootloader` exists on that
   running target; `helper` is the controller's explicit bootloader-reset mode.
3. After separately authorized installation of the fresh main and fallback,
   perform two ordinary boots. On each inspect `systemctl status
   rog5-platform-modules.service rog5-production-trial-commit.service`,
   `readlink -f /sys/bus/platform/devices/3d6a000.gmu/driver`,
   `/run/rog5-production-modules.record`, `/run/rog5-production-trial-shell`
   and `/run/rog5-production-health`. Require the current release/boot ID,
   GMU driver rog5-gmu-bind, a visibly working locked OLED and healthy state.
   Unlock promptly once to exercise the bounded re-lock case; wait for the
   healthy log before power-key sleep. Restart the commit unit after unlocking
   to check latch persistence. Test GNOME Mobile/headless separately only if
   those configured modes are used.
4. For USB admission, hold `/run/rog5-usb-reconnect.lock` using a bounded
   `flock -x /run/rog5-usb-reconnect.lock sleep 65` in a supervised test. A
   normal systemctl suspend request must fail admission after about 50 s,
   without entering sleep. After release, request suspend again; verify
   [s2idle], resume, and side-port hub enumeration. Keep kernel logs and unit
   timestamps; there must be no pre-suspend xHCI unbind. Repeat a successful
   reconnect/suspend sequence with both device and hub roles.
5. Rehearse fallback using the existing commitment-mask runbook: one primary
   boot stays pending, the next boot selects the authenticated new fallback;
   restore the normal service configuration and install a fresh default as
   documented. Verify shared-overlay recovery and retained user data. An actual
   package restore should use a separately backed-up/disposable upper with a
   prepared restore plan; do not introduce an aborting package hook into the
   normal phone root just to repeat the already passing fault test.
6. On-device blocked-restart2/SysRq behavior and physical reboot-mode landing
   still require a purpose-built one-use RAM wrapper, a deliberately blocked
   helper, withheld acknowledgements and an available rescue operator. Expect
   SysRq b at watchdog expiry plus at most the 15 s grace. Do not induce a
   stuck kernel shutdown or crash-residue experiment on the installed shared
   overlay. These destructive/hardware failure cases were qualified in the VM,
   not claimed as phone evidence.

## Deliberately not expanded

The broader audit's arbitrary database-writer quiescing/application backups,
USB SIGKILL repair, standby experiment leases, GPU-probe evidence, direct
wrapper-packager pathname races, kernel-series dirty export, exact Wi-Fi DT
subtree validation and all-composer atomic publication remain separate work.
They require policy choices, multiple-artifact qualification or driver/hardware
changes beyond the selected conservative boot/update fixes. Audio and unrelated
C-driver findings were outside the requested update/trial-state portions. No
production signing, install, live trial or physical failure injection occurred.
