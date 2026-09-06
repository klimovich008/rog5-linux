# Generation 45 recovery-fetch live result

Status: **consumed before bundle transfer or mainline; exact Alpine recovered;
never retry or flash**.

The one-use claim was entered at 11:55:34 CEST. Fastboot accepted the sealed
RAM-only recovery, and exact recovery NCM/ACM continuity was captured by
11:56:05. The bundle server reported both receive-only progress and bundle
listeners ready at 11:56:20, but PREPARE ended at 11:58:32 with:

```text
FAIL recovery refused PREPARE result=FETCH_FAILED state=IDLE last_error=FETCH_CONNECT
```

No bundle bytes were committed, no target kernel executed, and no UFS or phone
storage was enumerated. The initial fallback-profile restore correctly refused
because the privileged controller process remained active after its
unprivileged client died. After that exact process was identified and stopped,
the normal fallback procedure restored the known Alpine identity. Strict
key-only SSH proof completed at 12:01:14; fallback temperature was 39.5 C.

The defect was a recovery/host transport-lifetime failure, not evidence about
the QMP-UFS provider. Commit `1174e92781952c2e82b9051ec81ad4ef11107f68`
adds one bounded 15-second recovery connect, exact peer proof before host
readiness, pidfd-backed controller cancellation, and bounded cleanup before
fallback restoration. Generation 45 is irreversibly consumed.
