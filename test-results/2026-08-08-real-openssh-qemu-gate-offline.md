# Real OpenSSH ARM64 QEMU gate

Date: 2026-08-08

Status: local hardware-free acceptance passed; exact-head GitHub run pending

## Outcome

The existing board-neutral QEMU handoff now proves a real key-only OpenSSH
path instead of substituting an ordering stub. Under the pinned Linux 7.1.4
kernel and sealed AArch64 Arch runtime, real `systemd 260.2-2-arch` starts
OpenSSH 10.3, accepts one disposable Ed25519 key over IPv4 loopback, executes
the authenticated command through the configured root login shell, and rejects
a keyless login. Only then can the generated stage-140 unit and final systemd
acceptance unit complete.

This remains hardware-free evidence. It does not prove the ROG Phone DTB,
Qualcomm hardware, USB/NCM, NFS, a user credential, rollback, or any phone boot.

## Concrete defects fixed

1. `sshd.service` was a oneshot ordering stub. The gate could reach stage 140
   without loading an OpenSSH binary, listening on a socket, authenticating a
   key, or executing a remote command. The service now executes the real daemon
   through the existing static harness, and a dependent proof service requires
   both accepted key authentication and rejected keyless authentication.
2. The sealed CI runtime carried systemd only. It now carries the credential-
   free OpenSSH client, daemon, `sshd-auth`, and `sshd-session` executables,
   their recursive AArch64 `DT_NEEDED` closure, exact package provenance, and
   retained license texts. Keys remain per-run temporary inputs and are never
   stored in the sealed artifact.
3. The QEMU tiny kernel did not provide the minimum networking and process-
   isolation primitives required by OpenSSH. The resolved config now requires
   IPv4, networking devices, multiuser ownership syscalls, POSIX timers,
   seccomp, and seccomp filters in addition to the existing systemd options.
4. The QEMU kernel builder used `bc` during Kbuild without validating or
   binding it into the exact build state. `bc` is now an explicit required and
   hash-bound build tool.

## Regression and hostile behavior

The contract test was changed first. On the starting tree it failed at the
intended boundary:

```text
FAIL QEMU diagnostic handoff contract is missing: ExecStart=/usr/bin/sshd ...
PRE_FIX elapsed=0.294 user=0.054 sys=0.205
```

The updated contract rejects either `sshd-stub` or `SSH ordering stub`, pins
the real daemon exec path and proof service, and requires the key-only success
marker. The runtime verifier rejects missing OpenSSH split executables, any
ELF-count or manifest drift, mutation, mutable account state, SSH public or
private identity material, and unsafe file types. The in-guest proof fails if
the disposable key login is rejected or if the same daemon accepts a login
with public-key, password, and keyboard-interactive authentication disabled.

Focused final results:

```text
PASS board-neutral full-system QEMU smoke contract
FOCUSED_CONTRACT elapsed=0.208 user=0.071 sys=0.148

PASS reproducible sealed ARM64 systemd QEMU runtime contract
FOCUSED_RUNTIME elapsed=0.821 user=0.494 sys=0.436

PASS canonical reporter stream crossed real systemd units frames=17
PASS generated diagnostic units executed under ARM64 systemd
FINAL_QEMU_OPENSSH elapsed=8.690 user=5.803 sys=1.051
```

## Reproducibility and timing

- Starting repository SHA:
  `b1ab2f9fd512a2d88f343f584225f7c35e0503ce`.
- Ending repository SHA: recorded in the final handoff after the local commit.
- Source kernel: Linux tag `v7.1.4`, commit
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`.
- Final builder-owned `.config` SHA-256:
  `2e04051fe960c840a7324def4c48169373d2c40f00b7092d0f62bff1b9793885`.
- Final builder-owned QEMU `Image` SHA-256:
  `58abeeaf1fb592ae23f4855f26c84ee7ef24fd77a2433cf3eb0e8043fcaadf3c`.
- Clean kernel build: `264.024` seconds elapsed, `1610.265` user,
  `149.252` sys with `JOBS=8`.
- Exact-state incremental kernel build: `25.840` seconds elapsed, `15.416`
  user, `16.848` sys; `.config` and `Image` identities were unchanged.
- Previous sealed runtime: 9,628,993 bytes, SHA-256
  `5011267029d8da251c20e66f232cce2f36530e09d18a36e0a492018255f178f7`.
- Current sealed runtime: 12,006,001 bytes, SHA-256
  `990689a5ebc0a3cdc16f9c6198bab3a9cc4531ead17ffe4ee0ad14c81c1aebde`.
- Current runtime clean build: `7.497` seconds elapsed. An independent twin
  build took `7.700` seconds and was byte-identical to the tracked artifact.

The local missing host tools were downloaded as exact package-manager-resolved
archives and extracted only below the ignored `build/` directory. The host OS
was not modified. No phone, USB device, signing key, user SSH credential,
GitHub credential, NFS export, or boot authority was used.
