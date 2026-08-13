# Generation 49 read-only UFS enumeration live result

Status: **consumed successfully; exact Alpine recovered; zero phone-storage
mounts and writes; never retry or flash**.

The sole RAM-only cycle loaded release `7.1.4-gae717d919f87` and the exact
`phy_qcom_qmp_ufs`, `ufshcd_core`, `ufshcd_pltfrm`, and `ufs_qcom` module
chain. It discovered the expected 116 physical disk and partition nodes,
resolved userdata as `/dev/sda23` for this boot, and verified every node as
read-only. The target record reported zero block-backed mounts, blocked UFS
queries, blocked SCSI commands, phone-storage mounts, and phone-storage
writes.

Target NCM became stable in 59.377 seconds and remained exact for the complete
12.205-second control window. Exact Alpine fallback returned with boot ID
`4f3808d4-aa3a-4ff8-8632-38f2b46a9957`, maximum temperature 45.5 C, final
host cleanup, and durable `FALLBACK_RETURNED` intent. Pstore and PMIC PON
records were absent, which remains inconclusive. The consumed claim record
SHA-256 is
`15d4eee53a3198c77407b0d0c6bfa2b5671db023ad1eb1e73f1d02642da8678d`.
