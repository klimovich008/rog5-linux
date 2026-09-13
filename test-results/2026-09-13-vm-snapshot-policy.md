# VM snapshot policy repair and controlled app close — 2026-09-13

**Source repair and105 integrated checks PASS; complete VM session FAIL because Mousepad exits137. Phone physical tests remain NOT RUN.** Both apps map/focus in the changed VM; Foot closes0. This is generic ARM64 VirGL evidence, not ASUS/Adreno evidence.

## Demonstrated defect and repair

At source90ee0f2bad927ac642d808afdb9fb0e822a9d2fd (treefc23d23635017b242584884805e01eb0a88ba96e), the close-only control VM records `controller-exit phase=snapshot-periodic status=124`, then cleanup terminates Mousepad143. A single3-second timeout covered local diagnostic processing and required FIFO transport. The retained log establishes that controller failure chain, but not which pipeline stage was slow.

Source `b5e13cc97ff9d0e0e10e3f96a864d1a41cacc897` / tree `c6b977a420dcf2238590b2e8ae1d6570dd27b594` changes four files:

- `tools/qemu-virtio-drm/logind-apps.sh`: prepare bounded diagnostics in a0600 temporary file within an owned function subshell; discard partial preparation. Local124 becomes explicit `DENIAL_DIAGNOSTIC snapshot-prepare status=124 optional=NOT_RUN`; required marker transport must still succeed. All other preparation failures, transport failures and cleanup failures remain fatal. EXIT/TERM/INT cleanup preserves original nonzero status. SIGKILL cannot run traps; any residue is bounded private guest scratch, not acceptance evidence.
- `scripts/host/test-launcher-diagnostics.py`: actual producer, FIFO, writer, interruption and cleanup fault tests.
- `scripts/host/test-logind-apps.py`: actual controller, initial/periodic optional failure, both owned app processes, exact ACK and exit0 regression.
- `configs/repository-tests.json`: add actual prerequisite tools; host suite deadlines15→30s and30→45s accommodate measured12.715s/24.442s suites and new real waits. No app, ACK, VM, kill-after or cleanup-grace deadline changed.

The former joint3-second snapshot limit becomes separate3-second preparation and2-second transport limits. FIFO open is inside the transport timeout. This is an intentional per-stage policy change, not a claim that all timing stayed identical. Diagnostic bytes remain excluded from mandatory protocol/render/ACK/exit qualification.

## Failing before / passing after

Four selected diagnostic regressions produced3 failures and1 pass before the fix (9.034s); the actual initial controller regression failed before readiness (5.066s). Final22 diagnostic tests PASS12.715s,39 controller tests PASS24.442s, all under Python `-O`. Syntax and whitespace checks PASS. Independent read-only review found no blocking issue; reviewer did not execute tests or hardware.

The initial post-fix controller fixture was too broad: its fake `head` also broke the required2048-byte close-log replay. It was narrowed to the exact1048576-byte optional preparation call. That fixture failure is retained separately; no required production close check was weakened to make it pass.

Commands: `python3 -O scripts/host/test-launcher-diagnostics.py`, `python3 -O scripts/host/test-logind-apps.py`, `bash -n tools/qemu-virtio-drm/logind-apps.sh`, `git diff --check`, then `scripts/host/test-repository-linux.sh active` once on frozen source. Integrated result:105 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED;3 declared optional subchecks skipped. Duration177.134s, peak565.7MiB, no swap. Exit0 was captured inside the owning service; this is personally executed local evidence, not an imported GitHub result.

## One changed VM probe

Same retained kernel, runtime receipt, container images and session archive as the control. No Denial/Flutter/kernel rebuild. Small VM helper compilation/packing is retained in the command/step record. Both helper binaries and the other guest scripts match the control; changed output records are the snapshot script, containing initramfs, per-run random ACK token and execution logs. Runtime inventory/authentication is a retained prerequisite, not a fresh full root inventory in this run.

| Observation | Control | Changed source |
|---|---|---|
| Overall command | FAIL253.510s | FAIL310.942s |
| QEMU process | killed after observer failure240.251s | exits0 after296.834s |
| Snapshot outcome | periodic124; precise pipeline stage unknown | no snapshot timeout observed |
| Mousepad/Foot mapping and focus | incomplete | PASS; sequence mousepad, foot |
| Exact ACK / approved teardown | false / false | true / true |
| Foot / Mousepad exits | incomplete / early143 |0 /137 |
| VM poweroff | not qualified | observed normal poweroff |
| Container cleanup/absence | PASS | PASS0.038s/0.034s |

