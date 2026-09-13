# Authenticated VM startup isolation — September 13, 2026

The previous full UI run reached cleanup near its300s limit, while a later attempt arrived at service startup29.2s later and never completed interaction. This change adds an explicit `--startup-only` mode to the existing generic ARM64 runner. It uses the same combined runtime preparation, PAM/device/session checks, VM resources,300s deadline and cleanup. It does not execute Denial or downgrade normal combined rendering qualification. UI-observer flags are incompatible with this mode.

Nine fixed systemd units are queried before PAM to record sysinit transition times. The collector is bounded to8s and16KiB, emits hex diagnostics and preserves failures. The host requires a complete loaded-unit inventory, typed timestamps, PID1 handoff and explicit startup readiness in addition to existing scope cleanup and poweroff checks. A diagnostic inventory PASS would not mean every listed unit executed successfully. No rendering evidence is claimed by this mode.

Initial source: `cbc9dbfbb1f5b1d9932fb7b03c02c3eeade38d90`.
Corrected source: `23f4a5a9cf976a9963e3b533f5d6042fd3d4d2cf`.
The kernel, Denial, Flutter, GTK, Wayland and mobile payload were reused. Only the small generic ARM64 harness helpers were compiled/staged; this creates no phone candidate, signing operation or admission.

The first four new tests fail on the previous implementation because the explicit mode/decoder are absent. Initial implementation:80 runner tests PASS under Python `-O` in12.557s wall time;8 existing diagnostic cases PASS in4.232s. The runtime failure then exposed partial-output loss and the console-prefix mismatch; new regressions fail before correction. Final9 focused cases PASS, including actual shell dispatch, query failure124/42, preserved partial bytes, continued PAM dispatch, invalid unit/timestamp data and console framing. Exact-clock and authentication boundaries remain fixtures in host tests; runtime claims below come only from the actual VM logs.

The first startup-only VM failed when its nine-unit systemctl query reached the eight-second deadline. The collector returned124 and aborted the session supervisor before PAM. QEMU nevertheless exited0 after normal guest poweroff; this is not authenticated-session success.

The corrected collector retains any bounded partial stdout with its original failure status, and a diagnostic failure no longer aborts the independent PAM/device/scope-cleanup probe. A new regression also corrects acceptance of actual bash[PID]: systemd console prefixes. Failed/partial diagnostics remain incapable of qualifying the full timing inventory.

The second VM again timed out the same query with status124 and zero captured bytes. It then completed authenticated readiness, mediated virtual devices, removed the session/scope and powered off normally. Its QEMU step lasted145.269s (158.862s including host preparation). This is a scoped generic-VM authentication/cleanup PASS; the timing-mode overall result remains FAIL and Denial rendering is NOT RUN. The initial source failed after166.514s of QEMU (180.422s total).

PID1 handoff was61.44s versus60.84s on the guest BOOTTIME clock. Those are separate from systemd monotonic transition timestamps, which were not obtained. The retained service resource lines include hwdb/ldconfig CPU usage but RemainAfterExit wall time includes active lifetime; it is not ExecMain runtime and cannot be summed into a critical path. No argument error is established. Zero captured bytes does not distinguish a stalled query from buffered output lost when it was killed. Neither attempt establishes the cause of the earlier29.2s delay.

Stop repeating full UI or identical nine-unit queries. Next smallest diagnostic: isolate one unit query and preserve live/partial output plus query start/end/status, under the existing bounded VM isolation. Test output buffering explicitly before attributing the lack of bytes to DBus or unit execution. Independently prepare a short mapped-app close observation: the prior UI proof and this authentication/cleanup result still do not establish Denial-client teardown. No phone operation is authorized; phone OLED/touch/Adreno and physical qualification remain NOT RUN.

Final integrated active tier:105 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED;3 optional subchecks skipped. Exit0 captured inside owning service, duration169.758s. Final runner contains83 tests under Python `-O`.

[Qualification record](2026-09-13-vm-startup-timing-qualification.json) retains both source/artifact identities, commands, controls, results and limitations.
