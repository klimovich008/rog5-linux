# Authenticated VM desktop services — 2026-09-13

**Activated desktop services and the document FUSE mount now PASS in the VM. The complete session remains FAIL because the forced Foot stop returned230.**
Denial recorded27 raster frames/page flips with no recorded render errors; both
native clients configured. Cache transfer and all four service states passed.
Mousepad returned0 and Denial143 after requested stop. The VM powered off
normally without panic; the failed /var unmount message remains evidence.
Complete PAM/session/scope cleanup did not qualify after the client failure.

This is a generic ARM64 VirGL VM qualification. Phone A660, OLED, touch, power,
and physical security remain NOT RUN. Historical headless S06/R01 stay FAIL.
No phone operation, new phone candidate, signing, admission, claim consumption,
or protected-storage mutation occurred. The native-phone goal remains incomplete.

Start `7d8fe9bf7b6c5e71ec5503972c6322f7bd012365`, tree `e723c8a7669cf8394563bd2ca7267ea834ec4583`.
Kernel builder source `f16c48b459862f3f249920d805c7e9d91ab6051d`, tree `8b7b07f15404d56465e75a57c4bd7b0d04206d12`.
Guest source `87d9289d3538421cc2c1f01a82259e87355bd470`, tree `bd68ed381774391fe35984774cb52c5057d41930`. Publication changes evidence/status/documentation only.

The new `virtio-session` profile adds builtin FUSE to the generic graphics VM
profile. It preserves the old smoke/virtio-drm profile selections and all phone
kernel configurations. The exact clean Linux source remains
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. The prior generic Image/config/System.map
were rehashed and unchanged. This is not an exact ROG5 board-build result.

The produced Image is 7,049,224 bytes, SHA256
`2b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc`.
The merged config SHA256 is
`23af1f7083bb5607f65904ab6d46a101c5d67fd73a6ae10dd868877db16870af`.
The config delta also records the FUSE-selected/default FS_IOMAP, FS_POSIX_ACL
and FUSE_PASSTHROUGH settings, with CUSE/VIRTIO_FS disabled.
Its build-state identity records exact source/tree, builder/contract hashes and
compiler/linker/tool hashes. No modules/vermagic were produced; release is7.1.4+.

The first build failed after658.957s: inherited RLIMIT_FSIZE=8MiB stopped ld.lld
writing vmlinux.o. A real container probe confirmed that limit. This is not
established as an LLVM or kernel defect. The first resume was refused in0.649s
because INCREMENTAL_BUILD=1 was omitted. The final unchanged-input resume used
the existing identity guard, a separate256MiB per-artifact cap and an8MiB streamed
log cap, and passed in27.584s. Memory2GiB/no swap, CPUs2, owned-container cleanup
and the3GiB free-disk guard remained enforced. Failed receipts are retained.

Guest startup now transfers only GSETTINGS_SCHEMA_DIR and XDG_DATA_DIRS into
both D-Bus/systemd activation environments, verifying exact user-manager values
before launch. A20-second bounded service start must yield four exact active
states: AT-SPI, document portal, GTK portal backend, desktop portal. A successful
findmnt query must report exactly the expected user doc mount with FUSE type.
Services are not disabled and client/PAM/VM deadlines are unchanged.

The retained authenticated fuse3 package supplies root:root04755 fusermount3;
its bytes match the materialized runtime, which deliberately stripped setuid.
The fixture restores only a checked RAM copy's package ownership/mode. It rejects
wrong sources/destinations, symlink replacement on repeat, ownership failures,
and missing device/helper prerequisites. No host runtime metadata is changed.

Two VM setup failures improved the regression: cp -as preserves /./ in symlinks,
so compare canonical existing destinations; and the minimal guest lacks cmp,
so use the already-required sha256sum. Tests now execute the actual symlink-farm
producer and the helper with a constrained command PATH. The initial manually
created-link fixture and host command environment missed those conditions.
The32.521s and33.662s failed VMs both powered off normally before Denial launch.
A private wrapper's missing retained-receipt path was corrected before any VM
or output directory started; it is not another guest run.

