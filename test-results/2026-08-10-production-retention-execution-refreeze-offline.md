# Production retention execution refreeze — offline

Date: 2026-08-10

Starting repository SHA:
`223ac2d1160c8b776b6009078da40b0085600c1b`

Recommendation: **HOLD**

No phone, USB device, fastboot, ADB, ACM/NCM session, phone storage, claim,
policy row, flash, wipe, slot operation, persistent installation, or phone boot
was used. The existing project signing key was admitted only to the reviewed
offline clean-twin build. Its private snapshot was destroyed by the guarded
builder; no private key is present in the retained output.

## Concrete defect fixed

The joint retention-cycle profile still described its execution role as
`disposable-offline` and pinned the earlier disposable-key wrapper. The
dependency-complete production build instead used the reviewed project trust
root and produced different exact candidate-record, signature, initramfs,
wrapper, raw, and AVB identities. Leaving the old profile in place would make
the authority-free production artifacts unverifiable by the repository-owned
admission review and could allow an operator to select the wrong trust class.

The profile and verifier now require `trust_class=production-project` and bind
only the execution-side fields changed by that build. The observer role remains
the separately built execution-free Haven observer. The profile still requires
`state=hold`, `authority=none`, `boot_authority=none`, undefined execution and
observer claims, zero temporary-boot `allow` rows, `retention=unproven`, and
`missing_pstore=inconclusive`.

## Clean production twins

The dependency-complete clean build finished in 2,270 seconds. The immediately
preceding build took 2,253 seconds before failing after both wrapper compiles
because the detached checkpoint omitted the GKI certificate helper. After that
dependency was pinned, both complete release builds were byte-identical:

| Product | Size | SHA-256 |
|---|---:|---|
| candidate record A/B | 306 | `8082c10bde22d728696feb81b723505d35d08a790059f436d8714ffa7c8cf108` |
| runtime manifest A/B | 834 | `54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc` |
| runtime signature A/B | 64 | `0d1647bc485f6d7a0bd0c8945d17db6d79d7c14bc1acab62a580a5b8b7b40e88` |
| project public trust key | 32 | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| full recovery initramfs A/B | 7,605,169 | `ab0a3ee219684c994af386cb60e5280dcc4269457b196f96ca3928acce691f0b` |
| wrapper config A/B | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| wrapper Image A/B | 50,498,048 | `8a600acfc6f7e01f9eb932e0a04174079d6ee68142c44fad819fe96bbd34325d` |
| raw boot-v3 image A/B | 58,109,952 | `ea9e90fdbf1bfdbe75816462ae79897e6cf7749d9e87607be2b033b7cfb06517` |
| unsigned AVB image A/B | 100,663,296 | `cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d` |

The manifest identity is unchanged because the target payload is unchanged;
the signature and candidate record change with the project trust root. The
wrapper uses `Algorithm: NONE`, so this output is exact composition evidence,
not a fastboot-authorized image.

The observation role remains pinned to:

- initramfs `b2440d8ccc2f22b9c9072a2404569d2a5843f7dab186a2ccac307a929a4941ad`;
- wrapper Image `eedb7deb64aa42de582245b121f4ea581d0b1e21e9eb49f3591e98df8f63ef59`;
- raw image `5daf0919d38c9f7b1ffde85a8c5e9aabdbba526bcafa1a528bd8c31e27dda171`;
- unsigned AVB image `3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b`.

## Regression and host-state evidence

The new trust-class regression failed before the correction after 2.621
seconds: the repository profile contained `disposable-offline`. After the
correction, all 20 admission-review cases passed in 2.626 seconds. The hostile
case mutates the required class back to `disposable-offline` and proves that
the verifier fails closed.

The verifier also refused to review the production evidence through a
different checkout because evidence must remain below that verifier's ignored
`build/` root. This boundary was preserved. The final production-artifact run
is therefore performed after the production checkout reaches the exact
committed head; no cross-checkout exception is added.

The guarded build removed its detached checkpoint and temporary private-key
snapshot. The pre-armed host guardian then restored `qemu-aarch64` binfmt;
`systemd-binfmt.service` is active and the handler reports `enabled`.

## Remaining boundary

The project trust identity is durable build provenance only. No exact boot
claim exists for either role, the central policy has no `allow` row, and the
phone has not exercised this pair. Ramoops retention and the Generation-12
USB-loss cause remain physically unproven. Candidate admission, boot authority,
and one-use hardware execution remain separate safety decisions. The final
repository CI, exact production-root verifier result, ending commit, and
GitHub exact-head result are recorded in the checkpoint handoff after this
report is committed. Recommendation remains **HOLD**.
