# Generation 113 pre-USB timing discriminator

Date: 2026-08-24

Result: **CONSUMED; BOTH PRE-USB CHECKS PASS.** Never retry or flash.

Generation 112 returned exact fastboot 6.903 seconds after recovery departure.
That excludes its fixed 20-second UDC wait and `panic=10`, localizing the
boundary to immediate kernel-release or command-line validation. The native
verifier plan and Image banner are correct offline, but no independent target
transport exists before those checks.

Generation 113 reuses the exact Image and DTB and has no ConfigFS gadget, UFS,
block-device, SSH, installer, or payload path. It returns through the reviewed
restart2 helper after one of three fixed target delays:

- 5 seconds: kernel release mismatch;
- 15 seconds: command-line identity mismatch;
- 25 seconds: both checks passed;
- 60 seconds: watchdog/unexpected flow.

Identities:

- Image: `a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e`;
- DTB: `4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8`;
- clean-twin initramfs: `b859c7bfecd42a3d9087f01fe54fac887f81e3ce33fe7ed7b2a683ca101b1cd5`;
- signed manifest: `0ab3364d5622c3b85456f54ccdbc8fa4a9341f471a196027950fa3d352f2ffe3`;
- Generation 113 wrapper: `615ab41813ed4a3c5600d346fafa3e395155483dc383edd34edd071ec64465e0`.

The candidate is RAM-only, one-use, and flash-forbidden. Opus re-review was
attempted after Generation 112 but the service returned HTTP 529 overloaded;
the bounded local investigation continued from exact timing and source.

Live result: recovery USB departed at 07:42:55.324 and exact fastboot appeared
at 07:43:27.234, a 31.910-second interval. This matches the 25-second
both-checks-pass branch plus the measured 6.9-second bootloader overhead.
Kernel release and command-line validation are therefore exonerated. No USB
gadget, UFS, storage, SSH, or payload path existed in this target.
