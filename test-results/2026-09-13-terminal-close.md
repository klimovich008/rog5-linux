# Authenticated Denial VM normal terminal close — 2026-09-13

**The complete authenticated Denial session now PASSes in the generic ARM64 VirGL VM.** Foot exits0 through its normal child-exit callback; two native clients configured,30 raster frames/page flips were recorded, PAM closed successfully and the local session scope was removed. The VM unmounted all filesystems and powered off normally without a panic. These receipts do not establish practical application input, visual correctness or any phone capability.

No phone operation, protected-storage mutation, production signing, admission, claim consumption or new phone candidate occurred. Physical rows remain NOT RUN; historical headless S06/R01 remain FAIL. The native-phone goal remains active and incomplete.

Start commit `ca0074f578aa82ae52408fdb94e3116ac924e18a`, tree `7231372e843f091029b989e290e398cdfe99894f`. The normal-close implementation is `cd7c7a09591da98d7093d87a7327a50056daa148`, tree `578f1de521ccb198a0e63368f0c2f54df2da2f2b`. The final evidence-producing source is `de579359f37a87220da42fcb26fe473022d7ba48`, tree `c41d52a474c2bec74049155f6ad2e19cf9e9a58b`, clean at VM and integrated-suite launch. Subsequent publication changes only documentation, status and provenance.

Changed executable source: `tools/qemu-virtio-drm/logind-denial.sh` and `scripts/host/test-qemu-logind-runner.py`. The fixture gives Foot a real Bash child waiting on a private0600 FIFO. A bounded writer sends an exact exit token, the child exits0, and Foot must complete its normal shutdown callback before compositor stop. A missing reader has a3-second limit and a stuck terminal a5-second limit. Every other nonzero status, including124/230, remains a failure. Cleanup removes only its owned FIFO and reaps remaining processes. The existing65-second application watchdog and PAM/session/VM deadlines remain unchanged. This repairs test shutdown semantics; it does not modify Foot or globally allow its failure status230.

The host regression executes the actual shell launch/stop bodies, real child Bash, FIFOs and processes. Only the external Foot executable is replaced by a test executable that runs the passed child arguments; host tests do not prove GUI behavior. Cases include wrong tokens, early exits0/124/230, failure42, no-reader timeout, stuck terminal, interruption143, ownership cleanup and preexisting-path refusal. The original implementation fails the new normal-close test.

The first VM this turn failed after160.889s, before either native application launched, with user-session status124. Its journal shows desktop services completing near the20-second limit; the exact failed stage cannot be recovered from that uninstrumented run. It remains FAIL and normal terminal close was NOT RUN there. Added stage/status/timing receipts distinguish service-start20s, state-query3s and document-mount3s, writing only stderr so captured command output is unchanged. Fault tests exercise each failed boundary and verify that no later stage runs. No deadline was increased.

The single diagnostic successor passed in199.354s (runner199.291s). Its measured stage durations were19s service start,1s state query and0s mount query, with status0 throughout. These are coarse Bash SECONDS measurements. All four activated services were active and the document mount was `fuse.portal`. Foot returned0 without TERM; Mousepad returned0 and launcher143 after requested TERM. The complete PAM/logind cleanup passed. The earlier failure remains unresolved as to its precise stage: one successful near-limit run does not establish startup reliability.

| Executed check | Result | Seconds |
| --- | --- | --- |
| `python3 scripts/host/test-qemu-logind-runner.py FootClose`, before |1 failure |0.006 |
| Same command after |6 PASS |8.252 |
| `python3 -O scripts/host/test-qemu-logind-runner.py`, before stage diagnostics |39 PASS |8.439 |
| `python3 scripts/host/test-qemu-logind-runner.py ActivatedServices.test_each_boundary_reports_its_exact_status_on_stderr`, before |6 failed assertions |0.027 |
| `python3 -O scripts/host/test-qemu-logind-runner.py ActivatedServices`, after |5 PASS |0.111 |
| First combined VM |FAIL before app launch; normal close NOT RUN |160.889 |
| Final combined VM |PASS, VM only |199.354 |
| Final frozen `scripts/host/test-repository-linux.sh active` |97 PASS,0 FAIL/BLOCKED/SKIPPED,255 NOT_SELECTED |146.143 |

