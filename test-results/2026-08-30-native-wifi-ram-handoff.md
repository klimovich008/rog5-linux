# Native Wi-Fi RAM handoff checkpoint

Primary question: can the stock-derived WCN6855 DTB and exact V11 modules expose
a working radio while preserving UFS, charging and USB rescue?

The native RAM handoff passed, but PCIe activation reset the phone before MHI
or ath11k loaded. Wi-Fi is **not working yet**. V11 returned automatically and is
healthy. Both `native-wifi-ram-v1` and `native-wifi-ram-trace-v2` are permanently
consumed; never retry either.

## Minimal handoff correction

The installed standalone exitramfs always normal-rebooted, including when
systemd requested kexec. This R3 capability mismatch would prevent a native
RAM trial. The exitramfs now dispatches one syscall-only static executor only
for the kexec verb, clean storage teardown and a verified RAM-staged executor.
Missing/changed tools, incomplete teardown or any returned syscall fall through
to normal reboot. Ordinary V11 shutdown remains unchanged.

`load-native-ram-bundle.sh` checks source boot/kernel/model, safe power, exact
tools/libraries/trust, the signed target and all 117 UFS nodes read-only before
loading once and requesting normal systemd kexec shutdown. The existing exact
record consumer permanently consumes the trial before that request. The target
bundle keeps V11's unchanged initramfs/rollback; neither p24's selector nor a
boot partition is changed. The new helper is staged only in `/run/initramfs`.

## Offline and connected evidence

- Existing Wi-Fi commit `f1c432a` passed exact-head, merge, QEMU and publication
  CI in GitHub run `33308991547`.
- Two independent static executor builds are identical. No ELF interpreter is
  present; an unprivileged QEMU invocation returns failure, never success.
- Dispatch fixtures cover reboot/kexec, clean/unclean teardown, missing and
  symlinked files, wrong checksums and both zero/nonzero executor returns.
- Full-system QEMU loaded and executed the exact V11 kernel a second time with
  the verified kexec tools and new static syscall helper. It reached the unique
  target marker. No disk or network device was attached. This is not physical
  Qualcomm kexec or Wi-Fi acceptance.
- Connected non-consuming preflight passed on the still-running V11 phone.
  The native root lacked the verifier's public key; the exact public key was
  staged into its volatile overlay, not persistent storage.
- CI exposed an R1 fixture mismatch: runtime tests used current program bytes
  against historical process identities. Refreshing that historical pin was
  rejected by its own admission chain. The historical identities are now left
  unchanged; offline fixtures consistently bind their current test programs.
  The fast tier runs this regression first. New native RAM claims are read from
  the one canonical registry instead of copied into another historical list.

## Physical result

Source `abf3db66627c0d8ff39d3d74a8ddd3e7f1a14cdc` passed full local CI in
**453s**, plus every job in GitHub run `33311073552`. No kernel/wrapper rebuild
was needed. Exact-state module builds remain the preceding 91.60s checkpoint.

One-use entry occurred at Unix 1788092901.088912; dispatch at 1788092901.089000.
The kernel loaded once, systemd quiesced storage, and the RAM exitramfs executed
the Wi-Fi target. Its new boot ID was `7a95dcfa-ebc5-476c-877d-9c83971eea95`.
Root handoff passed at 1788092929.399 (**28.310s after dispatch**). Pinned SSH
then proved the Wi-Fi target cmdline, systemd running, zero failed units and
healthy battery telemetry. No boot partition, slot or persistent selector changed.

State/Tailscale were stopped and all 117 UFS nodes proved RO before each risky
boundary. The radio probe verified the exact module/firmware/userspace inputs
and armed a 600s systemd rollback. Crypto and power-sequencing modules loaded.
At target uptime 121.69s, `phy-qcom-qmp-pcie` loaded and triggered deferred PCIe
controller probing. The last kernel line, at 121.780805s, prints the controller's
MEM range. There is no subsequent MHI or ath11k load, PCI endpoint or PHY-ready
record. This is not a Wi-Fi firmware/BDF failure yet.

Host USB evidence shows mainline→ASUS 5.4 loader→mainline, and the new V11 boot
ID `3b71f143-439d-44db-ac09-991624e68c79` proves a reset/reboot rather than only
lost networking. V11 automatically restored Arch, pinned SSH, charging,
the exact sda/sda23 writable scope and the existing healthy Tailscale identity.
The 600s timer was not due; the reset mechanism remains unknown. No crash-free
claim follows from the missing panic text.

