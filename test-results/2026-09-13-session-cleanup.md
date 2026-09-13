# VM shutdown and client exit repair — 2026-09-13

**Normal VM shutdown is repaired; the combined Denial session still FAILS because both clients hit their deadlines.**
The final combined run recorded22 raster frames/page flips,14 delivered vsyncs,
two configured native clients, Foot124, Mousepad124 and requested compositor
stop143. Systemd completed swap/loop/DM teardown and normal poweroff without
the previous SIGBUS. No phone evidence or responsiveness/input PASS is implied.

Start `7b9aead86ae1e8e9d5c0b287e79b9381d9e123a2`, tree `f93edf3bff9975e3b2755794848c10d07ec6bc1c`.
Frozen implementation `44167bfa9d278c61798481b1dc1fe6218668f150`, tree `4aef55ef41c07c841e6f9de2d1adb265672e1ddd`.
Subsequent publication changes evidence/status only.

| Actual run | Result | Seconds |
| --- | --- | --- |
| Retained passing logind-only bytes, only SMP1→2 | PASS authentication/devices/cleanup/poweroff |76.842 |
| First staging-only fixture | FAIL before intended control: missing source guard |2.106 |
| Corrected staging-only control, no PAM/compositor/apps | FAIL same shutdown SIGBUS |75.915 |
| Same retained bytes, fatal-register diagnostics | FAIL; fault address and registers captured |74.689 |
| Exception trace | FAIL; libmount instruction-page fault identified |72.360 |
| Early ordinary alias unmount | FAIL EBUSY; alias not removed, later SIGBUS |76.668 |
| Lazy-only alias detach | PASS normal systemd shutdown |74.411 |
| Final frozen combined Denial/PAM/logind run | FAIL clients124; normal shutdown PASS |199.141 |
| Client-status regressions before repair | Expected4 failed assertions in2 methods |0.032 |
| Executable-view regressions before repair | Expected6 failed assertions in4 methods |0.020 |
| Final focused runner suite |18 PASS |0.761 |
| Frozen integrated active tier |{'PASS': 97, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255} |137.279 |

Three declared optional subchecks remain SKIPPED and are individually reported.
No mandatory selected suite skipped. VM attempts total2 PASS/6 FAIL; these counts
include the clearly labelled preparation failure and EBUSY attempt. Their raw
receipts remain unchanged. Overall session failure is not overwritten by poweroff.

The exception trace reports `IABT (lower EL), ESR0x82000007`, level3 translation
fault at `libmount.so.1.1.0` offset0x204a0. The exact packaged ELF maps this to
`mnt_table_parse_swaps`, whose first instruction is a register-only conditional
branch. The caller return address maps to systemd-shutdown immediately after
its indirect call through `sym_mnt_table_parse_swaps`. Thus an instruction-page
fault is established; the last “Deactivating swaps” message was not proof of a
swap-operation failure. Guest memory exhaustion was not observed.

The temporary `/run/original-bin` bind aliases the same live9P filesystem as
the root. Exact pinned kernel source shows that MNT_FORCE calls the superblock
umount_begin hook, and9P begins disconnecting that shared session, rejecting
non-clunk requests with EIO. The packaged shutdown ELF also has a forced-unmount
call path. Exact runtime flags were not traced, so that mechanism remains a
source-supported explanation rather than a syscall observation.

Ordinary early unmount failed EBUSY because services still hold executable
references through the alias. Lazy detachment preserves those references while
removing the owned alias from the namespace before forced shutdown cleanup.
The paired exception/treatment initramfs comparison differs by exactly one
`umount --lazy /run/original-bin` command; the treatment and final combined run
both power off normally. No force option, root-filesystem unmount, version
change, prefetch workaround or new kernel was used. This is a VM fixture repair,
not a phone shutdown fix, and historical S06/R01 remain FAIL.

The production fixture now tracks canonical restoration and alias detach as
separate completed stages. EXIT cleanup preserves the original failure code
and never repeats an already-completed stage. Executable host regressions use
the real shell decisions with mount commands stubbed; they do not pretend to
supply actual mount semantics. The VM controls supply that separate evidence.

Client teardown now records waits even if kill reports an exited child, rejects
early exit0 and deadline124, and still reaps the other owned processes. The final
run confirms both client timeouts, replacing the earlier unverified hypothesis.
Timeout values were not increased. The native clients configure but do not
survive until the intentional stop; no complete local-session cleanup PASS.

Independent source/log inspection identifies the next prerequisites: RAM GTK
caches are passed to direct clients but not activated user services. AT-SPI and
portals explicitly abort for missing schemas. Use a bounded explicit allowlist
with the retained dbus-update-activation-environment --systemd helper, and verify
the user-manager values before startup. Separately, document-portal logs missing
/dev/fuse and the exact generic kernel has CONFIG_FUSE_FS unset. A successful
modprobe unit did not prove device availability. Namespaces/modules/BPF/audit
and tmpfs ACL remain separate generic-kernel limits. Do not hide these failures
by disabling services or increasing client deadlines.

Changed implementation files:

- `scripts/host/test-qemu-logind-runner.py`
- `tools/qemu-virtio-drm/logind-denial.sh`
- `tools/qemu-virtio-drm/logind-session.sh`

Publication appends one private fixture set (519 total), updates the existing
combined-VM pointer and generates current status. Previous518 sets, unsigned
payload pointer, signed fallback, headless/mobile contracts, consumed claims
and historical current-state body are preserved. The Denial/Flutter binaries
and archive remain unchanged. No new GitHub CI or phone-kernel result is claimed.

[Qualification JSON](2026-09-13-session-cleanup-qualification.json) includes
exact commands, per-step times/statuses, source and artifact identities, kernel
and ELF analysis, before/after controls, memory snapshot and JSON/JUnit hashes.
All owned containers are terminal and absent. Host disk reserve remains3GiB.
No phone operation, phone candidate, signing/admission/claim or protected-storage
mutation occurred. Physical rows remain NOT RUN. The native-phone goal remains
active and incomplete.
