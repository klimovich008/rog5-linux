#!/usr/bin/env python3
"""Consume the exact Generation 162 local-root claim."""

from pathlib import Path
import runpy

PROFILE = "persistent-root-local-v53-generation162-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=persistent-root-local-v53-generation162-live-v1\n"
    b"candidate=persistent-root-local-v53\n"
    b"manifest_sha256=4a55d0f6010779abc0cc7ecc22367a1b75451b2fc3bfb26a4922d02557d316ca\n"
    b"state=BOOT_CLAIMED\n"
)
consumer = runpy.run_path(str(Path(__file__).with_name("consume-exact-boot-claim.py")))
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