Overall FAIL is retained despite QEMU exit0 and normal poweroff. This was not the300-second interaction deadline or an expired cleanup grace; the requested app cleanup failed. No text entry or OSK qualification is claimed from this close-only mode. Prior full caret/OSK scoped evidence is retained separately.

Source snapshot in the guest: `ad6675faab8523a5f3ff721643d96179e234feffdcad9ff60d54809b64086b1a` (18871bytes). The complete command, kernel/container/payload identities, both result hashes, guest output hashes, JUnit/counts and raw-evidence references are in the [qualification record](2026-09-13-vm-snapshot-policy-qualification.json). Private evidence root: `/home/deck/.local/state/rog5-vm-snapshot-policy-20260913-r1`.

Visual inspection of `01-mousepad-launched.png` and `03-foot-launched.png` confirms a rendered blank Mousepad document and controlled Foot prompt. It does not establish text entry, physical input calibration or successful Mousepad shutdown.

## Interpretation and next action

The source defect is demonstrated by failing-before/passing-after actual-function fixtures: optional local preparation124 previously prevented readiness. It now produces a bounded NOT_RUN record; required transport and non-timeout/cleanup failures remain fatal. The old3s combined deadline is now3s local preparation plus2s required transport, with no change to app/ACK/VM deadlines. No claim is made that the control VM124 came specifically from local preparation rather than its former combined pipeline.

Treatment reached Mousepad/Foot mapping and focus sequence, exact ACK, approved teardown, Foot0 and normal VM poweroff. Mousepad137 keeps overall FAIL. No snapshot timeout or optional NOT_RUN marker occurred in this VM; non-reproduction alone does not prove what consumed the old joint deadline. The source policy correction is proven offline.

The new close evidence identifies an explicit controlled-stop chain: supervisor calls stop_owned_group normal-close editor, which sends TERM to its owned GNU timeout PID904. GNU timeout records forwarding TERM and KILL. The Mousepad supervisor owner has raw start ticks24285; close begins at BOOTTIME280.40 and returns282.70. These close samples bracket waits and evidence transport; they are not exact signal timestamps. Owner start ticks are preserved raw, without converting them to a clock sample. The explicit controlled-stop route already explains forwarded TERM; these records do not establish expiry of the65-second child deadline. The two-second kill-after can activate after forwarded TERM. Why real Mousepad did not exit normally in that interval is unresolved; do not lengthen it speculatively or accept137 as success.

Next inspect the exact packaged Mousepad application shutdown API and its Wayland/GApplication behavior; build a source-coupled bounded normal-quit regression before another VM. A genuine normal application quit request may be appropriate, but its availability/semantics are not yet established. Do not replace the program with a trivial client, weaken exact owner/ACK/exit0 guards, or repeat the unchanged run. Full prior bottom-caret/OSK evidence remains scoped historical PASS; combined clean close, installed phone Denial/touch/Adreno and physical acceptance remain unqualified. S06/R01 remain FAIL. No phone operation is authorized.


Source/code qualification belongs to `b5e13cc97ff9d0e0e10e3f96a864d1a41cacc897`, not the later metadata commit. The original dirty checkout, historical source/artifact rows, signed V11 fallback, accepted server/rescue and all consumed claims remain unchanged. No phone/USB/SSH/fastboot, signing, admission or protected-storage operation occurred. S06 and R01 stay FAIL; installed Denial/touch/OLED/Adreno acceptance stays NOT RUN.

Metadata/report changes: configs/project-status.json, docs/current-state.md, docs/development-lessons.md, manifests/artifact-sets.json, manifests/current-artifact.json, this report and its paired qualification JSON. Existing artifact rows/pointers remain; one fixture set was added. Post-result checks PASS: artifact inventory540 sets (0.114s), generated mobile status (0.064s),19 metadata-checker regressions under Python -O (2.069s), whitespace (0.064s). Large/private artifact-byte verification by the metadata checker is NOT RUN; exact VM input/output identities are separately retained in this qualification. No second full integrated run was needed for metadata-only additions.
