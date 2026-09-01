# Native Wi-Fi V29 lifecycle result

Result: **PASS**.

The cycle asked one question: does a phone-local pre-stop transaction quiesce
persistent state and enter the exact already-signed Wi-Fi target?

## Proven cause and correction

V24-V26 were classified R8. They crossed host COMMIT, but exitrd reported
`teardown failed=detach`, set `clean=0`, refused kexec, and performed normal
fallback. Their intermediate `ROG5 recovery` USB identity was the stable
recovery wrapper, not the experimental target.

A claim-free physical comparison proved the correction:

- active persistent state: `teardown-clean=0`;
- local stop of Tailscale and persistent state plus all 117 UFS nodes read-only:
  `teardown-clean=1`.

The repository transaction helper now performs that proven ordering locally,
survives SSH loss, and requests V11 reboot if quiesce fails. The loader again
requires the state runtime record to be absent and all 117 nodes read-only.

## V29 evidence

- Source exitrd: `native-kexec enter`.
- Target kernel: `7.1.4-g1eea8970e87f`.
- Target boot: `54a5e437-9a04-402a-b14e-01dbcb8a3b5d`.
- Final target stage: `switch-root PASS`.
- Systemd: running, no failed units.
- Wi-Fi: `wlp1s0`, carrier 1, DHCP active; radio/WPA/DHCP units successful.
- Battery: Full/Good, 100%, 8.573 V, 29.9 C.
- Side USB power: online, 500 mA current limit.
- P24: read-only.
- Fresh V11 fallback: `f70ba888-af07-492c-920d-75fef09313b5`.
- Phone storage layout, slots, persistent selector, and boot partitions:
  unchanged.
- Claim: consumed; never retry V29.

## Validation

- Focused transaction/exitrd/state tests: 3.167 seconds.
- Full local CI: 507.308 seconds.
- GitHub workflow `33501662401`: exact-head, merge compatibility, QEMU system,
  and candidate publication all passed for lifecycle commit `09058633`.
