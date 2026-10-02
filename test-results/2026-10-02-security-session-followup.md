# Security/session follow-up, 2026-10-02

Host-only work on the existing security branch, continuing `bf4ef1e0`.
No phone access, publication, branch changes or PIN-file reads. Installed
component status is unchanged. Sources were reviewed against the five private
October 2 audit reports named in the task and the unfinished review notes.

## Existing work retained

| Task | Existing commits and implementation |
|---|---|
| Manual desktop gate / supervision | `c5b3e5e`: restricted polkit, request broker, one-use grants, BindsTo, bounded hint reads and security hand-back |
| Session carry | `c5b3e5e`: outer 7 s timeout + 1 s kill grace, regular-file configuration reads, repeated same-session checks, ordinary hand-back in one systemd transaction |
| VNC UID isolation | `065e096e`: per-user Unix RFB sockets, restrictive permissions/umask, Unix backend and proxy, SSH forwarding instructions |
| Rootfs secrets / signatures / programs | `506f5631`: PIN hash only on stdin, log redaction, revoked/expired-signature rejection, nftables and required-command manifest |
| FastRPC / sensor sandbox | `27850538`: primary/type output accounting and adjacent handler fixes, daemon error propagation, ASan harness, dynamic user and restricted service |
| Cheap audit items | `bf4ef1e0`: Wi-Fi credential parsing, ALSA parent rule, extensionless syntax and secret checks, profile geometry, backup child reaping, benchmark quoting/status, brightness request authentication and SSH multiplexing, documentation corrections |

## Finished in this follow-up

- Read-only Phosh `org.gnome.Shell.Locked` property (0003, recipe 1.4), checked
  through its unique bus owner, executable and system/user service cgroup.
  Forged logind hints, unrelated bus owners and unavailable properties refuse
  authorization. Missing mode defaults to manual. Require active seat0.
- Cancel a relock even after grant consumption; retain source-session identity
  until removal, including events arriving after a healthy GNOME read. Query
  errors cannot count as session removal. Bound activation and retain the
  supervision deadline across unknown unit status. Require ready monitors.
- Notify/watchdog supervisor: a stalled check gets no heartbeat; a quiet event
  wait feeds the watchdog without repeating session/work probes. GNOME remains
  bound to its supervisor. Carry skips collection on supervisor failure so
  recovery does not wait for application shutdown.
- Bind carry restoration to the active destination unit's session leader and
  seat, beyond logind's preferred Display session.
- Reject non-atomic sensor publication before either tree moves; test the
  exchange-failure path using the real installer block.
- Refuse unsupported/incomplete Wi-Fi security and a derived WPA2 PSK for SAE;
  never silently import those as open networks. Stream rootfs archive hashing.
- Register new Phosh-probe and benchmark suites. Make brightness API tests
  exercise real HTTP parsing in memory; isolate the profile test's unused
  private selector dependency. Add transition and destination regressions.

## Validation

The affected suites are recorded below; no full tier or target boot is claimed.

| Check | Result |
|---|---|
| `python3 scripts/host/check-repository-static.py` | PASS, including staged new scripts |
| `git diff --check` | PASS |
| `test-rog5-desktop-mode-events.sh` / `test-rog5-desktop-mode-lock.sh` | PASS, real event loop with fake tools plus transition/error tests |
| `test-rog5-phosh-lock-state.py` | PASS: 5 checks; 1 declared optional compilation skip |
| Phosh 0003 against retained v0.57.0 sources | PASS: both hunks apply |
| `test-rog5-session-carry.py` | PASS: 22 tests |
| `test-rog5-shell.py` | PASS: 50 tests |
| `test-rog5-security-config.py` | PASS: private VNC sockets and ALSA rule |
| `test-hexagonrpcd-listener.py` | PASS: complete patched daemon build, ASan/UBSan malformed requests and real close handler; publication failure test |
| `test-rog5-wifi-networkmanager.py` | PASS: credential and downgrade regressions |
| `test-rog5-build-rootfs.py` | PASS: 12 tests; 5 user-namespace boot/seal tests skipped |
| `test-rog5-device-profile.py` | PASS: 15 tests |
| `test-rog5-bench.py` | PASS: 3 tests; SSH replaced with mocks |
| `test-rog5-brightness-lab.py` | PASS: 4 tests; no socket/network required |
| `test-backup-readonly-storage-inventory.py` | PASS: 2 tests; local fake child terminated/reaped; stderr ResourceWarning remains |
| `test-check-repository-static.py` | PASS: 5 tests |
| `test-prepare-recovery-runtime-bundle.py` | PASS: 10 tests |
| `test-rog5-install-userspace.py` | PASS: 5 tests; 2 user-namespace installation tests skipped |
| `test-repository-test-report.py` | PASS: 19 tests; both new suites also PASS through the registered runner |
| ARM64 BusyBox syntax of modified POSIX device scripts | PASS through retained BusyBox + qemu, no device execution |

