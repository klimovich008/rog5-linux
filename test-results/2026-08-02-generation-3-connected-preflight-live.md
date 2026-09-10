# Generation-3 connected fastboot preflight

Date: 2026-08-02  
Repository checkpoint: `56ff2adb5f8dbcfbce9b47dce32173abc62eca96`

Result: **PASS — connected preflight only; no boot command was sent.**

## Scope

The host observed exactly one ASUS fastboot product (`0b05:4daf`) in the
`fastboot` state. `getvar product` returned exactly `lahaina`. The device
serial is deliberately omitted from tracked evidence.

The preflight selected
`headless-diagnostic-generation3-live-v1` and verified the retained recovery,
installed signed bundle, public trust root, host verifier, Android boot image,
and current fastboot device. It did not read a private key or phone
credential, start the bundle listener, issue `fastboot boot`, reboot the
phone, flash, wipe, mount, or write phone storage.

## Exact admitted chain

| Input | SHA-256 |
|---|---|
| generation-3 AVB recovery | `eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6` |
| recovery public trust root | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |
| signed runtime manifest | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| host bundle verifier | `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621` |

The image verifier reported a valid footer and `NONE` vbmeta structure, then
verified the boot partition's SHA-256 descriptor over exactly 58,101,760
bytes. The gate completed with:

```text
PASS stable recovery archive: fixed responder/session before USB bind, pinned loader, public trust root only, no interactive shell or SSH
PASS exact boot-only live gate profile=headless-diagnostic-generation3-live-v1 image_sha256=eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6
```

## Boundary and next step

This proves host-side admission and connected fastboot identity only. It does
not prove that recovery, the diagnostic target, USB/NCM, NFS, SSH, rollback,
or the corrected DTB works in this phone cycle. The sole admitted temporary
boot remains unexecuted. Its lifecycle and credential prerequisites require a
separate fresh action-scoped authorization under the current active thread
objective before any private key is inspected or `fastboot boot` is issued.
