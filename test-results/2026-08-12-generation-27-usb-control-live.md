# Generation 27 exact Generation 20 USB control: live result

Status: **PASS, consumed, never retry or flash**.

The sole RAM-only lifecycle transferred and committed the exact signed
`persistent-root-usb-control-v6` bundle. The target enumerated as
`ROG5 persistent root` on the anchored USB port, its NCM host profile became
stable, and the lifecycle recorded success 65.057 seconds after it began.
The deliberate kernel-release mismatch then stopped target init before UFS
discovery and returned the phone to exact Alpine. Strict key-only fallback
SSH, host cleanup, intent resolution as `FALLBACK_RETURNED`, and restoration
of Steam's TCP/8081 socket all passed. Maximum fallback temperature was
38.1 C.

The exact target tuple was:

- Generation 20 Image
  `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf`;
- Generation 20 DTB
  `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`;
- persistent initramfs
  `908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e`.

This disproves the persistent initramfs/configfs implementation and a
payload-independent residual kexec state as explanations for Generations
22–26 failing before target USB. The remaining changed boundary is the target
Image and DTB pair. Generation 28 cross-pairs the live-proven Image with the
UFS-enabled Generation 25 DTB to isolate those two inputs while retaining the
same pre-UFS release mismatch.

No UFS inventory, filesystem operation, or phone-storage access occurred.
Empty pstore remains inconclusive.
