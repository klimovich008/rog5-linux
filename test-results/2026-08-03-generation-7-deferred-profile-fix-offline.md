# Generation-7 deferred-profile-fix recovery — offline

Date: 2026-08-03

Result: **PASS focused offline issuance; unbooted and not admitted**. A
distinct Generation-7 outer AVB wrapper was issued twice after correcting the
host's exact fallback udev-model classifier and deferred NetworkManager
profile-association verifier. The recovery payload itself is unchanged.

## Exact identities

| Item | SHA-256 |
| --- | --- |
| Generation-7 AVB image | `d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901` |
| AVB-generation record | `8127197dcf0704bf7bee81a7b25a604fb9e7c9b752ba6d9523e073de2bf9799e` |
| AVB salt | `47daea8fa91810575df6d694bd5e3949eb6295920f7b980eb8935e86950506e4` |
| AVB payload digest | `5690894d337769a462828bc786de74724abf89115c1e456b8e4064ab6831b86b` |
| Canonical generation-zero source AVB | `eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6` |
| Unchanged raw recovery | `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce` |
| Unchanged recovery kernel | `8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c` |
| Unchanged recovery initramfs | `144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec` |

Both independently issued trees are byte-identical across the generation
record, A/B AVB wrappers, A/B raw images, kernels, configurations, and
initramfses. Generation 7 is distinct from every earlier nonzero generation.
The outer AVB algorithm remains `NONE`; the exact artifact pin and embedded
production Ed25519 trust root remain the authentication boundary.

## Scope of the successor

The Generation-7 wrapper does not embed the two host fixes. It is a fresh
single-use outer identity selected only after those fixes changed the host
lifecycle behavior:

- production fallback udev model `ROG_Phone_5_Linux_Server` is accepted only
  as one exact enumerated model; and
- deferred recovery NCM may retain either no NetworkManager association or
  exactly the pinned fallback profile UUID, but only after the interface is
  continuously proved address-free and unmanaged and the exact profile is
  proved interface-bound with autoconnect disabled.

Wrong, duplicate, mixed, prefix, suffix, case, whitespace, managed, addressed,
or autoconnect-enabled states remain fail-closed.

## Offline-only policy

`headless-diagnostic-generation7-offline-v1` is the only Generation-7
profile. It permits `policy-preflight` and `artifact-preflight` only.
Connected `preflight` and `boot` reject before dependency, host-state,
credential, fastboot, or phone inspection even when all live guard variables
are supplied. The prospective
`headless-diagnostic-generation7-live-v1` name is unsupported.

The artifact inventory contains one exact `authority=none`, `unbooted`,
`never flash` row. The temporary-boot policy contains no Generation-7 row and
no `allow` row. This checkpoint cannot boot the phone.

## Focused verification

- recovery inventory/boot-authority separation: pass;
- policy identity mutation matrix for recovery, trust root, manifest, host
  verifier, and bundle: pass;
- connected-preflight and boot early rejection: pass;
- unissued live-profile rejection: pass;
- artifact preflight against both independent production issuer trees: pass;
- cross-tree equality for every retained output: pass;
- generation-record mutation rejection: pass; and
- generic deterministic issuer regression through Generation 7, including
  non-reuse of both predecessor twins: pass;
- 39 compatibility-oracle tests: pass;
- 74 source/DTB tests: pass with one expected optional retained-source skip;
  and
- complete repository Linux `ci` tier: pass.

The first broad constrained Claude Opus response was invalid: despite its
tool-free wrapper, it printed a hallucinated Bash invocation and mangled
source, so it was discarded rather than treated as review evidence. Two
smaller self-contained retries completed correctly. The production gate and
manifest review returned `PASS`. The test review identified six hardening
opportunities; all supported findings were applied: clean CI no longer creates
an empty build directory, asymmetric production twins fail, mutation cleanup
handles read-only trees, a constant-length generation-field mutation is used,
issuer stdout and raw twins are compared, and source tests assert that no
Generation-7 live profile exists. The focused gates and complete CI pass after
those changes.

No credential, signing key, privileged host action, fastboot command, phone
interface, NFS export, or phone storage was used. A separate reviewed change
would be required to create a live profile; a still-separate central policy
change would be required to admit one temporary lifecycle.
