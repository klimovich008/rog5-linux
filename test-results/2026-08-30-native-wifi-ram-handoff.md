# Native Wi-Fi RAM handoff checkpoint

Primary question: can the stock-derived WCN6855 DTB and exact V11 modules expose
a working radio while preserving UFS, charging and USB rescue?

The native RAM handoff passed, but PCIe activation reset the phone before MHI
or ath11k loaded. Wi-Fi is **not working yet**. V11 returned automatically and is
healthy. Both `native-wifi-ram-v1` and `native-wifi-ram-trace-v2` are permanently
consumed; observe-v3 is now also consumed. Never retry any of them.

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

The observe-v3 identities are bound in the one exact-record registry. Its
diagnostic module is not a claimed production Wi-Fi fix.

## Observe-v3 physical result

All jobs in run `33319404144` passed for source `0ec00e7`. Observe-v3 executed
once and reached Arch/SSH. A long operator gap expired the temporary host
management link before radio activation; the trace-ready guard stopped the
probe. The same running trial was resumed after restoring that link and tying
reader readiness directly to the single probe command. No target was retried.

With all 117 UFS nodes RO, the diagnostic module reported probe-enter at
4533.405142s, probe-ready at 4533.699394s, and power-on-enter at 4533.987669s.
The trace separately records `pci_pwrctrl_create_devices` returning 0 at
4533.987601s. The reset therefore did not prevent client probe completion.
Power-on-return was not observed, and no individual rail/GPIO cause is proven.
MHI initialization overlapped the power operation. An isolated test on the
recovered V11, with PCI empty and 117 nodes RO, loaded MHI in approximately 0.01s and
unloaded it cleanly without a reboot. That rules out an unconditional MHI-init
failure, not every possible concurrency interaction.
The target had already run for about 75 minutes before radio activation, and
the newly armed 600s probe rollback was not due. The reset followed activation,
not a fixed short idle-watchdog deadline.

V11 returned automatically as boot `22963cf0-b453-444d-89e3-3444a41d1d29`.
Persistent state, shared networking and healthy enrolled Tailscale were restored.
Temporary management address/firewall/listeners were removed. No partition,
slot, permanent kernel or voltage-setting change occurred. The sanitized
fixture is `tests/fixtures/native-wifi/power-on-enter-reset.json`.

Next, compare stock power sequencing and capture individual power transitions.
The retained ASUS implementation serializes regulator enable calls; mainline
uses bulk enable. The WW33 base tree's S12/S2 init-mode values are from the
vendor levels.h namespace, not mainline's mode namespace. Their composed-tree
applicability and actual live modes remain unproven; do not guess a mode fix.

## Per-supply diagnostic preparation

The WCN diagnostic patch serializes the unchanged supply list only when its
bounded `serial_observation_ms` parameter is nonzero. It logs each enable and
clock/WLAN-GPIO boundaries, without changing voltages or modes. Failure tests
compile the actual added loop and inject errors at each supply position;
only successfully acquired references are rolled back. Default bulk behavior
is preserved. The patch is outside the production patch stack.

Exact-kernel QEMU cases 0/250/1001 pass, including unsupported getter results.
A regression caught unsigned `-EINVAL` appearing as a huge mode number; modes
now retain signed errors and every optional getter has an explicit status.
The normalized provider module and full module archives reproduce across
independent builds. Only that provider differs from observe-v3's module set.

The public `probe-native-wifi.sh` loads software before the PCIe PHY and defers
ath11k PCI binding until the exact endpoint is verified. Replays cover correct,
wrong and absent endpoints. This removes MHI module initialization from the
power-transition interval. Rails-v4 is signed/prepared but unissued; no new
phone boot has occurred during this preparation.

The QEMU parent now uses `PROBE_PREFER_ASYNCHRONOUS`, matching the Qualcomm
controller, and waits on a verified completion field. All three cases also
pass in that context. A stale-fixture build was rejected; the harness now
requires the expected completion field rather than waiting on missing data.

## Independent PMIC history

The existing ASUS PON driver identifies PMK8350 SDAM5 at0x7400, push pointer
0x46 and FIFO0x4b..0xbf. A small fixed-bank reader uses the existing kernel
NVMEM read API and exports a root-only125-byte snapshot; it has no write API
or address parameter. The sysfs file advertises128 bytes, which clips the
peripheral-relative FIFO, so the validated provider read callback is used
directly without changing the provider. Its fixed path is resolved to an OF
node identity; a regression prevents comparing local `full_name` with an
absolute path. Wrong-machine refusal and all FIFO wrap positions are tested.

