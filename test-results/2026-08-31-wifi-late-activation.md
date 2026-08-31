# Controlled Wi-Fi activation checkpoint

Question: can the cache-coherent1350mV hold support radio bring-up while UFS,
NCM and power remain stable? At this source checkpoint no new phone cycle had been admitted or executed.
Persistent V11 and ASUS slot A are unchanged. Current V11 battery is Full/Good,
8.610V/30.1°C; persistent state and Tailscale services are active.

## Changes and regressions

- R3: sealed BusyBox retried an ENODEV module initializer. A small static
  `module-once` uses exactly one `finit_module` call, including EINTR/EINVAL/
  ENOSYS/ENODEV failure. Real before/after frames are replay fixtures.
- R1/R2: active probe and tracer no longer select an old kernel release.
  Their caller must supply the release from the verified execution record.
- Radio startup is now explicitly staged. All regulator constraints are in
  the boot DT, but PMU, PHY and PCIe remain disabled. A separate diagnostic
  S12 consumer establishes the low hold and exact1350mV request first.
- The fixed activator enables only those three statuses after an in-kernel
  check of the held qualification, cache, enable/mode and fresh RPMh readback.
  No regulator property is changed after registration. Partial notification
  can have side effects, so any attempted apply pins the module/changeset
  until reboot; its result must be checked. It cannot be unloaded/retried.
- R6: `ROG5_TEST_TMP_PARENT` permits project RAM-backed test scratch while
  preserving the default HOME behavior and existing path checks. No evidence
  or old build was deleted; the verified kernel archive was reused.

