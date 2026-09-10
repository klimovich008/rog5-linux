# Independent observability review — offline

Date: 2026-08-09
Starting repository SHA: `0ea8427a09e8270c1441895286004be20747e434`
Scope: pstore/ramoops, Qualcomm GENI debug UART, EUD, and USB Type-C
Debug Accessory Mode. No phone, signing key, credential, candidate, or device
storage was used.

## Outcome

No lineage-safe channel independent of the USB-NCM path is ready for a phone
cycle. The accepted target has a valid SoC-side GENI debug-UART route, but
offline evidence does not prove that ASUS routed GPIO18/19 to either USB-C
connector, test pads, or another accessible connector. Ramoops is configured
coherently, but DRAM retention across target reset and bootloader/recovery
entry cannot be proven offline. EUD and standardized USB Type-C Debug
Accessory Mode are distinct mechanisms and neither proves UART accessibility
on this board.

The recommendation remains **HOLD**. This review does not request candidate
admission or boot authority.

A follow-up two-axis review found that the new host-port fault names were not
accepted by the native reporter and that the first UART verifier revision did
not bind its ancestor bus translation. Both defects now have fail-first
regressions and exact clean-twin AArch64 evidence. This improves the offline
component set; it does not turn either ramoops or UART into a proven physical
postmortem channel.

## Ramoops and lineage

The existing native bundle verifier already pins the complete target tuple:

```text
ramoops.mem_address=0x9b800000
ramoops.mem_size=0x400000
ramoops.record_size=0x100000
ramoops.console_size=0x300000
ramoops.pmsg_size=0
ramoops.ftrace_size=0
ramoops.dump_oops=1
```

It also validates a non-overlapping `0x9b800000 + 0x400000` reserved-memory
range in the target DTB. The accepted Linux 7.1.4 config has built-in
`PSTORE`, `PSTORE_CONSOLE`, and `PSTORE_RAM`. Stable recovery has the same
built-in pstore facilities and snapshots at most 64 records and 4 MiB from a
read-only pstore mount without unlinking records.

The target writes `rog5-target-lineage-v1` with the candidate and boot ID
before USB setup. The unresolved boundary is temporal: the installed Alpine
fallback cannot read the region, and recovery's current snapshot happens on
recovery entry. Offline parsing cannot prove that the region survives the
target → reset → bootloader/recovery sequence or that a later record belongs
to the just-consumed candidate. Absence of a pstore record therefore remains
`UNAVAILABLE`/`NO_LINEAGE` evidence, never proof that no crash occurred.

No additional pstore parser was added because it would duplicate the existing
bounded verifier without resolving physical retention or lineage.

## GENI debug UART

The accepted target DTB, SHA-256
`86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`,
contains all of the following:

- `/chosen/stdout-path = "serial0:115200n8"`;
- `/aliases/serial0 = /soc@0/geniqup@9c0000/serial@98c000`;
- an enabled `qcom,geni-debug-uart` at `0x98c000 + 0x4000` under an enabled
  QUP wrapper;
- a pinctrl reference to `qup-uart3-default-state`;
- RX on GPIO18 and TX on GPIO19, both using function `qup3`.

The accepted target config, SHA-256
`68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f`,
has built-in `CONFIG_SERIAL_QCOM_GENI=y`,
`CONFIG_SERIAL_QCOM_GENI_CONSOLE=y`, and `CONFIG_SERIAL_EARLYCON=y`. The GENI
driver registers this console as `ttyMSM`, so the current
`console=ttyMSM0,115200n8` command line is internally consistent.

The retained ASUS 5.4 source independently agrees at the SoC description
level:

- `lahaina.dtsi` aliases `serial0` to QUPv3 SE3;
- `lahaina-qupv3.dtsi` calls `0x98c000` the power-on-reset debug UART and
  enables it;
- `lahaina-pinctrl.dtsi` maps it to GPIO18/19 and `qup3`.

Those three source files have SHA-256 identities `eebd12d6…5169`,
`2f63d096…f063`, and `61d88fe4…8d75`, respectively. None of the ZS673KS
overlays overrides this route. This proves the intended Lahaina pin-level
route, not the PCB or connector route.

Stable recovery is weaker: its accepted config has
`CONFIG_SERIAL_MSM_GENI=y`, but both `CONFIG_SERIAL_MSM_GENI_CONSOLE` and
`CONFIG_SERIAL_MSM_GENI_EARLY_CONSOLE` are disabled. Its
`console=ttyMSM0,115200n8` token therefore does not establish a recovery UART
console. No recovery config or wrapper was changed in this review.

