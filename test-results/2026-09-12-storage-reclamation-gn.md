# Build storage reclamation and pinned GN, 2026-09-12

Reclaimed **8,786,944,000 bytes net** by archiving and verifying inactive kernel
intermediates, then removing their uncompressed copies. Approximately 14 GiB is
now free. The pinned GN tool was acquired and executed; the latest real offline
GN graph check reaches a specific **missing ARM64 sysroot** failure. Engine
compilation and phone operation remain NOT RUN.

Six complete August build directories were selected: `kernel-clean-a` through
`kernel-clean-d` under `rog5-contained-local-write-kernel-20260814-r1`, and
`kernel-clean-a`/`kernel-clean-b` under `rog5-local-write-kernel-20260814-r1`.
Their retained source mapping, configuration and final outputs were checked.
The selection contains only regular `.o`, `built-in.a` and `.tmp_vmlinux*`
intermediates, with no hardlinks. It excludes final kernels, modules, DTs,
configuration, symbol maps and source trees. Other roots with unresolved
container-relative source paths, hardlinks or incomplete final outputs were
left unchanged. The original dirty repository, all worktrees, stock/rescue
files and protected evidence were preserved.

All **23,280 selected files** were streamed into six compressed archives.
Before removal, each archive's member count, names, sizes, modes and complete
SHA-256 contents matched the originals. Input inode/size/link/timestamp checks
refused drift, accessible-process/mount checks guarded current use, and archive
files and receipts were flushed before removal. Final `vmlinux`, unstripped
symbols, Image, System.map, Module.symvers and `.config` hashes remained unchanged.
The archives occupy 3,596,407,396 bytes and retain the exact removed contents.
No historical result or sealed evidence file was rewritten.

The first verification failed before removing any input: the reused regular-file
hash helper seeks to offset zero, which is invalid for a streaming tar member.
A non-seeking hash loop fixes that interface mismatch. Five fixtures cover real
compressed-stream verification, non-seekable input, wrong hashes, missing members
and extra members. The existing archive was independently verified and resumed
only from its unconsumed ARCHIVED phase; it was not recompressed. The failure
log, original script and pre-resume receipt remain retained.

The six completed archival/removal cycles took **145.805 seconds** in aggregate;
this excludes the first compression that preceded the failed verifier. The five
focused fixtures passed in **0.020 seconds**. Peak resource limits were 768 MiB
RAM, no swap and one zstd compression thread; the 3 GiB reserve was retained.
No repository implementation changed, so an unrelated kernel rebuild or full
CI repeat was unnecessary. The final metadata checker regressions passed all
19 cases in 1.880 seconds.

The retained full-sync recipe still requires 80 GiB at startup. That guard was
not lowered and the old engine job was not restarted. Smaller explicit
build-tool dependency steps fit within current capacity. The bounded directory
usage survey is not a complete host inventory: its broad state scan hit its
60-second deadline and some protected directories were unreadable. Names or
lack of open handles alone were not used as grounds for removal.

Flutter DEPS pins GN revision `81b24e01531ecf0eff12ec9359a555ec3944ec4e`.
The retained CIPD client matches the checksum in pinned depot_tools:
`341314febc2b0e447914a20a3b845eb5052957451b30ed27b6221e8ddf9e0ed0`.
A public version lookup resolved the immutable instance
`zTMMtPTg2OXILKOlg3mOpTN_0BMIlS2-Inyd2LxR2FQC` of `gn/gn/linux-amd64`.
That exact instance was deployed only into the private host build-tool cache.
The cached package's SHA-256 independently matches its instance identifier:
`cd330cb4f4e0d8e5c82ca3a583798ea5337fd01308952dbe227c9dd8bc51d854`.
GN's executable SHA-256 is
`c6be2b6774aa536bbeef8f2c2c793f52fa4c27f883c7a01d4260653b0a71e0cf`;
it reports `2285 (81b24e01531e)`. Attestation metadata was retained, but its VSA
signatures were not independently verified. No system package or phone image
was installed.

The first real GN graph invocation failed because `vpython3` was unavailable
in its container environment. The second used the retained depot-tools cache
but reached its 120-second deadline while the interpreter manager tried to
export an uncached virtualenv package with networking disabled. The exact
container was cleaned up and subsequently confirmed absent. Both FAIL results
remain recorded.

A bounded, isolated, network-enabled single-script preflight then populated the
interpreter cache and executed the actual directory check successfully. Its
`False` result established that the ARM64 sysroot directory was absent. This
preflight does not establish complete interpreter or dependency closure. A third
GN invocation, with one worker and networking disabled, failed promptly at the
explicit missing-sysroot assertion in `build/config/sysroot.gni`. Source mounts
were read-only. The release ARM64 argument bytes remained unchanged throughout.

Next is the pinned ARM64 sysroot archive and installer under
`engine/src/build/linux/sysroot_scripts/`. Verify their source/hash and storage
cost before provisioning the dependency, then rerun the real offline graph.
GN graph success, compilation, matching engine/ICU/AOT, native session and all
physical results remain unqualified. The old 80 GiB full-sync entrypoint is not
required merely to acquire one bounded dependency.

Source HEAD stayed `871f876b7a2aa47010d85d02d6f74b731924b56a`, tree
`8b5932da7904abbfd272763abf712a356034e206`, throughout execution. The coordinator
utilities are retained privately with exact hashes; later Git changes record
qualification, status and lessons only. [Qualification JSON](2026-09-12-storage-reclamation-gn-qualification.json)
contains commands, per-test timings, archive manifests, tool identities, logs and
all failure references. Final commit/tree and changed files are in private
completion evidence. Two inventory sets were added while preserving all previous
465 sets: historical recovery archives and the active GN host tool.

For restoration, extract the relevant archive into a **new empty directory**,
verify each file against its retained manifest, and select any restoration
explicitly. Do not unpack blindly over an existing build. The inventory and
private receipts map each archive to its original root and record all hashes.

Accepted server/rescue, headless S06/R01 FAIL, the mobile acceptance contract,
authenticated Arch payload, Denial native binaries, ARM64 engine arguments,
kernel/DT/module artifacts, signed candidate/fallback, installed qualification
and consumed claims are unchanged. No phone operation, protected-storage
mutation, signing, admission, claim consumption or new candidate occurred.
Every mobile physical row remains **NOT RUN**.