The initial profile suite failed because importing an unrelated selector
composer required a missing private SHA256SUMS; its isolation now passes.
The initial brightness suite could not bind a local socket in this sandbox;
its real HTTP-handler regression now passes in memory. No skips mask those
security checks. GLib headers/gdbus-codegen and user namespaces are unavailable,
so generated-property compilation, a full ARM64 Phosh build, and rootfs
installation/boot tests remain pending. No kernel, initramfs or release build
was required or attempted. A full tier requires additional private artifacts
and the documented test environment.

[Upstream listener.c](https://github.com/linux-msm/hexagonrpc/blob/main/hexagonrpcd/listener.c)
was inspected: the accessible cached main view still shows the count gap.
Direct host DNS was unavailable, so latest remote HEAD is not certified.
The pinned archive stays patched locally; no upstream message was sent.

## Pending phone verification — later authorized hardware session only

Deploy the new Phosh package **together with** the userspace changes through
this project's reviewed deployment/bundle workflow first. This session did
not deploy them. Use the native production address and accepted identity
checks in that future session. Commands below run locally on the phone as
root unless marked otherwise; keep a working root SSH session for cleanup.

1. Check versions and dependencies:
   `pacman -Q phosh nftables wayvnc util-linux` and
   `test -x /usr/bin/nft && test -x /usr/bin/busctl && test -x /usr/bin/systemd-notify`.
   Phosh must be 0.57.0-1.4. Set `printf 'manual\n' > /var/lib/rog5/desktop-mode`,
   then `systemctl reload rog5-desktop-mode.service`.
   `nft list table inet rog5_firewall` must show the installed ruleset (check the
   table's name against `configs/firewall/rog5-firewall.nft` if changed).
2. On the lit Phosh PIN screen, query
   `busctl --address=unix:path=/run/user/1000/bus get-property org.gnome.Shell /org/gnome/Shell org.gnome.Shell Locked`:
   expect `b true`; after PIN unlock expect `b false`. Confirm the owner
   process with `busctl --address=unix:path=/run/user/1000/bus status org.gnome.Shell`
   and its `/proc/<PID>/exe` and `/proc/<PID>/cgroup`.
3. With a monitor attached, keep Phosh locked and run
   `systemctl start rog5-desktop-request.service`. Check
   `systemctl is-active rog5-gnome.service rog5-phosh.service`: GNOME inactive,
   Phosh active, PIN still required. In Phosh Console while unlocked, launch
   `(sleep 5; systemctl --no-ask-password start rog5-gnome.service) &`, lock
   before five seconds: direct unprivileged start must be denied.
4. Unlock normally and tap Desktop mode: GNOME must appear. Return with Phone
   mode, relock, and verify no automatic desktop starts while manual. Repeat
   requesting Desktop mode and immediately pressing Power to relock before
   handoff; inspect `journalctl -b -u rog5-desktop-mode -u rog5-gnome` for
   cancelled/refused transitions and verify no unlocked desktop appears.
   This is the required real conflict/PAM/session-removal ordering test.
5. From a working desktop, run
   `kill -STOP "$(systemctl show -p MainPID --value rog5-desktop-mode.service)"`.
   After at most the watchdog + stop grace (35 s, allow recovery startup),
   GNOME must stop and locked Phosh must return. Repeat with
   `systemctl stop rog5-desktop-mode.service`; check GNOME inactive, then
   `systemctl start rog5-desktop-mode.service` to restore supervision.
6. Open Firefox and Console; switch normally in both directions. Apps should
   reopen only after destination unlock. Relock during the restore delay and
   between launches: remaining apps must not reopen. Check
   `journalctl --user -b -u rog5-session-restore.service` as phone. Unavailable
   logind/lock reads are covered offline; any future live fault injection
   must use temporary supervisor-only command wrappers, not stop logind.
7. Reload/restart the changed user socket units and restart the headless
   desktop after deployment. As phone, use `rog5-desktop status` and confirm
   Unix endpoints with `ss -lx`; `ss -ltn` must show no phone-side 5900/5901.
   As root, test an unrelated UID:
   `setpriv --reuid=65534 --regid=65534 --clear-groups python3 -c 'import socket; s=socket.socket(socket.AF_UNIX); s.connect("/run/user/1000/rog5-vnc-phone.sock")'`.
   Expect PermissionError; repeat for `rog5-vnc-desktop.sock`. From the PC use
   `ssh -N -L 5900:/run/user/1000/rog5-vnc-phone.sock root@10.77.0.2` and
   `ssh -N -L 5901:/run/user/1000/rog5-vnc-desktop.sock root@10.77.0.2`;
   connect VNC clients to localhost:5900 / localhost:5901.
8. Deploy the patched hexagonrpcd and new sensor kit/unit together, then
   `systemctl restart rog5-sensors.service` and
   `systemctl show rog5-sensors.service -p User -p MainPID -p DynamicUser -p DevicePolicy`.
   Inspect `journalctl -b -u rog5-sensors.service` and SSC/IIO enumeration and
   live accelerometer/light samples using the existing sensor tooling. Confirm
   `/dev/fastrpc-sdsp` ownership matches the dynamic user, registry/config are
   readable, no seccomp/device denials occur, and readings still change when
   moving/lighting the phone. Stop/start the service once to verify node
   ownership cleanup and renewed access. Do not run malformed RPCs on hardware.

Rootfs PIN and signature checks use synthetic inputs offline. A future fresh
rootfs rehearsal must pass finalize's executable manifest and the namespace
boot/seal tests; never paste hashes or secret files into evidence.

## Deferred audit items and boundaries

Thermal emergency poweroff timing and kernel hardening need hardware/kernel
qualification. Firewall startup dependency/forwarding policy needs a separate
hotspot/container/Tailscale compatibility design. Touchpad overflow recovery,
Steam replacement journaling, personal GNOME-settings preservation, optional
framebuffer units, backup crash-resume journaling and historical post-wipe
recovery modernization are larger changes beyond the cheap-medium portion.
Status graphics, screenshot redaction and older SSH-alias documentation remain
separate documentation/publication work; no publishing or history rewriting
was authorized. Earlier documentation fixes describe the actual rollback
exclusions and historical automation boundary; they do not add database
backup protection. Rootfs checkpoints remain name-based.

The phone UID owns Phosh, its bus and user units. This patch prevents trusting a
bare forgeable logind hint; it does not provide a new isolation boundary against
arbitrary same-UID compositor replacement/ptrace. Actual PAM handoff timing,
watchdog dependency behavior, VNC permissions and SLPI compatibility require
the phone checks above before release.

## Checkout metadata

The sandbox mounts this worktree's Git metadata/index read-only despite the
writable common Git directory. The commit uses a separate index and Git
plumbing, writes objects in the permitted common object store, and advances
only `refs/heads/agent/fix-security-261002` with an old-value guard. The
protected original checkout index remains stale. After leaving this sandbox,
run `git read-tree HEAD` in this worktree **before further edits** to refresh
that index; it updates neither the working files nor other branch refs.
