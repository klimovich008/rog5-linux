# V25 live result: full charging stack, battery already full

Primary question: can the early-initramfs observer keep side-port NCM stable
while reporting valid battery/UCSI telemetry and net-positive charging?

Result: transport and the complete charging stack passed. Positive battery
current remains unproven because the pack was already 100% and `Full`. V25 is
consumed and must never be retried or flashed. Exact stock slot-A fallback,
host cleanup, and `FALLBACK_RETURNED` intent resolution passed.

Evidence:

- valid stream with 97 progress frames, 249 typed power records, nine host
  transport snapshots, and zero dropped events;
- all seven requested modules loaded and became observable;
- ADSP reached `running` with `adsp.mdt` and PDR observed `charger_pd`;
- PMIC GLINK published alt-mode, power-supply, and UCSI clients;
- Type-C reported device/UFP and sink on the side data port;
- USB was online at 5.038 V, drawing about 209 mA with a 500 mA limit;
- the battery was healthy at 30.0 C, 8.651 V, 100%, and `Full`;
- battery pack current was `0`, voltage changed from 8.651 V to 8.650 V, so
  the strict net-positive classifier correctly reported `absent`;
- no storage access or charging-control write occurred.

Disposition: this is not a kernel failure and needs no code regression. The
next discriminating experiment must use a byte-distinct candidate with the
battery below full; only then can positive pack current be evaluated.
