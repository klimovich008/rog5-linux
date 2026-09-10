# Generation 30 accepted-Image live result

Status: **consumed; target USB absent; exact fallback passed; never retry**.

The sole RAM-only cycle used the retained accepted persistent-root Image,
current UFS-enabled DTB, and USB-first read-only initramfs. The recovery
controller accepted exactly one COMMIT and recorded its transmitted intent.
No `ROG5 persistent root` USB identity appeared before the known-good Alpine
fallback returned.

Exact retained host timestamps (+0200):

- boot claim: 15:50:51.896;
- recovery boot request: 15:51:21.723;
- recovery USB anchor: 15:51:22.391;
- bundle completion: 15:51:46.953;
- COMMIT/transmitted record: 15:51:47.852;
- fallback profile restoration: 15:52:15.456;
- strict fallback identity: 15:52:17.734;
- intent resolution as `FALLBACK_RETURNED`: 15:52:20.619.

The strict fallback record proved Linux `5.4.134-qgki-perf-00001-g6c308144c23e`,
the anchored USB path, and maximum reported thermal value 42.8 °C. Pstore was
empty, which remains inconclusive. Because target USB never appeared, the
retained evidence cannot show the exact target failure instruction or prove a
reset cause. No target-side filesystem operation or phone-storage write was
observed.

Together with Generations 27–29, this result localizes the next experiment to
active UFS binding/probing before initramfs can expose USB. Generation 31 must
therefore expose NCM first and defer the Qualcomm UFS probe until the host has
recorded the target identity.
