# Persistent Arch P2 direct-procfs live attempt

Date: 2026-07-28

Result: **REJECTED BEFORE TARGET USB; EXACT FALLBACK PASS; NO FLASH.**

The attended command temporarily booted the clean, pushed, manifest-pinned
ASUS wrapper, reached exact recovery ACM, preflighted the exact Linux 7.1.4
payload, and issued exactly one `kexec -e`. The target exposed neither its
USB gadget nor strict SSH identity. Exact Alpine fallback appeared 37 seconds
after execute. This consumes the one-pass direct-procfs package; it does not
establish P2 target acceptance.

## Rejected input

| Input | Size | SHA-256 |
|---|---:|---|
| raw header-v3 wrapper | 96,067,584 | `edb14491d36a8e31da8e835479e0e117130cd23ffb5ef7853dc51acfc87d0d90` |
| temporary unsigned AVB wrapper | 100,663,296 | `94d420c6041711a2bb30d0e1cc7e082fcc22e7bab6ab856123d0af75f7e46ec1` |
| ASUS wrapper Image | 69,372,416 | `eb31cfa7f32a4b43078e7353c391f452bc97da4f54c3b04e799c5abdb4ad90a6` |
| nested staging initramfs | 26,687,735 | `74460279c7779b7ea6e035832344f4bbc29280eb81008dcfe2f66852aed59ce8` |
| target initramfs | 5,853,881 | `a2dae8b5c95863c09666355f4777f16c7c2f78a2763ea064907a557945a92992` |
| Linux 7.1.4 target Image | 38,607,360 | `832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f` |
| Linux 7.1.4 target config | 242,248 | `8a7fabffa076a65d09529ef1004c315e1296e547a02d08c362031d0363ba63c3` |

The image was used only with `fastboot boot`. No partition was flashed,
formatted, repaired, repartitioned, selected, promoted, or mounted by the
host.

## Guarded sequence

1. An initial live-run invocation saw zero fastboot devices and refused
   before ModemManager stop, temporary boot, or ACM use.
2. Exact fallback thermal preflight then refused one reboot attempt above the
   60 °C ceiling. A later snapshot showed a 56.4 °C maximum and full preflight
   passed, but the reboot command's repeated in-band check caught a new spike
   and refused again.
3. After cooling, a read-only snapshot showed a 52.4 °C maximum. The guarded
   reboot's complete exact-fallback check passed, sent
   `RESTART2("bootloader")`, and reached exactly one fastboot device.
4. The synchronized branch, manifest, credential metadata, and exact AVB
   image passed. Fastboot transferred and accepted the 100,663,296-byte
   temporary image.
5. Exact recovery ACM appeared. The first fixed load-marker read lost the
   serial-open race; one bounded byte-identical, read-safe load retry
   succeeded. No execute action was retried.
6. Recovery verified every nested payload hash, all 116 physical block nodes
   read-only, zero block-backed mounts, and a loaded kexec image.
7. Exactly one non-retryable execute action issued `kexec -e`.
8. The target exposed neither its expected USB gadget nor strict SSH identity.
9. Exact Alpine fallback was detected after 37 seconds and the runner exited
   rejected immediately.
10. ModemManager was restored to its initial active state.

The private rejection marker is caller-owned outside the repository, has
mode `0600`, size 83 bytes, and SHA-256
`c72bf59ff2f28f33932790da88f2cdcea5147bc3bdef8d066f877c8f39bdbc61`.
It contains only the rejection class and elapsed seconds, with no serial,
credential, or host path.

## Exact fallback and persistent-root state

Independent post-run checks passed the exact fallback kernel, init,
compatible string, ext4 root, empty pstore, zero project modules, safe
thermals, and active ModemManager. `/rog5/roots/arch-a` remained a real
directory with the exact whole-tree seal. Its seal metadata remained
root-owned, mode `0444`, and byte-exact. Promotion state remained `UNBOOTED`;
both selectors and the partial-publication marker remained absent.

The fallback panel again returned at brightness `1023`. The screen-state file
was absent and no screen-button daemon was running. One invocation of the
installed transient screen control set the physical backlight to zero,
created state `off`, and left strict SSH reachable. This proves manual
recovery only; automatic fallback screen-off and daemon persistence remain
unresolved defects.

## What the interval does and does not prove

The consumed target assigned 5 seconds to command-line failure, 20 seconds to
kernel-release-file/read failure, 25 seconds to release mismatch, and
35-110 seconds to later storage and USB branches. The 37-second fallback is
closest to the 20-second marker after the previously observed reboot and USB
enumeration overhead.

That alignment is not sufficient evidence that the procfs read failed.
Several materially different P2 initramfs packages have now returned in the
same 36-37 second range. A target panic before `/init`, the 10-second panic
timeout, scheduling, USB enumeration, or an earlier command-line branch can
share that interval. Empty fallback pstore cannot classify the event because
the installed fallback does not map the target command-line ramoops region.

Offline checks establish only the following:

- both clean target build directories and the exact Image report release
  `7.1.4-gcfd385a1c754`;
- the recovery stage pins that exact Image before kexec;
- the target archive carries the exact tested init and BusyBox 1.37.0;
- the target BusyBox shell successfully performs the same direct procfs read
  under AArch64 emulation; and
- the fallback's procfs release file is newline-terminated and the same shell
  syntax succeeds there.

Those checks reject a simple shell-syntax explanation but do not prove that
the target reached `/init`.

## Fail-first successor direction

The next diagnostic must stop inferring early execution from elapsed time.
It will:

1. retain the exact recovery-hashed Image, read-only UFS policy, and
   no-flash wrapper;
2. enter a command-line-selected diagnostic branch immediately after mounting
   only procfs, sysfs, devtmpfs, devpts, and tmpfs;
3. mount no block device and perform no userland storage access;
4. expose a credential-free, fixed-marker USB ACM endpoint from RAM;
5. report exact `/init` entry, command-line token counts, and direct procfs
   release status without exposing the full device command line;
6. use an independent fixed reset long enough to distinguish successful init
   entry even if USB setup fails; and
7. require exact Alpine fallback, unchanged root state, screen-off
   verification, and host-service restoration.

The diagnostic will receive its own fail-first host, initramfs, package, and
mutation tests before any live authorization.

## Decision

The direct-procfs package is consumed and must not be retried or flashed. P2
remains HOLD and P3 remains prohibited. No further timing-only P2 package is
authorized. The next live candidate must provide explicit early-init evidence
while preserving the no-storage and automatic-fallback boundary.
