#!/usr/bin/env python3
"""Consume the exact Generation 153 read-only partial inspection claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-partial-inspect-v44-generation153-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-partial-inspect-v44-generation153-live-v1\n"
    b"candidate=local-image-partial-inspect-v44\n"
    b"manifest_sha256=f5d6229a85f2842cb3c0242f01b7788fc99f6443ade34d330ccd251433856dde\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(
    str(Path(__file__).with_name("consume-exact-boot-claim.py"))
)
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
