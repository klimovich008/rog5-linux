# Generation-3 transfer-timeout live result

Date: 2026-08-03
Repository checkpoint: `8d0da7345cf7ed01f4744d026eda21f92cb59124`

Result: **REJECTED before COMMIT; generation 3 is consumed.**

## Scope and safety outcome

The standing project authorization admitted one guarded RAM-only lifecycle
with the dedicated phone SSH credential. Local key admission, connected
lifecycle preflight, complete local CI, and GitHub Actions run `30784042557`
passed at the exact synchronized checkpoint before the boot.

The lifecycle used only temporary `fastboot boot`. It did not flash, erase,
format, change slots, mount phone storage, or write phone storage. Private
logs, the device serial, USB location, boot identifiers, nonces, host pins,
and credential material remain outside Git.

## Observed sequence

1. Fastboot accepted generation-3 AVB
   `eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6`.
2. The fixed shell-free recovery exposed ACM/NCM, retained its independent
   rollback watchdog, and the receive-only diagnostic collector became ready.
3. The host bundle service became ready for exact manifest
   `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`.
4. Recovery reached correlated `PREPARED`. In the pinned responder this is
   possible only after the fresh fetcher exits successfully, the signed bundle
   and artifacts verify, and `kexec -l` accepts the exact Image, DTB, initramfs,
   and command line.
5. The host bundle service never emitted its independent
   `PASS one recovery bundle transfer completed` receipt. Consequently the
   lifecycle did not finish recovery-network cleanup and did not start the
   exact NFSv4.2 handoff service.
6. The control process failed closed with
   `exact network-root NFSv4.2 listener was not ready before COMMIT`.
   No `COMMIT_EXEC`, durable commit intent, target boot, or diagnostic target
   frame occurred.
7. The recovery watchdog returned the phone automatically. The exact same-port
   Alpine profile was restored, the pinned host and admitted client keys passed
   strict SSH verification, and the fallback kernel was accepted.
8. Final host inspection found only the exact managed fallback `/30`; no ROG5
   process, NFS export, NFS worker, project listener, or drop-zone ownership
   remained. The unrelated loopback-only port-8080 listener was unchanged.

## Bounded diagnosis

The current timeout lattice is inconsistent:

| Boundary | Current limit |
|---|---:|
| recovery fetcher | 190 seconds |
| host bundle transfer | 70 seconds |
| privileged host-controller watchdog | 75 seconds |
| lifecycle bundle wait | 95 seconds |
| recovery PREPARE exchange | 260 seconds |
| complete control process | 320 seconds |

The verified `PREPARED` response proves the recovery-side fetch, verification,
and kexec load completed. The absent host completion receipt and failed root
service prove the host side did not observe an orderly transfer-server exit
before its much shorter bounds expired. The strongest diagnosis is therefore
that generation 3 completed the device side near or beyond the host's
70/75-second cutoff. The retained evidence cannot identify the exact final-byte
timestamp, so this timing explanation remains a bounded inference rather than
a stronger claim.

NFS intentionally starts only after the bundle service exits and removes its
temporary recovery-network ownership. Because that cleanup receipt never
arrived, the parallel control process exhausted its 45-second pre-COMMIT NFS
gate. This ordering prevented execution without a verified NFS root and is
correct; the undersized host transfer bounds and missing cross-process receipt
are the defects.

## Required correction

Before creating generation 4:

- add hardware-free tests that encode the timeout lattice and prove a slow but
  valid transfer cannot be killed before the recovery fetch limit;
- cover `PREPARED` while the host transfer service is still completing, proving
  COMMIT remains impossible until the exact host receipt and NFS readiness;
- retain hostile missing/forged receipt, server failure, cleanup failure,
  no-NFS, and no-retry cases;
- extend the host transfer, privileged watchdog, and lifecycle wait bounds with
  explicit margins below the existing PREPARE/control/watchdog limits;
- preserve the current NFS-before-COMMIT rule and rollback behavior; and
- issue a distinct one-shot generation-4 admission only after review, local CI,
  GitHub CI, twin artifact verification, and connected preflight.

Generation 3 must never be booted again. Removal of its only `allow` row is the
versioned consumption record; no replacement image is currently admitted.

## Implemented source follow-up

The repository follow-up adds a hardware-free timeout-lattice regression and
changes the source limits to:

| Boundary | Corrected source limit |
|---|---:|
| device fetch worker | 180 seconds |
| recovery fetch supervisor | 190 seconds |
| host bundle transfer | 195 seconds |
| privileged host-controller watchdog | 205 seconds |
| lifecycle host-receipt wait | 220 seconds |
| recovery PREPARE exchange | 260 seconds |
| complete control process | 320 seconds |

Each outer host layer now has time to observe and clean up the inner layer. A
second hardware-free case drives recovery to a simulated PREPARED checkpoint,
prints every expected host receipt marker, then exits the host service nonzero;
NFS and COMMIT remain blocked. This validates process status as well as marker
text. The correction does not admit an image or authorize another boot. At
that checkpoint its reviewed host components still had to be installed before
generation 4 could be built.

Commit `4c2da4b` subsequently passed complete local CI and GitHub Actions run
`30785558945`. The reviewed host update was then installed without a phone
action. Installed controller SHA-256
`5f6ec19cbe87d57cfda4d95d872d07db1888cb631f8a01faa6f9aa756020b7d4`
and server SHA-256
`9258c0e72ca7adb626fdafccfc1bababb68263b40ad23b635b0cc8c19b7ffac0`
match their repository sources exactly. The fixed host-control socket is
active and enabled with its required caller-owned mode `0600`; no bundle,
recovery, or NFS lifecycle process was started.
