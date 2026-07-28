# Stable recovery initramfs integration — 2026-07-28

Result: **PASS offline; not boot-authorized**

## Scope

This checkpoint integrated the fixed framed recovery control stack into a
deterministic AArch64 initramfs and removed the interactive ACM shell from the
three active init variants. It did not create a production signing key,
wrapper kernel, boot image, AVB image, host installation, or phone action.

## Source changes

- `initramfs/recovery-init` now publishes a canonical owner-private
  rollback-watchdog lease, completes storage isolation, starts the fixed
  responder, requires a canonical device session, monitors responder
  liveness, and only then binds USB.
- Recovery uses only fixed `169.254.77.2/30`; DHCP, gateway, default-route,
  SSH, getty, and interactive-shell paths are absent.
- `initramfs/network-root-init` and
  `initramfs/persistent-root-init` expose NCM only.
- `scripts/device/build-stable-recovery-initramfs.sh` installs the three
  static helpers, pinned kexec runtime, and a supplied raw 32-byte Ed25519
  public key after scrubbing credentials and legacy access paths.
- `scripts/device/verify-stable-recovery-initramfs.sh` extracts and checks the
  complete archive and ordering.

## Inputs

```text
v18 recovery base  852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc
wrapper config      df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
kexec APK          bd8b6951f862af1123972b521c355c655b7a2f40c2bf9cfe700edd590a101c94
xz-libs APK        76dce86852903fef7adba0285d816e5ce9ffbe9fb3ca86bbb349b97afaba1f63
zstd-libs APK      2bb5136c89f5b0bbe1554c8915a3b520d5aa63ae2a51d4d821eb81698db5a818
packaged kexec     5e5d0a78b3f0bcf3921ff060f4dce5011cbac24b5e12fedeb8ca03ea5b40d015
```

The wrapper config contains kexec, memfd, seccomp/filter, namespace, tmpfs,
ACM, and NCM prerequisites. The AArch64 builders retained their previously
pinned IDs/digests. The Ed25519 private key existed only inside an OpenSSL
pipeline and was never written to disk. Its raw public key was test-only.

## Results

The initial manual integration produced:

```text
recovery init  5ba175e8bfcad5fb09c8e02abe6f0b04416974c8b14c5cb5cd71a4cddce4f2d6
responder      479ac6c7e0269a0ebb67e6c07745216ae37e79c61da60a3a862c51194a3b67ea
fetcher        920c9bb3ccb4ab4b3fc3ad783532c5620ed31b3bd52377c8fe3e340fd865702f
verifier       ce0f2d997c0243b43e417a41fb5daadd89dfde7b2738ce3bb2e33783ba403b4c
test public    1c0ed87304246ce97bb69560e79ecc24063f7d6ca0e9f6357bfb6f886aac075a
initramfs A    0f3f58020bf835ed280072eaabf34a839f26219c825eca56fa85c50e7fe769e4
initramfs B    0f3f58020bf835ed280072eaabf34a839f26219c825eca56fa85c50e7fe769e4
```

Both archives extracted and passed:

- exact helper and trust-root byte comparison;
- static-PIE AArch64 helper checks;
- pinned dynamic kexec and runtime-library checks;
- public-key mode/size checks;
- watchdog lease, storage isolation, responder/session, and USB-bind ordering;
- fixed NCM address;
- no SSH server, authorized key, host key, getty, private key, `sh -i`,
  `setsid sh`, DHCP, gateway, or arbitrary network override.

The repeatable integration runner also rejects 31-byte and all-zero 32-byte
public keys.

## Review status

The local source review, ShellCheck warning gate, repository quick suite, and
full AArch64 integration pass. Two bounded Codex reviewer attempts did not
return a verdict and were stopped. The separately authorized Claude CLI
review was attempted read-only but the service reported a session limit until
17:10 Europe/Warsaw. No independent-review verdict is claimed by this
checkpoint; that review remains required before a production candidate.

## Promotion status

The output hash incorporates an ephemeral public key and is intentionally not
recorded in `manifests/temporary-boot-images.tsv`. A production candidate
requires separate approval for the signing trust root, two complete
initramfs/wrapper/AVB builds, independent review, atomic pin updates, and the
staging-only live sequence.

The later ephemeral-key wrapper/boot-v3/AVB reproducibility proof is recorded
separately in
[stable recovery wrapper reproducibility](2026-07-28-stable-recovery-wrapper-offline.md).

## Superseded review note

The service-limit statement above records this checkpoint as it happened.
The separately authorized Claude Opus review later completed. Its accepted
findings and the corresponding cross-locale, credential-removal,
watchdog-ordering, exact-topology, negative-fixture, and wrapper-command-line
fixes are recorded in the follow-up
[stable recovery review hardening](2026-07-28-stable-recovery-review-hardening-offline.md).