The exact commands and per-step durations, source identities, inputs, outputs,
JSON/JUnit counts and cleanup receipts are in the
[qualification JSON](2026-09-13-terminal-close-qualification.json). No GitHub CI
run is claimed. Host semantic fixtures and actual VM execution are separate
results. Expected mutation failures inside passing regressions remain visible.

Reused generic kernel Image SHA256
`2b1c8d95f54dda28e772df82be54af7508b2ce84183f1b0024a7f14e3d5ce0fc`,
config `23af1f7083bb5607f65904ab6d46a101c5d67fd73a6ae10dd868877db16870af`,
Linux `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`, release7.1.4+, no modules.
This is the existing generic FUSE VM profile, not the ROG5 board kernel.
No kernel, Denial or Flutter rebuild was needed. VM helper compilation is
recorded separately by the runner. The readonly unsigned session archive remains
`1ff417307c96bac90977b64a143e1a81b535d94a03109ca967c40e9b1f269d0c`;
Denial binary remains
`40b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0`.
Denial revision85b2303e2f09ae7b7b993641f90061a200f03d53 and Smithay
812bd33259ff58810dadef6086d8385eeac1ca55 remain pinned with the retained fixes.
This turn does not rerun their modifier tests or replace their prior evidence.
Runtime package authentication is reused from the retained closure. No claim
about installed phone bytes follows from this source qualification.

Both VMs used the same retained kernel/runtime/payload/tool images, network
isolation,2GiB container memory without swap,2CPUs,1GiB guest memory,8MiB serial
cap and300-second VM limit. The26MiB archive was hardlinked readonly rather
than copied per run. All owned containers were removed and verified absent.
Disk free space remained above3GiB; no files were retired this turn.

The observed19/20-second service start is a remaining reliability limitation,
not proof of a kernel or GPU defect. Missing RealtimeKit/PipeWire feature warnings
remain separate unqualified functionality. Normal client configuration alone
also does not prove text entry or useful application interaction. The next
smallest offline experiment is to adapt the existing pointer-only OSK text-entry
oracle to this authenticated local session, reusing the qualified artifacts and
requiring actual application text plus cleanup. No new Denial/Flutter build is
justified by this result. The smallest unresolved hardware question remains the
existing reviewed display/provider trial on exact admitted bytes; it requires
fresh authorization and is not started or admitted here.

Publication appends fixture set521 while preserving the prior520 sets. Only the
current authenticated-VM pointer changes; the generic session-kernel, unsigned
payload, signed fallback and all other pointers remain identical. Headless and
mobile contracts, consumed claims and the historical current-state body remain
unchanged. Raw logs and runtime artifacts remain private.

The final active tier includes the40-method runner suite. Three declared optional
subchecks remain SKIPPED; no selected mandatory suite skipped. The final tier ran
once after the VM settled, under1GiB/no-swap memory,2CPU and2-worker bounds.
Qualification SHA256: `86ea19f3a119792849e4e9f9ab10a5fc2ced974d6d4c1b1f4bf248d018d21d5f`.

Publication verification: metadata checker regressions5 PASS (0.929s), mobile
status regressions8 PASS (0.021s), inventory PASS521 sets/827 registered/177
tracked files with68 small tracked hashes checked, generated status PASS and
`git diff --check` PASS. The inventory check explicitly leaves large/private
byte verification, admission and physical qualification NOT RUN. A separate
preservation comparison verified the prior520 sets, both acceptance contracts,
all other artifact pointers and the historical current-state body unchanged.
Free disk was3,371,413,504 bytes; the owned-container list was empty.
