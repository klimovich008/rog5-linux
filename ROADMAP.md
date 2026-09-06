# ROG5 priorities

The existing headless-server qualification goal is incomplete. The mandatory
[acceptance matrix](docs/release-acceptance.md), not this backlog, defines done.
See [current state](docs/current-state.md) for the next active outcome.

1. Finish the coherent headless release's mandatory charging, storage, network,
   ordinary/cold boot, soak and recovery outcomes. Do not reopen completed
   reviews without materially new evidence.
2. After qualification, finish the optional display test with an operator present: a short power
   press must turn on time/Wi-Fi/battery status and a second press turn it off.
   Validate the packaged service namespace before consuming another target.
3. Define the operator-selected server workload under an unprivileged account,
   with secrets confined to existing persistent service storage. Validate
   resource limits, updates, networking and recovery.
4. Investigate recurrent PMIC/UFS errors if fresh evidence appears; promote a
   finding into active work only when it blocks qualification or materially
   threatens the release. Retain the existing incident rather than another ledger.

GPU, desktop, audio, additional sensors and storage expansion remain deferred.
A kernel change requires a specific unresolved hardware question; host parser,
packaging and service-sandbox failures should be reproduced offline first.

The previous roadmap, including completed migration phases and historical
research, is preserved through the [archive index](docs/archive/README.md).
