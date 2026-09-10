# Generation 68 host-departure offline checkpoint

Date: 2026-08-14

Result: **OFFLINE PASS; UNBOOTED.** Generation 68 preserves the exact signed
v45 target bundle and raw recovery proven by Generation 67. It adds only a
bounded host-side correction for the transient recovery-ACM sysfs inspection
race observed after the canonical `CLAIMED` response.

The concrete defect was that a lost follow-up STATUS caused one immediate ACM
inspection. During kexec teardown that inspection could return `inspect-error`
even though recovery was departing, so the host rejected the already-running
target. The correction resamples only `inspect-error` for at most two seconds.
It accepts only `absent` or `product-mismatch`, rejects exact presence and all
other states immediately, and never resends `COMMIT_EXEC`.

Hostile regression coverage proves both the settling case and the bounded
failure case. Focused results were:

- stable recovery controller: 47 tests passed in 0.315 seconds;
- generic exact-record claim consumer: 14 tests passed in 0.274 seconds;
- persistent-root live runner: 13 tests passed in 0.232 seconds;
- exact current Generation 68 profile: passed in 0.526 seconds;
- stable-recovery live gate: passed in 5.176 seconds;
- recovery policy/inventory separation: passed in 0.700 seconds;
- retention executor contract: 8 tests passed in 0.168 seconds; and
- compatibility and source/DTB contracts: 116 tests passed with one optional
  retained-source skip in 12.567 seconds.

The two independent Generation 68 issuances took 2.004 and 1.687 seconds and
were byte-identical. Exact identities are:

- AVB image:
  `f7e42f5292cd41bd25296d6bef4a62d63d227d1961437a125fcbd359838dba4b`;
- raw recovery:
  `5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
- salt:
  `60f40c3dc73ca7293bc43c762624b8392656c5ef7aa75987ea0da491687acedc`;
- AVB digest:
  `52403902907e9651081a9c2d011a95aa0b6ae0cbbfd44b21f8bc3b7c92e348d8`;
- generation record:
  `5da119a026e3e6ba1cb50e98d6e1ac338174c998f0934ad49c47297b9fa4b032`;
- signed target manifest:
  `f039b0a34a6ca3f2447b9499f4c4023fa894f5089e5f346dd852e0f132201949`.

No phone was contacted and no claim was consumed while producing this
checkpoint. The complete repository `ci` tier passed in 449.496 seconds.
Generation 67 remains consumed and revoked. Generation 68 is one RAM-only use,
never flash, and must pass exact-head CI before physical execution.
