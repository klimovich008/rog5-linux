# Recovery v17 keyed diagnostic

Status: **DIAGNOSTIC COMPLETE; never publish or flash**. The local image
contained only the separately authorized recovery public key. The private key
remained in host tmpfs and no key material was committed or logged.

## Reproducibility and access

- Target and staging initramfs layers were each reproduced twice.
- Two fresh wrapper output volumes produced byte-identical config, embedded
  initramfs, metadata, and kernel Image.
- Two header-v3/AVB repacks are byte-identical.
- The complete network-disabled verifier passed in explicit `ssh` mode
  against the tmpfs public key.
- The exact `ROG5_recovery` product appeared at 06:52:09 after a guarded
  temporary boot.
- The host pinned the ephemeral recovery SSH host key on the direct USB link
  before authenticating.

## Live storage and rollback result

The live staging kernel reported:

| Gate | Result |
|---|---|
| kernel | `5.4.210-qgki-perf-kexec-stage-builtin-recovery` |
| root | `rootfs`, RAM-backed and writable |
| block-backed mounts | 0 |
| physical disks and partitions | 116 total, 0 writable |
| rollback marker | armed |
| watchdog process | alive |
| ACM supervisor | alive |
| SSH | key-only and running |

The 180-second timer returned the phone to exact fallback product at 06:55:26
with a changed boot identity. No recovery marker was removed. Kexec was not
loaded or executed.

## ACM root cause

The ACM configfs function and `/sys/class/tty/ttyGS0` existed, with device
number `505:0`, but `/dev/ttyGS0` did not. The ACM supervisor was therefore
alive but remained in its device-node wait loop.

A live RAM-only `mdev -s` rescan created `/dev/ttyGS0` immediately. The
supervised `sh -i` process then appeared and the host ACM endpoint returned the
expected kernel release and RAM-root mount. This isolates the failure to a
missing post-configfs device-node rescan rather than USB transport, shell
launch, storage isolation, or rollback.

V18 implements that exact fix, requires the character node, and repeats the
full storage-isolation gate before starting ACM or binding the gadget.
