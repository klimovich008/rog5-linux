# Display60 V7 observer ordering

Result: **target handoff PASS; observer/fallback unresolved**.

- The sole dual-address NetworkManager profile survived source ACM and target
  USB re-enumeration; both host collectors were ready before COMMIT.
- Source exitrd entered the exact target. Boot
  `93780831-4e9a-4721-8e0f-19be97cdfcc0` reported through UFS/runtime and
  reached `switch-root PASS`.
- The post-switch observer was attached to `multi-user.target`. It emitted no
  record before the exact 180-second collector deadline, so no REFGEN, DSI,
  DRM, framebuffer, backlight, or status result exists.
- The target did not return to V11 within the 1,020-second host envelope. NCM
  later stopped answering with host TX errors while the USB gadget remained.
- One exact-topology host USB reset failed and removed stale gadget `devnum 99`;
  no fastboot, ADB, V11, or target USB mode returned afterward.
- V7 is irreversibly consumed and must never retry. No phone-storage write path
  was introduced or exercised.

The offline correction moves the read-only observer to `sysinit.target` before
`basic.target`. Physical fastboot and fresh V11 recovery are required before a
successor can be considered.
