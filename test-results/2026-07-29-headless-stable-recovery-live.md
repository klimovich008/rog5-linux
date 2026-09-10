# Headless stable-recovery live result — fallback returned

Date: 2026-07-29

Status: **one signed target execution completed; target rejected before SSH;
exact persistent fallback returned; corrected DTB candidate is offline**

This was one attended, RAM-only validation of the shell-free stable recovery
path. Nothing was flashed, wiped, repartitioned, or written to phone storage.
The installed fallback and active slot were not changed. No production
credential was created or used.

## Exact recovery input

Two clean wrapper builds were byte-identical:

```text
stable recovery initramfs:
6245147d464985df3d861d2b177ea39f6132767b45c07e39a131fecf3bf69aa2

ASUS 5.4 wrapper Image:
91732d1bdbf73c5f574d87eb0d07b5394db2889e4c0dc4b258577a0bcdb0101f

raw boot-v3 wrapper:
854c48adb4316bc8496579ebab78cfbbd3e0550fe0c5204ae3c5661187818fb4

100663296-byte AVB temporary-boot image:
60a1230bd9c7c4a925042b1bd1c8d70dbb142160e3af9360ddb070ff4109de77
```

The initramfs carried only the raw Ed25519 public key, responder, fixed
fetcher, verifier, and pinned loader runtime. Its new init created the
fetcher's exact root-owned mode-`0700` volatile bundle directory before
starting the responder. The public-key hash was:

```text
5274b8db7490b3a84c10be2998ec819f25b9bf649313c011db93700a78d5520c
```

The preflight verified the twin images, initramfs composition, AVB footer and
descriptor, exact kernel/config hashes, product `lahaina`, and fastboot serial
before calling `fastboot boot`. Recovery enumerated uniquely as
`/dev/ttyACM0`. No flash command or partition target existed in the live
runner.

## Host fixes proven live

The first recovery transaction fetched and verified the signed bundle, but
the host client refused COMMIT because Fedora exposes
`/proc/fs/nfsd/{threads,versions}` only to root. The NFS server itself had
already proved those fields and was listening exactly on
`169.254.77.1:2049`; the unprivileged duplicate read was not a valid
rendezvous.

COMMIT was not sent, no intent was armed, and the recovery watchdog returned
the phone to fallback.

The corrected handoff uses a fresh 256-bit nonce shared by the unprivileged
control client and the fixed root NFS server. Only after checking its exact
NFSv4.2 configuration does the root server publish a root-owned mode-`0444`
marker in `/run`. The client requires the exact nonce, format, listener,
export root, metadata, and a single exact root-only TCP listener. The marker
is removed with the NFS export, mount, firewall state, and listener.

A real host-only run proved marker metadata `0:0:444`, successful
unprivileged validation, and residue-free cleanup. Ten control tests and the
network-root host contract cover missing/invalid nonce, failed rendezvous,
no-COMMIT behavior, marker/listener agreement, and cleanup.

The fixed recovery bundle host controller also proved:

- current and legacy NetworkManager managed-state fields;
- scoped handoff from the intentional fallback `/16` profile to recovery
  `/30`, followed by exact profile restoration;
- temporary disable/restore of forwarding on Fedora's otherwise-empty
  `drop` zone;
- one fixed peer, address, port, bundle, and manifest;
- rollback after every partial setup failure.

Its installed root-owned source hash matched the reviewed source:

```text
d437f234db99d65b534bcc2695a426f4028f14a42e79fe700b32fdb36af2be95
```

## Signed transaction and outcome

The second recovery session transferred and verified exactly:

```text
bundle: headless-network-root-v1
manifest:
23fc045c72c528ae60db6e4152cad685999edded8fcf983d252cc4ac29a1047e
```

The nonce-bound NFSv4.2 readiness gate passed before COMMIT. The recovery
returned one correlated `CLAIMED` response:

```text
session: ad58ffbeb95aac042bf90b8f34af335b
prepare request: 70cf6a00afd414a70fbf86917d67d0fa
commit request: cd1d4755665500f1322823b9ee1f5fb1
commit fingerprint:
d1a304d22192627128b6fe93a64a4b0daafbac5bdaca92a8c5b737a8b272150d
```

The target's exact `ROG5_network_root` NCM gadget appeared, proving that the
signed kexec target started and configured USB. It departed about 15 seconds
later, before target SSH or acceptance. The NFS server then removed its
export, listener, marker, mount, interface, and firewall state.

The phone returned automatically to the exact persistent fallback:

```text
boot ID: f3c6a4c3-7d65-483b-865f-2df510e45d92
kernel: 5.4.134-qgki-perf-00001-g6c308144c23e
PID 1: /bin/busybox
root: ext4
```

The strict fallback preflight passed with empty pstore, no project diagnostic
module, no fatal kernel signature, and safe thermal telemetry. The durable
intent was then resolved immutably as `FALLBACK_RETURNED`. A complete private
fallback dmesg was captured mode-`0600` outside the publishable evidence:

```text
artifact: test-results/private/2026-07-29-headless-live-return-f3c6a4c3.log
bytes: 198913
sha256: f8cb36b6b6d9d98ed18ab202cc7ba93829fadbaa35f89740ae3e75bef6647fb8
```

## Root cause and correction

The target timing matched the repository's historical network-root v1
16-second reset. Decompiling and comparing the exact signed DTB proved the
candidate had selected the old v1 object:

```text
rejected v1 DTB:
size 102774
sha256 255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6
```

Unlike the accepted v2/v3 recovery DTB, v1 leaves the RMTFS reservation,
GPUCC, GMU, and Adreno SMMU enabled. Historical live evidence already
localized the repeated reset to the GPUCC coldplug stall and the RMTFS/ramoops
overlap.

The tracked authority-free headless candidate now pins the byte-identical
accepted v3 DTB:

```text
path:
artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb
size: 102870
sha256: 86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
```

Its decompiled delta adds exactly the missing `status = "disabled"` entries
for `rmtfs_mem`, GPUCC, GMU, and the Adreno SMMU; the GPU node was already
disabled. A regression test pins the complete accepted DTB identity in the
headless candidate. The candidate adapter and full ephemeral-key
signed-bundle composition pass with this correction.

The corrected candidate is **not** signed by the consumed live trust root,
has not been booted, and grants no repeat authority. A future live attempt
requires a fresh disposable trust root/wrapper build, complete offline
revalidation, and separate attended authorization.

## Result

The stable shell-free recovery, framed transaction, fixed-host fetch,
signature and descriptor verification, NFS-before-COMMIT rendezvous,
at-most-once commit, target NCM startup, watchdog fallback, intent ledger, and
host cleanup all passed live.

The headless target itself is rejected because it carried the historical v1
DTB and did not reach SSH. The exact selection error is corrected and guarded
offline; GPU acceleration remains excluded from the headless core path.
