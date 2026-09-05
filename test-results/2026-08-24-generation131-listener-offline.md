# Generation 131 stage-listener wiring

Result: **CONSUMED; EXACT MODULE ABI MISMATCH.** Never retry or flash.

Primary question: what exact early `power-usb` stage does the existing target
reporter publish once the host opens the already-implemented port-8079 listener?

The fail-first regression proves the active run previously selected the
SSH-only helper. The fixed run selects `wait_for_target_host_key()` and forbids
the legacy helper in the post-COMMIT segment. Target twins are
`1d8fc7c7...d191d8b`; manifest is `84a21be6...d41d680`; Generation-131 recovery
is `ef44ce1a...a4f654`. Kernel, DTB, modules, reporter behavior, installer,
storage scope, and slot-A fallback are unchanged.

Live result: the stage listener captured terminal sequence 2,
`stage=power-usb detail=module-qcom-q6v5-load`. Exact fallback and cleanup
passed; no UFS, SSH, installer, or storage write ran. Offline inspection of the
sealed module reports vermagic `7.1.4-gae717d919f87`, while the target manifest
and running kernel require `7.1.4-g359318de534f`. Matching g359 twin UFS and
power/USB module roots are retained under the local-image write kernel builds.
