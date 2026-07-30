# Native power-key status indication

## Purpose and state

This is the first userspace component admitted after the SSH-only minimal
root. It gives a person holding an otherwise screen-off phone one bounded
sign that Linux received a real power-button press. It is **offline-ready and
live-pending**: no phone was contacted and no LED has been energized by this
milestone.

The accepted SSH-only root remains unchanged. `headless-v2` is a successor
staging profile which adds only:

- `/usr/local/libexec/rog5-key-indicatord`;
- `rog5-key-indicator.service`; and
- `leds-qcom-lpg` in one modules-load file.

It does not add Python, a compiler, display software, VNC, a browser, an AI
agent, wireless networking, firmware, or another package.

## Exact artifact

The production binary is a stripped static PIE for AArch64:

```text
path=artifacts/headless-indicator-v1/rog5-key-indicatord
size=67520
sha256=3792745382a390ebeef37a081e532884aae07bbcd73fd9f0da1c94e67bdabbc8
source_sha256=3d597f919d71a76f2aef0ae2aa269e219ffe7c0bdca0e9b73481d52dff686939
compiler=cc (Alpine 15.2.0) 15.2.0
source_date_epoch=1681862400
```

Two independent builds in the pinned ARM64 image produced that exact hash.
The fixture-enabled build is separate, temporary, and rejected by production
artifact checks.

## Runtime identity gate

The daemon refuses to run unless all of these are true:

| Boundary | Required value |
|---|---|
| input class name and ioctl name | exactly `pmic_pwrkey` |
| input capability | `EV_KEY` plus `KEY_POWER` 116 |
| matching input devices | exactly one character device |
| LED class name | exactly `green:status` |
| LED firmware node | suffix `/soc@0/spmi@c440000/pmic@2/pwm/led@2` |
| LED driver | exactly `qcom-spmi-lpg` |
| maximum brightness | exactly 511 |
| initial brightness | exactly 0 |
| selected trigger | exactly `none` |
| brightness endpoint | regular sysfs attribute, not a link |

`--probe` performs those checks and prints the canonical
`rog5-buttons-indicator-runtime-v1` record with the resolved OF and driver
paths plus the observed brightness and trigger text. It does not open the
brightness attribute for writing.

## Event and power policy

Only `EV_KEY`, `KEY_POWER`, value 1 starts a pulse. Release (0), autorepeat
(2), volume keys, unrelated events, a second press while a pulse is active,
and malformed/truncated records do nothing or fail closed. A pulse writes
brightness 31 for 180 ms using a `CLOCK_BOOTTIME` timer and then writes zero.
`SIGINT`, `SIGTERM`, device removal, and event-loop errors also restore zero
before exit.

Signals are blocked and consumed through `signalfd`, removing the
check-before-`poll()` stop race. The LED-active state is recorded immediately
after a successful on-write, so even a subsequent timer-arm failure enters
the off path. Off writes are retried three times. The service also invokes
the binary's identity-checked `--off` mode after every stop as a fresh-file-
descriptor fallback.

There is no heartbeat. The LED stays off at idle, so this feature adds no
continuous wakeup or LED current. It does not replace logind's long-press
poweroff policy and does not control the OLED.

The systemd unit runs as root only for the root-owned input and brightness
endpoints. It has an empty capability set, a closed device policy allowing
read-only input devices, no private network access, protected kernel
tunables, a strict filesystem policy with an explicit exception for the exact
brightness path, and a system-service syscall allowlist. The attended gate
must prove that the exception remains writable while another writable sysfs
attribute is denied; the offline systemd parser cannot establish mount-
namespace behavior on the phone.

The unit deliberately has no `ConditionPathExists` shortcut. If LPG or evdev
is not ready yet, exact validation fails visibly and `Restart=on-failure`
retries it; an early one-shot condition would silently skip the service
without activating restart policy.

## Tests

Run the portable logic and policy suite:

```sh
scripts/host/test-key-indicatord.sh
scripts/host/test-arch-headless-core-rootfs-contract.sh
```

Run the pinned AArch64 reproducibility and QEMU suite when its accepted local
image is present:

```sh
scripts/host/test-key-indicatord-aarch64.sh
```

Fixtures prove the one-pulse policy, ignored events, truncated-record
rejection, exact driver/OF/max/initial/trigger identity, linked-endpoint
rejection, cleanup after an injected timer-arm failure, explicit post-stop
cleanup from a nonzero state, and synchronous LED-off cleanup during a
five-second pulse. The
successor root contract proves that the sealed binary and service are
read-only build inputs and that no deferred UI or agent package entered the
minimal package list.

## Remaining live gate

A later attended RAM-only cycle must first pass the corrected minimal
SSH/storage/rollback contract. It may then run `--probe`, record physical
press/release events, enable the service, observe one low-power pulse, and
prove clean SSH, kernel logs, storage isolation, normal fallback, and zero
brightness afterward. The offline result grants no boot, credential, phone,
or hardware-write authority.
