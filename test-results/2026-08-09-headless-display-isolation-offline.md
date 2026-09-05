# Linux 7.1 headless display-provider isolation — offline result

Date: 2026-08-09

Result: **PASS for offline headless display-provider isolation; no phone boot or power claim.**

## Defect fixed

The accepted Linux 7.1 recovery/network-root DTB disabled MDSS, DisplayPort,
both DSI controllers and PHYs, GPU, GMU, GPUCC, and the Adreno SMMU.  DISPCC
was implicitly enabled because its node had no `status` property.  Live GPU
diagnostics had previously observed that separate display-clock provider in a
runtime-suspended state, so the minimal server profile did not have complete
display-provider isolation even though it could not light the OLED.

The new overlay adds only `status = "disabled"` to the exact DISPCC node.  A
bounded structural verifier pins the accepted base DTB and rejects any other
node or property change.  The runtime oracle separately requires all display
providers to remain disabled and rejects any MDSS/DISPCC platform device, DRM
card/render node, backlight, framebuffer, or display device node.

## Exact identities

| Input/output | Size | SHA-256 |
|---|---:|---|
| accepted recovery DTB | 102,870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| reproducible headless display-isolation DTB | 102,894 | `c4269bdca1e0e59ab2c9f99a75a142f92b33ce1ae7aefa87daca449d262966f2` |

The verifier reports:

```text
PASS headless display-isolation DTB approved_changes=1 dispcc=disabled
```

This candidate retains the accepted Linux source, config, Image, modules,
initramfs, storage isolation, USB/NFS/SSH design, and one-shot lifecycle.  No
kernel rebuild was required or performed.

## Fail-first and regression timing

Before implementation, the two new hostile suites failed for the intended
missing-contract reasons:

```text
dtb_status=1 dtb_ms=8
FAIL missing readable ordinary test input: .../sm8350-asus-rog-phone5-headless-display-isolation.dtso
runtime_status=1 runtime_ms=8
FAIL missing executable headless display-isolation runtime checker
```

After implementation:

```text
PASS hostile headless display-isolation DTB candidate contract
PASS hostile headless display-isolation runtime classifications
TIMING dtb_ms=833 runtime_ms=448 total_ms=1282
```

The suites reject enabled or missing providers, a linked status file, bound
MDSS or DISPCC devices, arbitrary DT changes, extra nodes, a stale/wrong base,
truncation, linked output/input attacks, and DRM, render, backlight,
framebuffer, `/dev/dri`, or `/dev/fb` exposure.

## Boundary and next acceptance

No panel, GPU, suspend, or battery behavior was tested.  A disabled display
stack is the safe minimal-server default; it is not proof that the Samsung
AMS678 OLED and Pixelworks Iris bridge can enter a measured low-power state.
The runtime oracle must run on a separately authorized temporary target before
this becomes live evidence.  A later display-capable DTB must independently
prove bridge/panel power sequencing, DPMS off/on, power-button wake, SSH
continuity, and wall-power or battery deltas.
