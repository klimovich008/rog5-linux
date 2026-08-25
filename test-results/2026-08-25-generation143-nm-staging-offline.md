# Generation 143 NetworkManager-race staging successor

Result: **CONSUMED BEFORE HOST-KEY READINESS; NO WRITE.** Never retry or flash.

Generation 142 transferred and committed the signed target, then post-COMMIT
cleanup observed its newly enumerated NCM interface before NetworkManager
exposed either managed-state field. The host aborted before target acceptance;
no target stage, SSH transfer, installer, or storage write evidence exists.
Exact fastboot fallback and cleanup passed.

Generation 143 changes only host observation. An exact ROG5 NCM interface with
no managed-state field is recorded as ownership-unknown. Non-final cleanup may
accept it only while no host `/30` escaped; final cleanup still rejects unknown
ownership, and any address on an unknown interface remains fatal. The signed
writer target differs only in its fresh bundle identity.

The NetworkManager ownership classification no longer aborted. The redundant
post-COMMIT cleanup wait still delayed target activation until exact fastboot
returned before host-key readiness. No stage, transfer, installer, or storage
write evidence exists; exact fallback and cleanup passed.
