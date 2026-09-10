# Live-proven g359 UFS baseline inputs

Result: **HASH-VERIFIED; NO CANDIDATE OR PHONE BOOT.**

The baseline that previously completed the Generation 64 bounded local-image
path is retained exactly:

- Image: `7c89d9a0a7ace2b0057b6cf2b535e134da596d3f3c3c3774c5b64014e32bf234`;
- DTB: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`;
- release: `7.1.4-g359318de534f`;
- `phy-qcom-qmp-ufs.ko`: `58fe4e216d3106dc52842e43f01f968752efba067f70e0635642affb7dd16094`;
- `ufshcd-core.ko`: `1f11fa1b0ce919ef44155dfc2138dcf87369b1b93e7962b98475b0d803081608`;
- `ufshcd-pltfrm.ko`: `f0b981d8ed155dfa4b53c94420689c2a47b1cb62799bb20b8fa12a74baba343f`;
- `ufs-qcom.ko`: `f60a248267e411506cd5b3de9a46e8c38aad480859d38124c0737d23f5eed44f`.

The next target will use these exact UFS inputs, NCM/stage reporting, and no
power-loader or phone-storage path. This separates restoration of the proven
UFS baseline from the later power/charging merge.
