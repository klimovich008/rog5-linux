# Corrected Impeller engine: VM cleanup passes — 2026-09-12

**The corrected engine fixes the observed render-context cleanup failure in the
retained ARM64 VirGL VM.** The raster thread explicitly unbinds, main-thread
cleanup binds successfully, and cleanup ends with an unbind. No EGL_BAD_ACCESS
or new Impeller teardown error occurs. The full session still **FAILS** with six
backing-store errors, despite 48 raster frames and 48 page flips. This does not
qualify phone graphics, input or a complete mobile session.

The preceding turn was progress: source diagnosis, actual-destructor fault tests
and real ARM64 translation-unit compilation. This turn completes a separate full
engine link and executes the cleanup correction. The pending queued-render review
and IO resource-context lifetime remain separate; the renderer was not switched,
permissions were not enlarged, and fences were not bypassed.

## Exact source and artifact comparison

Start: `bea9c6148d29c2da20b855d64e12c8304ea5201a`.
Harness/frozen integrated source: `8d4f0a12ac651a5e4b7b1585b756f54b26de5a7c` (tree `e9d7e83de7bcb75f1836b3f470ecbf759319de03`).
Engine patch source: `27f1dedde6544cb2417d66ddaa32d6377701c923`, against engine
`d728e61e7d835e02c453c70ae9523a40f6c03215`.
The trace-enabled Denial binary remains from
`09a4d25a1b923347c6bdc97ba9af68a8362b8146`:
`84bbe77ce67eea3f784e6341337a4e5b7c37116aea5f3eb3bc68411509d52304`.

Ninja's expanded link command records 3264 explicit object/archive inputs. There
are no thin archives hiding external members. Exactly one object is substituted:
the previously compiled corrected Impeller surface object. Cache and source are
read-only; output, response file and logs are private and separate. Link options
remain the retained options, with an explicit two-thread linker bound. The first
and second attempts use byte-identical response files and input inventories.
No AOT, Denial, kernel or additional engine object rebuild was needed.

| Engine | SHA-256 | Result |
| --- | --- | --- |
| Retained original | `1948c859989fc8721112ffb6eda4e6869745e0fafcec42d6c2f77d9bd402cadb` | Previous VM cleanup FAIL; bytes preserved |
| Corrected | `645f85f2ac274c5ec010dc011496043099a4e88eaea2e8540400f82b77e37bde` | Complete link and this VM render-context cleanup PASS |

The corrected library is 15976208 bytes. AArch64 architecture,
exported symbol names, SONAME and dependency list match the original. All 32
runtime bundle files are compared: only `lib/libflutter_engine.so` changes.
The guest uses the same authenticated Arch runtime, generic virtual kernel,
QEMU/VirGL container, Denial executable, AOT/data and guest script as the prior
control. The harness additionally rejects the correction's explicit teardown
error messages, with regression coverage, so they cannot silently become PASS.

## Executed results and resource bounds

- First link: **FAIL**, 198.601 seconds. Kernel evidence
  confirms a container-local memory-cgroup OOM killing ld.lld at the 3 GiB cap;
  it was not system-wide memory exhaustion. Preserve this failure.
- Second identical-input link: **PASS**, 201.103 seconds,
  using the earlier successful engine build's 4 GiB budget and no swap. Host
  available memory exceeded 7 GiB before launch; minimum disk during link was
  3433078784 bytes, above the 3 GiB reserve. Two CPUs, 600-second
  link and 8 MiB log bounds applied. Both containers were removed.
- ABI/bundle comparison: **PASS**, one changed engine file.
- VM: **FAIL** for the complete session, 48.571 seconds;
  **PASS** for observed render-context cleanup. All 236 trace records are
  contiguous; the cap was not reached. Sequence 229 records raster-thread
  unbind, 233 successful main-thread cleanup binding, and 235 final unbind.
  A subsequent raster-idle sentinel sees no current context and does not rebind.
- Six host prerequisite/classifier cases: **PASS**, including both new teardown
  errors. Frozen active tier: 87 PASS, zero FAIL/BLOCKED/SKIPPED suites,
  255 NOT_SELECTED, three declared optional subchecks SKIPPED;
  131.222 seconds. Existing source/destructor tests from
  the preceding frozen implementation remain applicable; they were not rerun
  merely for new evidence.
- Final metadata: 13 checker/status cases plus inventory, generated-header and
  whitespace checks PASS. Active service peak memory was 319.1 MiB, no swap.
  An exact-function before/after fixture also confirms both new teardown errors
  were falsely accepted by the old classifier and are rejected by the correction.
- Phone, visual/input interaction and IO resource-context final release:
  **NOT RUN**. Prior S06 and R01 **FAIL** remain unchanged.

The VM remains network-disabled, with read-only runtime/payload, only the host
render node exposed, 1536 MiB/no-swap container, 1 GiB guest, 120-second harness,
45-second session and 8 MiB serial bounds. No host/phone power operation occurs.

Exact commands, response/input inventory identities, logs, observations and
source/build bindings are recorded in
[qualification JSON](2026-09-12-impeller-engine-vm-qualification.json).
Raw serial SHA-256: `9a57c671f78d976fcf79faca3d02bd151c407b6e2faffa38e1626c922a68e250`.
Large/private inputs are retained locally, not downloadable merely because this
report is in Git. Querying Ninja and linking do not regenerate all upstream
sources or reauthenticate the runtime package graph.

## Next and preservation

Reuse the corrected engine in the next bounded VM. Return to the outstanding
queued-render ownership handoff: distinguish queued work mode/generation and
backing-store callback provenance before changing the one-use reservation policy.
The focused Pro review branch remains frozen; this cleanup result does not answer
its frame-admission questions. The IO resource context is another independently
unqualified lifetime, not evidence that the render-context correction failed.

Both original and corrected engine bytes, unstripped corrected library, input
hashes and all failed/passing evidence are retained. Only 33 verified duplicate
VM staging files were removed, with restoration mappings. Accepted server/rescue,
ASUS slot A, signed fallback, prepared phone artifacts and consumed claims are
unchanged. No new candidate, claim, signature, installation, phone operation or
protected-storage mutation occurred. The goal remains incomplete.
