# ROG5 priorities

The accepted standalone server milestone is complete. See
[current state](docs/current-state.md) and its linked evidence for what passed.

1. Complete the bounded repository/development-loop consolidation: compact
   context, demonstrated integration fixes, safe retention, reproducible
   packaging and proportionate CI. Preserve the working server.
2. Finish the minimal display test with an operator present: a short power
   press must turn on time/Wi-Fi/battery status and a second press turn it off.
   Validate the packaged service namespace before consuming another target.
3. Define the operator-selected server workload under an unprivileged account,
   with secrets confined to existing persistent service storage. Validate
   resource limits, updates, networking and recovery.
4. Investigate recurrent PMIC/UFS errors only if fresh evidence appears.
   Continue longer power/thermal and unattended-operation measurements.

GPU, desktop, audio, additional sensors and storage expansion remain deferred.
A kernel change requires a specific unresolved hardware question; host parser,
packaging and service-sandbox failures should be reproduced offline first.

The previous roadmap, including completed migration phases and historical
research, is preserved through the [archive index](docs/archive/README.md).
