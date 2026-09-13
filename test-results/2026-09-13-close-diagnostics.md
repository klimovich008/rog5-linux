# VM close diagnostics and recurrent missing icons — 2026-09-13

The VM **failed launcher readiness before any app launched**. All eight captures
show app labels without their icons; the coordinator inspected the first actual
capture. No action, acknowledgement or approved teardown occurred. Mousepad's
guest signal sender therefore remains **NOT RUN**, not resolved by this run.
The previous observed no-pan test/tes/test and cleanup137 remain separate evidence
in [the preceding report](2026-09-13-launcher-diagnostics.md).

## Implemented and verified

Source `b05ddefa4fba68e65511e9221a9d629d892bb6a6`, tree `69089e84e2ae840ca939ac1758949e3f2fd53fd6`, follows
starting commit `0015c0cc753df6fd5726ef866f898035affa6f77`. Three files changed: the authenticated VM supervisor
and its two focused test files. No kernel, native Denial, Flutter or session
archive was rebuilt. The manual VM runner compiled its existing small PAM/seat
fixtures and initramfs as usual; their exact commands and identities are recorded.

The supervisor now records timeout's own TERM/KILL diagnostics in a separate
regular guest log, then transfers a bounded excerpt after close. Client protocol
still uses its original FIFO. A thin bash exec restores that FIFO and preserves
the monitored client PID. Putting verbose timeout output on that FIFO was rejected
in review because a full pipe can block timeout before it sends a signal. A test
executes the production launch command against a full unread FIFO and verifies
that TERM still finishes promptly. Another test retains forced-kill137 as failure.

Boot-clock samples bracket close and return, including evidence transport; they
are not exact signal timestamps. The label is close-returned because Foot may
return an error before being reaped. Original65-second lifetime,2-second kill
grace,10-second controller close budget and all ACK/failure rules are unchanged.
Two compositor snapshots each allow30KiB framed output, reserving4KiB under the
unchanged64KiB diagnostic cap for close clocks and the bounded timeout excerpt.
Diagnostic text never qualifies a client or session.

| Personally executed check | Result |
| --- | --- |
| New close tests against prior source | 2 expected failures,2.633s |
| Final actual supervisor fixtures, Python-O | 27 PASS,7.782s |
| Final bounded snapshot fixtures, Python-O | 7 PASS,3.104s |
| Existing parser/socket/ACK suite | 51 PASS,3.060s |
| Diagnostic VM, same shell/native/kernel/archive | FAIL,233.810s |
| Frozen integrated active tier | {'PASS': 103, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255},154.539s |

Independent source review found no remaining blockers after the two diagnostic
corrections. It did not execute the tests. Three declared optional subchecks were
SKIPPED; no mandatory suite skipped or blocked. No new remote CI is claimed.

## VM evidence and remaining question

The failure was `launcher tile readiness not observed`, not a startup timeout.
The home screen was rendered. The observer received43,379diagnostic bytes, but
none identifies icon discovery/load/decode/invalidation stages. Retained scheduler
logs continue while later samples report no new render requests. This does not
establish a deadlock, decoding failure or driver bug. The same unchanged shell
has also rendered icons in a prior run, so this is an intermittent unresolved path.
The new app-close code was never reached and cannot explain this earlier failure.

All31 declared VM input hashes match after the failure. The runner terminated
and removed its owned VM; named-container absence checks passed. Host cleanup is
not normal guest shutdown or authenticated client/session cleanup. No new visual
typing, terminal rendering or physical qualification is claimed. No unchanged
second VM was started.

Next: instrument the exact home-tile icon path at resolution, byte load, decode,
completion/invalidation and frame presentation before another bounded comparison.
The retained home tile uses AppIconImage directly, bypassing DeferredAppIcon's
queue. App-specific errors and placeholders fall back to another SVG. Pinned
flutter_svg2.3.0 uses synchronous compute in debug but foundation.compute in
release; ordinary debug widget tests therefore cannot qualify that isolate
boundary. Trace DesktopAppSvgLoader.provideSvg through SVG byte encoding,
vector_graphics1.2.2 decode and completion/setState. Instrument copied pinned
package sources, preserving shared caches and loading behavior. Use the pinned
shell and actual production test seam; do not bypass the missing icons by
weakening readiness. Keep close diagnostics ready for the first run that
actually reaches the app-close boundary. Preserve current timeout grace meanwhile.

No phone, USB, signing, admission, claim consumption, phone candidate creation,
installation or protected-storage operation occurred. Physical rows remain
NOT RUN; S06/R01 remain FAIL; the native-phone goal remains active.

[Exact commands, source and artifact identities, and results](2026-09-13-close-diagnostics-qualification.json).
