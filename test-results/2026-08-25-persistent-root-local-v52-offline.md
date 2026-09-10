# Persistent-root local V52 / Generation 161 offline

- Primary question: does the read-only staged Arch image reach power/USB,
  systemd, and key-only SSH, or which reboot-mode boundary fails first?
- Generation 160 is consumed with R7 classification. The target exposed
  `ROG5 persistent root` NCM for 23 seconds while the host selected the obsolete
  `ROG5 local image stage` product. No storage write ran; exact fastboot returned.
- The host selector now matches the sealed persistent-root gadget. The target
  publishes `kernel-verified` and `ufs-ready` before loading the two reboot-mode
  modules, with exact terminal details for module-load and binding failure.
- Kernel, DTB, UFS modules, charging modules, firmware, reboot-mode modules,
  staged local image, read-only storage policy, and stable recovery raw bytes
  are unchanged.
- Target initramfs twins completed in 3.424 and 3.376 seconds and matched at
  SHA-256 `10201034765f9278ac1113952bbe4f81a559d2307b33a74729b4361ab282957f`.
- Signed bundle twins matched at manifest SHA-256
  `f70e79df8684b5b17c8ce98a0e16bc7c9fbf82241673f2cb8d12de0d310b7b21`.
- Generation 161 reuses exact stable-recovery raw bytes under fresh AVB SHA-256
  `130d4eea6022969360a100a6427717ff2c7a45633770e7cbc7b92e85fd640fc1`.
- Focused candidate, runner, and gate checks passed in 6.83 seconds. The active
  repository tier passed in 61.103 seconds; its legacy sparse-map check accounts
  for 34.309 seconds.
- Full local CI passed once in 464.307 seconds at the frozen candidate source.
- Exact-head, merge-compat, QEMU, and candidate-publication CI passed for
  `b5c2f78803fe4b26d41d1099061d6c899a1a778f`. Generation 161 is admitted once;
  no phone boot has occurred.

## Generation 161 live result

- Recovery transfer, PREPARE, COMMIT, and target NCM passed. The host selected
  the exact persistent-root product and activated the `/30` link.
- Target stages proved reboot-mode modules, charging/UFS, userdata resolution,
  userdata mount, image resolution, and read-only image mount passed.
- Terminal result was sequence 15, `root-verify/FAIL`.
- The exact host image independently matches every seal, UUID, mode, size, and
  boot-critical hash. Source inspection proves `staged-seal` was first passed
  through the UUID-only read-only branch, so its later absence check was
  unreachable.
- Classification: R1 policy/control-flow defect. No storage write occurred;
  exact slot-A fastboot fallback and host cleanup passed.
