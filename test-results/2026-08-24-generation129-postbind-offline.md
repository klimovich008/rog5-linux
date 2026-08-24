# Generation 129 post-bind UDC fix

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Primary question: does removing only the false instantaneous post-bind
`/sys/class/udc` inventory assertion allow the unchanged UFS-capable charging
kernel to enumerate NCM and enter the existing staging path?

The fail-first test rejects the Generation 128 assertion. Exact ConfigFS UDC
readback, bounded exact-only bind retry, `usb0` readiness, host identity,
key-only SSH, one-file storage scope, and stock slot-A fallback remain.
Target twins are `47b7be27...ebd4bc`; manifest is `c38000c3...cdfba6c`;
Generation-129 recovery is `53b74a35...b3fed0`. Image, DTB, modules, stable
recovery raw bytes, and installer are unchanged. Focused tests, sealed BusyBox,
and the active tier pass; no phone contact occurred during this build.