The target command line also does not contain `earlycon`. Kernel documentation
supports `earlycon=qcom_geni,<address>` only when the serial port has already
been configured. Adding it before proving the electrical path would increase
surface and change failure timing without yielding assured evidence, so it was
not added. See the [kernel command-line documentation](https://docs.kernel.org/admin-guide/kernel-parameters.html).

## EUD and USB Type-C Debug Accessory Mode

The ASUS 5.4 Lahaina description contains an enabled Qualcomm EUD block at
`0x88e0000`, but the USB controller's EUD `extcon` link is commented out.
Upstream Linux describes EUD as an on-chip mini USB hub; the binding in the
accepted 7.1.4 source permits only `qcom,sc7280-eud`, and the accepted SM8350
DTB has no EUD node. EUD is therefore not an available independent channel for
this target.

USB Type-C Debug Accessory Mode is a connector-detection mode identified by
Rd/Rd or Rp/Rp on CC1/CC2. The USB-IF specification does not require that a
commercial target expose a Qualcomm GENI UART through that mode; Appendix B
defines target-specific debug pin use. See the official
[USB Type-C Release 2.0 specification](https://www.usb.org/sites/default/files/USB%20Type-C%20Spec%20R2.0%20-%20August%202019.pdf).

No authoritative ASUS or Qualcomm source found in this review ties the ROG
Phone 5's GPIO18/19 UART to USB-C SBU pins, D+/D-, either connector, or a
`619 kΩ` detection network. That resistor/cable claim remains unverified and
must not be used as a purchase, wiring, or admission assumption.

## Input-surface consequence

The target config also has:

```text
CONFIG_MAGIC_SYSRQ=y
CONFIG_MAGIC_SYSRQ_DEFAULT_ENABLE=0x1
CONFIG_MAGIC_SYSRQ_SERIAL=y
CONFIG_MAGIC_SYSRQ_SERIAL_SEQUENCE=""
```

No `ttyMSM` getty or UART shell exists in the sealed initramfs/root sequence,
but a bidirectional serial path can still carry a serial BREAK and Magic SysRq
commands. A future electrical probe must therefore be receive-only from the
host's perspective: target TX → adapter RX plus ground, with adapter TX
physically disconnected. A USB-C debug cable that cannot prove this direction
is not suitable under the current one-shot authority model. Disabling serial
SysRq or changing console policy needs a separate reviewed design because it
also changes emergency recovery behavior.

## Defect fixed and regression coverage

Concrete defect: the signed native bundle verifier accepted a DTB whose
command line named `ttyMSM0` without validating `/chosen`, the serial alias,
the enabled GENI instance, or its exact pinctrl route. A wrong, disabled, or
redirected UART could silently remove the only latent non-NCM observation path
while still passing admission.

`tools/recovery_control/rog5-bundle-verify.c` now fails closed unless the
signed DTB contains the exact route listed above. It also binds the enabled
ancestor path: the exact `/soc@0` address/size cells and accepted identity
translation, plus the QUP compatible, register, cells, empty child
translation, and status. It resolves and compares the UART pinctrl phandle
rather than accepting an unrelated state with the same name.

`scripts/host/test-recovery-bundle-native.py` adds hostile mutations for:

- wrong stdout path and serial alias;
- disabled or translated/mis-sized ancestor buses;
- wrong QUP compatible, register range, cells, or translation;
- disabled QUP wrapper or UART;
- wrong UART compatible or register range;
- unrelated pinctrl phandle;
- swapped RX/TX pins;
- GPIO rather than `qup3` muxing;
- the actual repository-accepted DTB.

The original regression would have passed every hostile DTB because the
verifier ignored all serial properties. The first fix would also have passed
the hostile ancestor mutations, and its second revision would have accepted
wrong root address/size cells; independent standards review exposed both gaps
before the checkpoint was committed.

The sealed private ARM64 binfmt namespace restored the release gate without
administrator credentials or a host-global handler. Two clean verifier builds
are byte-identical at SHA-256
`33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef`;
the complete AArch64/QEMU mutation suite passed in `69 s`. The source hash is
`f41142a73d3c43ad0aad640cb1d99afa47461ef452bb522ad990a175c830760d`;
the builder image ID is
`13d758cd4c708ddb798dd539d1b6c4e3546ea5ef9129ed309c74bd8f4e620689`
with digest
`sha256:75f5179fe0164ffefa2f9bc5dba5a47eac47674d347311602256476aa2ee7a01`.
Stable recovery still contains its prior verifier binary; this review neither
repacked nor signed recovery.

The two-axis review also found a separate critical-path defect: the target
could set `host-port-probe-failed`, `host-port-unreachable`, or
`host-port-timeout`, but neither the native reporter nor host parser accepted
those values. The fail-first native/host round-trip test failed three cases in
`4.759 s`. The fixed test passes all 27 cases in `4.753 s`; two clean AArch64
reporter builds are byte-identical at SHA-256
`26249252916cf0f2cfba1547a845ef15caa07f6abc77c5149f1662f0a168bafa`
and the AArch64 fault/oracle gate passes in `13.508 s`.

Two clean diagnostic initramfs builds then produced 6,013,458 byte-identical
bytes, SHA-256
`94edd6254403759db423970e8cd313e4edde2e744f042f87f9f59815f8bbcffc`,
in `80.187 s`. This is an offline component with `boot_authority=none`, not a
candidate: no candidate contract, signed bundle, recovery wrapper, policy row,
or phone action was created.

Focused timing:

- before: 24 tests, `3.670 s` wall time;
- after: 26 tests including all hostile subcases, exact root and ancestor
  translation, and the real accepted DTB, `4.335 s` on the final focused
  rerun;
- runtime bundle packager: 8 tests, `4.279 s`;
- recovery prepare/load/execute integration: 2 tests, `5.297 s`.

The stable-recovery initramfs composition gate remains unavailable because its
ignored local input
`artifacts/recovery-stage-v18/rog5-recovery-initramfs.cpio.gz` is absent. This
is a retained-input availability limitation, not evidence that the prior
embedded recovery verifier was replaced.

## Remaining uncertainty and next gate

The SoC route is a **latent channel**, not a demonstrated independent channel.
Before any phone cycle relies on it, a reviewed hardware note must identify
the exact connector or pads, voltage level, orientation, ground, and a
receive-only hookup. The alternative is one separately authorized transition
cycle designed solely to establish ramoops retention and current-cycle
lineage. Neither experiment is authorized by this offline review.

The NFS/USB critical-path recommendation therefore remains **HOLD**.
