# Local-image direct V46 offline checkpoint

Result: **OFFLINE PASS; LIVE CONSUMED; FALLBACK_RETURNED.** Never retry.

The exact 16 GiB Arch image is represented by one generated 37-range map:

- image SHA-256: `533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153`;
- mapped direct-write bytes: 1,850,654,720;
- map SHA-256: `e21b9453662d5f24536144e322ed0ef6bde7038efb44fdf1afcb80ee823ccd94`.

The complete stream passed against a fake target. Exact sealed BusyBox 1.37
accepts the required `iflag=fullblock`, `oflag=direct`, `conv=notrunc`, and
`status=noxfer` behavior.

Target initramfs clean twins match at SHA-256
`732a107f835d882560b84e60d00caf9f3c6e10890d7e4456e7acf354d764cfc1`
and size 23,806,105 bytes. The signed bundle manifest is
`4872ce3609a87449ab309af201e5b06d8791306eb3240f27fbc0ef2e0fe4ce9b`.

Generation-155 RAM-only wrapper SHA-256 is
`cba61981d5a120744bd366bbde05af5f30a8ff36b163223fe53fa62ea0705344`;
the raw recovery payload remains
`4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8`.

The generic packager now accepts authority-free offline
`persistent-root-ro-v1` records, with an unknown-profile refusal regression.
After full local CI (433 seconds) and exact-head/merge/QEMU GitHub success on
the reviewed implementation, Generation 155 was admitted for one RAM-only
cycle. COMMIT or any ambiguous outcome permanently consumes it.

## Live result

The target passed NCM, power/USB, UFS, storage lock, runtime, and key-only SSH.
Its fixed `prepare` operation then failed before any extent stream. The old
host streamer replaced the target's bounded failure record with a generic
message, so the exact target predicate is unavailable. Exact slot-A fastboot
and host cleanup passed; intent resolved `FALLBACK_RETURNED`.

Failure class: **R7 host observability**, with a probable exact residual-state
mismatch. Generation 154 durably synced an empty benchmark directory before
the later buffered file stalled, while V46 accepted only one populated
residual directory.
