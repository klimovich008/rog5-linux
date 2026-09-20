# Native ARM64 close capture and CPU accounting — 2026-09-20

Source `aad76deef55f48db08ac91ca947d56220a4f05ff`, tree `2ab63558fd7d41e406a254f1ca6b36a062259410`, branch agent/review-correctness-20260912.
No product source changed. The preceding community recheck supplied no new fix
and was no progress toward qualification. This turn completed three bounded
native ARM64 component runs and changed the diagnostic disposition below.
No phone operation, signing, admission, claim, candidate or protected-storage
mutation occurred. Physical qualification remains NOT RUN; S06/R01 remain FAIL.

## Results

| Executed check | Result | Seconds |
| --- | --- | ---: |
| Existing stage/ptrace/stack helper ARM64 build | PASS | 4.005 |
| Loaded native component, one guarded PC | Close FAIL137; capture PASS | 81.988 |
| Existing default non-ptrace helper ARM64 build | PASS | 2.498 |
| Loaded component, CPU reader armed before contention/TERM | Close FAIL137; accounting PASS | 86.753 |
| Identical idle component and CPU reader | Close PASS0; accounting PASS | 82.088 |

Counts are per declared scope: builds2 PASS; controlled closes1 PASS/2 FAIL;
diagnostic observations3 PASS. No build/runtime check was skipped or blocked.
Metadata checks are recorded separately. Original idle/loaded controls and full
Denial VM failures remain historical evidence, not tests rerun or reclassified.

Both observed close failures used the existing2s TERM-to-KILL policy. The
ptrace arm closed in2.10s and the non-ptrace loaded arm in2.14s, exit137. The idle
arm closed in1.17s, exit0, with complete quit/shutdown phases; window removal to
quit return took0.896318048s. Every document before/after hash matched, every
reader exited0, and all recorded run inputs remained unchanged. VM poweroff and
owned-container removal completed. Normal VM shutdown is not application PASS.

## Instruction observation

The loaded component's PC maps to ELF/file offset `0x38cf4`, exported
`g_signal_handlers_destroy+0x94`, instruction `ldr w1,[x22]`, in the exact retained
libgobject-2.0.so.0.8800.3. SHA256:
`db2f18d8fd70549cfb99a4c53499b29154c42a4ee4746549ba594a4abf8d809f`.
Executable segment file offset and virtual address are both zero. Independent
read-only review confirmed attribution, symbol extent and preceding call.
The earlier Denial PC was `handlers_find` at `0x31528`: a different routine.
Neither sample proves a shared stuck instruction, infinite loop or GLib defect.

Capture detached after50,784us; stack collection reached its unchanged15ms
budget with zero frames. LR points to the return from the immediately preceding
call, not an independently recovered caller. The helper emitted five unclipped,
uninvalidated records, footer384ms. That footer excludes process startup delay:
window removal was76.558665904 and observation completion78.244526832, about
1.686s apart. Asynchronous launch before TERM did not guarantee arming before TERM.

## Non-intrusive comparison

Reused the existing default helper, with no ptrace/stage/stack build flags.
The fixture waits for its first valid identity-checked CPU record before starting
both synchronized four-second CPU burners and issuing TERM. No helper/close/VM
budget changed. The idle fixture uses the same helper, readiness and client bytes.

| Main-thread interval | Idle | Loaded |
| --- | ---: | ---: |
| Six sampled clock points, first-to-last wall | 1.002368s | 1.007724s |
| Main-thread CPU delta over those samples | 0.88s | 0.45s |
| Samples whose clocks follow WINDOW_REMOVED_ZERO | rounds1–5 | rounds2–5 |
| Their approximate elapsed interval | 0.799914s | 0.592035s |
| Their user CPU delta | 0.80s | 0.32s |
| Their system CPU delta | 0 | 0 |
| Their voluntary/involuntary switch deltas | 0/1 | 0/33 |

