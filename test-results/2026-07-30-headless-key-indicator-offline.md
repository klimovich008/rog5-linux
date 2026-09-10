# Native headless key indicator — offline

Date: 2026-07-30

Result: **PASS hardware-free; reproducible AArch64 artifact and exact
successor root archive sealed; hardware acceptance unproven;
live authority=none**

## Outcome

A native C service now turns the default-off green status LED on briefly only
when Linux reports a physical `KEY_POWER` press. It is independent of the
legacy Python/display-toggle path and adds no display, GUI, browser, VNC,
network, storage, boot, or credential behavior.

The exact production artifact is:

```text
source_size=20530
source_sha256=3d597f919d71a76f2aef0ae2aa269e219ffe7c0bdca0e9b73481d52dff686939
binary_size=67520
binary_sha256=3792745382a390ebeef37a081e532884aae07bbcd73fd9f0da1c94e67bdabbc8
format=ELF-64-AArch64-static-PIE-stripped
compiler=cc (Alpine 15.2.0) 15.2.0
build_image_id=d5fb16636fadea937b74dc3e062617d74a12577fd3fcc3f61fec24d0f7364495
build_image_digest=sha256:750150c51c8b5085d322ecaa5363356bb31ee243d6efab1035bd15f5ffe52355
```

Two builds were byte-identical. The AArch64 fixture binary ran under QEMU and
passed the same behavioral suite as the native host build.
Registered `ci` and `quick` tiers also pin the exact source size/hash before
compiling their host fixture, so source-to-sealed-artifact drift cannot pass
merely because the optional Podman/QEMU suite was not run.

## Enforced behavior

- exactly one ioctl-validated `pmic_pwrkey` device with `EV_KEY` and
  `KEY_POWER`;
- exact `green:status`, Qualcomm LPG driver, DT node, maximum brightness 511,
  initial brightness zero, and selected trigger `none`;
- one brightness-31 pulse lasting 180 ms for value-1 `KEY_POWER`;
- no action for release, autorepeat, volume keys, unrelated records, or a
  second press during an active pulse;
- rejection of malformed input and wrong/linked LED endpoints; and
- synchronous brightness-zero cleanup on timer expiry, signal, injected
  timer-arm failure, and an independently invoked post-stop `--off` path.

## Root boundary

`headless-v2` reuses and first verifies the existing SSH-only staging profile,
then installs only the sealed binary, hardened unit, and exact LPG module-load
line. The old `headless-v1` profile and accepted archive are not modified.
The successor verifier rejects a changed binary, service, module list,
missing exact LPG module, Python, or any deferred UI/agent command.
The service blocks general sysfs tuning with `ProtectKernelTunables=yes` and
declares only the exact brightness attribute writable; the phone-side
namespace behavior remains part of the live gate.

The successor root was then staged from clean commit
`6a8090e936bfbc2a8e93b430671a216593d11ca9` with the public-only
`rog5-headless-build-fixture` key. The source-volume verifier and a second
verifier over a clean extraction both passed:

```text
archive=artifacts/arch/rog5-arch-headless-core-7.1.4.tar.gz
size=535163814
sha256=f52bd75f023ab6209a04f842881356e5a224e1e1845f1d5732ab71da7d36e66b
profile=headless-core-v2
kernel_release=7.1.4-g7a5cef0db479
tree_entries=37674
installed_packages=150
authorized_key=SHA256:ylv66wbMSxVEAMiOFvMQOztcvtSB5wSbVe9FXePMLN0
```

The archive is ignored by Git and recorded as `tracked=no` in the artifact
manifest. Inspection found only the fixture public key and no SSH host
private key. This is an exact sealed-output claim, not a clean-twin
reproducibility claim: package installation used signed current Arch
repositories rather than a dated snapshot.

## Validation

The portable host suite, pinned AArch64 duplicate build, QEMU fixture suite,
legacy SSH-only root contract, successor root source contract, staged-root
verification, extracted-root verification, and complete repository `ci` tier
pass. Two tool-free, nonpersistent Claude Opus reviews found and then
confirmed closure of timer-arm cleanup, signal-race, post-stop-off,
sealed-source binding, CI registration, sysfs sandboxing, and early-probe
startup issues.

## Authority

No phone, fastboot, SSH credential, LED, boot, reboot, flash, partition,
network service, or external account was touched. A later hardware cycle
requires fresh authority and must retain the corrected minimal-server
watchdog, storage, SSH, and fallback gates.

See the [runtime contract](../docs/headless-key-indicator.md).