| Actual check | Result | Seconds |
| --- | --- | --- |
| Cache-activation regression before |10 failed assertions,4 methods |0.032 |
| Cache-activation suite after |22 PASS |0.809 |
| Service/mount regression before |12 failed assertions,2 methods |0.036 |
| Service/mount suite after |25 PASS |0.852 |
| FUSE-helper regression before |7 failed assertions,4 methods |0.023 |
| FUSE-helper suite after |30 PASS |1.111 |
| Real symlink-farm regression before |1 failure,6 methods |0.052 |
| Symlink-farm suite after |32 PASS |0.951 |
| Constrained runtime-command regression before |5 failures,7 methods |0.100 |
| Constrained helper after |7 PASS |0.116 |
| Final focused runner suite |33 PASS |0.992 |
| Kernel builder contract |PASS |0.415 |
| Complete frozen VM |FAIL Foot230; service/mount/render milestones PASS |193.432 |
| Final frozen integrated active tier |97 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED |137.931 |

Three declared optional subchecks remain SKIPPED; no mandatory selected suite
skipped. The earlier integrated runs passed on f16c48b/0de8c69d/df65180c in
163.794/141.582/140.172s; they preceded newly observed setup corrections and do
not substitute for final-source results. Starting integrated tiers while the VM
still found setup defects caused avoidable repetition. Future loops should finish
runtime prerequisite discovery first, then freeze and run the integrated tier.

The retained Foot manual documents230 as a Foot failure. [Upstream Foot1.28.0 source](https://codeberg.org/dnkl/foot/src/tag/1.28.0/main.c)
also has a specific forced-stop path that leaves the default failure code:
SIGTERM sets an aborted flag, direct teardown sends SIGHUP to the slave and
bypasses the callback that records normal child-exit status. This matches the
observed hangup message. The exact packaged ELF also retains the default-26
context value through that direct signal-teardown path (static correspondence);
the runtime branch was not traced. This does not justify accepting every230 result. Preserve
the failed run. Next qualify a normal terminal child exit with an explicit bounded
owned0600 FIFO stop token to a bounded real child shell. Require Foot0 and
terminal closure before compositor stop, keep the65-second watchdog and reject
124/230. Then require terminal/compositor/PAM and scope cleanup. Missing
RealtimeKit/PipeWire portal-feature warnings remain separate limitations.

The unsigned session archive remains SHA256
`1ff417307c96bac90977b64a143e1a81b535d94a03109ca967c40e9b1f269d0c`,
composition source4947e75d. Denial/Smithay/Flutter binaries are unchanged; this
turn did not rerun their compilation or modifier regressions. No GitHub CI run
is claimed. Runtime package authenticity is reused from the retained closure;
this turn compared exact fuse3 archive-member bytes, not all package signatures.

Verified retirement of twelve obsolete ignored host fixture duplicates reclaimed
276,381,696 allocated bytes (263.58MiB). Each had an identical retained durable
copy, no observed references/mounts/open handles, and separate single-link inode.
All original source, reports and manifests remain. The private restore map records
paths, hashes, modes and mtimes; the two canonical ignored artifact files must
remain retained. Six owner-read-only parents were temporarily made writable only
for this retirement, then restored. No unique project data was removed.

Changed source: `scripts/host/build-qemu-smoke-kernel.sh`,
`scripts/host/test-qemu-logind-runner.py`, `tools/qemu-virtio-drm/logind-denial.sh`,
`tools/qemu-virtio-drm/logind-denial-prepare.sh`, and relevant development docs.
Publication appends one fixture set (520 total), updates the existing combined
VM pointer and adds the distinct generic session-kernel identity. Prior519 sets,
unsigned payload/signed fallback pointers, headless/mobile contracts, consumed
claims and historical current-state body are preserved.

[Qualification JSON](2026-09-13-session-services-qualification.json) records
commands, identities, per-step durations, before/after evidence, JSON/JUnit
summaries, cleanup provenance and exact limitations. All raw evidence stays
private; no log result is silently promoted to phone proof.

Publication verification: metadata regressions5 PASS (0.934s), mobile-status
regressions8 PASS (0.022s), inventory coverage PASS520 sets/827 registered/177
tracked files with68 small tracked hashes checked, and generated status PASS.
The first metadata check caught a stale derived set_count519 after appending
set520; it was corrected and both affected checks passed. No validator weakened.
Large/private byte verification remains outside that inventory validator's scope.
