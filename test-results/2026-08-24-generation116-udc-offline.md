# Generation 116 extra-UDC classifier

Date: 2026-08-24

Result: **CONSUMED; NO EXTRA YET AT EARLY SAMPLE.** Never retry or flash.

Generation 115 proved that `/sys/class/udc/a600000.usb` exists but the class has
at least one additional entry. The strict exactly-one selector must not be
weakened. Retained evidence and DT/config inspection did not expose the extra
mainline basename, and two bounded Opus retries returned HTTP 529 overload.

Generation 116 binds no UDC and creates no ConfigFS gadget. It requires the
expected path, counts extras, and maps one extra basename to fixed timing buckets
for `a800000.usb`, DWC3 aliases, ChipIdea, MUSB, DWC2, dummy UDC, generic USB or
DWC3, unknown, and multiple-extra cases. It has no UFS, storage, SSH, or
installer execution surface.

Identities:

- Image: `a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e`;
- DTB: `4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8`;
- clean-twin initramfs: `489443769aa90f3ccb4bd2b1a6d28ead61e234195bf6882bc714be1ef1a8d317`;
- signed manifest: `16e4bdecca72d584c2cb00e263d9d3756778edcba7ab670ea2e95e2b601cebf9`;
- Generation 116 wrapper: `4c0ac09693ed1db066f78c64bf7024da6302b4aa193ffac13435320e512c0f83`.

RAM-only, one-use, no binding, and flash-forbidden.

Live result: exact fastboot returned 16.887 seconds after recovery departure,
selecting the 10-second `no extra` bucket plus bootloader overhead. Generation
115 observed an extra later in the same boot phase, proving asynchronous UDC
inventory change. No binding, gadget, UFS, storage, SSH, or installer ran.
