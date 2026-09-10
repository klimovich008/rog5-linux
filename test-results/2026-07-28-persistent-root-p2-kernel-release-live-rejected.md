# Persistent Arch P2 kernel-release live attempt

Date: 2026-07-28

Result: **REJECTED BEFORE TARGET USB; EXACT FALLBACK PASS; NO FLASH.**

The attended command temporarily booted the clean, pushed, manifest-pinned
ASUS wrapper, reached exact recovery ACM, preflighted the exact Linux 7.1.4
payload, and issued exactly one `kexec -e`. The target exposed neither its
USB gadget nor strict SSH identity. Exact Alpine fallback appeared 36 seconds
after execute. This consumes the one-pass kernel-release package; it does not
establish P2 target acceptance.

## Rejected input

| Input | Size | SHA-256 |
|---|---:|---|
| raw header-v3 wrapper | 96,067,584 | `7a0293daaf14939bd2dc6b6264fcdef955d8fb6c654deaf4ffe394e9b2c8bc31` |
| temporary unsigned AVB wrapper | 100,663,296 | `3c0355be52ebb005371b26e73a97a9899efaf9569c79442cc9f063779faf475b` |
| ASUS wrapper Image | 69,372,416 | `cfd65186afd75435d34cb33a36c76c4a80a861d0360bec13495c0b445836b7c2` |
| nested staging initramfs | 26,688,093 | `438aaf1c99455e23ff27f758738e779b0fd318e68c58467eeae7b77c55a87520` |
| target initramfs | 5,853,822 | `e2b58d50fae31509b8cd87ed01afbf25c90d49500e3d9d9691ecd77643fd434e` |
| Linux 7.1.4 target Image | 38,607,360 | `832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f` |
| Linux 7.1.4 target config | 242,248 | `8a7fabffa076a65d09529ef1004c315e1296e547a02d08c362031d0363ba63c3` |

The image was used only with `fastboot boot`. No partition was flashed,
formatted, repaired, repartitioned, selected, promoted, or mounted by the
host.

## Observed sequence

1. The first fallback preflight refused to reboot because one transient
   thermal-zone reading exceeded the 60 °C ceiling. No boot action occurred.
2. A later read-only snapshot reported a 43.8 °C maximum. The complete
   fallback preflight was repeated and passed before any reboot.
3. The synchronized branch, manifest, credential metadata, and exact AVB
   image passed. Guarded `RESTART2("bootloader")` reached exactly one fastboot
   device.
4. Fastboot transferred and accepted the 100,663,296-byte temporary image.
5. Exact recovery ACM appeared. The first fixed load-marker read lost the
   serial-open race; one bounded byte-identical, read-safe load retry
   succeeded. No execute action was retried.
6. Recovery verified every nested payload hash, all 116 physical block nodes
   read-only, zero block-backed mounts, and a loaded kexec image.
7. Exactly one non-retryable execute action issued `kexec -e`.
8. The target exposed neither its expected USB gadget nor strict SSH identity.
9. Exact Alpine fallback was detected after 36 seconds and the runner exited
   rejected immediately.
10. ModemManager was restored to its initial active state.

The private rejection marker is caller-owned outside the repository, has
mode `0600`, size 83 bytes, and SHA-256
`031a0bbdd1980b9927e33a36ce458f40a6eda8a748f0f0a3a27a3333090a0c6a`.
It contains only the rejection class and elapsed seconds, with no serial,
credential, or host path.

## Exact fallback and persistent-root state

Independent post-run checks passed the exact fallback kernel, init,
compatible string, ext4 root, empty pstore, zero project modules, and safe
thermals. `/rog5/roots/arch-a` remained a real directory with the exact
whole-tree seal. Its seal metadata remained root-owned, mode `0444`, and
byte-exact. Promotion state remained `UNBOOTED`; both selectors and the
partial-publication marker remained absent.

