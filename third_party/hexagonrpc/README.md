# hexagonrpc (hexagonrpcd) for the sensor DSP

`hexagonrpc-598b591.tar.gz` is `git archive` of
<https://github.com/linux-msm/hexagonrpc> at commit
`598b591ae9da6a6cfe2ca5ea78998019ca6395ea` (sha256 47924eab…cabb1b8). COPYING
is its GPL-3.0-or-later license. The user approved using it on 2026-09-26.

hexagonrpcd is the host end of the SLPI's FastRPC reverse tunnel: the SLPI's
sensor_process reads the stock sensor registry and config through it, and
without it the Snapdragon Sensor Core reports no sensors.

`0001-hexagonrpcd-serve-sns_reg_version-next-to-the-registry.patch` is ours.
The registry task reads `registry/../sns_reg_version` and, when it is
missing, rebuilds and writes the registry. hexagonrpcd serves read-only, so
the write failed and sensor_process asserted (`sns_registry_sensor.c:154`,
r89).

`0002-hexagonrpcd-validate-output-buffer-counts-and-sizes.patch` is ours
too (2026-10-02 audit; the prior agent checked upstream at da7a374).
The follow-up inspected [upstream listener.c](https://github.com/linux-msm/hexagonrpc/blob/main/hexagonrpcd/listener.c):
the accessible cached main view still lacks primary-output accounting.
Host DNS is restricted, so this is not a fresh remote-HEAD verification. The listener checked
a request's output-buffer count without the primary output buffer (and
without the buffer of a type sequence), so a request with one output buffer
for `apps_std_fread` or `remotectl_close` passed and `alloc_outbufs4()`
wrote past its array. 0002 counts every buffer the allocator fills, refuses
a request without its primary input buffer, an out-of-range inner type and
an output buffer over 64 MiB, skips the extended method ID word in the
allocator as the validator does, rejects empty strings before indexing
`s - 1`, decodes empty input buffers, and makes the daemon exit nonzero
when the listener ends (so systemd restarts it).
`scripts/device/test-hexagonrpcd-listener.py` builds the daemon and runs
malformed requests against the listener under AddressSanitizer.

`scripts/device/install-rog5-sensors.sh` builds it on the phone with the
root's gcc, installs `/usr/local/bin/hexagonrpcd` and stages the data
(root-owned, world-readable). `rog5-sensors.service` runs it as a dynamic
unprivileged user in a sandbox. The build was reproducible before 0002:
sha256 5668f659… twice.
