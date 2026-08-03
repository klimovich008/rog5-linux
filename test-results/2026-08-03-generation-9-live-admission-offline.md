# Generation-9 lifecycle admission — offline result

Date: 2026-08-03

Result: **PASS offline with complete local CI; publication pending**. Central
temporary-boot policy now admits exactly one Generation-9
recovery-ACM-classifier lifecycle after connected preflight. Generation 9
remains unbooted. No connected preflight, credential use, privilege, USB
discovery, fastboot command, reboot, phone action, or phone-storage access
occurred.

## Exact admission

The single active policy row admits only:

- path
  `build/stable-recovery-generation9-acm-classifier-20260803-a/repack/stable-recovery-a.avb.img`;
- size `100663296` bytes;
- SHA-256
  `b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008`;
  and
- basis `one generation-9 recovery-ACM-classifier diagnostic lifecycle after
  connected preflight; remove after any result; never flash`.

Issuance authority remains `none` in the artifact inventory. The central
policy is a separate one-shot admission and does not change the immutable
offline profile. It admits neither flashing nor a second execution.

## Fail-closed evidence

- central policy contains exactly one `allow` row and it is the exact
  Generation-9 path and basis above;
- the live profile requires both the lifecycle guard and that exact row;
- missing, duplicate, and wrong-basis policy fixtures reject both connected
  preflight and boot before host inspection;
- the immutable offline profile continues to reject connected actions before
  host inspection;
- an existing private per-profile consumption record rejects a run before
  connected preflight, while the first run atomically creates a mode-`0600`
  durable `BOOT_CLAIMED` record after successful preflight and immediately
  before boot; failed or standalone preflight leaves no claim, and every
  successor must use a distinct recovery-profile name;
- both retained 11-file Generation-9 twin sets are byte-identical and pass
  exact artifact preflight;
- the Generation-9 image remains distinct from every consumed Generation 1–8
  identity; and
- the admission must be removed after every accepted, rejected, interrupted,
  or ambiguous result. Generation 9 must never be retried or flashed.

The compatibility hash chain was refreshed to the policy-aware inventory:

- artifact manifest:
  `02ddf1ce6e6e4c39ec8a1d270952eab613db5c0eb55fc096a41c08d4c6e8339c`;
- minimal-headless profile:
  `3a7e951926f89984ac4e19e1abf8990cbadac57421fcef5e288e70f38ea04281`;
  and
- source/DT profile:
  `5a712ff1409c05ffea54692f748247afd45a36b68a2f45889bd4e7c226db9b3e`.

## Verification

- shell syntax: pass;
- minimal-headless lifecycle controller: 64 tests pass;
- `scripts/host/test-recovery-linux.sh`: pass;
- `scripts/host/test-run-stable-recovery-live-gate.sh`: pass;
- compatibility oracle: 39 tests pass;
- source/DT contract: 74 tests pass with one expected optional skip; and
- native recovery-fetch suite: 31 tests pass in three consecutive standalone
  runs; and
- complete repository Linux `ci` tier: pass.

The complete suite exposed a test-harness-only scheduling race: the raw fetch
server treated one 100 ms delay while waiting for the helper's canonical
request half-close as a protocol error. The harness now performs bounded
polling for at most two seconds, matching its existing request-read behavior.
Production fetch code, production transport limits, and phone behavior are
unchanged.

The predecessor live-profile transition passed exact-head GitHub Actions
[run `30843398402`](https://github.com/klimovich008/rog5-linux/actions/runs/30843398402)
at commit `4979581`. This admission has passed constrained review and complete
local CI; it must be published and pass exact-head GitHub CI before any
connected action.

No private credential, signing key, network listener, NFS export, phone, or
phone storage was used.
