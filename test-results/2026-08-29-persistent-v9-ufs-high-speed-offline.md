# Persistent native-root v9 UFS high-speed successor — offline PASS

- Root cause addressed: R2 deployed composition. Persistent v8 packaged the
  pre-high-speed `ufshcd-core.ko` even though its Image config allowed bounded
  data writes.
- Changed layer: one kernel module plus target initramfs composition. Image,
  DTB, p24 root, power modules, stable recovery raw bytes, slot A, GPT, and
  phone storage layout are unchanged.
- New persistent builder guard checks exact four-module inventory, AArch64 REL,
  g359 vermagic, BTF, `struct module` size `0x500`, names, dependencies, and
  mutually exclusive discovery/high-speed markers.
- Retained stale core SHA-256:
  `98547f2e54361f86d02085b55516556a1f65504884fa0444559e9843c8ff3e38`.
- Live-proven V49 core SHA-256:
  `e3a049d43352fcec6fca6467f6a27b5d827d3d9071a789f782fe26d67f2b777a`.
- Target initramfs A/B twins built in 6.8 seconds and match at SHA-256
  `e465beb0e55e45ec9619df3cf5909e37c5040b1734dc42ad5abdaefb6671f59a`.
- Extracted-tree comparison proves 632 non-core entries retain exact metadata
  and content; the core matches the V49 twin byte-for-byte.
- Signed bundle A/B twins:
  - manifest `8bc47f291c97c5d52754bd800011864dd385e6993f04d7da1be31b0fc96563e3`;
  - signature `5d0e1e27f7bca45304a72081ff503a9845ee7fd5dfbebdab35481970404c996a`;
  - trust key `cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054`.
- Generation-234 AVB twins match at SHA-256
  `6826c4632a835deec8e5249a601f96c47ba973657ff61dca1067b5eecf3a1334`;
  raw recovery remains `7e4c7423…19648`.
- The v9 lifecycle reuses the existing runner and generic exact-record claim
  consumer. A live-proven softdog module is transferred to target tmpfs and
  bounds one 64 MiB p23 write/flush/remove probe at 240 seconds.
- Focused module-profile test: 1.24 seconds, PASS.
- Persistent-initramfs suite: 11.56 seconds, PASS.
- Final active tier: 76.62 seconds, PASS.
- Full local CI: 7 minutes 22.177 seconds, PASS.
- Exact candidate source checkpoint:
  `97b83fed4d456f8ef3c523f516f465bc99890fec`.

The signed bundle is exposed through a read-only host bind mount. Candidate
authority is `none`; no v9 claim, phone boot, p24 modification, flash, or
storage probe has occurred. The next gate is exact-head publication/CI,
followed by one non-consuming connected preflight and one RAM-only cycle.
