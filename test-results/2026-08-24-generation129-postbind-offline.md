# Generation 129 post-bind UDC fix

Result: **CONSUMED; TARGET NCM PROVED.** Never retry or flash.

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

Live result: recovery departed at `15:22:35.399500`; the exact target product
enumerated at `15:22:37.695984` and disconnected at `15:22:38.215501`, a
0.519517-second target-NCM dwell. Slot-A fastboot appeared at
`15:22:42.816505`. The host's final “before target appeared” message is a
sampling artifact: the kernel journal proves the target appeared on the exact
port and driver. No SSH, installer, or storage write ran; fallback passed.
The next target must expose the existing stage protocol before the detailed
power/USB loader and retain terminal evidence long enough for host activation.
