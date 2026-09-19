# Retained hardware database integration — 2026-09-19

**Cache admission and guest consumption pass; the complete VM remains FAIL.**
Device initialization and PAM succeeded, Denial produced two frames/page flips,
but portal startup returned 124 and the outer 300-second VM deadline expired.
Phone physical qualification remains NOT RUN. No phone operation, signing,
candidate, admission/claim consumption, installation or protected-storage
mutation occurred. S06/R01 FAIL and all historical results remain unchanged.

## Source and changes

Starting commit `13c758a353c855326dea7415bf232000c22193e5`, tree
`68911f4a1deb9b3026b446fec178811485306b57`. Initial implementation
`7e5fd7f9a8d84cfd59d202c2dcd03c56a2f73012`; final executable/test source
`8cd7b08fce0bebd2a5d38fec95de7f01bf2dc028`, tree
`d258d7cc7711be6cef89a55f90c39700aa95264a`. Documentation/provenance publication
is a later revision, not the VM execution source. Community audit additions are
the separate `eb20cd43` commit.

- `scripts/host/stage-qemu-hwdb-cache.py` authenticates the retained generator,
  successful generation/query, tools, original/mapped runtime tree, cache header
  and bytes. It refuses existing databases/custom inputs and unsafe destinations.
- `tools/qemu-virtio-drm/logind-linker-cache.sh` shares the existing atomic
  transaction between linker and hardware databases. The hwdb consumer must
  answer the synthetic modalias before its narrow generator guard and marker
  are published. Failures/interruption clean owned outputs; input is read-only.
- `tools/qemu-virtio-drm/logind-boot.sh` explicitly stops setup on cache failure,
  preserving failure even when a subshell EXIT trap bypasses the parent ERR trap.
- `scripts/host/test-qemu-logind.py` adds optional `--hwdb-cache`, records its
  identity and uses the existing read-only `/run/payload` mount. It also refuses
  output beneath either retained runtime before creating directories.
- New `test-qemu-hwdb-cache.py` and `test-logind-hwdb-cache.py` exercise these
  functions. The existing linker admission test follows the new boot dispatcher.
  `configs/repository-tests.json` and `test-repository-linux.sh` declare both
  suites mandatory with existing bounded worker/deadline policy.

No `.updated` bypass, service mask, readiness relaxation, kernel/Denial/Flutter
rebuild or phone policy change was introduced. The cache remains VM-only.

## Regressions and checks

The original-runtime output regression failed before the fix: the real runner
created a directory inside a temporary retained-runtime fixture. It now refuses
that path before mutation. No actual retained runtime was used for this failure.

The first integration attempt exposed a real packaging error: placing the
13,996,390-byte cache in initramfs hit the existing 8 MiB file limit during cpio
(SIGXFSZ/-25). It failed after 58.346s of harness work; **guest execution NOT RUN**.
The fix stages large data on the existing read-only payload mount. A regression
uses a 14 MB fixture and the actual bounded cpio executor; the final compressed
initramfs is 218,601 bytes. The size limit is unchanged. An older linker test's
literal dispatcher reference was updated; its initial failure is retained.

Final focused checks: 23 host admission/assembly cases, 15 guest transaction
cases, 21 existing linker-transaction cases and 18 linker-admission cases pass
(0.127s, 0.822s, 0.813s and 0.098s respectively). The new suites also pass under
Python -O (0.265s and 0.916s including process startup). All 113 existing runner
cases passed in 22.372s before the payload-placement correction and run again
within the final integrated tier. These are host fixtures, not systemd or phone
hardware qualification.

Initial frozen active tier: 111 PASS in 179.840s. After the demonstrated
packaging failure and correction, final frozen tier: **111 PASS, 0 FAIL,
0 BLOCKED, 0 SKIPPED, 255 NOT_SELECTED**, 180.971s; 430.5 MiB peak, no swap.
Three declared optional historical subchecks remain SKIPPED. These are executed
local tests, not imported GitHub CI results. No unchanged integrated tier was
repeated merely for documentation publication.

The retained cache SHA-256 is
`f08f47c0b7054020ad7671e78d85b4d0633a4a88887f06e61e63085505484655`.
Full original/mapped runtime admission and staging took 15.380s. The actual
matching ARM64 `systemd-hwdb`, under qemu-user in an isolated namespace, queried
the cache from `/etc/udev/hwdb.bin` successfully in 0.067s. This is a synthetic
database lookup, not a USB-device operation. No regeneration was needed.

## Actual generic ARM64 VM

One guest boot ran after the packaging correction. Same kernel, Denial/Flutter,
session archive, single-threaded TCG with two guest CPUs, resource limits,
network isolation and read-only runtime. The command adds only the admitted
cache and a fresh output; the previously qualified EXIT journal fix is also
present. Four existing executable inputs intentionally differ from the previous
VM; 34 match. All 41 current inputs and the original/mapped runtime bytes and
metadata pass post-run verification. The owned container is absent afterward.

Guest cache setup passed. Its exact systemd unit condition result was not
separately captured; do not claim a measured 75-second boot improvement from
the preceding cold rebuild. Device readiness passed from boottime 187.35 to
193.65 (6.30s bracket around the unchanged eight-second command budget). PAM
opened the mobile session. These observations do not establish why the previous
device wait failed.

Denial's terminal counters report two raster frames, two output page flips and
two delivered vsyncs over 34.259s. The 25-second service-start command returned
124 after a reported 26 seconds. Neither application mapped; app switching,
app release and text entry remain NOT RUN. Overall VM **FAIL_TIMEOUT** at
300.018s; harness 357.046s, wrapper 357.118s. Normal Power down was not observed
before termination; successful full cleanup is not claimed.

The corrected supervisor EXIT journal ran successfully: 6,183 bytes, status 0,
not truncated. It records document-portal startup at monotonic 256.899 and
Started at 271.415; GTK backend and main portal start at 260.715/260.871 but
have no Started event before shutdown around 288.4. This narrows the unresolved
portal boundary. Journal receipt times are not exact command-cutoff timestamps.

One RCU self-stall occurred before the systemd banner, even with single-threaded
TCG. Recreating Image from the retained vmlinux using the recorded objcopy flags
produces exactly the executed Image. Its trace maps through `prep_new_page`,
`get_page_from_freelist` and the user page-fault path. This is symbolized VM
evidence, not proof of an allocator defect, cache causality, or a phone problem.

## Next action and improvement

Use the retained monotonic portal journal and exact-image RCU trace to isolate
VM scheduling/page-allocation delay and portal readiness before another run.
Do not increase deadlines, retry unchanged, or attribute this to phone hardware.
The final EXIT journal is now observed in the VM, superseding its earlier
NOT RUN limitation without rewriting that historical result.

Cache reuse must pass through the real packaging path at realistic size: a tiny
copy fixture missed the cpio limit. The new bounded-cpio regression closes that
gap. Keep large caches on the existing read-only payload mount, copy only into
guest RAM, and publish a suppression marker only after the actual consumer
succeeds. Runtime-output guards must precede directory creation, even when later
authentication would reject the mutation.

The previous goal turn was progress (requested community/source audit). This
turn implemented and qualified cache reuse, repaired two demonstrated host
issues and obtained later-stage VM evidence; the native-phone goal remains
active and incomplete. Exact commands, source/artifact identities and retained
failure references are in the [qualification JSON](2026-09-19-hwdb-cache-integration-qualification.json).
Raw VM evidence remains under `rog5-hwdb-integration-20260919-r1` and `-r2`
in private local state.
