# Generation-9 lifecycle profile — offline transition

Date: 2026-08-03

Result: **PASS offline**. The diagnostic lifecycle now selects exact
Generation-9 recovery through a distinct live-capable profile. Generation 9
remains absent from temporary-boot policy. No connected preflight, credential
use, privileged host mutation, fastboot command, reboot, or phone action
occurred.

## Exact transition

The immutable `headless-diagnostic-generation9-offline-v1` profile continues
to permit only `policy-preflight` and `artifact-preflight`. The new
`headless-diagnostic-generation9-live-v1` profile pins the identical:

- AVB image `b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008`;
- raw recovery `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`;
- generation record `29beac5ec4ef88194927283a45427fcc89b95f94c4afa4fda9d6b24301fc9961`;
- AVB salt `4ddc34b9dace6d11338be71dba16797ff38e8f8e9e572cd61a6b1434c18b59df`;
- AVB digest `8c97c36eed4dab241bc3353b8f70dc0ece8301fb795362cb129fe331af6c8dc0`;
  and
- recovery kernel, initramfs, config, control, fetcher, verifier, signed
  bundle, runtime manifest, trust root, and host verifier.

The lifecycle selector changed from the previous
`headless-diagnostic-generation8-live-v1` to
`headless-diagnostic-generation9-live-v1`. No payload, artifact, inventory,
credential, or central-policy identity changed.

## Fail-closed evidence

- both Generation-9 profiles pass the exact five-field policy mutation
  matrix;
- both profiles locally pass complete artifact preflight against both retained
  host-local issuer trees;
- the offline profile rejects connected preflight and boot before host
  inspection;
- the live profile rejects direct connected preflight and boot before host
  inspection unless the one-shot lifecycle guard is present;
- even with that guard, both actions reject on the absent exact central-policy
  row before host inspection;
- the lifecycle tests select exact Generation 9;
- the generation-record mutation still fails exact artifact preflight; and
- `manifests/temporary-boot-images.tsv` remains unchanged with no Generation-9
  row and zero active `allow` rows.

This profile wiring itself does not admit connected preflight or boot. A
separate reviewed central-policy change is required before any connected or
phone-side action.

## Verification

- `scripts/host/test-run-minimal-headless-live-cycle.py`: pass;
- `scripts/host/test-run-stable-recovery-live-gate.sh`: pass;
- shell syntax and `git diff --check`: pass;
- central temporary-boot allow count: zero; and
- complete repository Linux `ci` tier: pass.

The constrained Claude Opus review confirmed exact tuple reuse and the
zero-policy stop. It identified four actionable clarity/coverage gaps: the
boot-image path was scoped to the live profile only, a Generation-10
unsupported-name policy test restores the future-profile boundary, roadmap
status remains in progress until publication, and historical Generation-4
wording is now unambiguous. The executable lifecycle fixtures already verify
that both diagnostic preflight and boot supply the lifecycle guard.

The predecessor offline issuance passed complete local CI and exact-head
GitHub Actions [run `30841980164`](https://github.com/klimovich008/rog5-linux/actions/runs/30841980164)
at commit `6193056` before this separate transition began.

No private credential, recovery signing key, privilege, USB interface, phone,
network listener, NFS export, or phone storage was used.

## Subsequent transition

The separate
[Generation-9 one-shot admission](2026-08-03-generation-9-live-admission-offline.md)
later added the exact central-policy row without changing this historical
zero-policy profile checkpoint. Generation 9 remained unbooted during that
offline admission work.
