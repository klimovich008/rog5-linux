# Review brief: device profile, follow-up (2026-10-01)

Read-only follow-up to [the first review](2026-09-30-gpt-6.1-sol-device-profile.md)
and [the install-guide review](2026-09-30-gpt-6.1-sol-install-guide.md).
Worktree `~/.local/state/rog5-install-guide-wt`, branch
`agent/install-guide-20261001`, uncommitted changes against `ed73c81f`
(`git diff`, `git status`; `artifacts` and `build` are symlinks to the main
checkout, not part of the change).

Since the first review:

- The findings were fixed as listed in the two dispositions: `mktemp` in
  `rog5-install-userspace`; `nodiscard` + second `fallocate` + allocation
  proof in both stagers; a persistent image UUID in `rog5-build-rootfs`;
  `--device-profile` in `package-production-ram-trial.py` and
  `package-slotb-boot-wrapper.py`, a `device_profile` input in
  `rog5-make-bundle.py`, `ROG5_DEVICE_PROFILE` and `ROG5_RECOVERY_BASE_SHA256`
  in `build-persistent-slotb-recovery-initramfs.sh`; the state stager's ext4
  block pin replaced by a fits-the-partition check.
- New: the lower `ld.so.cache` pin moved into the profile block
  (`initramfs/persistent-root-init` `prepare_volatile_systemd_state`); the
  seal tool (`scripts/host/persistent-root-tool.py`) leaves out
  `boot/rog5-linux`; `rog5-build-rootfs` validates the lower root before
  sealing; `steam-fex-rootfs-install` re-owns the FEX guest root to root;
  `install-default-kernel.py` no longer shadows its `identity` variable (a
  `TypeError` at the render step in the first draft).

Questions:

1. Are the fixes correct and complete? Any regression for the reference
   phone (rendering the reference profile must stay the identity; the
   reference recovery base must keep every old pin)?
2. `build-persistent-slotb-recovery-initramfs.sh` with a non-reference
   base: is relaxing the verifier/kexec/key hash pins to "the caller pinned
   the base; the key member is 32 bytes" acceptable, given the packagers
   derive the signing check from that key member?
3. Anything in the boot path (`initramfs/*`) that would block a RAM trial of
   a reference-profile bundle built from this tree?

Findings by severity with file:line and a fix. Read-only; no device access.
