# Explicit VM main-thread PC observation — 2026-09-20

Generic ARM64 VM and offline fixtures only. No phone operation, signing,
candidate, claim, admission or protected-storage mutation. Physical NOT RUN;
ASUS slot A, V11 fallback, accepted server/rescue and S06/R01 FAIL preserved.
Previous turn made progress by implementing and testing the snapshot component.

Starting commit `144b2f92d029e07653ff37dc5177dbed0e64afaf`, tree
`0871e1f90f7d34f50899c31af72eab02165f9149`. Frozen implementation
`1ab6d7c64e5c431be80e48848e35e0d724bb5f5b`, tree
`81ca919acd20652b8e86297fcf270e974378ae66`.
Changes: `scripts/host/test-qemu-logind.py`,
`scripts/host/test-qemu-logind-runner.py`,
`scripts/host/test-app-close-probe.py`, and
`tools/qemu-virtio-drm/app-close-probe.rs`.

`--app-close-ptrace` requires the existing explicit proc-probe, close-only,
settings diagnostic and authenticated combined-VM chain. Only that mode copies
the separately recorded module and supplies rustc's close_ptrace configuration.
Default helpers compile no ptrace module. Existing VM/UID/stdout/identity guards
run before capture. One snapshot is attempted after proc round1; parent, UID,
comm and starttime are revalidated before attachment, while stopped, after detach
and after the bounded map lookup. Mapping is not an atomic stopped snapshot.

The sampler reserves1536 bytes from early optional observations for the two
snapshot records; both must actually be published. Missing, failed or unattempted
capture finishes with status125 rather than claiming diagnostic success. The
original app result still remains authoritative. The six rounds,8KiB/64 records,
1.2-second sampling budget and separate2-second outer watchdog remain. A new
check immediately before capture prevents starting it when the preceding proc
sample has already exhausted the budget. Syscalls/scheduling still lack a hard
wall-time guarantee; numeric-PID attachment remains non-atomic with validation.
This diagnostic perturbs execution and is not a timing-neutral comparison.

Two CLI/staging regressions fail before implementation (0.011s) and pass afterward
(0.018s). Seventeen Rust cases pass via two Python wrappers in3.836s, including
actual owned-process PC/mapping capture, invalid UID/starttime refusal, the new
deadline check, worst-case reserved-output publication, and the previously
qualified signal/detach/panic/exit tests. Both default and intrusive releases
refuse outside the VM before capture. The retained ptrace component is unchanged.

The executed single VM changed only the diagnostic helper/runner and new module
relative to the preceding CPU-counter run. Kernel, Denial/engine, runtime, caches,
GBM/fence policy, explicit20s readiness and all close/PAM/outer deadlines remain.
No phone or full kernel/Denial/Flutter build is part of this experiment.

## Executed result

The single VM **FAIL** took397.638779489s (wrapper397.710211511s).
Explicit20s device readiness passed in7.74s. Both clients mapped and received
initial focus; inspection of the retained captures shows Mousepad's blank editor
and Foot's controlled text. This is not text-entry or phone-touch proof.
Foot exited0; Mousepad exited137, preserving the failed session result.

The requested main-thread snapshot succeeded. PC `0xffffb44c20a0` maps to
`g_malloc+0`, ELF address `0x720a0`, in the retained GLib2.88.3 library
SHA256 `a94149b7c410bd66bc71491fe68fcade5bf736108ffca9fd1af23cf76eab37b7`,
build ID `6381a8b151ea04bc7dd41926f1b1dd6add016846`. The PT_LOAD mapping,
exported symbol size and instruction were checked against those exact bytes.
The instruction is `cbz x0,0x720d0`, before the allocator call. This proves
neither allocation failure, allocator lock, memory exhaustion nor a spin loop.

LR maps to `0x3f81c` in the same executable mapping. Its preceding call uses
GOT relocation `0x18da98 -> 0x720a0`; the preceding instruction loads56 into x0.
x0 itself was not captured. Comparison with
[GLib2.88.3 gdataset.c](https://github.com/GNOME/glib/blob/43bc79ea8803e33c5eb368085e2d5906f9f98079/glib/gdataset.c#L288)
strongly identifies the unexported caller as `datalist_append()`'s empty-list
allocation: header8 + two24-byte elements, followed by matching len/alloc and
key/data/destroy stores. This remains source/disassembly inference without
matching debug symbols or package-build reconstruction. No higher-level caller
was sampled. Objdump's nearest-symbol label `g_filename_display_basename+...`
is not that routine's identity; the exported symbol ends before the sampled caller.

Observed interrupt-to-detach time was22457us. The1010ms sampler published36
records with truncation=true, within its budgets. Five valid CPU points cover
0.788676048s and49 ticks (47user/2system at100Hz), with1 voluntary and226
involuntary switches. Round5 lacks the parent status file and supplies no CPU
point. The intrusive stop perturbs scheduling; these counters are not a neutral
performance comparison with the earlier read-only run.

PAM close/delete-credentials/end each returned0 while its session child returned1.
The initial `/var` unmount failed; ordinary VM poweroff passed the actual
RCU-aware checker. All owned build/VM containers are absent. Original runtime
bytes and metadata and the recorded unchanged inputs verified unchanged.
The ARM64 helper is568736 bytes, SHA256
`ab81d5d06d920c43d46952dd628d8bf22e016b0a6735147eb253012018e7640c`.

## Next discriminating step and limits

Recover the exact higher-level caller through matching debug information or a
bounded, separately tested ARM64 frame-pointer read at the existing single stop.
Validate mapped stack bounds, alignment, monotonic frame addresses and partial
failure while preserving detach/signal/identity/output/deadline guards. Do not
patch GLib, add repeated snapshots, raise the close grace, or rebuild Denial
from this single PC alone. Any new VM must carry a new, qualified diagnostic.
This VM result does not block independently authorized panel/touch source work.

This report closes publication of the already completed experiment; it does not
claim a new runtime this turn. The intervening community audit made progress by
identifying concrete dependency reuse defects; unchanged upstream refs did not
justify another build. Research documentation changed after source freeze and
is recorded separately from tested implementation bytes. Physical, OLED, A660,
touch, suspend and charging qualification remain NOT RUN under the offline scope.

Frozen active tier: {'PASS': 112, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255}, 191.692671017s; declared optional historical subchecks {'SKIPPED': 3}. Commands, artifact identities and step durations are in the qualification JSON/private records.
