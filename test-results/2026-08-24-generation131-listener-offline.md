# Generation 131 stage-listener wiring

Result: **OFFLINE PASS; ADMITTED ONCE.** Never flash or retry after entry.

Primary question: what exact early `power-usb` stage does the existing target
reporter publish once the host opens the already-implemented port-8079 listener?

The fail-first regression proves the active run previously selected the
SSH-only helper. The fixed run selects `wait_for_target_host_key()` and forbids
the legacy helper in the post-COMMIT segment. Target twins are
`1d8fc7c7...d191d8b`; manifest is `84a21be6...d41d680`; Generation-131 recovery
is `ef44ce1a...a4f654`. Kernel, DTB, modules, reporter behavior, installer,
storage scope, and slot-A fallback are unchanged.
