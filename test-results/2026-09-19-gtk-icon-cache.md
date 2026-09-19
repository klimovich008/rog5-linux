# GTK icon cache repair — 2026-09-19

**The production VM helper now reconstructs the missing GTK icon caches.**
Real ARM64 GTK running as UID1000 enumerated the same1030 icon names, resolved
four matching paths and mapped all three caches. Packaged systemd then powered
off normally. This is VM software evidence, not phone or full Denial acceptance.

Starting source `e4874f78b711588a40b1cf2166e7c91d18081928`, tree
`cfe63b3e04871d2d2ba02b8775bf43bc90e38632`; tested source
`23d9a942e3047e849747fcf271168d990398bea8`, tree `366b32488ff8fd14a4571688e5529a8cf2a50dc2`.
No kernel, GTK, Denial or Flutter rebuild. The only new compiled executable is a
small headless GTK measurement fixture, linked to the exact retained ARM64 runtime.
Its SHA256 is `15b5b6630186e4e3a243f2cfc6bf6418faad0e5284dcbeb394a979cb2f11d693`.

## Evidence and implementation

The extracted package runtime lacks icon-theme.cache in Adwaita, AdwaitaLegacy
and hicolor. The actual packaged gtk-update-icon-cache hook was not run during
extraction. GTK recursively scans directories when a theme cache is absent.
The headless fixture calls real GtkIconTheme APIs without opening a display;
its source, binary identity, commands and raw-result excerpts are in the paired
qualification JSON. All3575 asset entries in the uncached and cached comparison
views match the authenticated materialized tree (regular bytes/symlink targets).

| Measurement | Result |
|---|---:|
| Uncached enumeration, first control, readonly9P | 5.183975s |
| Cached enumeration, same9P experiment | 0.229572s |
| Uncached enumeration, second control | 5.219698s |
| Final production overlay, UID1000 enumeration | 0.109519s |
| Final cache generation in VM RAM | 9s shell-clock resolution |
| Final minimal systemd VM including normal poweroff | 34.016s |

All comparisons returned1030 names with SHA256
`fc88f5ae08017b0b1bdc458556bd27b8b6f3046ddfd5dc1d6618f5625cae482c`.
The four tested names are document-open, document-save, edit-copy and window-close.
/proc/self/maps proves cache mappings0/3/0 in the first controlled comparison and3
in the final mobile-UID run. These checks do not decode or compare image pixels.

`logind-icon-cache.sh` uses the existing kernel's overlay filesystem: the package
icons remain in readonly9P; only generated caches and directory metadata enter
private RAM. It bounds real packaged tool calls, validates nonempty caches,
handles inheritance-only aliases, and mounts the finished view readonly with
nodev/nosuid/noexec. It removes its temporary writable mount before success.
On failure it unmounts only owned mounts and retains scratch when unmount fails,
so cleanup cannot recursively traverse a remaining mount. PID1 preparation is
the only production entry. The host runner inventories and stages the helper.

13 focused host cases passed normally and under Python -O, including actual GTK
cache validation, inherited default, missing/invalid output, tool failure,
interruption, existing mounts, remount failures and failed-unmount retention.
The inheritance-only default regression failed before the correction. The first
seven-test version also failed before the helper existed; that only demonstrates
the missing implementation, not end-to-end startup behavior.90 existing VM-runner
cases passed. The final active-tier command ran once on the frozen final source;
it passed109 suites in176.094s, with0 FAIL/BLOCKED/SKIPPED and255 NOT_SELECTED.
Three declared optional subchecks were SKIPPED separately; they are not executed
qualification. Peak memory was541.3MiB with no swap. Complete JSON results, exact
commands and timings are in the qualification; JUnit is retained privately at
`rog5-icon-cache-integration-20260919-r4/active-report/summary.xml`.

## Failed attempts preserved

- Full-tree copy attempt: FAIL after the30s copy deadline; guest PID1 panicked.
  Expanded27MB copying was removed rather than extending the deadline.
- First overlay experiment: FAIL because a filesystem remount invoked unsupported
  overlay reconfiguration. The final code changes VFS bind flags instead.
- First final-helper guest: FAIL at the packaged default inheritance-only theme,
  whose successful tool invocation deliberately produces no cache. The bounded
  trace identified this; no cache timestamp hypothesis was established.
- Subsequent systemd guest: cache generation/mount and shutdown passed, but UID1000
  lookup was NOT RUN because the minimal fixture omitted the account (217/USER).
- Final guest: added the normal session's account prerequisite; actual UID1000
  lookup, three mapped caches and normal poweroff PASS. No production change was
  needed for the account fixture error.

Every attempt remains retained. Both extra diagnostic overlay runs and their
exact commands remain separate from final production evidence. The final guest
uses1GiB host/no swap,2CPU,64pids;512MiB guest,1vCPU,90s host deadline and8MiB
logs. Network/GPU exposure is absent. Retained kernel SHA256 is
`2b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc`.
Final VM initramfs SHA256 is
`7a8a24b1b598760f63d35869e7a6fa917a6060d561252471ec19ed80c797a17a`.
All nine experiment containers are absent; final17 input and9 output identities
passed rechecks. This runtime fixture has no phone boot or installation authority.

## Next boundary and run improvement

The earlier low-caret full-session120s timeout remains FAIL. Cache generation
cost is outside the app interaction window; it is not yet evidence that total
Denial startup improved. Next measure portal and Mousepad startup in a bounded
native VM session with this helper, unchanged packages/kernel/graphics and
unchanged deadlines. Do not repeat proven typing merely to qualify cache setup.
GdkPixbuf loaders.cache is separately absent and remains unqualified.

The previous turn only reverified completed storage receipts; it did not advance
Denial. This turn is PROGRESS: a demonstrated package-hook omission now has a
production repair, regressions and non-root ARM64 runtime/shutdown proof.
Avoid copying thousands of9P files to save directory lookups. Reuse exact validated
linker-cache staging by its recorded input/output hashes during fixture iteration,
rather than repeatedly walking the unchanged runtime. Preserve setup semantics
(account existence and pre-PID1 mount order) in reduced fixtures. No deadline
increase, full UI repetition, phone operation or hardware acceptance claim.
Physical tests remain NOT RUN; S06/R01 remain FAIL; the real-phone goal stays open.
