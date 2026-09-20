# Production display full-health integration — 2026-09-20

**Offline host qualification only. No phone, SSH, USB, VM, staging, candidate,
signing, admission, claim or protected-storage operation.** The previous logger
turn was progress. This turn adapts the existing full-health checker and its
session connection to the production identity and corrected acceptance protocol.

Start `20657b55c648b1194328fb9b8d9e27f1c52fe8ab`, tree `326c26dccfb747e08fd9bd02d5d31f6fad288972`.
Frozen implementation `2cfab2bc91e926ba02c835215488c18913cd6b4e`, tree `8032655698c604c98f3efdf5c8c680a8f3f1e756`.
Linux remains `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. Artifact pointer SHA256 remains
`5d168da495a9af5af842f24ad67631c58967f0b5c9bc8a148fab17c507ebd279`. No kernel/DT/module/Denial/Flutter rebuild.
Source changes do not alter signed or installed bytes. The four historical
health controls fail as expected; a fifth control demonstrates the old session
cannot call the new required health API.

## Corrections and evidence

The retained full-health checker required inactive rollback timers. The current
health helper intentionally keeps timers armed, so that requirement rejects a
healthy current protocol. Merely accepting active timers would be unsafe: the
probe helper can create the same timer name with an unconditional systemctl reboot.
The successor inspects loaded timer/service properties and the typed D-Bus
ExecStart, permitting only the guarded runtime rollback action, with empty extra
command hooks and successful quiescent services. Waiting and elapsed timers are
accepted; an executing service is conservatively refused. No timer is stopped,
started, reactivated or otherwise changed by this work.

Two historical counterexamples accept reordered descriptor/healthy records even
though runtime rollback requires canonical bytes. The successor checks exact
canonical text plus the admitted descriptor digest. The fourth counterexample
accepts pending persistent state when its hash is mistakenly sealed. The new
validator requires explicit healthy state, matching trial/bundle and schema,
in addition to the sealed digest. This does not repair or reinterpret a bad seal.

The collector embeds the already qualified endpoint source and checks production
identity before and after observation. Its inner root/readiness readers retain
their three-field contract. Owner and board hash remain admission bindings, not
independently observed physical identity. Guard owner, contract owner and private
seal owner must agree. The fingerprint comes from the future private seal.
The fixture's only normalization replaces the private fingerprint assignment;
original and normalized source hashes are in the qualification record.

The existing physical guard, input verifier and sealed binary reader are
unchanged. Tests still reject USB loss, unsafe thermal/voltage readings, wrong
write scope, altered runtime/firmware digests, stale boot/trial markers and
late health commits. The session passes the same contract/owner to script and
validator. Transport output hashes, timeout, child closure, post-observation
owner check and result publication retain their existing behavior.

## Personally executed checks

| Command | Cases | Wall seconds |
| --- | ---: | ---: |
| `python3 -O scripts/device/test-production-display-health.py` | 20 | 0.477 |
| `python3 -O scripts/device/test-production-display-session.py` | 28 | 5.083 |
| `python3 -O scripts/host/test-select-repository-test-tier.py` | 37 | 0.848 |

All85 focused cases PASS. Four old-health controls fail (three assertions and
one rejection at the obsolete timer predicate); the old-session API control
fails because required production arguments are absent. These are expected
negative controls, not failed successor tests. The initial selector command used
a nonexistent filename and exited2; its log is retained. The corrected existing
selector suite passed; passing health/session tests were not needlessly repeated.

The20 health cases execute actual predicates, the generated collection body and
real Endpoint identity logic against inert temporary proc/descriptor data.
Duplicate bundle tokens and a descriptor change after collection are rejected.
Systemd, root observation and physical-shell execution are explicitly stubbed;
there is no physical guard execution or phone observation. The28 session cases
include the actual health builder/validator over a fixture transport, refusing
pinned pending state without publishing a health result. Real process tests use
inert host children and virtual remote elapsed time, not phone or VM evidence.

The generated health fixture is23547 bytes (fixture request24509 bytes), below
the existing worker3MiB limit. This is not the size of a future private composed
guard. The target busctl JSON interface and complete35-second collection timing
still require exact composition qualification. Missing tools/errors fail closed.

Frozen `scripts/host/test-repository-linux.sh active` ran once:
**125 PASS,0 FAIL,0 BLOCKED,0 SKIPPED suites**;
255 NOT_SELECTED; 221.998 seconds.
Optional historical subchecks remain visible separately. Limits:1GiB memory,
zero swap,two CPU quota,256 tasks,600 seconds,two workers,disk scratch.
These are personally executed local checks, not imported GitHub CI results.

[Qualification](2026-09-20-production-display-health-qualification.json), SHA256
`1691f12fd3deb1a20ff0ac9a3e0abe75a53a5063f0e2083111d37ed83a172bb0`, records exact commands, per-suite durations and source/log hashes.
Private evidence: `rog5-display-health-20260920-r1` under the host state root.

## Community and upstream follow-up

Live Denial refs remain main `cd84b8b72f21024edc3da33d5f3c8dbe9ce44985`
and dev `5ab4004a36df28799b5f0636ee0cf31d1eba8c31`. No new upstream source
beyond the [retained community/upstream audit](2026-09-19-upstream-denial-community-audit.md)
was found. Earlier upstream command, coordinate and EGL dispatch fixes remain
useful; the reviewed modifier defects remain unresolved. No redundant rebuild
or patch retirement follows from unchanged refs.

The subreddit and linked Hotdog, wvkbd and Pocketblue pages were rechecked.
Same-SoC SM8350 source comparison remains the first kernel lead; Hotdog supplies
subsystem investigation ideas, wvkbd an independent protocol-test client, and
Pocketblue mobile browser configuration ideas. Other-board reports are not ROG5
qualification. No external code/package or firmware was imported.

## Limits and next step

The historical private source pins and health seal intentionally remain unchanged
and incompatible with this successor. No deployable composition or new authority
has been issued. Next: bind and qualify exact target staging/source admission and
private health inputs for the existing production cohort; verify firmware
root-transition lifetime. Do not create a new candidate merely for progress.

Once those prerequisites are qualified and physical operations are authorized,
the smallest unresolved hardware experiment remains the exact provider/panel
path preparing and accepting a zero command. Scanout, calibrated touch, GPU and
Denial session qualification remain separate. Physical **NOT RUN**, S06/R01 and
historical Denial VM failures **FAIL**; none is relabeled. No Ready requested.
The long-term phone goal remains active and incomplete.

Changed implementation files:

- `configs/repository-tests.json`
- `patches/display-controller/0004-production-session.patch`
- `patches/display-controller/0006-production-health.patch`
- `patches/display-controller/README.md`
- `scripts/device/fixtures/display-loader/health-before.py`
- `scripts/device/test-production-display-health.py`
- `scripts/device/test-production-display-session.py`
- `scripts/host/test-repository-linux.sh`
