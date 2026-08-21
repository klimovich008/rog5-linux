# Local-root power/USB composition offline checkpoint

Date: 2026-08-21

Result: **OFFLINE PASS; UNBOOTED.** No phone contact, signing, candidate
issuance, storage access, or boot occurred.

This checkpoint composes the Generation-70 read-only UFS/local-Arch path with
the V26 live-proven side-port charging stack. The build pins Linux commit
`ae717d919f87b47ea9ed2173ea96660186b62a66`, source tree
`939729426dcfa3bd72c75d81c0a675c6f0a193da`, and release
`7.1.4-gae717d919f87`. It uses qualified builder image
`bdb4bbda79ab38a55c72d23b269f5c3f5cb14d153e373ce50932c17538e9ccaf`.

Exact outputs are:

- config: `b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6`;
- Image: `a4648dd425616adff2dfb07590be4f85d17d5305e1f72830eb85e668490046d6`;
- composed DTB: `4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8`;
- twin initramfs: `b1f5f64eccd5b79fc5214ad9eea88d9dfabb6a1c3e8e57ba60cd25d7cbe16eda`;
- initramfs size: 23,810,042 bytes;
- exact deferred UFS closure: 4 modules;
- exact side-port power/USB closure: 15 modules; and
- exact V26 ADSP firmware inventory: 29 files.

The initramfs loads the charging stack before the deferred UFS stage, requires
safe battery voltage and temperature, requires side USB online with valid
voltage/current-limit telemetry, requires UFP/device plus sink roles, and
revalidates NCM carrier, address, and direct route. It performs no charging
control write. Firmware is copied to `/run`, which survives `switch_root`.

The clean kernel build took approximately 1,193 seconds from generated config
to final metadata, used 3.0 GiB of output, and the complete private checkpoint
uses 5.1 GiB including its exact source clone. Final local CI passed in
365.997 seconds.

The authority-free successor package uses target
`persistent-root-power-usb-v1`, signed manifest
`def5a06936e84c20e8609ae47b3fd8955500bf9c97de724897e52c6b7596d184`,
current stable-recovery raw image
`09c497ef23718cf74c94f3dc11085575b46982232d9e690df48c52637e5d9616`,
and deterministic AVB generation 77 image
`12f6a8559fae1824b2a82234edaf159f051c38956c0b8a6d528432ac2ae51f2f`.
Native bundle verification and full local CI pass; no policy allow row or boot
claim is included in this checkpoint.

The live question remains whether the combined ADSP/PMIC
GLINK/UCSI and deferred-UFS path reaches the existing local Arch root and
key-only SSH while preserving NCM and charging.

Generation 77 consumed its sole RAM-only cycle. Recovery and the complete
signed bundle transfer passed. Target NCM enumerated at the exact USB path for
2.77 seconds, then the target performed its fail-closed rollback before any
UFS or SSH evidence and returned exact stock slot A. The resolved outcome is
`FALLBACK_RETURNED`. The packaged `pdr_interface.ko` retained `.BTF`, matching
the already proven V18 module rejection. Generation 78 removes only that one
section; its `.text` bytes are identical.
