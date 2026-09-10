# Minimal-headless r2 live target USB-loss result

Date: 2026-08-01

Result: **RECOVERY PASS; TRANSFER PASS; TARGET REJECTED; FALLBACK PASS**

The first temporary boot of `headless-ssh-network-root-v3-r2` proved the
framed recovery and rollback path on the phone. The Linux 7.1 target exposed
its exact USB-NCM identity, but the gadget physically disconnected 23 seconds
later, before the host could pin its SSH key. The watchdog returned the same
physical USB port to the unchanged Alpine fallback, and strict SSH accepted a
fresh signed fallback identity record. No partition was flashed. Phone-side
effects were limited to the separately admitted read-induced ext4 atime
updates possible during strict fallback SSH.

## Admitted inputs

- phone serial: `M5AIKN00F0353YH`
- fastboot product: `lahaina`
- bundle: `headless-ssh-network-root-v3-r2`
- manifest SHA-256:
  `9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630`
- recovery AVB SHA-256:
  `11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c`
- root package SHA-256:
  `9eb60d6e4254986dc8e017fc1dd9d76d699e8d35cb3716d8fdef72ca6df1199d`
- installed root entries: `37,735`
- installed root tree SHA-256:
  `f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087`

The private mode-`0700` evidence directory is retained outside Git at
`/home/deck/.local/state/rog5-deployment-20260801-r2-live1`.

## Recovery and commit

`fastboot boot` accepted the sealed image. Recovery appeared on the expected
physical USB port, served the signed bundle exactly once, and accepted one
framed prepare/commit sequence:

- session: `05e725970bd9f5e619fe4afa3401f760`
- PREPARE request: `bc3365e4dfacffb9719698fc2b7e5acc`
- COMMIT_EXEC request: `9c74445006c87f67268c03935d285734`
- PREPARE result: `PREPARED`
- COMMIT_EXEC result: `CLAIMED`
- watchdog: `ARMED`

The host wrote one durable `TRANSMITTED/UNKNOWN` intent before execution. It
did not retry COMMIT or execute the payload twice.

## Target rejection

The host journal records Linux 7.1 enumerating at `03:27:28` on the exact
recovery USB port as VID:PID `1d6b:0104`, product `ROG5 network root`, using
`cdc_ncm` on `enp4s0f3u1u2`. At `03:27:51`, 23 seconds later, the device
physically disconnected and the NCM driver unregistered. The target host-key
gate therefore failed closed with:

```text
FAIL minimal-headless USB identity did not remain stable
```

No target host-key pin and no 88-field runtime record were accepted. This is
not evidence that SSH, systemd, sensors, storage, or later userspace failed;
the observable boundary is the early target USB disconnect.

## Rollback and intent resolution

At `03:38:50` the unchanged Alpine gadget returned on the same port. At
`03:38:52`, strict SSH accepted exactly one signed fallback proof:

- kernel: `5.4.134-qgki-perf-00001-g6c308144c23e`
- boot ID: `a2c11656-1404-4f20-b1d7-5d0988777413`
- maximum reported thermal value: `48.4 C`
- record result: `PASS`

The lifecycle's first final cleanup sample raced NetworkManager/udev: the
fallback `/30` address was already visible while the interface's exact udev
identity had not yet appeared. The controller correctly left the intent
`UNKNOWN`. Seconds later, the exact persistent profile was fully observable:

- profile: `rog5-fallback-usb-ssh`
- interface: `enp4s0f3u1u2`
- address: `169.254.77.1/30`
- no gateway or DNS; IPv4 and IPv6 never-default; IPv6 disabled
- driver: `cdc_ncm`; VID:PID `1d6b:0104`

The already-signed fallback proof and exact clean host state resolved the
single intent once as `FALLBACK_RETURNED`; the phone was not contacted again.

## Controller correction

The final cleanup gate now tolerates only the observed USB identity/address
view race. It requires one second of continuously clean state within one
10-second absolute deadline. All subprocesses share that deadline. Firewall,
NFS, listener, ownership, and other cleanup failures remain immediate and
fail closed. A failed final proof cannot open a second cleanup window, and
the fallback and COMMIT one-contact limits remain unchanged.

The lifecycle suite now has 26 hardware-free methods covering transient and
persistent udev gaps, address-view races, clean/dirty flapping, target and
fallback outcomes, immediate non-identity failure, shared subprocess
deadlines, and one-contact/one-COMMIT invariants.

## Final host state and next gate

The temporary PolicyKit source and installed rule were removed. NFS runtime
markers, exports, listeners, firewall state, and lifecycle processes are
absent; `ip_nonlocal_bind=0`; the drop zone is empty. The phone is in the
known Alpine fallback over USB-NCM.

The r2 payload is consumed and must not be executed again. The next live
candidate must have a distinct signed identity and add bounded early-target
diagnostics for the 23-second USB-loss boundary before another temporary
boot is considered.
