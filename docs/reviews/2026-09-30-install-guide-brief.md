# Review brief: public install guide (2026-09-30)

Read-only review requested from GPT-6.1-Sol. Repository:
the development checkout (working tree with
uncommitted changes). The project is about to get a public alpha release on
GitHub; `docs/install-guide.md` is for other owners of an ASUS ROG Phone 5
(ZS673KS: the 5, 5 Pro and 5 Ultimate, 8-18 GB RAM, 128-512 GB UFS).

Read `docs/install-guide.md` and check it against the repository: the
scripts it names (`scripts/host/rog5-build-rootfs`, `rog5-device-profile`,
`rog5-dtb-memory`, `rog5-make-bundle.py`, `package-slotb-boot-wrapper.py`,
`install-default-kernel.py`, `production-ram-trial.py`,
`scripts/device/rog5-install-userspace`, the stagers, the Steam scripts,
`install-rog5-speaker-firmware`, `install-rog5-sensors.sh`), the configs
(`configs/rootfs/*`, `configs/device-profiles/reference.env`,
`configs/production/bundle-inputs.json`), and the docs it relies on
(`README.md`, `docs/development.md`, `docs/bundles.md`, `docs/whats-left.md`,
`docs/hardware/bootloader-assessment.md`, `docs/recovery-bundle-contract.md`).
History of the original install is in `docs/history/` and the local tag
`archive/pre-cleanup-2026-09-29`. `docs/fresh-install-rehearsal.md` may still
be in progress.

Constraints the guide must respect: firmware only from the user's own phone
(never downloaded from the project); users make their own signing key; no
secrets or personal identifiers; never boot slot A Android after the install
(it formats the Linux userdata); flashing touches only `boot_b` and p24.

Questions:

1. **Correctness.** Commands, options, paths, file names, orders of steps
   and expected outputs that do not match the scripts. Steps whose
   prerequisites are not met at that point of the guide (circular
   dependencies between the root image, the device profile, the bundles and
   the flash).
2. **Safety.** Anything that could erase data unexpectedly, brick the phone,
   boot slot A, leak a key, or mislead a user into running an unsafe
   archived tool. Are the warnings sufficient and placed before the risky
   step? Is the recovery advice right?
3. **Missing steps.** What would a new owner need that the guide does not
   say (host packages, fastboot identity checks, USB networking, time
   estimates, how to verify each stage, how to back out)?
4. **Honesty.** Does the guide overstate what works for another phone? Are
   the "missing" items complete (compare with what the scripts pin: base
   archives, DTBs, recovery base, kits, trust keys, device-specific values)?
5. **Variants.** Is the RAM-map/memx/storage-profile treatment right for 8,
   16 and 18 GB phones and 128/512 GB storage?

Answer with findings ordered by severity, each with the guide section (and
file:line in the scripts when relevant) and a concrete fix. Do not modify
files and do not contact any device.
