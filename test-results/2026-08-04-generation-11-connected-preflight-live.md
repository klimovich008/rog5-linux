# Generation-11 connected preflight — live result

Date: 2026-08-04

Result: **PASS connected preflight — the exact Generation-11 diagnostic
recovery, signed bundle, deployment-key chain, installed host surfaces, and
one physical ASUS fastboot device passed. No recovery image boot, payload
transfer, target SSH, project server, flash, mount, wipe, or intentional
project storage write occurred; the fallback reads retain only the already
accepted bounded BusyBox-history and read-induced ext4-atime effects.**

## Published prerequisite

The preflight ran from clean pushed commit
`fcea8dc4b798573d84a4250350b0a4c54f1bf288`. Its implementation and
publication checkpoints passed complete local CI, independent spec and
standards review, and exact-head GitHub Actions. Run `30917116972` passed
recovery-core in 3m45s and QEMU in 34s.

Central policy admits exactly one RAM-only lifecycle for AVB
`8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562`.
Generation 11 remained `unbooted`, retained issuance `authority=none`, and had
no boot claim throughout this preflight.

## Connected sequence

Local admission matched the dedicated Ed25519 key to one non-fixture v3
package, exact `headless-netroot-early-diag-v1` candidate, and runtime manifest
`4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`.
An initial local-only invocation supplied the 536 MB source archive where the
gate requires its 731-byte package identity record. It failed closed on unsafe
record metadata before phone or privileged-host access. Supplying the exact
package record passed key admission.

SteamOS had activated `steam-web-debug-portforward.socket` on wildcard TCP
8081, conflicting with the fixed receive-only recovery progress listener. The
first lifecycle preflight rejected that listener. A bounded stop exposed the
next exact boundary: the phone was in verified Alpine fallback rather than
fastboot, so the complete host/artifact path rejected with:

```text
FAIL expected exactly one fastboot device, found 0
```

The Steam socket was restored. Strict key-pinned fallback SSH then proved the
accepted ASUS 5.4 kernel, BusyBox init, `qcom,lahaina-mtp`, ext4 root, empty
project-module/pstore state, readable nonfatal kernel log, and safe thermal
telemetry. The bootloader serial was privately recovered from one exact
`androidboot.serialno` command-line token. The reviewed anchored helper sent
`RESTART2("bootloader")` and verified disconnect, same-port ASUS fastboot
VID/PID and serial, and one product `lahaina` device.

TCP 8081 was released once more for the final preflight and restored
immediately afterward to its original enabled, active, listening state. The
terminal lifecycle marker was:

```text
PASS headless-netroot-early-diag-v1 lifecycle preflight is clean; the deployment key was admitted locally, and no phone boot, payload transfer, SSH connection, or privileged server was started
```

That marker describes the lifecycle preflight itself; the preceding guarded
fallback SSH session and bootloader reboot are separately recorded above.
Final observation found exactly one `lahaina` fastboot device, no
Generation-11 `.record` or `.record.entered` claim, and the restored Steam
listener on TCP 8081. Private serial, credential, and invocation-state paths
remain outside Git.

## Integrity chain

- temporary-boot policy:
  `889ee216f09a788be5c71eb1f70fa4c83224a577bbc441f9333b2a16bd72d4e8`;
- artifact manifest:
  `4c1c4bc6af7e5a1f5f52f97ea5f768a5162d2a8fed257e0f2fdbca4d314246da`;
- minimal profile:
  `28abed39d5182f0f8a7702f4fe8fde959370b0952c693fe0dce68d081a61e60c`;
  and
- source/DT outer:
  `7cc263208382bf812f6a1a9bed9f09af35c262023353f08d531bacfb6f7b734f`.

## Publication

Independent spec and standards review and the complete local Linux `ci` tier
passed. Commit `7b767333835dfabdb0acf116cd3bc7a3da851425` published this
evidence. Exact-head GitHub Actions run `30921019231` passed recovery-core in
4m01s and QEMU in 39s.

This pass establishes the connected-preflight precondition for the sole
Generation-11 lifecycle. It is not runtime evidence, does not consume the
artifact, and authorizes neither flashing nor a retry after any later ambiguous
execute.
