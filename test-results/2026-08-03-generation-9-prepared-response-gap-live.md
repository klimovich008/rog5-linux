# Generation-9 PREPARE-response gap — live

Date: 2026-08-03

Result: **REJECTED safely; consumed; never retry or flash**. The sole admitted
Generation-9 RAM-only recovery boot reached exact recovery ACM/NCM and served
the complete signed diagnostic bundle, but recovery never returned a
`PREPARED` response before its watchdog returned the phone to Alpine. No
COMMIT intent existed, no target ran, exact fallback returned, and final host
cleanup passed.

## Admission and connected preflight

The admission checkpoint was published at commit
`eea098963edd3ab3f1155e8a4f6ff33bf5dcc84b`. Complete local CI passed, and
GitHub Actions run `30847253087` passed both `qemu-system` and
`recovery-core` at that exact head.

The first connected preflight found zero fastboot devices because the phone
was in the exact Alpine fallback. The pinned strict-host-key helper verified
the fallback kernel, BusyBox init, board compatible, ext4 root, empty pstore,
clean kernel log, and safe thermal telemetry. It then issued one acknowledged
`RESTART2("bootloader")` and proved that the same physical USB port returned
as the exact ASUS fastboot device with product `lahaina`. A fresh connected
preflight passed without booting the phone or starting a transfer service.

## Sole RAM-only lifecycle

The lifecycle used the 100,663,296-byte AVB image
`b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008`.
Its private evidence remains outside Git and records:

- the exact fastboot image was verified and accepted once;
- recovery ACM/NCM appeared on the anchored physical USB port with rollback
  armed;
- a valid framed `PREPARE` request reached recovery, because that request
  caused the fixed bundle fetch;
- the one-transfer server sent all 46,163,787 bytes: manifest, signature,
  Image, board DTB, and diagnostic initramfs;
- the NFSv4.2 server reached its pre-COMMIT ready state;
- recovery emitted no `PREPARED` response before its USB gadget departed;
- the receive-only target collector ended with zero frames and zero dropped
  USB events; and
- no durable COMMIT intent, kexec claim, target execution, target SSH, or
  phone-storage access occurred.

The kernel USB timeline shows exact `ROG5 recovery` enumeration followed by a
disconnect about 178 seconds later, then exact Alpine fallback. This is
consistent with the recovery watchdog expiring while PREPARE was still
synchronous.

## Classifier interpretation

The final control line was:

```text
FAIL recovery ACM identity did not remain stable; states=product-mismatch:216; transitions=product-mismatch; identity_changes=none; transitions_truncated=no
```

The controller did not label which discovery phase produced that line. The
best-supported interpretation is the **same-session replay connection after
the original transport was lost**, not the initial recovery connection. That
is an inference from two independent facts: the initial exact ACM connection
necessarily succeeded and delivered PREPARE, as proved by the complete
request-triggered bundle transfer; and the USB timeline shows watchdog fallback
before the terminal discovery finished. Alpine's known USB product correctly
classifies as a recovery-product mismatch. The 216 identical samples, single
transition, no identity changes, and no truncation therefore support a stable
non-recovery product during replay; they are not direct phase evidence and do
not prove initial recovery ACM flapping.

The controller currently lets replay-discovery failure replace the original
transport-loss diagnostic. That observability defect may also explain why the
Generation-8 result appeared to be an ACM-stability failure even though its
bundle transferred completely; the Generation-8 terminal record likewise
lacked an explicit phase label.

## Rollback and cleanup

The lifecycle made no retry. It stopped the bounded NFS window, restored the
exact Alpine NetworkManager profile, proved the signed fallback identity over
strict SSH on the anchored port, and passed final cleanup. Independent checks
also found no project service, NFS or bundle listener, export marker, server
state, or export mount. The isolated fallback address is again
`169.254.77.1/30`.

The private durable consumption record is
`BOOT_CLAIMED` for `headless-diagnostic-generation9-live-v1`. Generation 9 is
removed from `manifests/temporary-boot-images.tsv`, recorded as consumed in
`manifests/artifacts.tsv`, and must never be retried or flashed.

The consumed compatibility chain pins artifact-manifest SHA-256
`df4817aae883e56aa2cfa334369d8cec29f340283baa45fba1598a8e328b00d2`,
minimal-headless profile SHA-256
`8dee6d8c71009bdb1c27760c16c23f1d88d8d31c619f2be6f6b7ae3646734288`,
and core source/DTB profile SHA-256
`3fa93ff9590fdf5b4c6e4bef6fe26d31cc3fa946b5ce36328e227f623fb4fe03`.

## Next test-first correction

Do not issue Generation 10 from the unchanged recovery payload. First add
hardware-free regression coverage that forces:

1. initial exact ACM connection and PREPARE delivery;
2. transport loss while PREPARE is outstanding;
3. replay discovery observing a known fallback product; and
4. preservation of the original transport-loss phase plus bounded replay
   classification in the terminal error.

Then add bounded recovery-side phase evidence around fetch completion,
signature verification, kexec load, PREPARED publication, and watchdog exit.
The next live candidate is justified only when that evidence can distinguish
where the roughly 160-second post-transfer gap occurs. Extending a timeout or
reissuing the same raw recovery would not resolve the failing boundary.
