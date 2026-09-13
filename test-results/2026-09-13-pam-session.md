# Denial PAM boundary and mobile entry — 2026-09-13

**Eight actual ARM64 PAM cases PASS; mobile entry prepared, not installed.**
The correct synthetic password is rejected with stripped unix_chkpwd permissions
or NoNewPrivs=1. With authenticated package mode06755 and NoNewPrivs=0, the
actual pinned Denial PAM backend accepts it. Wrong passwords, expired accounts
and locked accounts are refused. This resolves a concrete prerequisite for
password unlock; it does not qualify the full lock-screen or real login.

Starting source `c1dd5d34ff00ce772c5472150623fbe108af19c2`, tree `59986cf9f9cd39a5279ae8e095b25a1727d5fd67`.
VM/build source `1ebf577797694ca184dca7f3a136473bfe7047d9`, tree `fa68f1e2d52dbc9a571b302568eebba02c5bb346`. Final entry source
`42ce254d23ce8de2e0af189e953d51ba368886e8`, tree `53d3a5deaf2e2962c8efcfba002899d520a6c707`.
The final active run also included evidence/status metadata bound by tested tree
`3548c626f4adce6a508471710cb5cab4b5b5a318`; publication now records that result. The previous goal turn was no progress; this turn executes new evidence
and implements the prepared session entry. Denial source remains
`85b2303e2f09ae7b7b993641f90061a200f03d53`; the extracted authentication code is byte-identical
to the matched current native source. No compositor, engine, AOT or kernel rebuild.

| Executed check | Result | Duration |
| --- | --- | --- |
| Final ARM64 extracted-backend build | PASS | 6.464s |
| Initial six-case PAM VM | PASS; synthetic clock warning retained | 13.680s |
| Eight-case VM with deterministic guest clock | PASS | 18.745s |
| Final frozen build in eight-case VM | PASS | 18.994s |
| Mobile entry Python -O fixtures | 18 PASS | 0.394s |
| Initial integrated active tier | 95 PASS, 0 FAIL/BLOCKED/SKIPPED, 255 NOT_SELECTED | 135.778s |
| Final entry integrated active tier | 95 PASS, 0 FAIL/BLOCKED/SKIPPED, 255 NOT_SELECTED | 151.731s |

The new `packaging/arch/mobile/denial-mobile-session` delegates to upstream after
checking mobile UID/GID1000, a private runtime directory, original PAM-helper
metadata and NoNewPrivs=0, and an active local `loginctl show-session self`.
It forces logind/mobile mode and the qualified login PAM service, and requires root-controlled machine configuration
with explicit KMS/render devices and a mobile-owned output file. It changes no
privilege bits, capabilities or service state. The separate desktop entry makes
it discoverable when a future qualified composition installs it. These shell
checks use bounded fact fixtures; actual logind device access remains NOT RUN.

The PAM experiment compiles the unmodified backend, conversation, secret erasure,
account check and result mapping, with a small Rust synthetic caller. The rootless
VM has256MiB guest/512MiB container memory, no swap/network/GPU exposure, a60s
outer deadline,8s cases and8MiB serial bound. Accounts, PAM fixtures and helper
permission changes exist only in guest RAM over a read-only runtime. The helper
bytes match authenticated pam1.7.2-2 archive SHA256
`a0c3f35ba05a7da5de8e8cb7c50ff05c1e51512e6055ba6958ddb80e17dcd880`;
the package signature audit is retained, not rerun. The default packaged login
stack comes from pambase20260616-1. No real password is accepted or recorded.

Initial source lookup failed because an exported source tree was not Git.
The first two small builds failed on missing host proc-macro discovery and the
retained thin-LTO setting; both errors and logs remain. The final builder owns
its container, enforces bounds and cleans up after timeout. The initial six-case
VM passed but warned about a future password-change date because the generic
kernel had no initialized RTC. The final fixture sets only its disposable guest
clock and exercises account expiration. An initial agent fixture failed because
command substitution strips the empty-groups newline; its regression passes.

Probe SHA256 `304985e2565aacdcbebed9de3d353027813b9946cb46a9039112754352098cf3`, 567520 bytes.
[Qualification](2026-09-13-pam-session-qualification.json) retains exact commands,
all run results, input/output hashes, source extraction identity and the full VM
driver. Tests were local; no new GitHub CI result is claimed. Active-tier source
changes include the manifest and retained public selector together.

Changed files: `scripts/host/build-denial-pam-probe.py`,
`tools/denial-modifier-tests/pam-guest-main.rs`,
`tools/qemu-virtio-drm/pam-boundary.sh`,
`packaging/arch/mobile/denial-mobile-session`,
`packaging/arch/mobile/denial-mobile.desktop`,
`scripts/host/test-denial-mobile-session.py`,
`configs/mobile/session-policy.json`, `configs/repository-tests.json`,
`scripts/host/test-repository-linux.sh`, `docs/development.md`,
`docs/development-lessons.md`, plus this report/qualification and the existing
artifact inventory/pointer, project status and generated current-state header.

The known NoNewPrivs conflict is resolved as a tested packaging prerequisite,
not by weakening the existing VM profile. Package-byte trust, nosuid mounts,
real authentication/session creation, logind TakeDevice and lock-screen input
isolation still require qualification. No installable mobile package, production
session configuration or phone candidate was produced. Next assemble the retained
ARM64 binaries with upstream launcher/target/CLI and this mobile entry, preserving
authenticated package permissions and default-off remote services; qualify a real
local logind session in the isolated VM. Exact phone60Hz output/device selection
remains tied to the separate authorized A660 trial.

No phone operation, signing, admission/claim, candidate generation or protected
storage mutation occurred. Existing non-root rendering/interaction evidence,
headless baseline, ASUS rescue, signed fallback and consumed claims are unchanged.
Mobile physical rows remain NOT RUN; S06/R01 remain FAIL. The goal remains active.

Final review found that an inherited PAM-service override could select a stack
other than the one qualified. Pinning login and refusing conflicting machine
configuration passed the extended18 fixtures (0.346s), then the final integrated
tier. The earlier integrated PASS remains recorded; unchanged PAM VM execution
was reused. Final tier memory peaked at285.2MiB with zero swap. Publication
metadata regressions and historical-preservation checks passed separately.
