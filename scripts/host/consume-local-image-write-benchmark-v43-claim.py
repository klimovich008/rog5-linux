#!/usr/bin/env python3
"""Consume the exact Generation 152 local-image write benchmark claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-write-benchmark-v43-generation152-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-write-benchmark-v43-generation152-live-v1\n"
    b"candidate=local-image-write-benchmark-v43\n"
    b"manifest_sha256=65203683173ceacfa412d5dad54662bf46a7aa823016e2129c9aea869f3cf0c6\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(
    str(Path(__file__).with_name("consume-exact-boot-claim.py"))
)
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
