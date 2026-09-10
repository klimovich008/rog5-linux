#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
PROFILE="local-image-stage-glob-v32-generation141-live-v1"
EXPECTED=(b"format=rog5-temporary-boot-consumption-v1\n" b"recovery_profile=local-image-stage-glob-v32-generation141-live-v1\n" b"candidate=local-image-stage-glob-v32\n" b"manifest_sha256=d4fa6160215e68a8919f077894e8b608aa3bf645c93bf2267a90c643c78501d4\n" b"state=BOOT_CLAIMED\n")
def main():
 source=Path(__file__).with_name("consume-exact-boot-claim.py"); spec=importlib.util.spec_from_file_location("c",source)
 if spec is None or spec.loader is None: raise RuntimeError("generic exact claim consumer is unavailable")
 c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c); c.CLAIMS[PROFILE]=EXPECTED; c.consume(PROFILE); print(f"PASS exact durable BOOT_CLAIMED record entered: {PROFILE}"); return 0
if __name__=="__main__":
 try: raise SystemExit(main())
 except (OSError,RuntimeError) as e: print(f"FAIL {e}",file=sys.stderr); raise SystemExit(1)