The read/unload succeeded on V11 without reboot or PMIC writes, with117 UFS
nodes locked RO. Service state/Tailscale were restored. The retained history
contains three PS_HOLD warm resets with counts1,2,3, and no OCP/UVLO records in
that window. This is consistent with software-requested reset but does not
identify the Linux failure or prove cycle attribution. The private before-v4
snapshot is available for a paired comparison after the next physical cycle.

## Rails-v4: S12 entry and independently correlated reset

All jobs in GitHub run `33330357462` passed for `e4b7dccb7679cb513d1e436e0eca9576647d9c1a`.
The preceding run failed only the compact-document budget; the active handoff
was reduced from 110 to 98 lines without rebuilding the Image, DTB or initramfs.
The matching module twins and 80.233s active-tier result remain valid. Exact-head
CI took 6m16s, merge compatibility 6m24s, and cached-kernel QEMU 1m52s.

Rails-v4 executed once with all 117 UFS nodes RO. Its claim was consumed at
1788117886.769026. Target boot `7f014b9b-bbec-408c-8f9b-b72357fe6daa`
passed switch-root 27.225s later and pinned SSH 34.447s later. Readers and the
single radio probe ran contiguously; no operator gap interrupted observation.

The serial diagnostic captured vddio return 0 at 39.423480s and vddaon return
0 at 39.999323s. Vddpmu/S12 entry at 40.287364s was the last delivered rail
record. **It does not prove entry to regulator_enable or a physical rail fault:**
the last delivered trace, 40.511640s, predates the end of the 250ms pre-call
pause. The 1.352V and mode-zero getters are cached/unknown, not measurements.

Before/after read-only PMIC snapshots advanced the 117-byte FIFO pointer from
175 to 78, exactly five records (20 bytes). The new records contain PS_HOLD,
WARM_RESET and warm-reset count 4 after the previous count 3. This correlates a
new reset with this cycle, not merely USB loss. No OCP/UVLO record was added;
that does not prove there was no electrical fault or kernel panic.

V11 automatically recovered as `3acd9da0-e927-4e97-85ea-b668f4cc6215`.
All nodes were relocked for the post-reset snapshot, then normal persistent
state and Tailscale were restored. Final checks showed Full/Good, 100%, 8.638V,
30.0°C, no failed systemd units and only sda/sda23 writable. Temporary host
address/firewall rules and observers were cleaned up. No slot, partition,
permanent bundle selector or voltage/mode setting was changed.

The partial real output is a regression fixture in
`tests/fixtures/native-wifi/s12-entry-reset.json`. It must not satisfy the
completed-power-sequence validator or be treated as proof of the faulting call.
All four Wi-Fi trials through rails-v4 are consumed. R8's evidence gap is
narrower, not eliminated; Wi-Fi is still unavailable. Audit the exact stock S12
initial mode and RPMh requests before selecting the next correction.

## Stock S12 mode correction, not yet hardware-proven

Offline composition of all three authenticated WW33 base DTBs with all 20
overlays confirms the same S12 contract in all 60 results: resource `smpb12`,
type `pmic5-hfsmps`, initial voltage 1.256V, allowed 1.224–1.360V, initial mode
vendor RET=1. The ASUS driver maps this to PMIC retention mode 3 and includes
the declared mode in its aggregated RPMh requests. CNSS's RFA2 load request is
zero, so a guessed extra load/HPM request is not justified.

Our addition omitted `regulator-initial-mode`. The correction explicitly sets
mainline RET=0, which maps through STANDBY to the same PMIC mode 3. It changes
one DT property only; the existing voltage request remains unchanged. A new
regression failed for missing mode and wrong values 1/2/3 before the verifier
fix, then passed. All seven DT and eight probe tests pass. Both DTB builds
match and took 332ms total. Kernel, modules, initramfs and firmware are reused.

The signed s12-ret-v5 twins match. They are prepared, not issued or executed.
This fixes a stock-description mismatch; it does **not** yet prove that the
missing vote caused the reset or that Wi-Fi works. The next RAM-only cycle
tests that one change, retaining the per-rail diagnostic and paired PON reader.
