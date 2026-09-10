# Current storage preflight / Generation 164

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
  passed in 4.944 seconds total.

## Live result

- Exact phone/product/topology/slot and battery gates passed: serial
  `M5AIKN00F0353YH`, `lahaina`, side port `1-1.2`, slot A, 8699 mV and
  `battery-soc-ok=yes`.
- The generic claim entered both durable locations and the source record was
  removed. Fastboot accepted the exact sealed snapshot in 12.757 seconds.
- The first recovery-anchor attempt hit the already observed transition race;
  a fresh same-boot anchor immediately passed on the same physical port.
- The canonical terminal report passed at `S99_COMPLETE`: 32 GPT entries,
  unchanged userdata LBAs 2352680--61865978, ext4 size 59513299 blocks,
  minimum 1219496 blocks, proposed split at LBA 53477375/53477376, all block
  nodes read-only, and zero block mounts.
- Recovery remained stable until the bounded automatic rollback. It
  disappeared at host timestamp `1787678123106944855` ns; exact slot-A stock
  recovery unauthorized-ADB USB appeared on the anchored port at
  `1787678141896525474` ns, 18.79 seconds later, with no USB network function.
- No mount, storage write, GPT operation, flash, slot change, or destructive
  Stage-1 authority occurred. Generation 164 is consumed and revoked forever.
- Private canonical evidence is retained under
  `/home/deck/.local/state/rog5-generation164-live-20260825-r1`.
