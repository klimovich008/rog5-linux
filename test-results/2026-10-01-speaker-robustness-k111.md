# Speaker robustness on main-k111-d10-261001a (2026-10-01 01:16-01:24)

PipeWire S16LE, both CS35L45 amps with the protection DSP (0121-0124), volume 80 %.
- 20 playbacks of a 2 s music snippet with 7 s gaps (PipeWire closes the PCM after 5 s, so every snippet is a full DAPM/DSP start + stop): CSPL_STATE 0 and CSPL_ERRORNO 0 on RCV and SPK during every snippet; 0 kernel lines matching mailbox / "DSP1 event failed" / cs35l45 fail|error.
- 5 min continuous playback: CSPL state/errno 0 throughout, SPK CSPL_TEMPERATURE stable (0x074cf8..0x075c1c, settling at 0x074656), 0 amp errors.
- User: "Speakers work" (and had confirmed full-strength both speakers earlier on 2026-09-30).
Not done: s2idle between streams and a reboot cycle (done implicitly many times today; no amp errors since r204). Result: PASS.