The panel backlight was initially `1023` after fallback, so this run did not
prove automatic screen-off restoration. The installed transient screen
control was invoked once. Its status output raced with the button daemon, but
immediate direct assertions proved the final physical backlight value was
zero and `/run/rog5-screen-state` was `off`. Automatic fallback screen-off
therefore remains a separate reliability defect; the successful manual
restoration does not convert this P2 run into acceptance. A process snapshot
also appeared to show two screen-button-daemon entries; whether those were a
parent/child presentation or duplicate workers remains unresolved.

## Classification

The consumed target assigned 5 seconds to command-line failure, 20 seconds to
running-kernel-release failure, and 35-110 seconds to later storage and USB
branches. The 36-second fallback aligns most closely with the 20-second
release branch after baseline reboot and USB-enumeration time. This is a
bounded clue, not proof: `panic=10`, scheduling, and fallback enumeration all
contribute to the observed interval.

Offline evidence still establishes that the intended Image is coherent:

- both clean target build directories report release
  `7.1.4-gcfd385a1c754`;
- the exact Image contains only that release identity;
- the recovery stage pins the exact Image hash before kexec; and
- the Image's embedded IKCONFIG stream equals the pinned config byte-for-byte.

The consumed init used BusyBox `uname -r`; that applet exists in the target
archive. Empty pstore provides no target panic record, so the run cannot
distinguish an applet failure, a release mismatch, or another reset that
shared the interval.

## Fail-first direct-procfs successor

The target test was first changed to require a direct read from
`/proc/sys/kernel/osrelease`, to reject `uname -r`, and to keep rejecting any
`/proc/config.gz` dependency. It failed against the consumed implementation
before the init was changed.

The successor now reads the release with the shell builtin, compares it to
`7.1.4-gcfd385a1c754`, and separates file/read failure from identity mismatch:

| Stage | Added delay |
|---|---:|
| invalid command line | 5 s |
| kernel release file/read | 20 s |
| kernel release identity | 25 s |
| UFS discovery | 35 s |
| UFS power containment | 50 s |
| physical storage lock | 65 s |
| exact userdata identity | 80 s |
| UFS inventory | 95 s |
| USB setup | 110 s |

It still verifies the recovery-hashed target Image, retains offline
byte-exact embedded-config attestation, arms no watchdog and inspects no
storage before both release checks pass, and changes no P2 storage policy.

Two independent builds at every changed packaging layer are byte-identical:

| Successor product | Size | SHA-256 |
|---|---:|---|
| target initramfs | 5,853,881 | `a2dae8b5c95863c09666355f4777f16c7c2f78a2763ea064907a557945a92992` |
| nested staging initramfs | 26,687,735 | `74460279c7779b7ea6e035832344f4bbc29280eb81008dcfe2f66852aed59ce8` |
| ASUS wrapper Image | 69,372,416 | `eb31cfa7f32a4b43078e7353c391f452bc97da4f54c3b04e799c5abdb4ad90a6` |
| ASUS wrapper metadata | 410 | `c6c4a7ba1934418b313c5c3d16faa952aae8617bf40000069d85545ceb566931` |
| raw header-v3 image | 96,067,584 | `edb14491d36a8e31da8e835479e0e117130cd23ffb5ef7853dc51acfc87d0d90` |
| unsigned AVB image | 100,663,296 | `94d420c6041711a2bb30d0e1cc7e082fcc22e7bab6ab856123d0af75f7e46ec1` |

The wrapper builds use separate immutable source volumes and match in Image,
config, metadata, and their one exact embedded staging archive. Two
header-v3 repacks also match. Pinned `avbtool 1.4.0` verifies the algorithm
`NONE` footer and complete boot-image hash.

## Decision

The one-pass `uname -r` package is consumed and must not be retried or
flashed. Its direct-procfs successor subsequently received its sole attended
boot and [returned safely to exact fallback after 37 seconds without target
USB](2026-07-28-persistent-root-p2-osrelease-live-rejected.md). That package
is also consumed. P2 remains HOLD and P3 remains prohibited. Repeated
36-37 second returns no longer justify another timing-only diagnostic; the
next candidate must provide an explicit RAM-only early-init oracle. Only
complete target acceptance plus exact automatic fallback can pass P2.
