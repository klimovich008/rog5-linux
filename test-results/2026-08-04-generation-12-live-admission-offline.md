# Generation-12 live profile and one-shot admission — offline

Date: 2026-08-04

Result: **PASS — the published authority-free Generation-12 recovery now has a
separate exact live profile, one lifecycle selector, one central-policy
admission, and a dedicated irreversible boot-claim consumer. All work and
verification in this transition were host-only. Connected preflight and phone
boot remain separate future actions.**

## Starting checkpoint

The deterministic Generation-12 twins were issued and reviewed as an offline,
unbooted successor at AVB SHA-256
`615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6`.
Commit `52ce322` published that authority-free checkpoint. Exact-head GitHub
Actions run `30935842119` passed recovery-core in 4m11s and QEMU in 35s.

The successor preserves the exact Generation-11 raw recovery, kernel, config,
and NCM-capable initramfs. Its only payload change is a distinct deterministic
AVB generation. Generation 11 remains consumed, absent from policy, and never
reusable.

## Transition

- `headless-diagnostic-generation12-live-v1` pins the same complete recovery,
  trust, signed-bundle, manifest, host-verifier, target, and AVB-generation
  tuple as the immutable offline profile.
- The one-shot lifecycle selects only that live profile for the next
  diagnostic sequence.
- `manifests/temporary-boot-images.tsv` contains exactly one `allow` row: the
  Generation-12 twin-A AVB path with basis `one generation-12
  host-confinement-corrected diagnostic lifecycle after connected preflight;
  remove after any result; never flash`.
- Direct connected actions reject unless the lifecycle guard is present.
- The gate copies policy and artifact inventory once into a private invocation
  snapshot before durable claim entry, validates that snapshot early, and
  reuses the same bytes at final image-path admission. Concurrent path changes
  cannot mix policy generations inside one execution.
- `boot` invokes only `consume-generation12-boot-claim.py`. The consumer
  validates the exact owner-only state root and exact 0600 claim record, links
  it to a durable entered name, verifies inode/content identity, fsyncs the
  directory, removes the source, revalidates that the canonical pathname still
  names the opened root, and refuses reuse.
- The artifact inventory remains `unbooted`, `authority=none`, and `never
  flash`; its complete role text and `tracked=no` state are pinned by the live
  profile gate. The central policy is the separate execution authority.

## Hardware-free verification

- Generation-12 claim consumer: **11/11 pass**. Coverage includes exact one-shot
  entry, reuse, wrong/extra content, unsafe metadata, symlinked record/root,
  hostile `HOME`/`XDG_STATE_HOME`, a symlinked passwd home, opened-root
  replacement during initial validation and after durable entry, pre-existing
  entered record, and record-path replacement after validation.
- Minimal-headless lifecycle: **69/69 pass**. The controller creates the exact
  Generation-12 durable claim only at the non-retryable run boundary;
  diagnostic preflight stops before phone access and creates no claim.
- Stable-recovery live gate: **PASS**. Both retained twins pass both offline
  and live artifact profiles. Direct bypass, claimless boot, missing or
  duplicate rows, malformed headers, wrong basis, denied status, identity
  mismatch, consumed or altered-unbooted role, tracked-state mutation, and
  policy/artifact trailing fields fail closed before host inspection.
- Recovery policy aggregate: **PASS**. It requires exactly the sole
  then-pre-consumption Generation-12 admission and exact authority-free
  inventory row (Generation 12 is now consumed and never reusable)
  while continuing to reject every consumed generation.
- Shell/Python syntax and `git diff --check`: **PASS**.
- Complete local repository `ci` tier: **PASS**, including the retained exact
  Generation-12 twin gate and all recovery, lifecycle, builder, source/DT,
  compatibility, and QEMU contracts selected by that tier.
- Independent standards/security and specification/documentation re-reviews:
  **PASS — no remaining actionable P0–P3 findings**.

Publication, exact-head GitHub CI, and connected preflight are the remaining
gates for this transition.

The production producer and consumer both derive the claim root from the
passwd database home for the effective UID, not caller-controlled `HOME` or
`XDG_STATE_HOME`; that home is canonicalized once before producer/consumer path
construction, and the lifecycle contract test requires both calculations to
remain identical. A failure after the entered hard link is published burns the
candidate without a phone boot. It must not be repaired or retried by editing
the record; a distinct successor generation is required.

## Effects and authority boundary

No credential, signing private key, ADB, fastboot, ACM, NCM, SSH, phone reboot,
phone boot, flash, erase, wipe, slot operation, phone-storage mount, or phone
write occurred. The current operator standing authorization permits later
in-scope preflight and gate-admitted temporary boot without another consent
prompt, but it does not remove any technical gate or the temporary-boot-only,
no-flash boundary.
