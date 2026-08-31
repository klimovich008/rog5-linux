# Charger-runtime qualification — prepared, not executed

V21 proved native-root/Wi-Fi startup after USB data was removed before root
mount. The next physical question is whether the running Wi-Fi target remains
safe and non-depleting when its side-port cable moves from PC SDP to the original
ASUS charger, then back to PC for V11 recovery. This is runtime qualification,
not yet charger-only startup from the bootloader.

The exact qualified Image/DT/initramfs are reused; no kernel/module/firmware or
wrapper rebuild occurred. A RAM-only observer records battery/USB power_supply,
Type-C roles/mode, thermal maximum and all117 storage read-only flags. It never
writes charging, role, thermal or storage controls. Two exact samples on the
current Arch root pass in3.318s.

The controller boots on PC data, proves automatic WLAN SSH, starts the observer,
then emits an explicit cable-switch prompt. It waits at most90s for PC USB to
disappear,30s for charger online state, observes120s with bounded WLAN traffic,
then waits90s for the exact PC USB device to return before V11 recovery. Target
600s/900s timers remain armed. Complete assembled binding checks and switch/
charger/reconnect ordering replay pass. An `operator-ready` file with exact
content/mode/owner/link metadata is required before any live preflight.

Executable source remains`84c38b597e1530e885c2ad0c3f4abfd0d5814c10`, whose
exact-head run33439112540 passed all jobs. Candidate
`persistent-native-root-wifi-charger-v22` has identical signed twins;
packaging0.438s. Manifest:
`f89172917b75af2187192e948ae92d5550c6d4fe91f6c8b2ab0493a71be25d0f`.

V22 is admitted but unconsumed. The operator-ready marker is absent. No phone
boot, cable change, flash, partition, slot or selector operation occurred during
this checkpoint. Keep the PC cable connected until the operator confirms they
can perform both switch and reconnect during the bounded live window.
