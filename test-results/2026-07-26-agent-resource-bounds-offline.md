# Browser-automation resource bounds — offline result

Date: 2026-07-26

Result: **PASS OFFLINE for native systemd resource/restart controls and the
complete Arch rootfs archive round trip; no phone or external account was
used**.

The fail-first isolation test rejected the existing unit at the first absent
control, `StartLimitIntervalSec=300`. The implementation adds no daemon or
package. It uses the existing service's cgroup and systemd start limiter:

| Control | Value | Boundary |
|---|---:|---|
| `CPUQuota` | `200%` | at most two CPUs of aggregate runtime |
| `CPUWeight` | `25` | yields CPU share to normal-priority work |
| `MemoryHigh` | `1536M` | applies reclaim pressure before the hard cap |
| `MemoryMax` | `2048M` | hard cgroup memory ceiling |
| `MemorySwapMax` | `512M` | bounds swap/zram churn |
| `TasksMax` | `256` | bounds Chromium processes and threads |
| `IOWeight` | `25` | yields I/O share to normal-priority work |
| `OOMPolicy` | `stop` | stops the unit after a cgroup OOM |
| `RestartSec` | `15s` | delays failure restarts |
| start limiter | 3 starts / 300 seconds | prevents rapid restart loops |

The static contract passes and ShellCheck 0.10.0 reports no warning-or-higher
finding. A disposable extraction of the preceding agent-isolated rootfs,
updated with only the new unit, passed the complete AArch64 rootfs verifier
and in-rootfs `systemd-analyze verify`.

The full clean staging pipeline then installed the authenticated package set,
exact Linux `7.1.4-g7a5cef0db479` modules, pinned firmware, and the bounded
unit. The complete verifier passed before archival and again after extraction
into a second clean volume with ACLs and xattrs preserved. Independent
host-side SHA-256 and `gzip -t` checks matched the pipeline result.

## Exact output

| Field | Value |
|---|---|
| Source commit | `efea034488df41b7bf672309cb45462accbe02bb` |
| Size | `2,006,969,518` bytes |
| SHA-256 | `246b6e67482472756edef5641ab190a9bde9245cacda1dac6accaf16edb855e2` |
| Builder image | `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c` |

## Source identities

| Input | SHA-256 |
|---|---|
| `rog5-chromium-headless.service` | `6e6cfd6a3ede945f67dc9dd42650153a1abfc63651175f54868e1e394cdac8cb` |
| `test-agent-isolation.sh` | `fd456f191ba8c33009311810d6eda30e3360d4dbe6b70924e84d2dd8c5bdf709` |

## Remaining gates

The limits are conservative safety ceilings, not an on-device performance or
battery result. Hardware acceptance must confirm cgroup-controller support,
page-load and automation reliability, peak/high memory behavior, OOM and
restart handling, thermals, latency, charging, and energy use with the panel
off. Model clients still need separate job-time, thermal, provider-rate, and
network-egress policies. This development archive remains outside Git and is
not the manifest-pinned NFS root.