All selected post-window main-thread state samples are R. This demonstrates
user-mode execution with preemption in the loaded arm and rules out continuous
sleep/blocking throughout that sampled interval. It does not distinguish useful
cleanup from spinning or prove the original Denial cause. The unmatched interval
lengths are not a throughput benchmark. Approximately1.23s after the loaded
arm's final clock point remained unsampled before close-end.

The clocks precede identity/proc reads, so comparisons are approximate. R means
running or runnable; it does not establish continuous CPU execution. Only main
thread CPU is collected; extra tasks have state/syscall observations. The pinned
kernel lacks CONFIG_SCHEDSTATS, so wall minus CPU is not runnable-wait accounting.
Both default-helper footers retain truncated=true for bounded task/FD inventory;
all six CPU/clock pairs are present and unclipped, with invalidated=false.
Independent review confirmed these limited inferences.

## Scope, identities and commands

These are generic ARM64 system VMs using native UID1000 Mousepad, Weston15.0.1-3
headless/Pixman, the retained GTK/runtime and actual production diagnostic helpers.
No Denial, phone GPU, panel, touch, input focus or full mobile session is tested.
The component's known missing seat/focus and document-FUSE support remain.
Kernel, Mesa, runtime libraries, portal preparation, synchronized burner code,
Wayland/IM overrides and document input are unchanged from the retained fixture.

Stage helper SHA256 `ff7067958d7f444764317680ff65dbe55188d6f07e51e010b72a80dd35cc8517`;
default helper SHA256 `f7a025863b7230bb6c717d6601baadc5729abccbb398e7057914060cf5401cf0`.
The matching source hashes, exact compiler commands, initramfs/serial hashes,
QEMU commands and step timings are in the qualification JSON. Private run records
also retain all1,300+ input hashes and raw diagnostic captures.

Commands used the private roots
`rog5-native-close-capture-20260920-r1` and
`rog5-native-close-accounting-20260920-r1` under /home/deck/.local/state:
`python3 build.py`, `python3 run.py loaded`, and the second root's
`python3 run.py idle`. Read-only analysis used the recorded `llvm-objdump` and
`llvm-readelf` commands, and each root's analyze.py. Shell syntax checks passed.
VM bounds remain95s overall,70s guest session,45s application startup,2s close
and1200ms helper budget; containers have1536MiB/no swap, two CPUs, no network.
The captured arm additionally preserves15ms/64KiB/four-frame stack bounds.
No unchanged kernel, compositor, engine or full active suite was rebuilt/rerun.

## Decision and next work

CPU contention changes completion in this controlled component comparison.
No GLib or Denial source defect was established, and no deadline relaxation is
justified. Preserve the failed full Denial close and unmount results; neither is
phone evidence. Stop repeating instruction captures at this unchanged boundary.

Return priority to native ROG5 graphics: inspect the current unsigned board,
corrected panel and disabled touch artifact closures against the newest module
qualification and trial prerequisites. Implement only a demonstrated missing
offline prerequisite for the60Hz scanout/blank, touch or A660 questions. Reuse
matching compiled bytes. The historical signed136f candidate lacks current
review fixes and must not substitute for the corrected artifacts. No candidate,
signing, phone probe or Ready request is authorized by this work.

Qualification SHA256 `223062393eaf5b4392c434f9ac9acf087731c624fa985631ce7b391e9cf7228c`.

## Metadata verification and changed files

Final metadata/preservation checks PASS in0.441s: inventory0.101s; status header
write0.044s; status verification0.039s; eight status regression cases0.095s;
git diff --check0.050s. All590 prior artifact rows, both acceptance contracts,
historical current-state tail and previous artifact-pointer entries are unchanged.
Idle/loaded accounting controls have identical recorded input dictionaries; their
generated guest scripts differ only in the contention flag. No containers remain.
The inventory check explicitly leaves large/private and physical verification
NOT RUN; the run-specific streaming input checks above are separate evidence.

Changed files: configs/project-status.json, docs/current-state.md,
docs/development-lessons.md, manifests/artifact-sets.json,
manifests/current-artifact.json, this report and its qualification JSON.
