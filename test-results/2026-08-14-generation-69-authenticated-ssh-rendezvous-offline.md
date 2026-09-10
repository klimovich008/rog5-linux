# Generation 69 authenticated-SSH rendezvous offline checkpoint

Date: 2026-08-14

Result: **OFFLINE PASS; UNBOOTED.** No phone boot or persistent phone-storage
operation occurred while producing this checkpoint.

The demonstrated Generation 68 defect was a host deadline: the first cold
authenticated SSH session did not complete in ten seconds even though the
target remained reachable and `sshd` stayed active. The runner now performs a
harmless exact-marker command with strict key-only authentication, retries
transport failure or a bounded per-attempt timeout for at most 150 seconds,
and records every attempt. A successful command with any unexpected output is
rejected. The storage runtime evidence command remains single-shot.

The focused fail-first test failed before the implementation because the
rendezvous did not exist. After the change, the runner's 16 tests passed in
0.140 seconds, including cold-start retry, timeout, and wrong-output cases.
The current-profile, live-gate, exact-claim, retention admission, and execution
closure tests also passed.

The final complete local repository CI tier passed in 449.318 seconds.

The signed v45 target bundle and raw recovery are unchanged. Two independent
Generation 69 issuances took 1.847 and 1.671 seconds and are byte-identical:

- raw recovery SHA-256:
  `5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
- AVB salt:
  `989ac285e377d1fa566ccf0360b55fad1fff8854170f1d4386117b6d8f26b5d6`;
- AVB digest:
  `09e72f846dbc5500f7fc287e6e1013813006b3cfbd67c8338dd71704de19d343`;
- AVB image SHA-256:
  `4dfc0efc92b511b424b7d9db115d692c79b0366459e23582421cd37d9c307a65`;
- generation record SHA-256:
  `4c98edd39c2474edb387d6342a51ffd5e784f4a6a107d70190bbccfcd2506fda`.

Generation 68 remains consumed and revoked. Generation 69 permits one
RAM-only cycle and must never be flashed or retried after claim entry.
