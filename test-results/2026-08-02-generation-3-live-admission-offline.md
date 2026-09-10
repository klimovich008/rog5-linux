# Generation-3 live admission

Date: 2026-08-02

Result: **PASS offline — the fresh-fetch generation-3 recovery is admitted as
the sole temporary-boot image for one connected-preflight-gated RAM-only
diagnostic cycle. No phone interface, credential, reboot, or boot was used.**

The published `headless-diagnostic-generation3-offline-v1` profile remains
immutable and rejects `preflight` and `boot`. The separate
`headless-diagnostic-generation3-live-v1` profile reuses the same exact
artifact implementation and pins:

- AVB wrapper `eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6`;
- raw wrapper and deterministic AVB salt
  `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`;
- recovery initramfs
  `144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec`;
- fresh-only fetcher
  `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800`;
- signed runtime manifest
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`;
- production public trust root
  `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b`;
  and
- host verifier
  `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621`.

The lifecycle now selects only the live profile for diagnostic execution. Its
deny-by-default boot policy row requires the exact bundle, NFS handoff,
receive-only diagnostic collector, and verified Alpine fallback. The row is
one-shot: remove it after any boot result, including ambiguous or failed
execution, and never flash the image. The gate refuses direct generation-3
boot without the lifecycle guard, and the controller passes that guard only
to its boot child after admission and connected preflight have completed in
the same invocation; the boot child repeats all artifact and connected
fastboot checks. This environment guard records the reviewed invocation path,
not an unforgeable caller identity. Consumption remains the existing
versioned-policy operation: remove the sole allow row immediately after any
result; the gate does not modify Git itself. The historical generation-2
profile is offline-only.

Hardware-free verification covers both generation-3 profile names, every
caller-supplied identity mutation with its exact rejection reason, every
internal artifact pin, the unique allow row and matching artifact identity,
the full retained 9.4 GiB production tree under both profiles, and all 41
lifecycle regressions. Connected preflight remains the next required gate.
Independent standards and specification reviews prompted the explicit
lifecycle-guard wording and historical-profile retirement; Claude's final
tool-free review returned `NO FINDINGS`.
