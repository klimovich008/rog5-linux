#!/usr/bin/env python3
"""Consume the exact Generation 161 local-root observer claim."""

from pathlib import Path
import runpy

PROFILE = "persistent-root-local-v52-generation161-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=persistent-root-local-v52-generation161-live-v1\n"
    b"candidate=persistent-root-local-v52\n"
    b"manifest_sha256=f70e79df8684b5b17c8ce98a0e16bc7c9fbf82241673f2cb8d12de0d310b7b21\n"
    b"state=BOOT_CLAIMED\n"
)
consumer = runpy.run_path(str(Path(__file__).with_name("consume-exact-boot-claim.py")))
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
