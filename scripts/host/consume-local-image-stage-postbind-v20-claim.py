#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
PROFILE="local-image-stage-postbind-v20-generation129-live-v1"
EXPECTED=(b"format=rog5-temporary-boot-consumption-v1\n" b"recovery_profile=local-image-stage-postbind-v20-generation129-live-v1\n" b"candidate=local-image-stage-postbind-v20\n" b"manifest_sha256=c38000c3818d0c170eca7150517d127b6feef75819072d56f33f40840cdfba6c\n" b"state=BOOT_CLAIMED\n")
def main():
 source=Path(__file__).with_name("consume-exact-boot-claim.py"); spec=importlib.util.spec_from_file_location("c",source)
 if spec is None or spec.loader is None: raise RuntimeError("generic exact claim consumer is unavailable")
 c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c); c.CLAIMS[PROFILE]=EXPECTED; c.consume(PROFILE); print(f"PASS exact durable BOOT_CLAIMED record entered: {PROFILE}"); return 0
if __name__=="__main__":
 try: raise SystemExit(main())
 except (OSError,RuntimeError) as e: print(f"FAIL {e}",file=sys.stderr); raise SystemExit(1)
