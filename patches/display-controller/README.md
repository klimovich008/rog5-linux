# Draft display-loader ordering repair

`0001-default-dark-probe-ordering.patch` is an offline successor source patch,
not a kernel patch, admitted controller or installable payload. It applies to
`load-display.py` SHA-256
`5c298ba05fe7a6f338471cd178a10b49cd9c03914f4a696ad442e7e0dbc1838d`.
The exact historical source is retained in
`scripts/device/fixtures/display-loader/load-display-before.py`. It contains no
unit serial, USB topology or credential. Do not import this fixture: the test
extracts only the functions under test and substitutes hardware/identity I/O.

During insertion the successor observes the qualified default-zero brightness
property. After both insertion children finish and are reaped, it validates the
framebuffer endpoint and sends one zero command. It requires command success
and a final caller health/monitor check. Failed preparation, DSI errors and
zero-property readback after a failed write remain failures. Independent cleanup
still runs and cannot overwrite the original failure. No insertion retry is added.

Neither framebuffer registration nor insertion completion proves preparation.
The current kernel disables deferred fbcon takeover, but deferred driver probing
is possible; the resulting EPERM remains a conservative failure. Do not add
retries or modesets to turn that result into PASS without reviewing the actual
activation operation. The historical endpoint's framebuffer routine checks the
zero property, not proof of an earlier successful command; a successor must
update its “after blanking” docstring to reflect that distinction.

The old helper/module pins intentionally remain unchanged. They are incompatible
with the current production cohort, and the old panel's default1023 is rejected.
Before this can become a usable controller, bind the default-dark panel and the
complete production dependency closure, qualify insertion order and timing,
update the endpoint and enclosing component contracts, and requalify admission,
one-use ownership, independent cleanup and rescue. Never edit sealed controllers
or reuse a consumed claim. Applying this patch grants no execution authority.

Run `python3 -O scripts/device/test-display-loader-ordering.py` for semantic
coverage. It applies the patch without fuzz, executes the actual loader/child
supervision, and compiles the actual current panel plus pinned DRM/backlight core
extracts. Sysfs, identity, module insertion effects and preparation timing are
fixtures. The test also verifies the previous loader fails with EPERM. No module
is loaded and no phone operation, optical result or physical PASS is implied.

## Current production module input

`scripts/device/build-production-display-modules.py --output /absolute/new.tar`
materializes the fixed REFGEN/GPUCC/panel/MSM symbol dependency closure from the
machine-readable current board qualification. It validates that qualification,
module metadata, dependency-index hashes, actual ARM64 ELF identity/vermagic and
default-dark panel hash before atomically publishing an inert tar with an embedded
manifest. Existing outputs are never replaced. Nothing is loaded or signed.
The manifest binds builder/checker hashes and the exact board inputs. No helper,
service, aliases, modprobe index, firmware or boot image is added. Future archive
consumers must verify the archive hash and its exact members before staging it.

Its order is only a symbol dependency order. REFGEN's DSI-PHY supply and GPUCC's
GMU/SMMU clock/power relationships come from DT, and MSM can trigger fbcon/panel
preparation automatically. Those activation edges require review in the successor
controller; no insertion commands are generated. Inserting GPUCC can program PLLs,
and opening MSM DRM can load firmware/start the GPU. These are hardware actions.

All14 current modules have empty `.modinfo` firmware fields, but exact A660 source
requests SQE/GMU firmware and the overlay names `qcom/sm8350/a660_zap.mbn`.
Firmware status is explicitly NOT PACKAGED; empty module metadata is not proof of
runtime firmware completeness. The archive is an unsigned host fixture, not a new
phone candidate. Keep the historical loader and consumed claims unchanged.
