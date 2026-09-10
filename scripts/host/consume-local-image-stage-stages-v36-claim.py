#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
PROFILE="local-image-stage-stages-v36-generation145-live-v1"
EXPECTED=(b"format=rog5-temporary-boot-consumption-v1\n" b"recovery_profile=local-image-stage-stages-v36-generation145-live-v1\n" b"candidate=local-image-stage-stages-v36\n" b"manifest_sha256=70f3cb11d345e42a961e9b2a0ad4d5a6f43462d106c237dd67f678944a7c805f\n" b"state=BOOT_CLAIMED\n")
def main():
 source=Path(__file__).with_name("consume-exact-boot-claim.py"); spec=importlib.util.spec_from_file_location("c",source)
 if spec is None or spec.loader is None: raise RuntimeError("generic exact claim consumer is unavailable")
 c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c); c.CLAIMS[PROFILE]=EXPECTED; c.consume(PROFILE); print(f"PASS exact durable BOOT_CLAIMED record entered: {PROFILE}"); return 0
if __name__=="__main__":
 try: raise SystemExit(main())
 except (OSError,RuntimeError) as e: print(f"FAIL {e}",file=sys.stderr); raise SystemExit(1)
