#!/usr/bin/env python3
"""Consume the exact Generation 163 local-root repeat claim."""

from pathlib import Path
import runpy

PROFILE = "persistent-root-local-v54-generation163-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=persistent-root-local-v54-generation163-live-v1\n"
    b"candidate=persistent-root-local-v54\n"
    b"manifest_sha256=af693192164aa50849639bed0e4cae3349dab3f66ea91f5979933b4b88fd0607\n"
    b"state=BOOT_CLAIMED\n"
)
consumer = runpy.run_path(str(Path(__file__).with_name("consume-exact-boot-claim.py")))
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
