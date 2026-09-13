# Wayland diagnostic framing and VM controller failures — September 13, 2026

**Wayland string framing is corrected and semantically tested; the real ARM64 library builds with unchanged exported ABI. Full touch text-entry qualification is still incomplete.** All runs here are isolated ARM64 VirGL VM or host fixtures. Phone physical rows remain NOT RUN, S06/R01 remain FAIL, and no phone operation, signing, admission, claim consumption or protected-storage mutation occurred.

## Demonstrated source defects

The earlier GTK-module VM failed when a surrounding-text string contained a literal newline. Its retained log subsequently shows `set_cursor_rectangle(92,1070,0,20)` and a commit. That is evidence that GTK published the lower rectangle, but the host oracle had already rejected the split record; it is not a successful lower-caret/OSK session.

Exact Wayland 1.26.0 `wl_closure_print()` prints string arguments as raw quoted `%s`. Although it constructs the record in a memory stream, raw LF splits it into multiple physical records. Raw quotes also prevent reliable reconstruction after prefixing. A text payload can resemble another diagnostic protocol record. Relaxing the host parser would lose the distinction between application text and evidence.

The patch escapes quotes, backslashes, LF, CR, TAB, other C0 bytes and DEL at the producer. Printable UTF-8 bytes and the existing null representation remain. Wire protocol data is unchanged. Tests compile the actual production string case and helper, feed its output into the unchanged caret parser, reject forged records, preserve genuine neighboring records and retain the expanded-record size limit.

- Exact Wayland commit: `87cc8a8728a923fc57938faa81ba0e74f34ecdc7`.
- Library-source repository commit: `5a8ad8addbb5d414620f443de6d1acd0f55b65e9`.
- Original control: **4 PASS / 7 FAIL**, 1.127s. Patched: **11 PASS**, 1.286s; Python `-O`: **11 PASS**, 1.263s.
- Real upstream Meson ARM64 build: **PASS**, 4.961s, 11 Ninja steps, no captured compiler warnings.
- Library SHA-256: `06c191678e78eb896e2a672c748cd061b7ec62c8bf4280db62d609e92b720d29`, 148,432 bytes.
- All 86 dynamic exports match the packaged library. SONAME, dependencies and absence of RPATH/RUNPATH match. This does not establish the complete distribution packaging patch closure.

The VM payload adds only the library and exact old/new hash contract; 41 pre-existing files retain identical bytes, sizes and modes. Its SHA-256 is `05c9013043ab83bc441f933b71b6ec1a24912fd348a26114fc586a8c78a1bd17`. The original runtime remains unchanged. The explicit override requires regular files, exact hashes, a fresh bind and verified read-only remount. Both GTK and Wayland override guards pass 49 host cases normally and under Python `-O`; mount effects in those cases are adapters. The first VM actually passed both override checks.

## First combined treatment retained as FAIL

VM source `c9697e9717b1096222234e1de1632d295431bbae`, duration245.780s: launcher home observed, then Mousepad supervisor TERM143 before its toplevel mapped. No lower-caret or OSK sequence occurred. Named-container cleanup and absence passed. This did not reach the record-framing behavior and does not demonstrate a regression in the new library.

The second diagnostic snapshot starts just before termination. Source inspection and a real FIFO/process regression demonstrate that snapshot failure42 or timeout124 exits the controller, whose cleanup TERM-signals the client supervisor. Previously the controller's reason was missing, leaving only the downstream TERM143. The original VM's initiating status cannot be recovered from those records.

The corrected controller retains its current phase and emits one bounded failure record before cleanup. Original status, deadlines, signal targets and successful-session behavior remain. Missing evidence ownership skips the extra write; failed delivery cannot replace the original failure. The actual session EXIT function is exercised. Full supervision suite: **37 PASS**,18.770s; five new cases under Python `-O`: **5 PASS**,10.420s. The negative control reproduced the missing reason before the implementation changed.

## Instrumented VM result

The bounded comparison uses controller source `1c5b85828357be363369270a3ef14dfe4968a4e3` and the same kernel/runtime/payload as the first combined treatment. No application or graphics library was rebuilt for this diagnostic comparison.

The instrumented VM completed the lower-caret coordinate sequence (**PASS**), native editor key protocol (**PASS**) and all four focus visits Mousepad → Foot → Mousepad → Foot (**PASS**). The multiline surrounding-text record now stays on one physical line as escaped `line-50\nline-51`; the unchanged oracle accepted it. Manual capture inspection shows `line-50tes` after backspace and `line-50test` with the caret visible above the OSK after retyping. Translation preserved delivered surface coordinates without a manual viewport pan. The dismissal capture still contains a sliver of keyboard, so fully settled dismissal is not established by that frame.

Overall VM result: **FAIL**,314.866s including preparation and cleanup. The QEMU command hit its unchanged300s host deadline. The host had sent its completion acknowledgement and authorized teardown; Foot and Mousepad close-begin clocks were recorded at guest CLOCK_BOOTTIME293.42s and293.92s. Clean client exits and complete session teardown were not observed before termination. Named-container removal passed in0.523s and absence in0.034s. No controller-error record occurred in this run; the earlier snapshot failure hypothesis remains unproven. Successful interaction does not supersede either overall VM FAIL.

Next unresolved boundary: completion of graceful app/session cleanup within the bounded VM test. Audit the startup/interaction/teardown timing allocation and retain per-stage clocks before another run. Reuse these exact binaries and successful interaction evidence; do not rebuild GTK, Wayland, Flutter or the kernel merely to investigate the harness cutoff. The phone OLED/Adreno/touch trial remains separately unauthorized.

The active-tier launcher itself was interrupted with143 while its systemd unit continued. The same unit was monitored to completion without restarting tests. Its terminal report contains105 selected PASS, zero FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED and three explicitly optional skipped subchecks. Measured service-start to terminal resource-journal interval:168.923s; peak memory579.3MiB. The launcher's final result and service exit status were not captured before unit collection; they remain unknown, rather than being invented as zero. The complete per-test results and final summary are retained.

Integrated active tier: {'PASS': 105, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255}, 168.923s on `1c5b85828357be363369270a3ef14dfe4968a4e3`. Source-dependent string tests ran separately against exact Wayland source; the active tier does not rerun that standalone build.

[Qualification JSON](2026-09-13-wayland-debug-qualification.json) retains commands, identities, counts, timings, VM outcomes and limitations.
