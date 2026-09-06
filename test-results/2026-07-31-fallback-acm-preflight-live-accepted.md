# Fallback ACM preflight live acceptance

Date: 2026-07-31

Result: **ACCEPTED; signed private proof retained; temporary boot unused**

## Outcome

A physical reboot restored the installed Alpine fallback's supervised ACM
reader. The phone first returned to its exact `lahaina` fastboot identity,
then a normal, non-flashing reboot returned the expected Alpine composite
gadget on the same physical USB port.

The first fresh signed exchange reached the phone and rejected at its thermal
health predicate. A read-only diagnostic payload, verified with the same
pinned Alpine Ed25519 host key, isolated every other signed field as healthy:

- exact fallback kernel, BusyBox init, device compatibility, and ext4 root;
- no project modules, no pstore records, and no fatal dmesg signatures;
- Python 3 and a canonical fresh boot ID; and
- 96 contiguous thermal-zone objects with a live maximum below 40 C.

The former controller required exactly 70 readable thermal zones. The current
fallback exposes a larger valid topology: core CPU, GPU, modem-subsystem, and
always-on sensors are readable, while unsupported auxiliary modem and board
channels return `EIO`, zero, or the Qualcomm inactive sentinel. Treating every
declared auxiliary channel as a mandatory thermometer made the health gate
reject safe telemetry.

## Corrected thermal contract

The signed health collector now requires:

- a contiguous topology of 70 through 128 thermal zones;
- at least 29 positive, readable thermal values per sample;
- readable `aoss-0-usr`, CPU-cluster, GPU, modem-subsystem, and NSP core
  sensors;
- exactly three samples with a stable readable-sensor count;
- rejection of any non-sentinel negative or value above 200 C; and
- the unchanged 60 C preflight and 80 C fallback-return ceilings.

Unreadable values are accepted only for the exact auxiliary sensor types
observed unavailable during this boot. Zero and `-274000` remain accepted as
inactive-channel values and do not contribute to the thermal maximum or
sensor quorum. An unavailable required or unknown sensor, malformed value,
sparse topology, changing readable count, or over-range value still fails
closed.

All 39 hardware-free ACM tests pass, including both topology boundaries,
non-contiguity, sparse and changing auxiliary sensors, every required-core
loss, malformed and over-range temperatures, policy-copy drift, signed-record
mutations, serial framing, and authenticated reboot behavior.

## Live result

The corrected controller completed one fresh nonce-bound exchange, verified
the phone's signature against the retained private host-key pin, and wrote the
no-replace preflight record outside Git with mode `0600`. The signed maximum
remained safely below the preflight ceiling.

## Safety state

- No experimental image was booted.
- No partition was flashed, erased, mounted, or exposed to the host.
- No fallback configuration or `authorized_keys` file changed.
- Only the separately authorized BusyBox-history and possible ext4-atime
  effects apply to the ACM exchanges.
- The one authorized temporary Linux boot remains unused.

## Next action

After review, full CI, and publication of the corrected controller, use its
authenticated ACK-before-`RESTART2` action to return this same fallback boot
to fastboot. Then run the complete lifecycle preflight before allowing one
temporary `fastboot boot` cycle.
