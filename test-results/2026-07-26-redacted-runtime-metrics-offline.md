# Redacted runtime metrics — offline result

Date: 2026-07-26

Result: **PASS OFFLINE for the staged one-shot collector and the complete Arch
rootfs archive round trip; no phone or private evidence was used**.

The existing baseline collector was not installed in the Arch target and
reported only a small vendor-kernel snapshot. The extended
`rog5-collect-baseline.sh` now emits stable `key=value` fields for:

- total/available/used memory and total/free/used swap;
- uptime, one-minute load, runnable tasks, and aggregate CPU total/idle ticks;
- selected Plasma/KWin/KRDP/Xwayland process count and proportional set size;
- the browser-agent active state, current/peak memory, task count, consumed
  CPU time, and restart count;
- battery presence/status/capacity/voltage/current/temperature and the maximum
  readable thermal-zone temperature;
- saved screen state, panel brightness, DSI state/modes, DRM render-node
  count, BTF, and legacy KGSL model/reset/fault counters; and
- presence, state, RX bytes, and TX bytes for USB, Wi-Fi client, AP, and VPN
  interfaces.

The collector deliberately does not read or emit kernel command-line data,
network addresses, MACs, SSIDs, serials, process arguments, account data, or
credentials. Missing hardware produces `unavailable` rather than a failure.
Two snapshots provide CPU and interface deltas without a resident monitoring
daemon.

## Verification

- A fail-first synthetic proc/sys/systemd fixture rejected the historical
  collector.
- The completed fixture requires all desktop, automation, power, display,
  thermal, DRM, target/inhibitor, and interface-counter fields and rejects
  forbidden identifier sources.
- A host smoke run produced the complete redacted schema with absent
  phone-only hardware reported as unavailable.
- ShellCheck 0.10.0 has no warning-or-higher finding.
- A disposable extraction of the preceding rootfs passed the complete AArch64
  verifier after adding only the collector.
- A full clean Arch staging passed the complete verifier before archival and
  again after extraction into a second clean volume with ACLs/xattrs
  preserved.
- Independent host-side SHA-256 and `gzip -t` checks matched the pipeline
  result.

## Exact output

| Field | Value |
|---|---|
| Source commit | `5292f3caf4acba7e548505a004f55e6c3276661e` |
| Size | `2,007,027,068` bytes |
| SHA-256 | `5863cacf23a9c0cb972b37e3c71f801df77ccb708a277c0f2787d3afd9ac51e4` |
| Builder image | `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c` |

## Source identities

| Input | SHA-256 |
|---|---|
| `collect-baseline.sh` | `2726ffda517aa13d97da4c9b04712524ccded2ba6ac25f2021f337a10523b946` |
| `test-collect-baseline.sh` | `194d831aef5169aea17fdc4d9dc5853f0e0ff8be62682fc56fba2c000040a105` |
| `stage-arch-rootfs.sh` | `b9bde0627b86e08fb4bab1e2d6b3ea22199f132bb170719aabd285b749215038` |
| `verify-staged-arch-rootfs.sh` | `691ac1e2f362629145b0104777e1a8b5ca55b5ad81b63e148ac36649cc01226e` |

## Remaining gates

The helper prepares evidence; it does not constitute a phone measurement.
The live matrix still needs fixed-duration headless, Plasma, KRDP, browser,
panel-on, DPMS-off, compositor-stopped, charging, radio, VPN/hotspot, and load
runs. Battery-current sign and energy use must be correlated with charge
status and an external wall-power meter. This development archive remains
outside Git and is not the manifest-pinned NFS root.
