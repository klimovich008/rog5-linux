# Early-target diagnostic production build

Date: 2026-08-01

Result: **PASS — the exact diagnostic successor was signed with the external
project Ed25519 key, twin-built byte-for-byte, and admitted by the complete
production artifact gate. No phone interface was contacted.**

## Scope

The guarded production builder ran from clean, synchronized checkpoint
`529f3aaef33e55f72a354547ecc32364936a3af6` against the immutable
`headless-netroot-early-diag-v1` candidate. Before signing, its dedicated
signing-input preflight staged and validated the exact candidate and key,
scrubbed the child environment, destroyed the private snapshot, and produced
no signed output.

The full operation then made two clean ASUS 5.4 wrapper builds, two signed
runtime bundles, two recovery initramfses, two raw boot-v3 images, and two
test-only AVB wrappers. Every A/B pair is byte-identical. The source key was
unchanged, the private build snapshot was destroyed, and only the raw public
trust key remains in the ignored output.

## Pinned diagnostic tuple

| Artifact | SHA-256 |
|---|---|
| signed manifest | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| recovery public trust root | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| recovery AVB wrapper | `9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef` |
| raw boot-v3 wrapper | `0d101a12ff456414fda7bb0e0c2b5e4c8f61e5469625bb6b75214e2fc6497f9a` |
| ASUS wrapper `Image` | `d348cdfedccb55aabf15eb97b5136f2e45ba906b85989c6c7c3b842914f69eb5` |
| wrapper configuration | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| stable-recovery initramfs | `cd30a2067322edc12c3be172cd05bd5d365a1ad09815594b8fa56302cd0b813b` |
| recovery responder | `f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77` |
| bundle fetcher | `677fa731b1bd9fd11efc46aabeb32e7a725725483c86a2f58d417f482c27f392` |
| target bundle verifier | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| host bundle verifier | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |

The signed payload itself retains the previously accepted identities:

- Linux `Image`: `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf`;
- corrected board DTB: `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`;
- diagnostic initramfs: `10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c`.

## Independent admission

The production diagnostic profile is separate from the consumed r2 profile.
The r2 wrapper, kernel, initramfs, verifier, and host-verifier pins remain
unchanged. The diagnostic profile alone advances to the tuple above.
The central deny-by-default temporary-boot policy now lists the exact ignored
wrapper path once for the authorized diagnostic cycle, and the artifact
inventory binds that path to size 100,663,296 and the AVB hash above. Connected
preflight and boot fail unless both central records remain exact. The admission
row must be removed after candidate resolution; the one-shot payload and
no-ambiguous-retry rules remain independently enforced by the lifecycle.

Its credential-free `policy-preflight` emitted the exact canonical profile,
bundle, manifest, target, wrapper, trust, and host-verifier record with
`authority=none`. The complete `artifact-preflight` then verified:

- all A/B comparisons and every pinned SHA-256;
- the shell-free stable-recovery archive and embedded public key;
- the signed bundle through the native host verifier;
- the raw boot image against the AVB hash descriptor;
- the header-v3 kernel, ramdisk, and command line; and
- absence of phone-storage, legacy-network, and persistent-write inputs.

`avbtool verify_image` passed the embedded `NONE` vbmeta/footer structure and
the boot hash descriptor. This is a temporary-boot wrapper integrity check,
not OEM signing and not authorization to flash it.

## Review and regression

- The stable-recovery live-gate contract passes with independent normal-r2 and
  diagnostic tuples plus the central boot-policy/artifact binding.
- The 39-test compatibility oracle and 74-test source/DTB contract pass after
  advancing their exact manifest/profile seals.
- The complete repository Linux `ci` tier passes with its expected optional
  retained-source skip.
- Independent Standards/safety and objective-fidelity closure reviews report
  no remaining findings. A constrained, tool-free Claude advisory review also
  identified policy-scope and contract-coverage hardening that is included in
  this checkpoint.

## Boundary and next action

The retained output is Git-ignored and has no private signing material. This
checkpoint used no privilege, host installation, network mutation, fastboot,
ADB, ACM, SSH, or phone action. The next boundary is reviewed publication,
then exact host-side installation and connected preflight. A single temporary
boot remains downstream of those technical gates; flashing, wiping, and
persistent installation remain prohibited.
