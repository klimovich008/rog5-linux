#!/usr/bin/env python3
"""Enter the fixed V28 claim through the generic exact-record consumer."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PROFILE = "local-image-stage-v1-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-stage-v1-live-v1\n"
    b"candidate=local-image-stage-v1\n"
    b"manifest_sha256="
    b"cef076e59fd114ad2559178f115d2873c3a62912a1a00f5028f6a02e392d7271\n"
    b"state=BOOT_CLAIMED\n"
)


def main() -> int:
    source = Path(__file__).with_name("consume-exact-boot-claim.py")
    spec = importlib.util.spec_from_file_location("rog5_exact_claim_consumer", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("generic exact claim consumer is unavailable")
    consumer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(consumer)
    consumer.CLAIMS[PROFILE] = EXPECTED
    consumer.consume(PROFILE)
    print(f"PASS exact durable BOOT_CLAIMED record entered: {PROFILE}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
