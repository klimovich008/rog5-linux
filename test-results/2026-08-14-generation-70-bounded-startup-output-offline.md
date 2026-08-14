# Generation 70 bounded startup-output offline checkpoint

Date: 2026-08-14

Result: **OFFLINE PASS; UNBOOTED.** No phone boot or persistent phone-storage
operation occurred while producing this checkpoint.

Generation 69 demonstrated a host parser defect: an authenticated SSH command
returned status zero within the rendezvous deadline, but bounded startup text
beside its exact marker caused rejection before the runtime evidence command.
The fail-first regression reproduced that case. The runner now accepts a
bounded stream only when it contains exactly one marker line, rejects NUL,
missing or duplicate markers, and output above 4096 bytes, records the byte
count and SHA-256, and still invokes the exact runtime evidence command once.

Focused results were:

- persistent-root live runner: 17 tests passed in 0.142 seconds;
- generic exact-record claim consumer: 14 tests passed in 0.185 seconds;
- retention admission: 27 tests passed in 3.253 seconds;
- exact current Generation 70 profile: passed in 0.401 seconds;
- stable-recovery live gate: passed in 4.745 seconds;
- retention runtime closure: 13 tests passed in 0.966 seconds;
- retention executor contract: 8 tests passed in 0.087 seconds; and
- compatibility and source/DTB contracts: 116 tests passed with one optional
  retained-source skip in 12.155 seconds.

The final complete local repository `ci` tier passed in 454.651 seconds. The
previous Generation 69 checkpoint took 449.318 seconds, a 5.333-second
wall-clock increase in this run. The target kernel, DTB, initramfs, signed
runtime bundle, and raw recovery are unchanged.

Two independent Generation 70 wrapper issuances took 1.858 and 1.631 seconds
and are byte-identical:

- raw recovery SHA-256:
  `5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
- AVB salt:
  `16a5bcc417b28d927996d6bbaeff33b405439f489307137a2944b55751aae787`;
- AVB digest:
  `fb5dc23cd31297fb4fb5546048b9f7d9a97d3fed4f1a4e8ac80d1fd7b289e794`;
- AVB image SHA-256:
  `0f8352ad767ffb77def5e2ac644af994c0df577c89f6051f87e1e8fb49b6635d`;
- generation record SHA-256:
  `5b33f9e4dacf97b29faa1c3170058435903e7a652970aceb1c4c679ef885298a`.

Generation 69 remains consumed and revoked. Generation 70 permits one RAM-only
cycle, must pass exact-head CI before physical execution, and must never be
flashed or retried after claim entry.
