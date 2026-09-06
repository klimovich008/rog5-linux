# Stable-recovery exact UDC selection — offline

Date: 2026-08-09
Starting repository SHA: `4ce783145bc060f72cf4272c32ba30d0b9543332`
Recommendation: **HOLD**

## Outcome

Stable recovery no longer falls back to the first arbitrary USB device
controller. It waits only for one exact `a600000.dwc3`, requires that sole
candidate to remain unchanged across two observations, revalidates it
immediately before binding, and proves the same sole candidate is still bound
after the configfs write. Zero candidates retain the existing bounded
20-second wait; zero-at-deadline, wrong, renamed, multiple, or changing
candidates fail closed into the already-armed recovery rollback.

The concrete defect was in `initramfs/recovery-init`: a nonmatching first UDC
became the fallback candidate, and a substring match containing `a600000`
could be selected without proving uniqueness or stability. That could attach
the recovery ACM/NCM control plane to an unexpected controller and make future
postmortem observations ambiguous.

No protocol, address, responder, storage-isolation, watchdog, fallback, or
one-use lifecycle behavior changed. No phone, credential, signing key,
candidate, policy row, wrapper, flash, wipe, slot, phone storage, or boot was
used.

## Patch and regression boundary

- `initramfs/recovery-init` now uses fixed `expected_udc=a600000.dwc3`, exact
  candidate counting, two-sample stability, pre-bind revalidation, and
  post-bind identity proof. The arbitrary-first fallback was removed.
- `scripts/device/verify-stable-recovery-initramfs.sh` requires the exact UDC
  identity and helper surface under `exact-a600000-v1`, rejects the former
  fallback, and preserves the session-before-bind ordering proof. Immutable
  consumed artifacts use a distinct `historical-pinned-v1` contract only
  after the gate proves their exact archive hash; a current exact archive
  cannot downgrade into that contract.
- `scripts/host/test-recovery-init-policy.py` executes the production shell
  functions against private synthetic sysfs/configfs trees.

The fail-first policy run rejected the old source with two failures in 0.07
seconds because no exact-selection functions existed. The fixed 11-group run
passes in 0.18 seconds and covers:

- one exact controller and delayed exact enumeration;
- no controller through the bounded deadline;
- one wrong or renamed controller;
- exact plus an unrelated second controller;
- replacement between the two stability samples;
- identity loss between selection and binding;
- identity loss after the configfs write;
- no UDC write before a successful exact selection.

The first complete repository CI run exposed the historical/current verifier
conflation after 195.55 seconds: Generation-3's immutable archive was compared
with the current recovery init and failed at byte 312. The fixed historical
live-gate regression passes in 166.72 seconds, while exact archive identity is
proved both before and inside its historical contract. Shell syntax and
`git diff --check` pass. The final complete hardware-free repository CI tier
passes on this exact working tree in 458.87 seconds (`user 144.39`, `sys
148.13`); its embedded historical live-gate run passes in 166.96 seconds.

## Reproducible recovery composition

The final two clean shell-free initramfs builds using reconstructed base
profile `reconstructed-v18r-v1` completed in 92.77 seconds and compare
byte-for-byte:

| Component | Size | SHA-256 |
|---|---:|---|
| recovery init source | — | `19020d0d099de5495c432927fea940f9ccd4f2033d2046d281462b19c59c3320` |
| native recovery responder | 132,896 | `897a521c94557152a466f33c295f008100e3a183d84f94bf767c65bf49f91fea` |
| fixed bundle fetcher | 132,824 | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| native bundle verifier | 4,467,272 | `33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef` |
| disposable public trust input | 32 | `1126cf7255c1727b049d2ad192a835375f98fde2ede4a13424e43e1554bb0ac8` |
| stable-recovery initramfs A/B | 7,602,307 | `afc55f96157079594a4241b380f2c02a6c6d77877d6e9b3b0872c306a6c0d790` |

The ignored evidence occupies approximately 19 MiB below
`build/recovery-exact-udc-offline-20260809-r2/`. It is test evidence only: the
trust input is disposable, no ASUS wrapper was rebuilt, and no bootable or
signed candidate exists.

## Remaining critical path

This removes one recovery-controller ambiguity but does not prove physical
USB enumeration, NFS behavior, or ramoops retention. The next hardware-free
observability increment should define and prove a distinct observation-only
recovery composition that can report correlated postmortem status but cannot
prepare or execute a payload. A later physical retention experiment still
requires separately reviewed one-use execution and observation identities.
Admission remains **HOLD**.
