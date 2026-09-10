# Server development resumed — transport and retained-build checks

Starting source: `a2e3efb4b48bc1fad614d701a548a593e3e296a2`.
Primary question: is the accepted server reachable and healthy enough to test
the next unconsumed display candidate?

## Live transport: not recovered

The anchored `1-1.2` USB gadget reports `1d6b:0104`, “ROG5 persistent root”.
Host NCM carrier is 1; runtime power is active and USB autosuspend control is
`on`. These descriptors alone do not prove fresh exact-device or server health.
The host has the expected `10.77.0.1/30` direct route and existing shared profile.

Host kernel logs show repeated `NETDEV WATCHDOG` transmit-queue timeouts
(about 5.6–6.0 seconds). RX remained 386 packets / 69,632 bytes while TX errors
rose from 2,575 to 2,590. Neighbor resolution for `10.77.0.2` fails. Strict
host-key-pinned SSH to that address and the last known Wi-Fi address both
returned “No route to host”. This proves a transport symptom, not whether the
target is alive, panicked, or whether the host USB path caused the failure.

One bounded reactivation of the existing phone-only NetworkManager profile
succeeded but did not recover SSH. Profile configuration was not changed.
An ACM node found on a different USB topology was deliberately not opened.
Requested side-port data-cable reconnection without a forced reboot, retaining
charging. Fresh battery/temperature, storage and service health remain unknown.

At 22:25:14 host local time the old USB device disconnected. Fresh enumeration
attempts on the same path failed with descriptor errors `-110` and `-71`, then
“unable to enumerate USB device” at 22:25:29. The gadget and NCM interface are
now absent. This places the current failure below IP/SSH, but does not isolate
the cable/hub, host controller or target gadget/kernel. Await the operator's
screen observation before choosing recovery; no reset was sent by this agent.

## Offline checks and demonstrated R3 test-tool fix

No new signed V15 artifact was found in the current display build directory;
V15 remains interrupted preparation, not a tested successor. V14 and earlier
display candidates remain consumed and must not be booted again.

The retained V14 archive has SHA-256
`8dbc37f659a67e69a6b00b174898786bed0b7f39d1164e1674571a6e90bdfa70`.
It is suitable for offline testing only. No kernel or wrapper was rebuilt.

The sealed-shell test initially failed because external child applets entered
QEMU via binfmt without inheriting the parent's `-r` argument. They reported
the host kernel version and searched the wrong `modules.dep` directory.
Installed QEMU help documents `QEMU_UNAME` as the environment equivalent.
Passing that variable inside the already isolated namespace fixes children
without exposing host `/lib` or changing phone payloads.

Regression `test_shell_children_keep_target_release` failed before the fix
with the host release twice, then passed with the exact target release twice.
All four sealed-runner tests passed in 0.367 seconds. The actual V14 shell
probe passed in 0.848 seconds, proving runtime shell syntax, `qcom_pon` name,
`7.1.4-rog5-display60-v1` vermagic and module metadata `0:0:644:1` with the
explicit simulated runtime module index. This is not hardware/systemd proof.

Power-button behavior/confinement and status-screen time/Wi-Fi/battery tests
passed. The complete active tier passed, including the new child-exec test.
Full unchanged kernel/recovery CI was not repeated for this offline-tool fix.

## Next action and boundaries

Reconnect data and obtain pinned SSH plus current identity/slot, power/thermal,
storage and fallback evidence. Then finish the unissued display successor's
existing composition/admission checks and use one attended physical cycle.
Do not infer boot eligibility from offline success or USB descriptors alone.

No phone boot, flash, slot change, storage write, signing or claim consumption
occurred. Stock slot A, installed native server and signed fallback are unchanged.
