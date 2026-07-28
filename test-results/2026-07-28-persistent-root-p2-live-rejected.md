# Persistent Arch P2 first live attempt

Date: 2026-07-28

Result: **REJECTED; FALLBACK PASS; NO FLASH.**

The attended P2 gate temporarily booted the ASUS wrapper, reached recovery
ACM, loaded the exact Linux 7.1.4 payload, and issued one `kexec -e`. The P2
target never exposed its USB gadget or SSH identity. The independent rollback
returned the phone to the exact Alpine fallback, where the staged root
remained `UNBOOTED`, both selectors remained absent, and the backlight was
off.

## Accepted inputs for the rejected attempt

| Input | Identity |
|---|---|
| temporary AVB wrapper used live | `ac60d65c7ca89c92320c978470a0cf3803a2e8b063a24489182fc031a42232ee` |
| wrapper raw image used live | `fd614701b859c77a1d5b7187cc7a83623d1ae71b673e3aebcb9691e1bb9b2237` |
| target kernel | `7.1.4-gcfd385a1c754` |
| fallback kernel | `5.4.134-qgki-perf-00001-g6c308144c23e` |
| sealed root state after fallback | `UNBOOTED`; selectors absent |

The phone reported the expected unlocked `lahaina` fastboot product. The
temporary image was loaded with `fastboot boot`; no partition was flashed,
erased, formatted, repaired, or selected.

## Observed sequence

1. Manifest/image preflight and fastboot identity checks passed.
2. Recovery ACM appeared and the fixed load action reported the exact payload
   marker.
3. The staging preflight printed a missing
   `/run/rog5-ufs-blocked-query-count` error, yet the host helper reported
   PASS.
4. One attended `kexec -e` disconnected recovery USB.
5. No `ROG5 persistent root` USB gadget or exact-target SSH response appeared.
6. Exact Alpine fallback USB and strict SSH returned about 26 seconds later.
7. Fallback checks passed the exact kernel, root seal, `UNBOOTED` state,
   absent selectors, and screen-off contract. ModemManager was restored.

No usable pstore or `last_kmsg` record survived, so this run does not locate
the target's pre-USB failure within `/init`.

## Control defects found

The recovery serial console echoes submitted commands. The complete P2
success marker occurred literally in the old preflight command, so marker
matching could accept the echoed input even when `set -e` stopped the shell
at a failed check.

Independent boot-v3 inspection also proved the wrapper command line omitted
`rog5.ufs_discovery=1`. Recovery creates the two blocked-command counter files
only when that exact flag is present, so the preflight was guaranteed to fail
before the echoed marker hid the result.

The target SSH polling loop had a separate latent issue: a non-target peer
could populate the volatile known-hosts file before failing the exact-kernel
attestation, blocking a later target with a different host key.

## Corrections and fail-first evidence

Before implementation, three regressions failed for the observed reasons:

- the complete preflight marker appeared in the command string;
- the runner retained a rejected candidate host key; and
- the canonical boot image contained zero `rog5.ufs_discovery=1` tokens.

The helper now produces the complete marker only through successful `printf`
output. The runner truncates candidate known-hosts state after every failed
exact-kernel probe and recognizes exact pinned Alpine during target polling,
recording elapsed time and restoring host state without waiting for the full
target timeout. The first correction made a standard-library Android boot-v3
parser require one wrapper UFS-discovery token. A later live attempt proved
that requirement crossed the ASUS-wrapper and Linux-target contracts, so the
package below is historical and rejected. The target timing changes
themselves remain valid. Target initramfs, nested stage, ASUS wrapper, and
that rejected repack each reproduced twice:

| Stage | Added delay |
|---|---:|
| invalid command line | 5 s |
| kernel-config attestation | 10 s |
| UFS discovery | 20 s |
| UFS power containment | 35 s |
| physical storage lock | 50 s |
| exact userdata identity | 65 s |
| UFS inventory | 80 s |
| USB setup | 95 s |

The first immediate-failure cycle took about 26 seconds from kexec disconnect
to fallback USB. The diagnostic classification uses the newly recorded
execute-to-fallback interval and the unique added delay; timing is evidence
for the branch, not target acceptance.

| Diagnostic product | Size | SHA-256 |
|---|---:|---|
| target initramfs | 5,853,871 | `f69d31c78bd8ce154516e701f0166760d2934b009152242a752795249b1103f2` |
| nested staging initramfs | 26,687,246 | `b14c2a54eb413f1dbb2b808691b5c6b77614b7a502cd4ff7eb5a34d9bac0c54e` |
| ASUS wrapper Image | 69,372,416 | `b133ebcee9c2b0a99876da1dd20615c9f569c67e7e91a089d9de5a54e6ad8d17` |
| raw header-v3 image | 96,067,584 | `deaa9c047cd2251c4981f1c41ba5d144118b6ba1fceb216e58c310d6e6491bdf` |
| unsigned AVB image | 100,663,296 | `439a945babb5af1af83b7f6ad07ec6a8c0bf3e74fe416925b2e1a416e3b39ae0` |

The diagnostic image preserved the exact target kernel, DTB, verifier, root
seal, read-only UFS policy, watchdog, and target successful-path behavior.
Its first follow-up boot was rejected before staging because the attempted
wrapper correction enabled a target-only UFS mode that the ASUS wrapper does
not implement. That separate event and its fail-first correction are recorded
in the
[wrapper-contract rejection](2026-07-28-persistent-root-p2-wrapper-contract-live-rejected.md).

## Decision

The original live attempt and its first wrapper correction are rejected. The
safe fallback results prove rollback, not target acceptance. Do not flash
either image, do not promote or select the staged root, and do not begin P3.
The wrapper-contract correction later received its sole attended
timing-diagnostic boot and
[safely selected the runtime kernel-config branch](2026-07-28-persistent-root-p2-config-timing-live-rejected.md).
Only the latest manifest-pinned one-pass config-identity package may receive
one further attended diagnostic temporary boot.
