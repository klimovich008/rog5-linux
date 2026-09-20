# Default-dark display-loader ordering — 2026-09-20

Offline source repair only. No phone, USB, SSH, VM, signing, admission, claim,
reboot or protected-storage operation. Physical results remain **NOT RUN**.
Previous goal turn was progress (default-dark panel module qualification); this
turn is progress (demonstrated controller failure and executable source repair).

Start `40a09cc4393b54a5b8b6a0bb02b2efd2060ddb9c`, tree `e452440e04ec8cbf02dc0d13d6a2b7b7eebea94d`.
Frozen implementation `32d9dbac4fa4abc1a2f1e2d0c32830d828222cdc`, tree `65bb7cfd90895cd3c28f8a3c41c16d5b461b8568`.
The ending documentation commit records this report; no history rewrite or push.

## Demonstrated failure and repair

The historical loader observer sends zero as soon as the backlight appears.
The new regression executes its actual Loader/insert functions against real owned
insertion children and the current compiled AMS678 driver with exact pinned DRM
and backlight-core extracts. Before preparation, the actual zero callback returns
EPERM even though the core property is zero. The old loader fails and reaps the
insertion child. This is host evidence of the ordering defect, not phone evidence.

The draft successor patch observes default-zero properties during insertion, then
requires completed/reaped insertions and a validated framebuffer endpoint before
one startup zero command. Command errors remain failures. Independent cleanup
still executes; its success cannot erase an original failure. A second regression
showed that losing health after successful zero could return loader PASS: a final
caller health/monitor check now catches that loss and preserves cleanup.

The exact Linux `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` source creates
fb0 before `fbcon_fb_registered()`; panel backlight registration precedes attach.
`drm_fb_helper_set_par()` also discards the modeset restore return. Current config
disables deferred fbcon takeover, but driver deferred probing remains asynchronous.
Neither fb0 nor successful insertion proves preparation. The deferred-preparation
fixture therefore still fails EPERM, including failed independent cleanup; no
startup retry, implicit modeset or permission exception was added.

## Personally executed checks

- Original loader with corrected driver: expected FAIL, one case,0.214s;
  EPERM and child reaping established. Preserved `before.log`.
- Initial fixture compile: FAIL (unused shared-fixture variable), preserved;
  only that fixture's unused variable reference was corrected.
- First post-patch run:12PASS/1FAIL,1.939s. Failure was an assertion expecting a
  libc error string while the fixture supplied its own; error type/errno used now.
- First complete ordering suite:16PASS,2.327s.
- Added post-zero health regression: expected FAIL before final gate,0.218s.
- Final focused suite:17PASS,1.965s, including automatic old-source rejection.
- Test-tier selector:37PASS,0.647s.
- Frozen integrated active tier: 113PASS/0FAIL/
  0BLOCKED/0SKIPPED suites,
  255NOT_SELECTED; 205.237s. Three declared optional
  historical subchecks remain separately skipped. New suite: 2.277s.

Focused commands used `python3 -O scripts/device/test-display-loader-ordering.py`
(with `--before Ordering.test_preparation_finishes_before_insertion_returns` for
old code and the named post-zero case for its failing control), and
`python3 -O scripts/host/test-select-repository-test-tier.py`.
Integration used `scripts/host/test-repository-linux.sh active`, with two workers,
1GiB memory/no swap,2CPU quota,256tasks and600s outer deadline. Final tests used
disk-backed TMPDIR; the initial failed tiny C compilation used system /tmp.
The regression's registration/observer handshake replaced a sleep window identified
in review; old-source rejection no longer depends on sampling within80ms.

[Qualification JSON](2026-09-20-display-loader-ordering-qualification.json) retains
exact integration commands, every suite duration, JSON/JUnit hashes, changed-file
hashes and private log identities. It is local execution, not GitHub CI.
Qualification SHA256: `ed416cc6070011156c78d59b91eb37a408be0c274d82b1c62b5b2e4cd586ce4c`.

## Scope and next dependency

The patch is **draft source**, not a deployable or admitted controller. Historical
controller/endpoint bytes and pins are unchanged. The fixture preserves the exact
old loader SHA256 `5c298ba05fe7a6f338471cd178a10b49cd9c03914f4a696ad442e7e0dbc1838d`; tests extract only
specified functions, never import the device controller. Identity/payload ownership,
sysfs and insertion effects are fixtures. Existing exact-file/ownership routines
are unchanged, not newly qualified by this test. The actual driver/core decides
preparation, zero-command return and property behavior; DSI/regulators remain stubs.

The production dependency indices were read and the14 transitive module bytes
hashed for REFGEN, panel, GPUCC and MSM. Their graph is retained in qualification;
this is a dependency inventory, **not reviewed hardware activation order**. The
historical two-module loader cannot be made production-ready by changing hashes.
Next: bind a separately reviewed successor to this production closure and qualify
its payload validation, one-use insertion order and independently owned cleanup.
It must include the corrected endpoint contract and default-dark panel identity.
No deployment or claim is prepared by this source patch.

Current panel hash remains
`79dc4d21db7726fd939acd10d35ce0f681fee07a847074734485c11008d72994`.
The current-artifact pointer is unchanged. No Image, DT, module, Denial or Flutter
rebuild was needed. Accepted headless/rescue, signed fallback and consumed claims
remain unchanged. S06/R01 and the previous Denial VM failures remain FAIL; this
turn adds no VM or physical qualification. The previous launcher intermittent
failure is retained; its suite passing here does not establish a fix.

Changed implementation files:

- `configs/repository-tests.json`
- `patches/display-controller/0001-default-dark-probe-ordering.patch`
- `patches/display-controller/README.md`
- `scripts/device/fixtures/display-loader/load-display-before.py`
- `scripts/device/test-display-loader-ordering.py`
- `scripts/host/test-repository-linux.sh`

Metadata adds this report/qualification, the existing structured project status,
its generated current-state header and one development lesson. No new state ledger.

Final metadata verification: `check-mobile-status.py --write`,
`check-mobile-status.py`, `python3 -O scripts/host/test-mobile-status.py` (8PASS,
0.022s), `check-artifact-inventory.py` (593sets;68small tracked hashes) and
`git diff --check` passed. Large/private inventory byte verification was NOT RUN
by that checker. Current artifact/inventory/acceptance/trial contracts are byte
unchanged from40a09cc4; only the generated current-state header changed, with
historical text preserved. Owned integrated service exited successfully,
3min25.310s runtime and307.6MiB peak memory,0swap. No owned job remains running.

Exact metadata files:

- `test-results/2026-09-20-display-loader-ordering.md`
- `test-results/2026-09-20-display-loader-ordering-qualification.json`
- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
