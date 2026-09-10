# Power/USB v13 incident: channel-size hex strings were not canonical width

ID/date: power-usb-v13 / 2026-08-21
Earliest failed stage: accepted-DT channel-0 reservation comparison, before ADSP hardware.
Observed evidence: runtime/SSH, volatile masks, armed rollback, ADSP and QRTR geometry passed; channel-0 failed because expected `0x80000` was encoded as a 31-digit concatenation. Exact fallback passed.
Root cause: proven R7 normalization defect in two static expected hex strings.
Was the candidate consumed?: yes. Phone storage modified: no.
Regression: both channel values are zero-padded to 32 digits; source tests retain exact accepted paths, and the lifecycle requests orderly reboot after success or clean probe refusal.
Successor: V14; kernel, DTB, firmware, recovery, and probe policy are unchanged.
