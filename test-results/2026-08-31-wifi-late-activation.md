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
