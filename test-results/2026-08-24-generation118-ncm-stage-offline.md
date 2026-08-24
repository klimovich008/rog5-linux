# Generation 118 NCM-only Arch staging

Date: 2026-08-24

Result: **OFFLINE PASS; ADMITTED ONCE.** Generation 118 remains unbooted.

The cycle answers one question: does removing unnecessary ACM and requiring
five seconds of continuously unique `a600000.usb` allow the full staging target
to expose stable NCM and key-only SSH?

The Image and DTB are unchanged from the clean-twin Generation 111 writer.
Two target initramfs builds are byte-identical at
`65da1da9c63fe1239000af1f36d19b195f077b0f0495f25e82dfa2f7532edc0d`.
Two signed runtime bundles match at manifest
`ec657d94aea6a71aa7efab80bcddba7794256209609ddc7031bd37764c17a4b5`.
The stable recovery raw payload remains byte-identical; only AVB generation 118
is new, at
`6e1fc8bf8e2c5f65d0e391c6b5275c8dceaf9f1c236d9feee23367a27e4ae1dc`.

If NCM and SSH appear, the existing continuous runner transfers the exact
649,960,943-byte compressed Arch image, installs only
`/rog5/images/arch-local-a.ext4`, verifies its 16-GiB identity, relocks every
UFS node read-only, and requests exact fastboot. No kernel or recovery image is
flashed.
