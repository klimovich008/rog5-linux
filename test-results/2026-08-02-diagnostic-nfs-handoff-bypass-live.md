# Diagnostic NFS-handoff bypass: live result

Date: 2026-08-02

Result: **recovery fetched and verified the exact signed diagnostic bundle,
accepted `PREPARE`, and claimed one `COMMIT_EXEC`, but the host control policy
omitted the diagnostic bundle from its network-root set. The commit therefore
preceded NFS startup, no target diagnostic frame arrived, and the watchdog
returned the exact same-port Alpine fallback. The intent is resolved
`FALLBACK_RETURNED`; the recovery wrapper is consumed and denied.**

No phone partition was flashed, wiped, or written. The only phone boot was one
100,663,296-byte RAM-only `fastboot boot` of AVB SHA-256
`332889a83f541ed0e17c94656836c512a35b5bfd6bbbaf735d2f5f6b94b51830`.

## Accepted boundaries

- Draft-PR QEMU and recovery-core checks passed at exact head `d60498c`.
- The branch was clean and synchronized; deployment-key, artifact, installed
  controller, fallback-host, and connected fastboot preflights passed.
- Signed Alpine health passed before the bounded reboot to exact same-port
  `lahaina` fastboot.
- Recovery reached fixed ACM/NCM and the receive-only diagnostic collector was
  ready before the transaction.
- Recovery returned `PREPARED` for manifest `4eacb90f…f7e76`, proving the
  signed bundle was fetched, verified, and loaded.
- Recovery returned one correlated `CLAIMED` response for `COMMIT_EXEC`; the
  durable host intent became `TRANSMITTED/UNKNOWN` and was never retried.

## Failure and cause

No `network-root-server.log` was created. The host
`stable-recovery-control.py` installed its pre-commit NFS rendezvous only for
`headless-network-root-v1` and `headless-ssh-network-root-v3-r2`, omitting
`headless-netroot-early-diag-v1`. Although the lifecycle supplied the exact
NFS guard, fresh token, v3 profile, and admitted package SHA-256, the control
client ignored them for the diagnostic name and sent `COMMIT_EXEC` immediately
after `PREPARE`.

This also explains the apparent cleanup race. The control process exited while
the deferred root bundle controller was still inside its bounded one-transfer
window, so the lifecycle's first fallback-profile restore was correctly
refused as a concurrent controller. The controller subsequently exited and
removed its address, listener, and firewall state. A second bounded restoration
then passed.

The host has no proof that target execution reached userspace after the atomic
claim response. The collector retained only its exact `READY` line and no
frame. The image remains consumed because `execution_started=NO` in the
`CLAIMED` response is the intentional pre-execute state; recovery persists the
execution marker only after transmitting that response, when transport loss
is inherently ambiguous.

## Fallback and resolution

The phone returned as the exact Alpine USB gadget on the anchored physical
port. Bounded profile restoration passed, then strict SSH verified vendor
kernel `5.4.134-qgki-perf-00001-g6c308144c23e`, a new boot ID, and maximum
sampled temperature 41.8 C. No project process, NFS listener, export, handoff
marker, recovery listener, or recovery firewall rule remained. SteamOS
read-only mode is enabled.

After same-port fallback and final host cleanup were independently proven, the
single durable intent was resolved exactly once as `FALLBACK_RETURNED`.

## Corrective test boundary

The host control now defines one fail-closed network-root policy set containing
the legacy, deployment, and diagnostic bundles. Both v3 bundles require the
exact `headless-ssh-deployment-v3` marker and admitted package SHA-256 before
commit. An unknown bundle that carries the NFS handoff guard is rejected before
device discovery. The new tests fail against the live code and pass after the
fix; all 20 recovery-control and 39 lifecycle tests pass.

The next phone action requires reviewed publication, green local/GitHub CI, a
distinct generation-2 AVB identity over the unchanged recovery payload, and
fresh connected preflight. Generation 1 must never be retried or flashed.

## Private evidence hashes

| Evidence | SHA-256 |
|---|---|
| `stable-recovery-boot.log` | `fd52c3be343b68e3fca28e022cfa244a776439b96df9d6dc3ea4f41dda0784e3` |
| `recovery-usb.anchor` | `998685dfa4ca155d474dc71cecf7dd961a53fa47b0c0d0b1afdf961730030729` |
| `recovery-usb-anchor.log` | `017ec9cd2b1ebb5e62d411e0035375d1fd67ec453b28f1a72e987b106c70bfb4` |
| `bundle-server.log` | `f45a6cb5e2207d8d36947d4d9544b44a4f0c1a1ee69a579c1fc10a9a9723aa1b` |
| `recovery-control.log` | `0a090ac0be8438f0a9d5b046d68f759a87eabc98d45560eadd5ef6f186304212` |
| `early-target-diagnostics.log` | `860714e24102606aee7dc40637e7bbd620d1d7f3743f018657cb9db56178f088` |
| initial `fallback-profile-restore.log` | `9d53b96b509887ef2dfd7e2b285f95a85562457296018867de48ae3e0abfd485` |
| manual strict-SSH fallback identity | `2023b445274a498188990dce27f0c2997f1767513cbfcd2f6ec2830707b3780c` |
| resolved durable intent | `bb154111f776c4c13f011ff73517cee26d4c643961d3a604cddfa0fb64cfefcb` |
