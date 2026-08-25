# Current storage preflight / Generation 164 offline

- Reissued the retained live-proven V4 read-only preflight bytes under fresh AVB
  generation 164. Raw wrapper, kernel, initramfs, and report behavior are
  unchanged.
- The public checkpoint binds current dedicated-layout geometry, current
  userdata UUID, current source image, slot-A rescue, and Generation 163.
- Wrapper SHA-256:
  `d9a500dd7285b6f7789df89c8da0735f75bb04ee893808bb4f59de1e9e46fdf1`.
- Exact-head GitHub CI passed for source checkpoint
  `b9ace7c67b5e623f0fd5acd0d1dfa4addf0b6008` on the second run; the first run
  was cancelled after the QEMU job stalled in checkout rather than executing
  repository code.
- Generation 164 is now narrowly admitted for one read-only RAM boot. The
  candidate manifest remains authority-free; the separate policy row and
  generic exact-record consumer bind only this manifest and wrapper.
- Focused admission, generic claim, retention-admission, and collector suites
  passed in 4.944 seconds total. No claim has been consumed and no phone boot,
  mount, storage write, GPT operation, or destructive confirmation exists yet.
