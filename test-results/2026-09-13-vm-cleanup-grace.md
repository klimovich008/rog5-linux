# Bounded VM cleanup allowance — September 13, 2026

The preceding VM proved lower-caret coordinates, the OSK key sequence and four native-app focus visits, but hit its300s host cutoff during approved cleanup. Both close-begin records arrived and Mousepad destroyed its Wayland surface; clean exits and full session teardown were not established. That historical run remains FAIL.

This change is restricted to the host VM supervisor. Startup and interaction retain the original300s cutoff. A single30s cleanup reserve is available only if a successful observer tick verifies complete interaction, a fully sent host acknowledgement, an approved guest teardown record and no observer error **before** that cutoff. Late ticks or predicates cannot qualify. The hard end is the original cutoff plus30s, never the current time plus30s. Further messages cannot reset it. Strict observation, clean-client receipts, serial completion, guest poweroff and container removal remain required. All guest/client deadlines and all phone guards are unchanged.

Review exposed a pre-existing terminal-child loophole: a child exiting during a cutoff-crossing observer call could bypass the loop's time check. Two regressions first failed because no timeout was raised. The runner now checks before accepting child termination and after its final observer call. Focused coverage also tests a tick or predicate crossing the original cutoff, unapproved cleanup, repeated eligibility, hard expiry, protocol/predicate errors, missing polling and the actual apps-only call site.

Final focused suite:13 PASS under Python `-O`. The earlier optimized full runner suite passed72 tests; two final cases were then added and are covered by the frozen integrated tier. Deadline fixtures use a real subprocess for completion and failure/cleanup paths; exact clock-boundary cases use virtual clocks and an inert child adapter. Neither is VM or phone evidence.

Source starts at `a890792b2b96c24dbdfa989fa17b7a7c4d471a6b`; tested supervisor commit is `d3490fa3455d8ad7e5aac82a125d4e0d251a69a8`. Reused payload SHA-256 is `05c9013043ab83bc441f933b71b6ec1a24912fd348a26114fc586a8c78a1bd17`; no Denial, GTK, Wayland, Flutter or kernel build was needed. Generic ARM64 helper compilation and initramfs staging belong to the VM harness and are separately recorded.

The integrated test worker now records its command status from inside the owning systemd service. Losing the external launcher no longer loses a completed test result. The previous interrupted-launcher result remains explicitly unknown; this does not rewrite it. Memory/concurrency limits and the independent600s service deadline remain.

All operations are offline host/VM operations. Phone physical rows remain NOT RUN, S06/R01 remain FAIL, and no phone I/O, signing, admission, claim consumption or protected-storage mutation is authorized or performed.

## Latest bounded VM result

The latest VM remains **FAIL** at the original300s command deadline. It reached Mousepad and began the interaction sequence, but did not complete the host acknowledgement or reach approved guest teardown. The cleanup reserve was therefore correctly **not granted**. This run provides no runtime qualification of that reserve. Fifteen retained guest scripts/binaries match the prior run byte for byte; the payload and graphics/application binaries were reused.

The service-start boundary arrived at guest CLOCK_MONOTONIC239.153914688s, compared with209.950470800s in the prior VM: **29.203443888s later, before portal startup**. The four measured font intervals totaled17s versus19s previously. Guest journal timestamps also place logind/PAM startup34s later, but those use synthetic realtime and must not be subtracted from monotonic measurements. Independent snapshot timing includes scheduling and collection overhead. The exact earlier source of the delay remains unproven.

Both logs show hardware-database, linker-cache and journal-catalog update jobs before system initialization. The fixture reconstructs RAM `/etc` and `/var`, and the exact packaged units condition these jobs on update state. This identifies recurring work to measure; it does not establish that these jobs caused the extra delay.

Named-container removal passed in0.417s and its absence check passed in0.034s. No clean application/session exit was established. The prior VM's lower-caret, OSK and four-focus-visit results remain separate scoped PASS evidence, while both overall VM results remain FAIL.

Next: isolate startup to authenticated readiness and retain PID1 handoff plus unit start/exit monotonic timestamps. Prepare a short mapped-app closure observation separately; do not repeat the full interaction flow solely to investigate teardown. Preserve the original interaction deadline and all guest/client limits. Phone physical rows remain NOT RUN.

Integrated active tier:105 PASS, zero FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED; three optional subchecks skipped. Runtime164.039s; worker captured exit0. The final runner entry includes74 tests under Python `-O`.

[Qualification JSON](2026-09-13-vm-cleanup-grace-qualification.json) records exact commands, hashes, source identities, timing and limitations.
