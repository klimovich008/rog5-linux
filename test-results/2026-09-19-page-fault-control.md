# Reduced kernel page-fault control — 2026-09-19

**Both final kernel controls PASS; full Denial startup stall NOT REPRODUCED.**
This tests anonymous-page allocation and copy-on-write in a generic ARM64 VM.
It does not qualify ROG5 hardware or close the earlier RCU/portal failures.
Physical tests remain NOT RUN; S06/R01 FAIL are unchanged. No phone, signing,
candidate, admission, claim or protected-storage operation occurred.

Starting repository commit/tree:
`7417e8300914b7d59649c5d300ab6269501a0921` /
`79b42ec63581bf22d93768b5a19e96e79fa72b9a`.
Final compiled/tested source:
`117f46d627f90783f8697ebfd7c7511e1dff5e76` /
`8f778a6482fb74e838593f058587181f13875bef`.
The earlier probe at `8e3ce2b8` is retained as a failed fixture. The isolated
checkout was clean for each frozen run; the original dirty repo was preserved.

## Exact source findings

The retained kernel source is clean at
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`, tree
`2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9`. Its documentation and
`arch/arm64/kernel/pi/idreg-override.c` support `arm64.nomops` as an alias for
`id_aa64isar2.mops=0`. Both `copy_page.S` and `clear_page.S` select their MOPS
alternatives through `ARM64_HAS_MOPS`. This permits a control using the same
Image; no kernel rebuild or patch was needed.

The retained container uses QEMU8.2.2, Ubuntu package
`1:8.2.2+ds-0ubuntu1.18`. Paused QMP CPU-model expansion rejects `mops=false`
with `Parameter 'mops' is unexpected`; `-cpu max,mops=off` is not a supported
control here. No guest instructions executed during that introspection.

The examined [SET/XZR fix](https://github.com/qemu/qemu/commit/854c001f121578c96b023b5db0c5550250505a0e)
and [reverse-copy MTE fix](https://github.com/qemu/qemu/commit/4d044472ab7666adf99d4daa0cc90b7502b90109)
already exist in the inspected v8.2.2 source. The later
[concurrent-unmap fix](https://github.com/qemu/qemu/commit/8009519b3094ab515def1fe9bbc444d463579448)
adds helpers that are no-ops outside user-mode emulation at that revision.
It does not identify a fix for this system VM. The exact distro patch archive
was checked; this bounded search is not proof that no relevant QEMU bug exists.
The source audit transcribes tool outputs; separate raw audit files were not
saved, and the entire distro binary was not rebuilt from source.

## Executed probe and correction

New source: `tools/qemu-smoke/page-fault.c`, a freestanding ARM64 PID1 fixture.
It maps32MiB, checks zero samples, writes page sentinels, forks one child, checks
child copies and unchanged parent samples, unmaps, and repeats eight times.
Checks sample four offsets per4KiB page; they are not a whole-buffer checksum.
Only one child is live at a time. The user-test build exits normally and never
uses the guest poweroff path; the VM build powers off only as PID1.

The first implementation used MADV_DONTNEED. Both actual guest runs failed at
`discard-pages` and powered off in about1.4/1.2s. The exact kernel disables
`CONFIG_ADVISE_SYSCALLS`. User-mode success had not established that guest
syscall availability. The correction uses ordinary private anonymous mmap and
munmap, preserving the kernel configuration. Failed records remain unchanged.

The corrected ARM64 user-mode probe passes in0.374s. An intentional parent-page
corruption fails at `parent-isolation` with exit1 in0.051s, confirming the actual
data-checking oracle. This exercises host-kernel memory behavior through
qemu-user, separately from the full-system kernel controls below.

| Final control | Guest workload | Host command including cleanup | Result |
| --- | --- | --- | --- |
| Normal MOPS | 2485ms | 3.844s | Eight rounds, expected MOPS boot feature, no RCU/panic, normal poweroff |
| `arm64.nomops` | 2649ms | 3.995s | Eight rounds, MOPS boot feature absent, no RCU/panic, normal poweroff |

Both runs used the identical Image/initramfs, QEMU image, `-cpu max`, two guest
CPUs,1GiB guest RAM and single-thread TCG. Each container had2GiB memory with
no swap allowance,2CPU quota,64-task bound, no network, read-only inputs and
a120s deadline. The only execution-mode difference was the kernel argument;
container names and serial destinations were distinct. There was no desktop,
9P mount or host render-node exposure in these reduced controls.

The small timing difference from one run per mode is not a performance finding.
Basic copying passes in both modes; it neither establishes universal MOPS
correctness nor justifies making nomops the default for Denial or the phone.

The final active tier on source117f46d6 passes **111 suites,0 FAIL/BLOCKED/SKIPPED,
255 NOT_SELECTED** in179.422s,499.1MiB peak and0swap. Three declared optional
historical subchecks are SKIPPED separately. The earlier active run passed on
8e3ce2b8 but did not catch unavailable guest madvise; it is not substituted for
the final run. These are local executions, not imported CI results.

## Identity and reproduction

- Kernel Image SHA256:
  `2b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc`.
- Guest executable SHA256:
  `78de0be36596748c8d9297bf08f47b9fb8a1e245930e3de8c6d31ef7d864c777`.
- Initramfs2027bytes, SHA256:
  `2984a435185075fc7d1ba94af3eeaf81e1d9659029c13d5420ddf7b810956c60`.
- QEMU image:
  `d2ea0285ee5edfbf79679684ad70c53c06eb45b705e0fa1cf9967d1560f4023d`.

The [qualification record](2026-09-19-page-fault-control-qualification.json)
contains exact compile/container commands, source/tool hashes, both initial
failures, final controls and test timings. Compile the source with the recorded
freestanding clang flags; `PROBE_USER_TEST` selects the user-mode oracle and
`PROBE_CORRUPT_PARENT` its negative test. For the VM use the normal binary as
`/init` in an initramfs containing `/dev`; the host wrapper uses the existing
runner's bounded executor, owned-container cleanup and RCU/poweroff gate.
Use fresh output names; retained execution directories must not be replayed.
Private evidence is in `rog5-page-fault-control-20260919-r1` and `-r2`.

## Next question and improvement

The real startup includes read-only9P file-backed faults and concurrent services
absent here. Prepare a bounded file-backed/COW control before another full
Denial attempt. Existing anonymous and file-backed kernel paths can both call
the page-copy helper; the retained stack alone does not identify the backing
file or assign responsibility to9P.

The prior goal turn and this turn are progress. This turn establishes a supported
control, rules out neither mode broadly, and provides a fast executable memory
probe. Check optional guest syscall configuration before the target run, and
complete focused target checks before the integrated tier: the first premature
active run cost181s without detecting the missing syscall. Keep diagnostic
controls distinct from fixes and preserve earlier failures. No Denial/Flutter,
phone kernel, accepted image or fallback was rebuilt or replaced.