Pstore/archive directories are empty. The actual config has PSTORE_RAM built
in, but this native DT has no ramoops node and runtime mem_size=0: there was no
working ramoops backend. No lineage-safe reset-cause field was captured here.
The temporary host alias, 8079 firewall rule and observers were removed, and
the normal shared profile was reactivated after its external-address race.

Private radio log SHA-256:
`d8e9396ba2b249ce18c74eac787fc6632464f10594d991b5cd55c572c3f7340e`.
Private live kmsg SHA-256:
`85b5be9e1bc12424d27c57c2b4678d12956361f8068189e151cc276fba7713d1`.
Sanitized evidence is retained in
`tests/fixtures/native-wifi/pcie-reset-before-mhi.json`.

## Next discriminating step

Trace controller initialization, clock enabling, reset controls and PHY power
before changing hardware settings. Exact V11 exposes KPROBE_EVENTS and the
relevant built-in symbols; FUNCTION_TRACER is disabled. A bounded runtime trace
can narrow the failure without rebuilding the kernel. Do not guess a rail,
firmware or calibration fix. Preserve the consumed trial and V11/slot-A rescue.

The userspace timer cannot resolve a hard kernel lock. PCIe stability, radio
firmware/BDF selection, association and Wi-Fi SSH remain unproven.

## Tracer preparation

`trace-native-wifi-pcie.sh` uses a private trace instance and 20 bounded
entry/return probes. It neither loads a driver nor touches PCIe/storage. Its
plan is checked against the captured pre-MHI failure fixture. An on-device
setup/marker/cleanup roundtrip passed on the recovered V11 without reboot or
PCIe activation; the original global kprobe definitions were restored exactly.
Battery remained Good/29.9°C and the boot ID did not change. The void version
detector deliberately has no claimed return value. A failing deadline test
caught the initial 600s reader ending before its 600s radio rollback plus margin;
the reader is now 900s. Setup/cleanup semantics are unchanged.

The trace-v2 bundle reused the unchanged kernel, DTB and target initramfs with
a fresh identity and an exact, different diagnostic tool package. Native claim
tests now derive the native entries from their one canonical record registry;
historical source pins remain unchanged. Focused claim/runtime/admission tests
pass, with no new kernel or wrapper build.

## Trace-v2 physical result and offline reproduction

Source `8b08c15` passed all jobs in GitHub run `33313046551`. Trace-v2 executed
once, reached Arch/SSH and relocked all 117 UFS nodes before the radio probe.
It again reset and automatically returned to healthy V11, now boot
`e4fbe654-af38-4e6c-9987-97968419a68f`. Normal shared networking and Tailscale
were restored, and temporary observers/host changes were cleaned up.

The trace proves `qcom_pcie_init_2_7_0` returned 0, including successful clock
and reset calls. `phy_power_on` returned 0 at 174.526138s. The last delivered
event is entry to `pci_pwrctrl_create_devices` at 174.526142s. It does **not**
prove a fault inside that function: the same USB transport may have lost later
buffered events during reset. No voltage or firmware fix follows from this.

A hardware-free fixture using the exact Image and matching WCN provider/client
modules then passed creation, driver binding and dummy power-on/off in QEMU.
It uses no physical GPIOs or supplies and refuses non-virt machines. This does
not reproduce ASUS electrical behavior, but it rejects an unconditional
creation/ABI failure as the explanation. The Opus review again could not run
because its saved OAuth session expired; no independent approval is claimed.

Classify the observation gap as R8; the electrical/software reset cause remains
unresolved. Before another phone attempt, the diagnostic-only pwrctrl patch
adds disabled-by-default, bounded pauses at probe/power entry and return so
USB evidence can drain. QEMU passes at 0 and 250ms, and 1001ms rejects binding
before power-on. A regression validator checks the actual boundary delays.
Two normalized module builds and complete module archives are byte-identical;
only the pwrctrl `.ko` differs from the existing module set. Exact vermagic/BTF
and the final-module QEMU 250ms case pass. The Image, DTB and firmware did not
change. The active tier passed in 80.385s; focused observer/claim/admission
checks passed. No second full local CI was run for this module-only change.

The observe-v3 signed bundle, different module archive and tools are prepared
but unissued. Their identities are bound in the one exact-record registry.
This remains a diagnostic experiment, not a claimed production Wi-Fi fix.
