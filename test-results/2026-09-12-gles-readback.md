# Offscreen GLES readback preparation — 2026-09-12

Added a Rust component that draws a 4×4 shader pattern and checks all 64 RGBA
channels before reporting successful EGL cleanup. The [probe and usage
contract](../tools/a660/README-gles-readback.md) distinguish software-fixture
results from the strict A660 renderer mode. Neither mode grants admission or
physical acceptance. The existing Vulkan helper submits an empty command
buffer; its historical callers and qualification were not changed.

Real host Mesa llvmpipe rendered the expected pixels with `/dev/dri` hidden.
Removing the actual draw call produced the required pixel-mismatch failure.
This closes a missing offline test capability, not an observed phone defect.
The [qualification receipt](2026-09-12-gles-readback-qualification.json) contains
build commands, tool and output identities, test durations and raw-result hashes.
Raw logs remain in the private `rog5-gles-readback-evidence-20260912-r1` directory.

## Identity and scope

- Starting commit: `bcedb75e483a01a9d060357b2de0d777d0aa41f6`.
- Starting tree: `893ed4e35de8e7d528a6827a68579703992b86fa`.
- Frozen source: `bdea5a5ef8585092d5f1fcf52b835089b890161d`.
- Frozen tree: `f0c518d2d6b0d91955d683d021f0da3c97f402c9`.
- Rust source SHA256: `799f2449210e331d925d10c331bed2516d605e45643079131572c295f997c93b`.
- Identical 4,654,144-byte ARM64 twins:
  `fd715ddaa7d38664fe63794bf144c3e43200c4cc5019fa1b9e436f76ee5ae1ac`.

The cached builder uses Rust 1.98.0, GCC 13.3.0 and GNU ld 2.42. Its immutable
image identity and compiler/linker hashes are recorded. No builder download or
host package installation occurred. ARM64 ELF dependencies are `libgcc_s.so.1`
and `libc.so.6`, with GLIBC requirements through 2.34; EGL/GLES are loaded at
runtime. Target execution and the target Mesa dependency closure are **NOT RUN**.
The host rendering receipt identifies Mesa 25.3.0, llvmpipe LLVM 20.1.8. It is not
a target Mesa lock or a hardware identity receipt.

The new private build set is classified **fixture** in the existing artifact
inventory and selected by the separate `gpu_readback_probe` pointer. All 453
previous sets and all previous current-artifact fields remain unchanged. No
board, DT, module, signed candidate, installed image or fallback was replaced.
No new kernel build was necessary for this standalone userspace component.
Ending commit/tree and every changed-file hash are recorded after the metadata
commit in private `completion.json`.

## Personally executed checks

| Check | Result | Seconds |
|---|---|---:|
| Initial focused suite | 6 groups PASS | 3.509 |
| Cleanup/stall additions, Python `-O` | 7 groups PASS | 3.645 |
| Final source focused suite, Python `-O` | 7 groups PASS | 3.549 |
| ARM64 twin A compile | PASS | 1.167 |
| ARM64 twin B compile | PASS; bytes match | 1.016 |
| Native optimized compile | PASS | 0.916 |
| Debug Rust test compile / execution | PASS; 3 tests | 0.615 / 0.004 |
| ARM64 ELF inspection | PASS: AArch64 | 0.008 |
| Retained native software Mesa execution | PASS: 16 pixels, 64 channels | 0.165 |
| Builder identity capture | PASS | 0.315 |
| Frozen active tier | 83 PASS, 0 FAIL, 0 BLOCKED, 0 suites SKIPPED, 256 NOT_SELECTED | 111.291 summed test time |

The seven focused groups include 25 injected EGL/GL/cleanup failures, explicit
mode parsing, six renderer-mode combinations, three Rust semantic tests, real
software Mesa success and strict-A660 refusal, a no-draw mutation, and a stalled
readback killed by its external deadline. Every channel is separately corrupted
in the Rust unit test. Fault libraries exercise the actual Rust executable;
only EGL/GLES boundaries are fixtures. The no-draw mutation executes against
real Mesa, so a successful library load or clear cannot satisfy the pixel test.

The active tier runs the suite under Python `-O`. It records three declared
optional **subchecks** skipped and no mandatory/whole-suite skips. Individual
commands and durations are retained in JSON/JUnit. The aggregate above sums test
durations, excludes orchestration overhead and overlaps parallel work; an outer
monotonic wall duration was not captured. `ROG5_LINUX_SOURCE` was unset. Existing
exact-board evidence is unchanged, not re-executed by this tier.

The runner contract passed separately. One earlier invocation mistakenly used
Python for that shell script and executed no tests; the corrected Bash command
passed. That focused contract's duration was not captured. Final metadata and
workflow checks are recorded in private `final-checks.json`. No GitHub Actions
run is claimed. Rustfmt and Clippy are **NOT RUN**, unavailable in the retained
builder; rustc builds use `-Dwarnings`.

## Limits and next question

Synchronous driver calls can block, including cleanup. The future coordinator
must enforce a process deadline and retain stderr/recovery evidence. A killed
run emits no success receipt and does not prove successful EGL cleanup. Exact
renderer strings filter accidental software fallback but do not establish
trusted device, kernel, firmware or Mesa identity.

A660 execution, OLED scanout, DMA-BUF formats/modifiers/export/import, native
fences, Vulkan rendering and Denial integration remain **NOT RUN**. No phone
operation, signing, admission, claim creation/consumption, candidate generation,
module loading or protected-storage mutation occurred. Touch remains disabled.
Historical headless S06 and R01 **FAIL** and all historical evidence remain
unchanged.

The next smallest hardware question remains one stable 60 Hz pattern followed
by clean blanking, after separate exact-artifact preparation and execution
authorization. The [GPU plan](../configs/mobile/trial-plans.json) now records
this offscreen component as a separate prerequisite for a later A660 shader
readback question. It does not arm a session or bypass the display, power,
identity and recovery guards.
