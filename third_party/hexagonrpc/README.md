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

`scripts/device/install-rog5-sensors.sh` builds it on the phone with the
root's gcc, installs `/usr/local/bin/hexagonrpcd` and stages the data.
`rog5-sensors.service` runs it. The build is reproducible: sha256 5668f659…
twice.
