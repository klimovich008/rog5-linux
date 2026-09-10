# Wi-Fi connectivity pass

V17 completed WPA2/CCMP association, DHCP and strict-key SSH over Wi-Fi on the
exact ROG5. It is consumed. No persistent Wi-Fi deployment or host-free cold
boot is claimed yet. Earlier power/firmware work remains in
`test-results/2026-08-31-wifi-late-activation.md`.

## What ran

- Executable source: `5d30695510348eb2066fa15f055c7070303f878f`.
- Source CI: run33419227736; exact-head, merge, QEMU and publication passed.
- Data-only admission: `5febbc25ae137e6f3b264165d09c51cafde629c5`.
- Target: `e9d40eb5-4cb8-4e16-b82a-75dce3717af1`.
- Kernel: `7.1.4-g1eea8970e87f`; the qualified kernel/DT/modules/firmware
  were reused without rebuilding them.
- The target package included the corrected foreground systemd WPA launcher.
  Exact package/controller replay passed in8.090s; packaging took4.501s.

S12 query/AUTO/held-OEM checks, direct UFS reads, firmware/PHY/scan and NCM
passed. WPA reached COMPLETED with CCMP pairwise/group ciphers. DHCP configured
`wlp1s0`. The host route used `wlan0` and the SSH client bound its WLAN address.
Strict known-host verification and the expected new phone boot ID passed over
that Wi-Fi connection. SSIDs, passwords, raw scan data and connection details
remain private; no credential content or digest entered Git/artifact manifests.

Entry→USB SSH took45.198s, entry→association100.845s, and entry→Wi-Fi
SSH108.475s. Requested reboot→restored V11 took75.840s; total184.502s.
Maximum sampled temperature across30 thermal zones was37.5°C.

## Recovery and limits

Normal reboot restored V11`1bc4a53b-ab56-40f2-a4ec-ead762590d01`, shared USB
SSH, persistent state and Tailscale services. Experimental storage stayed117-RO;
normal service restored only sda+sda23 writable. Final battery was Full/Good,
8.602V/30.1°C. The temporary management address,8079 permission and observers
were removed. No flash, slot, selector or partition-layout operation occurred.
V17 and all earlier experimental candidates must never be retried.

This proves a short Wi-Fi connection, not a long soak, automatic reconnect,
Internet independence or persistent boot. V11 remains the active fallback and
does not load the experimental Wi-Fi stack automatically.

## Next implementation boundary

Make the qualified composition boot without host assistance, then validate
repeated boots and loaded networking/power before changing the persistent
selector. The exact sealed initramfs still waits for USB carrier before loading
UFS. Its later P2 check requires the management address and SSH policy, but not
USB carrier, so the diagnostic wait is the identified early host dependency.

The existing state service follows P2 and mounts the verified4GiB state image
at `/persist`, with writes scoped to p23. Persistent SSH identity follows that
service. Reuse this mechanism for private Wi-Fi configuration; do not embed
credentials in public/reproducible firmware artifacts. Keep ASUS slot A and
the V11 bundle as independently usable rescue routes.
