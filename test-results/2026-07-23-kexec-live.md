# Live kexec recovery follow-up - 2026-07-23

The target-handoff conclusion below is superseded by
[the later mainline recovery result](2026-07-23-mainline-recovery-usb.md).
The self-kexec isolation remains useful historical evidence.

Result: **PASS** for temporary ASUS 5.4 staging and payload loading;
**BLOCKED AT TARGET HANDOFF** for both self-kexec and Linux 7.1.

## Passing live gates

- Official pinned fastboot temporarily boots the header-v3 staging image.
- Authenticated USB NCM/SSH recovery starts on ASUS 5.4.210.
- The recovery timer is armed and no phone storage device is mounted.
- The embedded kernel, DTB, and initramfs manifest verifies in RAM.
- `CONFIG_KEXEC=y` legacy loading accepts the exact payload.
- A rebuilt kernel with `CONFIG_KEXEC_FILE=y` boots, and file loading accepts
  the exact same self-kexec payload.
- The repository `KEXEC_FILE=1` build path reproduces that kernel from the
  retained PC cache: config SHA-256
  `221e3a82a995595244132ed506a440ab1d1389ef74a1c4af108ac8f0c9e04ba8`
  and Image SHA-256
  `d8a203e2ad579b7da86fd02be6190989785af1aa0c9bacfba7d3cf6f2dae0e46`.
- The sole exposed watchdog control belongs to the Haven hypervisor watchdog;
  it disables successfully without a secure-watchdog error.

## Failure isolation

- Linux 7.1 execution returns to fallback when `panic=10` is present.
- An identical ASUS 5.4.210 self-kexec behaves the same, ruling out Linux 7.1
  and the recovery DTB as the first failure.
- Offlining every secondary CPU does not change the result.
- Legacy and file-based loading both fail at execution, ruling out userspace
  purgatory and file-loader acceptance.
- With the Haven watchdog disabled and `panic=0`, self-kexec remains
  nonresponsive instead of automatically rebooting.
- Adding `reset_devices` does not restore target USB/SSH.

The next gate reads the persistent ramoops record from the existing unused
4 MiB ASUS debug reservation. No partition was flashed, no storage was
mounted, and all failed tests remain recoverable through a forced fastboot
restart.
