# Active context

[Current state](current-state.md) is the single authoritative handoff.
Do not duplicate its device identity, artifact hashes or historical incident list.

The existing server goal is active, now governed by
[headless release acceptance](release-acceptance.md); display remains optional.
See the
[boot-code review and focused correction](../test-results/2026-09-04-native-boot-review.md).
Registry closure and the corrected RAM-only v4 rescue have restored pinned SSH
and persistent service state. Keep Arch: the proven recovery blocker was project
handover ownership, not the distribution. Capture and host cleanup are complete.
The SSH restart dependency cascade is now corrected in source and passes real
systemd regression tests, but is not yet deployed. Normal USB SSH was restored
with an address-only change; state/Tailscale remain stopped behind the failed
boot-only P2 gate. The phone did not reboot. Publish and validate a fresh coherent
rescue with the corrected service graph; do not retry consumed v4 or bypass P2.
The original installed-boot failure remains unproven; RAM rescue success is not
installed-release qualification. See current state for deployed versus pending fixes.

Physical display validation is paused; the interrupted V15 preparation did not
sign or execute. Do not infer a need to reboot from the SSH failure alone.
Use [development](development.md) for commands and [lessons](development-lessons.md)
for the relevant failure class. Historical evidence is linked from current state.
