# V26 live result: sub-full net-positive side charging

Primary question: with the battery below full, can mainline Linux keep side
NCM stable while PMIC GLINK/UCSI reports positive pack current at a safe
temperature?

Result: passed. V26 is consumed and must never be retried or flashed. Exact
stock slot-A fallback, host cleanup, and `FALLBACK_RETURNED` intent resolution
passed.

Evidence:

- valid stream with 96 progress frames, 249 typed power records, 11 host
  transport snapshots, and zero dropped events;
- all seven requested modules loaded; ADSP reached `running`; PMIC GLINK
  published alt-mode, power-supply, and UCSI clients;
- the side port remained device/UFP and sink with USB online;
- USB input measured 4.983 V and 500 mA with a 500 mA input limit;
- battery capacity was 98% and temperature was 30.2 C;
- battery voltage rose from 8.624 V to 8.654 V;
- pack current rose from +10 mA to +154 mA;
- `summary/net-positive=present` and `summary/result=complete`;
- no storage access or charging-control write occurred.

This completes the early power/USB prerequisite. The next candidate should
combine the proven charging stack with the existing read-only local-image Arch
and key-only SSH path before any native partitioning work resumes.