The kernel [changeset API](https://docs.kernel.org/devicetree/changesets.html)
applies properties before notifications. Exact local source inspection also
confirmed that notifier errors can follow device creation; a zero module-load
status alone is not qualification. The platform notifier supports enabling
the root PMU and the PHY/PCIe children of the populated SoC bus.

## Offline results

The five focused activation tests run in0.254s. Thirty focused tests including
S12, tracing and power-control replays pass. The scratch regression passed
in6.270s. An independent bounded source review found no blocker; it did not
provide physical evidence.

Active tier passed in90.760s. The first full run stopped at415.509s because
the chosen nested RAM scratch exceeded AF_UNIX's pathname limit. No phone
was contacted by this test. A short project-private parent fixes the fixture;
the runner now proves the actual broker socket path before expensive suites,
with a regression for overlong parents and cleanup. Kernel/modules are unchanged.

The corrected runner contract and all19 broker tests passed first. Full local
CI then passed in438.238s on tree`80d5dd4ac2f69416023060b61cce25ffe25c3b39`.
This final result-only addition does not change executable inputs. The previous
successful full run took614.760s; these are observed durations, not a controlled
benchmark. The failed415.509s run is retained separately, not counted as a pass.

Four-module twins completed in18.083s/17.905s with identical hashes and exact
release`7.1.4-g1eea8970e87f`/BTF. Kernel, config and base kit are unchanged.
Staged DT twins match:
`8b1250cefd69870662edb9131190f005f492b4c93c192ee7e2b89b9a121f22da`.
Static loader twins match and built in4.160s.

Exact-Image QEMU passed in6.028s:19 base modules and17 Wi-Fi roots loaded,
including actual observation parameters. The new S12 initializer entered once
and refused the wrong board; the activator likewise refused. An inert,
QEMU-only symbol fixture provided its dependency and must never enter a phone
package. This smoke proves ABI, parameter compatibility and refusal behavior,
not radio, regulatory firmware or physical power qualification.

The read-only PON observer also has exact-release twins (3.186s/2.982s).
The387409-byte activation artifact archive is verified member-by-member:
`59a26c6068f083096a8479a2fbb2031914a9e4579f2035ab43a9acedc284d4a0`.
It excludes all QEMU-only fixtures. The original kernel archive remains the
authority for Image/config/base modules; no kernel or wrapper was rebuilt.

## Before the next physical attempt

Freeze and publish source after active/full CI. Assemble a fresh signed target
and one-use execution record; retain V11/slot-A rescue. The cycle must account
for S12 qualification plus radio/probe/cleanup deadlines together, deploy the
matching module set and exact firmware/regdb, collect independent USB/PON plus
RPMh/PCIe evidence, and check all117-RO/power/transport before activation.
PCI identity must pass before ath11k binds. No persistent radio deployment,
partition write, or experimental flash is authorized by this offline result.

## V14 data-only admission

Source`cda918bdbfabf9cd3610e671604206ac58b23608` passed all jobs in GitHub
run33397881681. Matching signed V14 RAM bundles and the exact probe package
are prepared. The controller replays power/cache/radio failures, late-start
refusal, source/target release parsing, partial SSH timeout output and fallback.
The sole added claim binds the core manifest, complete probe package, runtime
tools and timing plan. AST comparison proves that no executable repository
code changed since the fully validated source; historical claims are unchanged.
Focused artifact and claim tests qualify this data-only admission without a
second full CI run. It is not new full-CI evidence for the admission commit.

One temporary V14 execution is admitted under standing project authority,
subject to the connected identity, power, all117-RO and observation gates.
It remains unconsumed until the existing generic consumer irreversibly enters
the exact record. V13 and all earlier trials remain consumed. No persistent
deployment, partition/slot write or fallback change is included.

## V14 live: power/PCIe pass, hw1.1 driver rejection; consumed

Executed once from data-only admission`73494da8f9f92e2165d03cafe6526f7154dd8133`.
Target`0545d4eb-59fa-4c31-af74-17440892044f` reached strict SSH37.536s after
claim entry. Query, AUTO and held-OEM phases each completed once; matched RPMh
write/readback and cached1350mV checks passed at54.303s. Three direct p24 reads,
NCM and power gates passed before radio activation; all117 UFS nodes were RO.

The fixed changeset succeeded. WCN regulators, clock and WLAN GPIO sequencing
completed, followed by PCIe Gen3x1 at uptime62.432s and the exact expected PCI
endpoint. At63.367s ath11k printed `Unsupported WCN6855 SOC hardware version:
1 16` and returned EOPNOTSUPP. Source inspection places that exit before MSI
allocation, MHI registration and firmware initialization. No PHY appeared.
The runtime failure is now a sanitized fixture exercised by the hw1.1 selector
test. It is not evidence of bad firmware, another S12 reset or USB/UFS loss.

The existing [WCN6851 addition](https://patchew.org/linux/20260601-sm8350-wifi-v1-0-242917d88031%40oss.qualcomm.com/20260601-sm8350-wifi-v1-2-242917d88031%40oss.qualcomm.com/)
covers this observed1/0x10 revision. Use its three-vdev variant and matching
vendor firmware; do not force hw2.0 or change the qualified kernel/DT path.

Normal reboot restored V11`22ec3b83-0967-41dd-ba0a-5bea2a93e0a2` and shared
SSH/state/Tailscale services in74.901s; total claim→restored223.396s. Source
and pre-vote target PON snapshots match. The fallback FIFO advanced40 bytes,
with the requested PS_HOLD/HARD_RESET sequence. Absence of a crash dump still
does not prove no crash. Maximum sampled thermal-zone value was37.8°C across
30 zones. Final battery was Full/Good,8.608V/30.1°C; normal sda+sda23 write
scope was restored. Temporary8079 listener permission, management alias and
observer processes were removed. No slot, loader, selector, partition-layout
or experimental storage-write operation occurred. V14 must never be retried.

## Matching hw1.1 successor inputs, not admitted

The four ABI-coupled ath modules built in58.135s/50.906s with matching hashes,
against the V14-qualified kernel kit. Exact-Image QEMU passed in5.877s,
including AHB. Active tests passed in101.013s with the real hw1.1 rejection
fixture. No kernel, DT, initramfs or wrapper rebuild was needed.

The missing base dependency list was recovered from the exact archived ELF
export/namespace/GPL tables:450 symbols, with MODVERSIONS explicitly disabled.
It also matches the retained original modpost output. This avoided recompiling
the base Wi-Fi kit; it did not invent symbols or modify any module bytes.

Matching AMSS/M3/regdb and three BDF ELFs were extracted read-only from the
hash-verified official WW33 vendor image. The retained ASUS observer reports
MP/stage7. The ASUS MP filename logic selects by QMI board ID and chip GF bit,
not PCI subsystem0108. A proper board2 container preserves all three complete
ELF payloads and uses exact PCI/QMI aliases for the supported non-GF range and
board IDs13/52/255. It contains no generic bus/chip alias or board.bin fallback.
The exact kernel parser selected the correct unchanged ELF for all384 aliases
and rejected wrong PCI, GF, unmapped board and out-of-range chip keys.

This reproduces retained ASUS source rules, not proven WW33 binary equivalence.
Both source implementations default missing board information to255; chip0 can
also be a default. A matching key therefore does not prove both QMI fields were
explicitly reported. These prepared firmware inputs still require a fresh
physical qualification; no successor has been admitted or booted.

## V15 admission

Source`eb257433d1545ec632e4acd0724fdd4e46e29a98` passed all jobs in GitHub
run33406085857. The fresh signed V15 core twins match, reusing the V14-proven
Image/DT/initramfs. Its probe package replaces the coupled ath family and
provides only the matched hw1.1 firmware with exact-keyed board2 data.

Assembly took3.930s. The unpacked module tree is no longer duplicated in the
transfer archive; exact two-layer extraction and both file manifests pass.
Controller replay passed in4.288s, including the bounded optional scan path's
sealed-shell syntax. Signature, package, timing, source-delta and one-use
checks remain separate from the successful source CI. Only literal admission
data/status text is added, so full CI is not repeated for unchanged executable
source. V15 is admitted once under standing authority, subject to the fresh
connected gates. V14 and earlier candidates remain permanently consumed.

## V15 live: firmware, PHY and scan pass; consumed

V15 executed once from admission`86b057eda1442a3b5d63d25d3079d30fc6c26bcb`.
Target`6309aa2a-b741-4520-87e6-9562d245b57f` reached strict SSH39.566s after
entry. Coherent S12, direct UFS, WCN sequencing and PCIe checks passed again.
The driver accepted hw1.1, allocated32 MSI vectors and started MHI/firmware.
It logged chip0, family0xb, board255 and SoC0x400c0110, followed by the expected
WLAN.HSP.1.1.c3-00205 firmware build. Board255 may be defaulted; the log alone
does not establish its validity flag.

`phy0` appeared at uptime64.48s; the interface renamed from wlan0 to `wlp1s0`.
The exact-parent interface check passed and scanning returned status0 with33
BSS records across2.4/5/6GHz frequencies. Raw SSIDs/BSSIDs remain private.
This proves firmware/PHY/scan operation, not association, DHCP or Wi-Fi SSH.

Normal reboot restored V11`699959e3-9635-4f6c-9765-b12bf3ff3597` and services
in73.318s; total entry→restored156.807s. Battery was Full/Good,8.607V/30.0°C;
maximum of30 sampled thermal zones was36.5°C. Source/pre-vote PON snapshots
match. Experimental UFS stayed117-RO, and normal sda+sda23 write scope was
restored. Temporary observer processes,8079 permission and management alias
were removed. No persistent Linux deployment or slot/layout change occurred.

Next is userspace-only association with the exact working composition.
The WPA2 client runtime is prepared from seven signature-verified Alpine
packages; AArch64 wpa_supplicant/wpa_cli2.11 checks pass. No network credential
has been read or deployed yet. Separately, inspection of the exact sealed
initramfs confirms an unconditional USB-carrier rendezvous before deferred
UFS loading. Remove that production host dependency only in its own tested
checkpoint; do not weaken the diagnostic or storage-write path.
