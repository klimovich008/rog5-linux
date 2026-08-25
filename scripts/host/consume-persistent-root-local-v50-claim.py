#!/usr/bin/env python3
"""Consume the exact Generation 159 staged-seal local-root claim."""

from pathlib import Path
import runpy

PROFILE = "persistent-root-local-v50-generation159-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=persistent-root-local-v50-generation159-live-v1\n"
    b"candidate=persistent-root-local-v50\n"
    b"manifest_sha256=b5f3c2665a5ac68d255449102c06d210348b4c88c1457c762e31ec58d1febe03\n"
    b"state=BOOT_CLAIMED\n"
)
consumer = runpy.run_path(str(Path(__file__).with_name("consume-exact-boot-claim.py")))
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
