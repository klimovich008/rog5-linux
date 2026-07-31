# Accepted core baseline revalidation

Date: 2026-07-31

## Result

Hardware-free result: PASS.

The retained Linux 7.1.4 source, accepted isolated DTB, matching configuration
and modules, buttons/indicator source contract, and corrected-successor
artifact gate all pass from the current Linux host. No phone interface,
credential, privileged service, signing key, or live authority was used.

## Exact retained inputs

- source commit:
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`
- accepted DTB:
  `artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb`
- DTB size: `102870`
- DTB SHA-256:
  `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`
- configuration SHA-256:
  `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f`
- module archive size: `300439504`
- module archive SHA-256:
  `5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9`

The v3 artifact manifest declares the module archive as a byte-identical reuse
of the v1 archive. The retained host therefore uses the one existing ignored
v1 copy rather than creating a duplicate 300 MB file.

## Commands and evidence

The 74-case source/DTB suite ran with
`ROG5_ACCEPTED_KERNEL_SOURCE` set to the clean retained source. Its optional
real-input case reported `status=baseline-verified`; every hostile mutation
also passed.

The buttons/indicator verifier then accepted the same source, the tracked v3
configuration, and the retained v1 module archive. It reported:

```text
buttons=power,volume-down,volume-up
indicator=pm8350c-lpg-channel-2-green-default-off
PASS accepted kernel source, config, and module capability contract
```

Finally, `test-corrected-successor-live-gate-offline.sh` reported:

```text
PASS retained corrected successor satisfies the exact phone-free live-gate boundary
```

## Interpretation

This proves the accepted baseline inputs remain internally consistent and
reproducible enough to serve as the behavioral oracle. It does not prove the
corrected target on hardware. The next hardware gate remains the separately
authorized signed fallback ACM preflight followed by one guarded temporary
lifecycle boot.
