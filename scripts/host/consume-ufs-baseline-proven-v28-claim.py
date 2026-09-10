#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
PROFILE="ufs-baseline-proven-v28-generation137-live-v1"
EXPECTED=(b"format=rog5-temporary-boot-consumption-v1\n" b"recovery_profile=ufs-baseline-proven-v28-generation137-live-v1\n" b"candidate=ufs-baseline-proven-v28\n" b"manifest_sha256=914681f89fe74cf657efc33a26c5ee18f21d31940105491c8e57d21621b555c2\n" b"state=BOOT_CLAIMED\n")
def main():
 source=Path(__file__).with_name("consume-exact-boot-claim.py"); spec=importlib.util.spec_from_file_location("c",source)
 if spec is None or spec.loader is None: raise RuntimeError("generic exact claim consumer is unavailable")
 c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c); c.CLAIMS[PROFILE]=EXPECTED; c.consume(PROFILE); print(f"PASS exact durable BOOT_CLAIMED record entered: {PROFILE}"); return 0
if __name__=="__main__":
 try: raise SystemExit(main())
 except (OSError,RuntimeError) as e: print(f"FAIL {e}",file=sys.stderr); raise SystemExit(1)
