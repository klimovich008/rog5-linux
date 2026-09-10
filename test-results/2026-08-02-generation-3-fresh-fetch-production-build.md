# Generation-3 fresh-fetch production recovery build

Date: 2026-08-02

Result: **PASS offline — the production-bound diagnostic bundle, shell-free
recovery initramfs, and two clean ASUS 5.4 wrapper builds are byte-identical
and pass the complete phone-free artifact gate. The image is not
boot-authorized, is absent from the temporary-boot allowlist, and must never be
flashed.**

Generation 2 reached correlated recovery `PREPARED` without a completed host
HTTP transfer. The NFS gate correctly stopped before `COMMIT_EXEC`, no target
ran, and exact Alpine fallback passed. The generation-3 correction makes a
verified `/run` tmpfs mandatory before USB bind, rejects every pre-existing
final bundle, ties the lifecycle fixture's PREPARE event to a real transfer,
and keeps cleanup plus deferred NetworkManager-profile proof stable under one
deadline.

Commit `1af3275` also lets the production builder reuse only a verified
inherited private ARM64 binfmt namespace. Direct runs still create the sealed
rootless namespace. Nested runs must prove the guard identity, uid 0 inside a
rootless uid map, the private root mount propagation, and the private
`qemu-aarch64` handler before bypassing a second namespace.

Local repository CI passed, Claude returned `NO FINDINGS`, and GitHub Actions
run `30750260056` passed `qemu-system` in 37 seconds and `recovery-core` in 2
minutes 40 seconds at exact commit `1af3275` before the signed build began.

## Exact identities

| Field | Size | SHA-256/value |
|---|---:|---|
| Builder qualification | 753 | `b3032dd2c946df30f487fba84772b40ac902ca5b0ef2f5c3b06f9912840494f6` |
| Recovery init source | — | `23791f8e22924773baf6aa223a13bfa4bdd65ae3e51187ea221e61874ee7b7ab` |
| Recovery control | 132896 | `f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77` |
| Fresh-only bundle fetcher | 132824 | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| Native bundle verifier | 4467272 | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| Host bundle verifier | 48144 | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |
| Production public trust root | 32 | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| Stable-recovery initramfs A/B | 7594809 | `144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec` |
| Diagnostic target Image A/B | 40049152 | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| Diagnostic target DTB A/B | 102870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| Diagnostic target initramfs A/B | 6010870 | `10cc407e2bb5a9c9b63fd7eb30c7fc785d78b587e0c7c0b32346f7b1a50ce35c` |
| Signed runtime manifest A/B | 831 | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| Manifest signature A/B | 64 | `44123a0817816295fc8a8359ddd78b36c59c9f7c6d9e88373e4ed37191235f6b` |
| ASUS wrapper config A/B | 185763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| ASUS wrapper Image A/B | 50498048 | `8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c` |
| Raw boot-v3 wrapper A/B | 58101760 | `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce` |
| AVB wrapper A/B | 100663296 | `eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6` |
| AVB salt | — | `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce` |
| AVB digest | — | `6de238c36bd8325d2a6f431f27ee39e5d7bab81d9fe91bd6d3d0bad48ba3c60d` |

The logical name “generation 3” identifies the third attended diagnostic
successor in this project. This is a fresh twin production build, not an output
of the earlier AVB generation issuer, so it intentionally has no
`avb-generation.txt` record. AVB remains algorithm `NONE`; trust comes from
the exact host-pinned image identity and embedded production Ed25519 public
root.

## Verification and authority

The build and follow-up checks proved:

- A/B bundle payloads, recovery archives, wrapper kernels, raw images, and AVB
  images compare byte-for-byte;
- the external signing key still has mode `0600`, size 119, and its original
  2026-07-31 modification time; its derived public key equals the embedded
  public trust root;
- the mode-`0444` candidate retains exact SHA-256
  `7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8`;
- the private signing snapshot and temporary recovery workspace were
  destroyed;
- native verifier, composition, boot-v3 unpack, AVB footer, descriptor,
  command line, and raw-prefix checks pass; and
- no phone interface, fastboot command, reboot, boot, mount, storage write, or
  external network service was used.

`headless-diagnostic-generation3-offline-v1` pins the complete artifact chain
for `policy-preflight` and `artifact-preflight`. It explicitly rejects
connected preflight and boot, even if boot environment guards are present.
The image is recorded in `manifests/artifacts.tsv` with `tracked=no` and is not
listed in `manifests/temporary-boot-images.tsv`.

The retained ignored output is 9.4 GiB under
`build/early-target-diagnostic-deployment-20260802-fresh-fetch-r5-production`.
The 753-byte residue from the pre-fix failed attempt was preserved separately
under `archive/ignored-builds` rather than overwritten.
