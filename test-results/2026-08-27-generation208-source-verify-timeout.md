# Generation 208 source verification timeout

Result: **FAIL-CLOSED; consumed; never retry.**

Mainline reached 117-node UFS, NCM, runtime and key-only SSH in 6.95 seconds.
The clone emitted only `source VERIFY`; the full-tree verifier then exceeded
the 850-second host bound. Exact slot-A fastboot and host cleanup passed.

Softdog was not armed, `clone WRITE` was never emitted, and the p24 write
window was never opened. This is a prewrite source-admission performance
failure, not a UFS write or rollback failure.

The successor must reuse the boot-critical identity verifier already proven by
the successful local-root boots instead of scanning all 37,736 sealed entries
four times around one clone.
