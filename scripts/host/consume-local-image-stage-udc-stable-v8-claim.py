#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
PROFILE = "local-image-stage-udc-stable-v8-generation117-live-v1"
EXPECTED = (b"format=rog5-temporary-boot-consumption-v1\n" b"recovery_profile=local-image-stage-udc-stable-v8-generation117-live-v1\n" b"candidate=local-image-stage-udc-stable-v8\n" b"manifest_sha256=f26c2a4c90d19250f9c3475ac5d0008e9d5024cde66a123befc9f545b50a9e09\n" b"state=BOOT_CLAIMED\n")
def main() -> int:
    source = Path(__file__).with_name("consume-exact-boot-claim.py")
    spec = importlib.util.spec_from_file_location("rog5_exact_claim_consumer", source)
    if spec is None or spec.loader is None: raise RuntimeError("generic exact claim consumer is unavailable")
    consumer = importlib.util.module_from_spec(spec); spec.loader.exec_module(consumer)
    consumer.CLAIMS[PROFILE] = EXPECTED; consumer.consume(PROFILE)
    print(f"PASS exact durable BOOT_CLAIMED record entered: {PROFILE}"); return 0
if __name__ == "__main__":
    try: raise SystemExit(main())
    except (OSError, RuntimeError) as error:
        print(f"FAIL {error}", file=sys.stderr); raise SystemExit(1)
