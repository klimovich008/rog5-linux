#!/usr/bin/env python3
"""Irreversibly enter one repository-owned exact temporary-boot claim."""

from __future__ import annotations

import os
from pathlib import Path
import pwd
import stat
import sys


# This is the repository-owned lookup. A caller selects a reviewed identifier;
# it cannot supply a pathname, candidate, manifest, or expected record bytes.
CLAIMS = {
    'native-wifi-ram-stage-v26': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-stage-v26\n'
        b'candidate=persistent-native-root-wifi-failure-v25\n'
        b'manifest_sha256=596fb9288f38cb56c48d3698bd3b70e549e9fb227ece7aa645a0fafa99ca321e\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'automatic_initramfs_sha256=edc4b3fa28bfbdbb45f9743c0b2fe8915b546a77e4f81e204e4ad0df9f26bdd8\n'
        b'plan_sha256=e78f3f55c5e5579f7c121af0eb887854cd309f592190caca2e42c2d0a8dfc821\n'
        b'controller_sha256=788b5f3122c97b8c8960d931b89245859232ce580019cb528cdc8698624c87ba\n'
        b'stage_collector_sha256=f3fffbb206cfc3769dc86cd88f515655e754fc9aa3dddaec5844f539ca9afc94\n'
        b'management_helper_sha256=571dc2d7ffebfe11c34e2ec96e691d34e1737550c60d61d005b35eec25a4e6f2\n'
        b'loader_helper_sha256=bd9341e3ed294ac7eb23d5319673bc4860144b66a82c2834e7e13a90b4a4bcf8\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-failure-v25': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-failure-v25\n'
        b'candidate=persistent-native-root-wifi-failure-v25\n'
        b'manifest_sha256=596fb9288f38cb56c48d3698bd3b70e549e9fb227ece7aa645a0fafa99ca321e\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'automatic_initramfs_sha256=edc4b3fa28bfbdbb45f9743c0b2fe8915b546a77e4f81e204e4ad0df9f26bdd8\n'
        b'plan_sha256=4ee0a13b0352a976a219fbc047f390c882f254d809368a28e3f9cdf70a53a367\n'
        b'controller_sha256=d07a72f95204bef2b5bfccf95b72ff1a1600424f4b3ae5730e57c3669b2c685c\n'
        b'failure_collector_sha256=784d91061d2f1fd289a5dd2a810f46f851f2c5439814cac62c949723f55c6f9f\n'
        b'loader_helper_sha256=bd9341e3ed294ac7eb23d5319673bc4860144b66a82c2834e7e13a90b4a4bcf8\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-charger-exitrd-v24': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-charger-exitrd-v24\n'
        b'candidate=persistent-native-root-wifi-charger-v22\n'
        b'manifest_sha256=f89172917b75af2187192e948ae92d5550c6d4fe91f6c8b2ab0493a71be25d0f\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'automatic_initramfs_sha256=1d4a8ff015af00da56074ea28545cb6e63b7e72c92800a5565489b647dd3e3d2\n'
        b'plan_sha256=53efe6257259f4c21f4b4c5c792cbbca45970aa0d9055bbe2d86529274c5435a\n'
        b'charger_observer_sha256=5dcb2444da2ef811f9d138b691815e1e548f233f50bde9d91d92eed9c5ea459c\n'
        b'controller_sha256=94c63dea8c67dcb12a667dfb02d0422726704c67c295f6420ed9b624c3de74c6\n'
        b'loader_helper_sha256=bd9341e3ed294ac7eb23d5319673bc4860144b66a82c2834e7e13a90b4a4bcf8\n'
        b'controller_binding_checker_sha256=21cbda3b7d34915dcb0f3d9f45a500dc7ca39ccf8b75d729c64531b5016dee06\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-charger-no-acm-v23': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-charger-no-acm-v23\n'
        b'candidate=persistent-native-root-wifi-charger-v22\n'
        b'manifest_sha256=f89172917b75af2187192e948ae92d5550c6d4fe91f6c8b2ab0493a71be25d0f\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'automatic_initramfs_sha256=1d4a8ff015af00da56074ea28545cb6e63b7e72c92800a5565489b647dd3e3d2\n'
        b'plan_sha256=84b50700861b5994bfd6eeb3a4ca597be9039cfe2679c1045cc251bcf1129292\n'
        b'charger_observer_sha256=5dcb2444da2ef811f9d138b691815e1e548f233f50bde9d91d92eed9c5ea459c\n'
        b'controller_sha256=20b70c90065e2db7adbeebbca4c6bca5f9c0791ab7ccf421acc14ab73b27d443\n'
        b'controller_binding_checker_sha256=21cbda3b7d34915dcb0f3d9f45a500dc7ca39ccf8b75d729c64531b5016dee06\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-charger-v22': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-charger-v22\n'
        b'candidate=persistent-native-root-wifi-charger-v22\n'
        b'manifest_sha256=f89172917b75af2187192e948ae92d5550c6d4fe91f6c8b2ab0493a71be25d0f\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'automatic_initramfs_sha256=1d4a8ff015af00da56074ea28545cb6e63b7e72c92800a5565489b647dd3e3d2\n'
        b'plan_sha256=d7bed7e23552fa4954f7327abcdf4bdef6c12ce3e42a9114f974c8eafafb1281\n'
        b'charger_observer_sha256=5dcb2444da2ef811f9d138b691815e1e548f233f50bde9d91d92eed9c5ea459c\n'
        b'controller_binding_checker_sha256=21cbda3b7d34915dcb0f3d9f45a500dc7ca39ccf8b75d729c64531b5016dee06\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-early-cut-v21': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-early-cut-v21\n'
        b'candidate=persistent-native-root-wifi-early-cut-v21\n'
        b'manifest_sha256=f42315c90cc27ed2c585846330b85041f6554501e2863b58fda2e6a27cf9e99e\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'automatic_initramfs_sha256=1d4a8ff015af00da56074ea28545cb6e63b7e72c92800a5565489b647dd3e3d2\n'
        b'plan_sha256=db55e676d9981f452218bded7820e52d8c95595f7940b1ec930234c99826bed6\n'
        b'gate_helper_sha256=71b5cb4d71a669535820dc04cb3cd10ba4ad62263031b78f3512e484817abbc6\n'
        b'discovery_helper_sha256=8598a29e6070af74e8ea514b8772fca23e42d4ed338c36f533e168d9d4fbff66\n'
        b'controller_binding_checker_sha256=21cbda3b7d34915dcb0f3d9f45a500dc7ca39ccf8b75d729c64531b5016dee06\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-early-cut-v20': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-early-cut-v20\n'
        b'candidate=persistent-native-root-wifi-early-cut-v20\n'
        b'manifest_sha256=e459948131640d19d7f5e03105b00c828177c0a05cf226dcd49c4db480a767ed\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'automatic_initramfs_sha256=1d4a8ff015af00da56074ea28545cb6e63b7e72c92800a5565489b647dd3e3d2\n'
        b'plan_sha256=7f641b6e890d56db9a0156ec58e5d68303fb4bdf5e9ef29c314488a9f4bb4991\n'
        b'gate_helper_sha256=71b5cb4d71a669535820dc04cb3cd10ba4ad62263031b78f3512e484817abbc6\n'
        b'discovery_helper_sha256=8598a29e6070af74e8ea514b8772fca23e42d4ed338c36f533e168d9d4fbff66\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-isolation-v19': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-isolation-v19\n'
        b'candidate=persistent-native-root-wifi-isolation-v19\n'
        b'manifest_sha256=b62f7c1e7b7cd790c64b4e0576345289420699c60324c5f95778997b7620e224\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'automatic_initramfs_sha256=1d4a8ff015af00da56074ea28545cb6e63b7e72c92800a5565489b647dd3e3d2\n'
        b'plan_sha256=82b501fea55dfe11940333224e0f50dbf7161ea7e1de779e38f0d969a833cb99\n'
        b'gate_helper_sha256=71b5cb4d71a669535820dc04cb3cd10ba4ad62263031b78f3512e484817abbc6\n'
        b'runtime_sampler_sha256=436464312e49474a81feb7f30b6cc7cb4faf2e973c17f45451b61f404d9b73ac\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-automatic-v18': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-automatic-v18\n'
        b'candidate=persistent-native-root-wifi-automatic-v18\n'
        b'manifest_sha256=ac1b008b67394a4c4641ec567e10474e484ff90d6382a643f498a9a41e0d88da\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'automatic_initramfs_sha256=1d4a8ff015af00da56074ea28545cb6e63b7e72c92800a5565489b647dd3e3d2\n'
        b'plan_sha256=c9a68d15e67c75787f4f73d5b6a77e4420eace2e1cd9b35c2133fe509fa2e747\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-association-v17': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-association-v17\n'
        b'candidate=persistent-native-root-wifi-association-v17\n'
        b'manifest_sha256=4a0bf5a9d19897eba9a8be545a90dd84b5b0054058a9bc70054c1dc57ff38152\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'probe_package_sha256=b2af8210d0bfb7a0ed7f032eada1c813ec8326fb4a23d16496475903e405863d\n'
        b'plan_sha256=1b65b5bc3f2d1a3d2d6c29670907ed8ec48299aee1efde4aa2ca749bafdeea44\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-association-v16': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-association-v16\n'
        b'candidate=persistent-native-root-wifi-association-v16\n'
        b'manifest_sha256=4fa7001c9f6676b38af0d23815aba15d0ec3e75331660bb7c752751e0de384a5\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'probe_package_sha256=dc5073d59255fe496747b56f2721b3e0fed0de54e68ad46d954293e0397b0b70\n'
        b'plan_sha256=d2cdcb7e6c019e81c7b7e95a84ce5d307f47e0570d3e85d3c4f30dc646de60e8\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-hw11-v15': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-hw11-v15\n'
        b'candidate=persistent-native-root-wifi-hw11-v15\n'
        b'manifest_sha256=0c648f44933251a7e1aa79d07b982e55296a2d20610f8fc59658aa54548db9bd\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'probe_package_sha256=1808b222793e965d085e118f4ded3b5f41cbb340cbed0e72e18c39197c96ca5a\n'
        b'plan_sha256=122601d26ef2294f6140c5a1d937f1ae74c8d4843eeab1df7f072ae8f76e6b4b\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    'native-wifi-ram-late-activate-v14': (
        b'format=rog5-temporary-boot-consumption-v1\n'
        b'recovery_profile=native-wifi-ram-late-activate-v14\n'
        b'candidate=persistent-native-root-wifi-late-activate-v14\n'
        b'manifest_sha256=d1777e938757e047f9a8e5471e00512aae0b98c816f6e6fdaa1f407f7c812a5d\n'
        b'tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n'
        b'probe_package_sha256=7b734ef1b3ed7842790344a03689e557716dad212d7968dc586b43ff7e3a1905\n'
        b'plan_sha256=292c02ae917ba114cc9174136fe090b5dad583bf9d8fa1e7292540236565ccb8\n'
        b'execution=mainline-kexec-ram-only\n'
        b'state=BOOT_CLAIMED\n'
    ),
    "native-wifi-ram-s12-oem-v13": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-s12-oem-v13\n"
        b"candidate=persistent-native-root-wifi-s12-oem-v13\n"
        b"manifest_sha256=8415684bed3b6e8a3def12ba127609c03b94581867d94c302683a51c8a46d5ec\n"
        b"tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n"
        b"module_sha256=0c6d91c195d35e774882d761fddaa2ce9df3117ad7458e66b2eb2241e326e639\n"
        b"plan_sha256=f906f7c9851ae414b1d43e507826e6cf02fb7aede0b4179c216e7896dfd486a2\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-s12-revote-v12": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-s12-revote-v12\n"
        b"candidate=persistent-native-root-wifi-s12-revote-v12\n"
        b"manifest_sha256=cede41c3bb8d306e7a24bc682f8de8608bc9efd826a2036d306631e9b486c99b\n"
        b"tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n"
        b"module_sha256=293b3d9659c8cd4fca592df6513fb4d7f537c8bb9fac208b3aef4efcb2bc44ca\n"
        b"plan_sha256=8753c1883aca9be4ac9cfaeedd882ca8c74d2ce11ce3bc8449ec5e5e4d08e1d1\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-rpmh-readback-v11": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-rpmh-readback-v11\n"
        b"candidate=persistent-native-root-wifi-readback-v11\n"
        b"manifest_sha256=efbe767ee49d7fd721176d4a261dec4e8a5dd5407437d91688c13dbf9ca4f426\n"
        b"tools_manifest_sha256=355b948a36a3be9fdcad7706652e557000c011e347e65d16016fac5155acc123\n"
        b"observers_manifest_sha256=f2989d751dcc3ea98afe1211d151966b34122e07471b1670bbd407f8392a7a2b\n"
        b"plan_sha256=e9108d3758d8bf89a72cfe0a9af113cf7806506042666faeb0651a119d507aed\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-s12-held-v10": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-s12-held-v10\n"
        b"candidate=persistent-native-root-wifi-s12-held-v10\n"
        b"manifest_sha256=e6a02ed3752097f65af0415b9093ced4b049410bb1aeaf7b32cdfc7db045f89e\n"
        b"tools_manifest_sha256=5521436a5b5e6983ca215183ccadcf6cb6740f37cfd04c6bf52681a8be4c26de\n"
        b"modules_sha256=1a2d45fb6b9e8df4b72dfad249a984613e38b0c722134833c076e75f63fecee0\n"
        b"radio_manifest_sha256=2bda1c83e1aaa0a4b9886e538a8ce070464b6f7bb941c9e983597131140de064\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-s12-ready-v9": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-s12-ready-v9\n"
        b"candidate=persistent-native-root-wifi-s12-ready-v9\n"
        b"manifest_sha256=a884d52a301e2d798c479dee544c7c509ea87e9c55d51acf7f07d7578c95ce03\n"
        b"tools_manifest_sha256=5521436a5b5e6983ca215183ccadcf6cb6740f37cfd04c6bf52681a8be4c26de\n"
        b"modules_sha256=1a2d45fb6b9e8df4b72dfad249a984613e38b0c722134833c076e75f63fecee0\n"
        b"radio_manifest_sha256=2bda1c83e1aaa0a4b9886e538a8ce070464b6f7bb941c9e983597131140de064\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-s12-mode-v8": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-s12-mode-v8\n"
        b"candidate=persistent-native-root-wifi-s12-mode-v8\n"
        b"manifest_sha256=c11f856523c7cd288259b229eb77fcafcb9208365d3d77a5365bb7f6335df26b\n"
        b"tools_manifest_sha256=5521436a5b5e6983ca215183ccadcf6cb6740f37cfd04c6bf52681a8be4c26de\n"
        b"modules_sha256=1a2d45fb6b9e8df4b72dfad249a984613e38b0c722134833c076e75f63fecee0\n"
        b"radio_manifest_sha256=2bda1c83e1aaa0a4b9886e538a8ce070464b6f7bb941c9e983597131140de064\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-handoff-v7": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-handoff-v7\n"
        b"candidate=persistent-native-root-wifi-handoff-v7\n"
        b"manifest_sha256=79288e8b8ff9f61ae65554b009d83ec040d7ab982cfbfb2b687edc65113c8000\n"
        b"tools_manifest_sha256=6e185a1784275eb37345cd87231140de6dd212a0706f7de9d1df2ca97d205b3b\n"
        b"modules_sha256=1a2d45fb6b9e8df4b72dfad249a984613e38b0c722134833c076e75f63fecee0\n"
        b"radio_manifest_sha256=2bda1c83e1aaa0a4b9886e538a8ce070464b6f7bb941c9e983597131140de064\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-rpmh-v6": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-rpmh-v6\n"
        b"candidate=persistent-native-root-wifi-rpmh-v6\n"
        b"manifest_sha256=4b2587ec3c5fb169345109a0aff06defa8f65dd180580ce0b05b2f402f33bb37\n"
        b"tools_manifest_sha256=99d9905bf78bf3070085bb7b97814cd6d910c3b11017004654036f7f44c5a395\n"
        b"modules_sha256=1a2d45fb6b9e8df4b72dfad249a984613e38b0c722134833c076e75f63fecee0\n"
        b"radio_manifest_sha256=2bda1c83e1aaa0a4b9886e538a8ce070464b6f7bb941c9e983597131140de064\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-s12-ret-v5": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-s12-ret-v5\n"
        b"candidate=persistent-native-root-wifi-s12-ret-v5\n"
        b"manifest_sha256=a7838892008db35272914d189931217f9cff1c5e830d068d54237ab5ccee93a0\n"
        b"tools_manifest_sha256=c79912d1428871b505eb09d437fd37c6284bfa830fa48b5c4163d5933f77d095\n"
        b"modules_sha256=1a2d45fb6b9e8df4b72dfad249a984613e38b0c722134833c076e75f63fecee0\n"
        b"radio_manifest_sha256=2bda1c83e1aaa0a4b9886e538a8ce070464b6f7bb941c9e983597131140de064\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-rails-v4": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-rails-v4\n"
        b"candidate=persistent-native-root-wifi-rails-v4\n"
        b"manifest_sha256=31250bda28db2738492b9f2aa6e68d2fbd647f37b45cfdf0d8ae59e836cf743e\n"
        b"tools_manifest_sha256=c79912d1428871b505eb09d437fd37c6284bfa830fa48b5c4163d5933f77d095\n"
        b"modules_sha256=1a2d45fb6b9e8df4b72dfad249a984613e38b0c722134833c076e75f63fecee0\n"
        b"radio_manifest_sha256=2bda1c83e1aaa0a4b9886e538a8ce070464b6f7bb941c9e983597131140de064\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-observe-v3": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-observe-v3\n"
        b"candidate=persistent-native-root-wifi-observe-v3\n"
        b"manifest_sha256=20fed0675791be7971a8204beae3382b39e16f80f4ec10c4ad3713f36cbafa20\n"
        b"tools_manifest_sha256=03ed45984f23429a3c499b17d67ab862110f386fae032fc7720d3716d7c1f044\n"
        b"modules_sha256=aa2bfd1398178421eb2b2bb93c3f084c5377bd26bb7ea85e16ee0d52a9cd70f8\n"
        b"radio_manifest_sha256=2bda1c83e1aaa0a4b9886e538a8ce070464b6f7bb941c9e983597131140de064\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-trace-v2": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-trace-v2\n"
        b"candidate=persistent-native-root-wifi-trace-v2\n"
        b"manifest_sha256=30eb98395295f1ee53b2e68c2433598193576e25ad202580270c760e5be084f4\n"
        b"tools_manifest_sha256=7d320311463d5d89a8abd13e123f3bf95109634f93c61d5248180bb13e22d77c\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "native-wifi-ram-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=native-wifi-ram-v1\n"
        b"candidate=persistent-native-root-wifi-v1\n"
        b"manifest_sha256=101ba0acf593d4b97052cc5cdef10409ead0cae1ce4f3a8eced8754e92aecbb4\n"
        b"tools_manifest_sha256=735a589aefe241c7d52c9b41a8ee49f3d5da15fb6fc13b4cce436c02c6600312\n"
        b"execution=mainline-kexec-ram-only\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "stock-charging-memory-fixed-v4-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=stock-charging-memory-fixed-v4-live-v1\n"
        b"candidate=stock-charging-memory-fixed-v4\n"
        b"manifest_sha256="
        b"5b3323d2259160e37c74d2f5b9e972ca6aa5a62d0b596d604b592e7c720313a1\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "stock-charging-memory-fixed-v3-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=stock-charging-memory-fixed-v3-live-v1\n"
        b"candidate=stock-charging-memory-fixed-v3\n"
        b"manifest_sha256="
        b"67ec60a2acf4b600491dfd58d86bea1bf1efeeb3e14914fe0c0452cb1d4caa06\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "stock-charging-explicit-dtb-v2-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=stock-charging-explicit-dtb-v2-live-v1\n"
        b"candidate=stock-charging-explicit-dtb-v2\n"
        b"manifest_sha256="
        b"1df5c41b2a7687bbfd66c201ef9ab164bb77767df41b5cc7c1c05f0b6de03fdf\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "charging-direct-stock-storage-isolated-v3-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=charging-direct-stock-storage-isolated-v3-live-v1\n"
        b"candidate=charging-direct-stock-storage-isolated-v3\n"
        b"manifest_sha256="
        b"713314d66035b37ae4111c1270a39bf2def66afbe41a93029c088856eafdfedb\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "stock-charging-recovery-v1-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=stock-charging-recovery-v1-live-v1\n"
        b"candidate=stock-charging-recovery-v1\n"
        b"manifest_sha256="
        b"3e15b8a23b440d1e58bf05592df7d4e40fb8401d6c80c74ae47e7c93043233b5\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "official-ww33-charging-rescue-v2-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=official-ww33-charging-rescue-v2-live-v1\n"
        b"candidate=official-ww33-charging-rescue-v2\n"
        b"manifest_sha256="
        b"0d3cca84453b17409fefbbda650f5a46836bb0d3b9e105b0581b37f9d7e2011f\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "charging-hybrid-asus-recovery-v2-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=charging-hybrid-asus-recovery-v2-live-v1\n"
        b"candidate=charging-hybrid-asus-recovery-v2\n"
        b"manifest_sha256="
        b"5b1297a25bb7d42cfb2bcafd27c6cc82524fc90401b76d20eef1a48654c58a9f\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "charging-hybrid-asus-recovery-v1-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=charging-hybrid-asus-recovery-v1-live-v1\n"
        b"candidate=charging-hybrid-asus-recovery-v1\n"
        b"manifest_sha256="
        b"07b7754c20f80e573d007f909543a8bd4e61262b89f937f4a39e85624b02638e\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "charging-telemetry-v1-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=charging-telemetry-v1-live-v1\n"
        b"candidate=charging-telemetry-v1\n"
        b"manifest_sha256="
        b"1cfffb18008c07099e2950689043572806bec9318700e95375adc97e2792a800\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "charging-rescue-fastboot-v2-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=charging-rescue-fastboot-v2-live-v1\n"
        b"candidate=charging-rescue-fastboot-v2\n"
        b"manifest_sha256="
        b"95d80165ebf94d6ec6db3a812d8438bb88215254b4292d6f0a8b031f5785fa6f\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "charging-rescue-fastboot-v1-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=charging-rescue-fastboot-v1-live-v1\n"
        b"candidate=charging-rescue-fastboot-v1\n"
        b"manifest_sha256="
        b"1b770a941fa8f4fa11dc7100ddd2313795c5256bab1269db4b7520cc87b62e0d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "userdata-ext4-reset-generation99-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=userdata-ext4-reset-generation99-live-v1\n"
        b"candidate=userdata-ext4-reset-generation99\n"
        b"manifest_sha256="
        b"121adc0df0d2a395685983c573fe37ca25da8a31497c2cf9843e9372ab40a3c5\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-preflight-v4-generation74-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-preflight-v4-generation74-live-v1\n"
        b"candidate=storage-preflight-v4\n"
        b"manifest_sha256="
        b"4ab1ad92b75b975c887bca9b1f4d2617f0d9267dd1b179bb36a0f37c791bff64\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-preflight-current-generation164-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-preflight-current-generation164-live-v1\n"
        b"candidate=storage-preflight-current\n"
        b"manifest_sha256="
        b"8f0f1f5c22231e7c2090299c1b0878b38e09b1839ecaf9cf8cdaf2643e365f6a\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-current-generation165-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-current-generation165-live-v1\n"
        b"candidate=storage-layout-stage1-current\n"
        b"manifest_sha256="
        b"7e3bb797375f5b3a38a4bf76bb57f2a51e344b36a9613e0f25cf2e6c97862215\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-current-generation166-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-current-generation166-live-v1\n"
        b"candidate=storage-layout-stage1-current\n"
        b"manifest_sha256="
        b"cc348a62688135492e36e02604b7a197b081cc671e0c65f48969015414963d88\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-load-backup-generation167-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-load-backup-generation167-live-v1\n"
        b"candidate=storage-layout-stage1-load-backup\n"
        b"manifest_sha256="
        b"f9df41fb58858b9eeed9528650f1461d0a71bd2bb0bd8dd926f740ad65954ccf\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-load-backup-generation168-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-load-backup-generation168-live-v1\n"
        b"candidate=storage-layout-stage1-load-backup\n"
        b"manifest_sha256="
        b"902890bd36b067fd7a262fd71334f418766777b3c8beb47711776b251878c9ea\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-prewrite-observer-generation169-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-prewrite-observer-generation169-live-v1\n"
        b"candidate=storage-layout-stage1-prewrite-observer\n"
        b"manifest_sha256="
        b"c129243271b42c6efb38e3248d5a2ba58b11346720f8c188250efa5f8482e207\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-prewrite-observer-generation170-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-prewrite-observer-generation170-live-v1\n"
        b"candidate=storage-layout-stage1-prewrite-observer\n"
        b"manifest_sha256="
        b"74aaa7c64929f33d1758853c0a191d6e9104f97f7f81e3d13c32095c319c9553\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-config-diag-generation171-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-config-diag-generation171-live-v1\n"
        b"candidate=storage-layout-stage1-config-diag\n"
        b"manifest_sha256="
        b"acee0a4e68fdc3e5e0dd60618719bb25e6a28f2afff602d1f329fead3a6d0b64\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-production-generation172-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-production-generation172-live-v1\n"
        b"candidate=storage-layout-stage1-production\n"
        b"manifest_sha256="
        b"8df8f0152e66180f368c55f31e9b788ea3d120ce87117d3386ef2cd7f46fead0\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-production-generation173-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-production-generation173-live-v1\n"
        b"candidate=storage-layout-stage1-production\n"
        b"manifest_sha256="
        b"09895a561a5086542463ba3fce4ecd4daf632fd8bb311e425ac385060cea3754\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-production-generation174-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-production-generation174-live-v1\n"
        b"candidate=storage-layout-stage1-production\n"
        b"manifest_sha256="
        b"e259fda8dcba14b5cfd1e53adc1dfa2e1782b548f6c7980fde994d9d1412d780\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage1-production-generation175-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage1-production-generation175-live-v1\n"
        b"candidate=storage-layout-stage1-production\n"
        b"manifest_sha256="
        b"7dc95a58248ba2613f09da8a032449e8a8e2f0b635aee66445fd518f4494ae4f\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation176-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation176-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"3ee8244a6ccef26f594cf4aceecb2efc1e27b731fa7bdfc03917602def1b9f8d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation177-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation177-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"8764447295144136ef58f759ca2f118da36025a49bdc2e13c918cd2a97a48381\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation178-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation178-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"5d2a7541fc708a76e19afa2252460f12c9cceb5d766a9f35af07b172b9379d85\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation179-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation179-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"707cae20d3ed363599fbae4174a0081485f26ca213decd4b52a39f24b61dbaaa\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation180-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation180-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"827e5b67f6e2c876af21fbc01c79ee79025f03a59d21639e25df3d8cf0b305a4\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation181-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation181-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"ba2fa54f3e343e3e0a7921281ab5f0f7219723deb6c0b49f687e86f51e272bb8\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation182-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation182-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"35590291bdacb3a8dc198c27a38b8a41333d49d6f72f5c6bb74b6d81bcd65747\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation183-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation183-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"ab476c8cca14aff156943ff72e6fd2bf702df02b2069f191cedc2c93f757d2ba\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation184-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation184-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"c11a8e0ce53f29188b845fdaa471163319e3c02c2771488f06c3f4ddd25548e6\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation185-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation185-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"39ac9cde4c24d0aefca63ff231113bc4b7a6ab72eaa243d83895ccdb934d2659\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation186-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation186-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"faecb6ded2dea36099195dbb0e611e39a47dfef733ba3f94d9f17bd127a2e345\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation187-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation187-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"b9f01bbc792cc41c054fb3c00e39bf8703ab122f74262a3efae83c444e9b987b\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation188-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation188-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"110480d6a5e39cb887f5b707c09931c0b116206433457e420a5085f60e50dd0c\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation189-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation189-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"995836aa417803d584485bc9f996a1162e97446dab29c3d20b41eb0297475c04\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-preflight-generation190-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-preflight-generation190-live-v1\n"
        b"candidate=storage-layout-stage2-preflight\n"
        b"manifest_sha256="
        b"4d23f203add015b888289c915c8defdf2ed0fb34b39adaa9dcb77fe2e5aa9ed7\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-mainline-readonly-v1-generation191-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-mainline-readonly-v1-generation191-live-v1\n"
        b"candidate=storage-layout-stage2-mainline-readonly-v1\n"
        b"manifest_sha256="
        b"75c44d8d069dd79e448fd546aaa3cabb60fa9fada04e8f4310f9d2d04f490e65\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-mainline-readonly-v2-generation192-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-mainline-readonly-v2-generation192-live-v1\n"
        b"candidate=storage-layout-stage2-mainline-readonly-v2\n"
        b"manifest_sha256="
        b"c2b05bfbebb23a8936a54678ce68954a4634d4d966dbc02afe08f253a13058af\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-mainline-readonly-v3-generation193-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-mainline-readonly-v3-generation193-live-v1\n"
        b"candidate=storage-layout-stage2-mainline-readonly-v3\n"
        b"manifest_sha256="
        b"1384d198998f3a055487c747b38f59f0abcfb452049d7b77879f9e0cf1e0380a\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-mainline-clone-v1-generation194-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-mainline-clone-v1-generation194-live-v1\n"
        b"candidate=storage-layout-stage2-mainline-clone-v1\n"
        b"manifest_sha256="
        b"115fc705b9e3eb396ba75760ca0db4bae663ccc95fadc1ead21b84b874d97f06\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-native-postmortem-v1-generation195-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-native-postmortem-v1-generation195-live-v1\n"
        b"candidate=storage-layout-stage2-native-postmortem-v1\n"
        b"manifest_sha256="
        b"307188a2c6d6630e8f5732d7d0b84e297a6dd171cc687100a4714a565b4303f1\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-mainline-clone-v2-generation196-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-mainline-clone-v2-generation196-live-v1\n"
        b"candidate=storage-layout-stage2-mainline-clone-v2\n"
        b"manifest_sha256="
        b"cea60920ad773c05cf85ec396461ecdaa49b14d7ea481bf1f5d5e64ef9233cf3\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-mainline-clone-v3-generation197-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-mainline-clone-v3-generation197-live-v1\n"
        b"candidate=storage-layout-stage2-mainline-clone-v3\n"
        b"manifest_sha256="
        b"dd3455a16c59c61d56d78636c3de94a9230e9d25aa895f36834d9e041dfcd6a3\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-watchdog-probe-v1-generation198-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-watchdog-probe-v1-generation198-live-v1\n"
        b"candidate=storage-layout-stage2-watchdog-probe-v1\n"
        b"manifest_sha256="
        b"a289b401846593d0a6c49250da810c2b2f602596b878f2eb51dcf88ac85afb56\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-mainline-clone-v4-generation199-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-mainline-clone-v4-generation199-live-v1\n"
        b"candidate=storage-layout-stage2-mainline-clone-v4\n"
        b"manifest_sha256="
        b"d941385ab07dfa59142a3ff25eed6329a209b57f58d86157171ed6829e5ce5a3\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-watchdog-lifetime-v1-generation200-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-watchdog-lifetime-v1-generation200-live-v1\n"
        b"candidate=storage-layout-stage2-watchdog-lifetime-v1\n"
        b"manifest_sha256="
        b"8544f57d85d0a75af067fa02ec2747f01a6c0fa6c666b94a5ea0931b61444452\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-watchdog-lifetime-v2-generation201-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-watchdog-lifetime-v2-generation201-live-v1\n"
        b"candidate=storage-layout-stage2-watchdog-lifetime-v2\n"
        b"manifest_sha256="
        b"eaadc07583a675edf398e8d74c73658e3e0783a839fceee3d3510f1a403fe741\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-watchdog-observer-v1-generation202-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-watchdog-observer-v1-generation202-live-v1\n"
        b"candidate=storage-layout-stage2-watchdog-observer-v1\n"
        b"manifest_sha256="
        b"57359d0f1e3a3471c733d79985edca7f271e352fb92cfa81d9fa94b65b76e4d2\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-watchdog-observer-v2-generation203-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"storage-layout-stage2-watchdog-observer-v2-generation203-live-v1\n"
        b"candidate=storage-layout-stage2-watchdog-observer-v2\n"
        b"manifest_sha256="
        b"e984aa8be8b6d3ce24071035edfbd63e73b8fc08a32a2b5c31b9e63a9562cdb1\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-watchdog-mmio-v1-generation204-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-watchdog-mmio-v1-generation204-live-v1\n"
        b"candidate=storage-layout-stage2-watchdog-mmio-v1\n"
        b"manifest_sha256=596df1af9bc9a3cc3710be7802559983849f2ef381a38f105414d2df7e0dcaf8\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-watchdog-mmio-v2-generation205-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-watchdog-mmio-v2-generation205-live-v1\n"
        b"candidate=storage-layout-stage2-watchdog-mmio-v2\n"
        b"manifest_sha256=436f32b67473360af215486d275966cc9b3504dfaf9b6e3a704f5ce8a188dcd0\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-watchdog-mmap-v1-generation206-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-watchdog-mmap-v1-generation206-live-v1\n"
        b"candidate=storage-layout-stage2-watchdog-mmap-v1\n"
        b"manifest_sha256=840e40b59cd266f9545773c971f38e85ded0165349b3b61997dcb1f6f5ee7d97\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-softdog-probe-v1-generation207-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-softdog-probe-v1-generation207-live-v1\n"
        b"candidate=storage-layout-stage2-softdog-probe-v1\n"
        b"manifest_sha256=ec5d0890e83589c9b564908a511d266c873e9d7f5a76d7c16b4024e0c5dd8344\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-softdog-clone-v1-generation208-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-softdog-clone-v1-generation208-live-v1\n"
        b"candidate=storage-layout-stage2-softdog-clone-v1\n"
        b"manifest_sha256=8aab1a2c3eb96fc275caf05f7ea1e99f58197f1c13ecd024bac4ed68d2b277c4\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-softdog-clone-v2-generation209-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-softdog-clone-v2-generation209-live-v1\n"
        b"candidate=storage-layout-stage2-softdog-clone-v2\n"
        b"manifest_sha256=dd9a427854d7ad9a1b762774b3a7ac859c2710bc0b077a0959a819ade274afd1\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-native-postmortem-v2-generation210-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-native-postmortem-v2-generation210-live-v1\n"
        b"candidate=storage-layout-stage2-native-postmortem-v2\n"
        b"manifest_sha256=b4dd750fc3493d13512cd602580913c9cd2944c04de6d7e45c4c6eeaa471bfef\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-softdog-direct-clone-v1-generation211-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-softdog-direct-clone-v1-generation211-live-v1\n"
        b"candidate=storage-layout-stage2-softdog-direct-clone-v1\n"
        b"manifest_sha256=7dec2c357c4f3e229abf0eb8c71cecfdda71008b4ed2238f0b85040e8e19971b\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-direct-chunk1-v1-generation212-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-direct-chunk1-v1-generation212-live-v1\n"
        b"candidate=storage-layout-stage2-direct-chunk1-v1\n"
        b"manifest_sha256=20e853d57dac1a105cb8e26fbb0c0f9a96ccca9f8461c8b84a8a54dae781a1cb\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-direct-extent18-v1-generation213-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-direct-extent18-v1-generation213-live-v1\n"
        b"candidate=storage-layout-stage2-direct-extent18-v1\n"
        b"manifest_sha256=7fde21cb984eade74e369d3da58f12a4e73999d95aeb3582d05cbad304b7a6dd\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-direct-extent19-v1-generation214-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-direct-extent19-v1-generation214-live-v1\n"
        b"candidate=storage-layout-stage2-direct-extent19-v1\n"
        b"manifest_sha256=6459d0b38a3d041d6e696fa5abca22e68fd7d3e6d3eabfcd40a0c25f4788bc9a\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-direct-extent20-seg1-v1-generation215-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-direct-extent20-seg1-v1-generation215-live-v1\n"
        b"candidate=storage-layout-stage2-direct-extent20-seg1-v1\n"
        b"manifest_sha256=140124bc1647493f9c2db270c338397bdb9de71caa9b9e86ca97c760e69def72\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-direct-extent20-seg2-v1-generation216-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-direct-extent20-seg2-v1-generation216-live-v1\n"
        b"candidate=storage-layout-stage2-direct-extent20-seg2-v1\n"
        b"manifest_sha256=774135c181bb33fc8ab799f825f7a9ac97ac11f1d85d8386540348dfad57bf34\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-direct-extent20-seg2a-v1-generation217-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-direct-extent20-seg2a-v1-generation217-live-v1\n"
        b"candidate=storage-layout-stage2-direct-extent20-seg2a-v1\n"
        b"manifest_sha256=9dbc63aebab26ecef036297924dd9b099aacccbec48243943b226e9550cbaa1c\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-direct-extent20-seg2b-v1-generation218-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-direct-extent20-seg2b-v1-generation218-live-v1\n"
        b"candidate=storage-layout-stage2-direct-extent20-seg2b-v1\n"
        b"manifest_sha256=f607405e5fcd04db8f9efc3d42ebcb2202d447eec73b0ca5ebad75c75472f4f2\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-direct-extent20-seg3a-v1-generation219-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-direct-extent20-seg3a-v1-generation219-live-v1\n"
        b"candidate=storage-layout-stage2-direct-extent20-seg3a-v1\n"
        b"manifest_sha256=f95bc32ff18a90f4015f3a51603cb875f46eeeb64c18b6735eccf5947b01014f\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-native-progress-v1-generation220-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-native-progress-v1-generation220-live-v1\n"
        b"candidate=storage-layout-stage2-native-progress-v1\n"
        b"manifest_sha256=c6373ab89d55d494c9e4336200ca9fe3399a05c1eb66908e70a359dd77cbaddb\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-native-verify-v1-generation221-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-native-verify-v1-generation221-live-v1\n"
        b"candidate=storage-layout-stage2-native-verify-v1\n"
        b"manifest_sha256=4767bb1a9b480c1245df34e0f8a926ceaaf9be4686880420d39e6100cbd6c008\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-native-tree-detail-v1-generation222-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-native-tree-detail-v1-generation222-live-v1\n"
        b"candidate=storage-layout-stage2-native-tree-detail-v1\n"
        b"manifest_sha256=907b2447757ad3c0e9d7f3d3ffed0e89e044585fddfbf97b6717a63c99e7b9e9\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-native-ssh-repair-v1-generation223-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-native-ssh-repair-v1-generation223-live-v1\n"
        b"candidate=storage-layout-stage2-native-ssh-repair-v1\n"
        b"manifest_sha256=a510c69ee2f3f1957773428c58fdd1ea20b0f80296f0edfbd2c59d6e5dd46289\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-native-postrepair-verify-v1-generation224-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-native-postrepair-verify-v1-generation224-live-v1\n"
        b"candidate=storage-layout-stage2-native-postrepair-verify-v1\n"
        b"manifest_sha256=7cbec8fedf21126234d164654ac08577be00e0143672fed711874fc6f19b4ba0\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-layout-stage2-native-fsck-v1-generation225-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-layout-stage2-native-fsck-v1-generation225-live-v1\n"
        b"candidate=storage-layout-stage2-native-fsck-v1\n"
        b"manifest_sha256=60db65fda138a675a002f05d49fb9f6bf9e5fabaf4d19c60b13b325415c7f2bd\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-native-root-v1-generation226-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-native-root-v1-generation226-live-v1\n"
        b"candidate=persistent-native-root-v1\n"
        b"manifest_sha256=4dc87544ec35dc9747a9e2a860b93fc4765228d5ab5acb0a54f67dec59fa9af3\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-native-root-v2-generation227-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-native-root-v2-generation227-live-v1\n"
        b"candidate=persistent-native-root-v2\n"
        b"manifest_sha256=6c89b951cc340b4503cc6f6b828f46a04cf6e7508b95dc55a9ca4649a865ea82\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-native-root-v3-generation228-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-native-root-v3-generation228-live-v1\n"
        b"candidate=persistent-native-root-v3\n"
        b"manifest_sha256=b165584d1e335efad249552d9fd3de6554f411149de08aa9dcf9403b608aca1e\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-native-root-v4-generation229-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-native-root-v4-generation229-live-v1\n"
        b"candidate=persistent-native-root-v4\n"
        b"manifest_sha256=5ac2a406ba6e132c3b7488830eda125151e6aa532e4b7867f8b962c22c3051a8\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-native-root-v5-generation230-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-native-root-v5-generation230-live-v1\n"
        b"candidate=persistent-native-root-v5\n"
        b"manifest_sha256=2454db0ff2a558d8764c824f0a6c4d82f0212e39714d540163a9f7a865c5d9da\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-native-root-v6-generation231-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-native-root-v6-generation231-live-v1\n"
        b"candidate=persistent-native-root-v6\n"
        b"manifest_sha256=2725e66cc321d9d019d86a298090f89d5bac68df45fda4d807e12bb35ec0497a\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-native-root-v7-generation232-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-native-root-v7-generation232-live-v1\n"
        b"candidate=persistent-native-root-v7\n"
        b"manifest_sha256=772615e8488932270a9571c93fa75b0cd9dba1f4191d015281a5e35c056ab0ac\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-native-root-v8-generation233-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-native-root-v8-generation233-live-v1\n"
        b"candidate=persistent-native-root-v8\n"
        b"manifest_sha256=7e57c523fa344808fbf551635993d1e712243cf5a93e82ddc83ac9785ca48992\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-native-root-v9-generation234-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-native-root-v9-generation234-live-v1\n"
        b"candidate=persistent-native-root-v9\n"
        b"manifest_sha256=8bc47f291c97c5d52754bd800011864dd385e6993f04d7da1be31b0fc96563e3\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-preflight-v3-generation73-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-preflight-v3-generation73-live-v1\n"
        b"candidate=storage-preflight-v3\n"
        b"manifest_sha256="
        b"1721186c050eb2c2130492217cb1838782d0c63936183968fef716b62bcce4b6\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-preflight-v2-generation72-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-preflight-v2-generation72-live-v1\n"
        b"candidate=storage-preflight-v2\n"
        b"manifest_sha256="
        b"7a436a3716d56536326040fd626c3dc8b760c2ef94ee2d0695e536d2ee779935\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "storage-preflight-v1-generation71-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=storage-preflight-v1-generation71-live-v1\n"
        b"candidate=storage-preflight-v1\n"
        b"manifest_sha256="
        b"a14872f8ca4db705015586f4e199e5bdf607f947f96949eecd35e42a137d19c5\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-early-ssh-v45-generation70-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-early-ssh-v45-generation70-live-v1\n"
        b"candidate=persistent-root-local-image-early-ssh-v45\n"
        b"manifest_sha256="
        b"f039b0a34a6ca3f2447b9499f4c4023fa894f5089e5f346dd852e0f132201949\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-power-usb-v1-generation77-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-power-usb-v1-generation77-live-v1\n"
        b"candidate=persistent-root-power-usb-v1\n"
        b"manifest_sha256="
        b"def5a06936e84c20e8609ae47b3fd8955500bf9c97de724897e52c6b7596d184\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-power-usb-v2-generation78-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-power-usb-v2-generation78-live-v1\n"
        b"candidate=persistent-root-power-usb-v2\n"
        b"manifest_sha256="
        b"ffbdb39dc4c5c959c4214c7987b954f70c63e33ba78305f821ccd07c32fb17a6\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-power-usb-v3-generation79-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-power-usb-v3-generation79-live-v1\n"
        b"candidate=persistent-root-power-usb-v3\n"
        b"manifest_sha256="
        b"d0a1e7b2d9a2fce6d934fc560af466c476f66c1b5ee700dd6efdc6134b6e68eb\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-power-usb-v4-generation80-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-power-usb-v4-generation80-live-v1\n"
        b"candidate=persistent-root-power-usb-v4\n"
        b"manifest_sha256="
        b"2240afeecc90e45e4cf51e94365473a8fbe269731cebc7d1dcba86b7bfd84bf2\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-power-usb-v5-generation81-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-power-usb-v5-generation81-live-v1\n"
        b"candidate=persistent-root-power-usb-v5\n"
        b"manifest_sha256="
        b"5320f9cca8582ca7475f06f0a4c3e25e0b961fd1596077c832e9e622667b19bf\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-power-usb-v6-generation82-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-power-usb-v6-generation82-live-v1\n"
        b"candidate=persistent-root-power-usb-v6\n"
        b"manifest_sha256="
        b"b83d5bacb8b22a7125a33c087b10403cc5e1e9cf35dc5e8ee8d1e48e185e935a\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-power-usb-v7-generation83-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-power-usb-v7-generation83-live-v1\n"
        b"candidate=persistent-root-power-usb-v7\n"
        b"manifest_sha256="
        b"ed43083b35d7f1e4d3c7aa6aa8dacb4ec4e22a2d1e57cd818c4efa20f78080cd\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-power-usb-v8-generation84-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-power-usb-v8-generation84-live-v1\n"
        b"candidate=persistent-root-power-usb-v8\n"
        b"manifest_sha256="
        b"c70ed13367192b26225aa3408bf8cdf4dd3a91da1d3a0c0f5fba59c81be36289\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-early-ssh-v45-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-early-ssh-v45-live-v1\n"
        b"candidate=persistent-root-local-image-early-ssh-v45\n"
        b"manifest_sha256="
        b"f039b0a34a6ca3f2447b9499f4c4023fa894f5089e5f346dd852e0f132201949\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-ufs-detail-v44-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-ufs-detail-v44-live-v1\n"
        b"candidate=persistent-root-local-image-ufs-detail-v44\n"
        b"manifest_sha256="
        b"07e7f72c7c88ea4c081d77e3e561c36278ef0a0273dee6b831ca691f6518ee2e\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-post-write-v43-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-post-write-v43-live-v1\n"
        b"candidate=persistent-root-local-image-post-write-v43\n"
        b"manifest_sha256="
        b"9a57ef7dab71d782bce1893525129e24bd350ee74f24aeabe4ed033af6500d07\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-write-mountpoint-v42-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-write-mountpoint-v42-live-v1\n"
        b"candidate=persistent-root-local-image-write-mountpoint-v42\n"
        b"manifest_sha256="
        b"8b2e95268be4e5e0c65eb9367514bb93ab2c20f38a3848a0986de4fe4336d221\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-write-contained-v41-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-write-contained-v41-live-v1\n"
        b"candidate=persistent-root-local-image-write-contained-v41\n"
        b"manifest_sha256="
        b"5125eddd0aeeb394eea7f24b427b04c1c001276c5b8b2e9dbf544a49c4af0646\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-write-roclass-v40-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-write-roclass-v40-live-v1\n"
        b"candidate=persistent-root-local-image-write-roclass-v40\n"
        b"manifest_sha256="
        b"c284330d2e37cda85d125c098c6acece877ae5e5b69be66edcae326e57ee0f4b\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-write-window-v39-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-write-window-v39-live-v1\n"
        b"candidate=persistent-root-local-image-write-window-v39\n"
        b"manifest_sha256="
        b"35cdc621f44873e42b1b8f2619e383d1a6ed2236f49790fdf36c7435e7883824\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-write-diag-v38-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-write-diag-v38-live-v1\n"
        b"candidate=persistent-root-local-image-write-diag-v38\n"
        b"manifest_sha256="
        b"a12844274c1bc707cee9ae1f3e464e73ffed57adcd477af8f21fbb678173c444\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-write-v37-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-write-v37-live-v1\n"
        b"candidate=persistent-root-local-image-write-v37\n"
        b"manifest_sha256="
        b"5033263fbdb28f795fe92b74a850d3e33119f2d440f9e3999b3ebff3804ef259\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-ed25519-v36-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-ed25519-v36-live-v1\n"
        b"candidate=persistent-root-local-image-ed25519-v36\n"
        b"manifest_sha256="
        b"cc41176df74def7a8953dfcd8621e1d1ad2457eb98a7822a0d40ce50ab8c2be0\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-volatile-v35-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-volatile-v35-live-v1\n"
        b"candidate=persistent-root-local-image-volatile-v35\n"
        b"manifest_sha256="
        b"1def5f276c7d07668ccb90a9ca3ed966660e0af359e49e2f847371b058291e30\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-loader-v34-repeat-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-loader-v34-repeat-live-v1\n"
        b"candidate=persistent-root-local-image-loader-v34\n"
        b"manifest_sha256="
        b"8f2d0d8382a4bf8fd8a18669575af00ec0bfa717c8512db3b59771e4ddce1d79\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-loader-v34-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-loader-v34-live-v1\n"
        b"candidate=persistent-root-local-image-loader-v34\n"
        b"manifest_sha256="
        b"8f2d0d8382a4bf8fd8a18669575af00ec0bfa717c8512db3b59771e4ddce1d79\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-fast-attest-v33-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-fast-attest-v33-live-v1\n"
        b"candidate=persistent-root-local-image-fast-attest-v33\n"
        b"manifest_sha256="
        b"40b5573a4d03f4571ead025083a7989e6ac9288a89b8fe64e4b8439b64aaa42e\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-local-image-v32-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-local-image-v32-live-v1\n"
        b"candidate=persistent-root-local-image-v32\n"
        b"manifest_sha256="
        b"ae1069eb2f85e1b93c24f831e440a54303ca80934864f7fca07afcf34adfaca1\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-ufs-fast-admission-v31-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-ufs-fast-admission-v31-live-v1\n"
        b"candidate=persistent-root-ufs-fast-admission-v31\n"
        b"manifest_sha256="
        b"3cee4b788a2005e90b4c901955a3b1df392cad8b332ea7252580fe1621af1f89\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-ufs-local-root-stage-v30-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-ufs-local-root-stage-v30-live-v1\n"
        b"candidate=persistent-root-ufs-local-root-stage-v30\n"
        b"manifest_sha256="
        b"53afa65bb7134e7d5acccc2126aa8764fd3918c7cab02c61417f4be1572aad27\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-ufs-local-root-v29-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-ufs-local-root-v29-live-v1\n"
        b"candidate=persistent-root-ufs-local-root-v29\n"
        b"manifest_sha256="
        b"ae22914906d63accc893157b51c683f24a3a7e933bba84e13661e664764b9cc6\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-ufs-readonly-enumeration-v28-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-ufs-readonly-enumeration-v28-live-v1\n"
        b"candidate=persistent-root-ufs-readonly-enumeration-v28\n"
        b"manifest_sha256="
        b"9ea343f70b9dfa3658a13d4b1e4dfd2cb841881ec21ce0444cd4422899434045\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-ufs-phy-provider-stage-v27-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-ufs-phy-provider-stage-v27-live-v1\n"
        b"candidate=persistent-root-qmp-ufs-phy-provider-stage-v27\n"
        b"manifest_sha256="
        b"734bd5af4c2f7db1af87e08d0a6c1de0e6d0b013be4901110b892fd065e7656c\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-ufs-phy-creation-stage-v26-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-ufs-phy-creation-stage-v26-live-v1\n"
        b"candidate=persistent-root-qmp-ufs-phy-creation-stage-v26\n"
        b"manifest_sha256="
        b"7f05c55c553e057b418f2adc23f284a907dd9ca693d532228372ad9dfe3e57c4\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-clock-provider-cleanup-stage-v25-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-clock-provider-cleanup-stage-v25-live-v1\n"
        b"candidate=persistent-root-qmp-clock-provider-cleanup-stage-v25\n"
        b"manifest_sha256="
        b"14f9b93e9951d664e036ef189526bef59a167572dd7a23c052ba56aed9fd44cf\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-clock-provider-cleanup-stage-v24-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-clock-provider-cleanup-stage-v24-live-v1\n"
        b"candidate=persistent-root-qmp-clock-provider-cleanup-stage-v24\n"
        b"manifest_sha256="
        b"1bc07a9e0b0acf874f542a84f1d7d8c12505504790bc4da433eb22989b76839b\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1\n"
        b"candidate=persistent-root-qmp-third-clock-runtime-pm-stage-v23\n"
        b"manifest_sha256="
        b"6d8195d2e384558b9ff79a42966fd6841837b38d4b41e83dd745bf554be14dc6\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-second-clock-runtime-pm-stage-v22-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-second-clock-runtime-pm-stage-v22-live-v1\n"
        b"candidate=persistent-root-qmp-second-clock-runtime-pm-stage-v22\n"
        b"manifest_sha256="
        b"052d462cbd7820de331c446598f69224128eced8175665acd703428efb75b371\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-first-clock-runtime-pm-stage-v21-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-first-clock-runtime-pm-stage-v21-live-v1\n"
        b"candidate=persistent-root-qmp-first-clock-runtime-pm-stage-v21\n"
        b"manifest_sha256="
        b"782756493f38d5ea9a634678043214926e9b49ef1ca01ce35e9e41e37169fd4b\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-first-clock-name-stage-v20-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-first-clock-name-stage-v20-live-v1\n"
        b"candidate=persistent-root-qmp-first-clock-name-stage-v20\n"
        b"manifest_sha256="
        b"86c8262c080b0b7254a9175bc8487f464db7a4304ba7879b450a74504a23f713\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-allocation-stage-v19-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-allocation-stage-v19-live-v1\n"
        b"candidate=persistent-root-qmp-allocation-stage-v19\n"
        b"manifest_sha256="
        b"82f38e524cc9f8c65bd5ae225bbb4d0acf4a7ef20021d61af313880c98731835\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-first-fixed-clock-stage-v18-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-first-fixed-clock-stage-v18-live-v1\n"
        b"candidate=persistent-root-qmp-first-fixed-clock-stage-v18\n"
        b"manifest_sha256="
        b"f047d1c0ca676afa62a8a4f30d7b68306622b2eee5fc8dfb8b94e9d71450d3c5\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-fixed-clocks-stage-v17-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-fixed-clocks-stage-v17-live-v1\n"
        b"candidate=persistent-root-qmp-fixed-clocks-stage-v17\n"
        b"manifest_sha256="
        b"abd615f73576c798505464c07a3816da470eee5eeb9c26bc2f8f201f85b44ba4\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-clock-provider-stage-v16-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-clock-provider-stage-v16-live-v1\n"
        b"candidate=persistent-root-qmp-clock-provider-stage-v16\n"
        b"manifest_sha256="
        b"dd832a7655e4a1130b69f07188907f80853004f5e05c150e827a0aee4e1c6447\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-mmio-stage-v15-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-mmio-stage-v15-live-v1\n"
        b"candidate=persistent-root-qmp-mmio-stage-v15\n"
        b"manifest_sha256="
        b"d81ff27520337a91e556018109173d4d14d9c38d0846639f2d056150fa39886d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-regulator-stage-v14-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-regulator-stage-v14-live-v1\n"
        b"candidate=persistent-root-qmp-regulator-stage-v14\n"
        b"manifest_sha256="
        b"03e49b58a082826c1d88ab328c82d6c903c9130e56522fb645eaa3be31eb69a7\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-module-load-control-v13-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-module-load-control-v13-live-v1\n"
        b"candidate=persistent-root-qmp-module-load-control-v13\n"
        b"manifest_sha256="
        b"30fb6c355aa8e34097592cf4b33fe7ae4c4193a4c85ae36744c90778f1818cb7\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-qmp-ufs-phy-control-v12-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-qmp-ufs-phy-control-v12-live-v1\n"
        b"candidate=persistent-root-qmp-ufs-phy-control-v12\n"
        b"manifest_sha256="
        b"330f33a533f8f65e1d32b9e9c90bce10b4301983d7dced88fddfcd8f49e9f294\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-deferred-qmp-ufs-v11-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-deferred-qmp-ufs-v11-live-v1\n"
        b"candidate=persistent-root-deferred-qmp-ufs-v11\n"
        b"manifest_sha256="
        b"e40da74acb705843b0f29c485ca922209e44073f7baab144cbac17c5b285500e\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-deferred-ufs-v10-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-deferred-ufs-v10-live-v1\n"
        b"candidate=persistent-root-deferred-ufs-v10\n"
        b"manifest_sha256="
        b"dc22fde250d88f75859d544737d3703f9a3cf09ca2987eaf213dd744204cd8f7\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-accepted-image-v9-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-accepted-image-v9-live-v1\n"
        b"candidate=persistent-root-accepted-image-v9\n"
        b"manifest_sha256="
        b"90c3cd03ab749003d46f039b31d6bffd51b98d2ea18e858eaddf59cb64c0efbd\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-image-control-v8-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-image-control-v8-live-v1\n"
        b"candidate=persistent-root-image-control-v8\n"
        b"manifest_sha256="
        b"c3cab07c75012941b103a9100e69298ef69de7aa4d73893d6d02ea4602f66f56\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-dtb-control-v7-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-dtb-control-v7-live-v1\n"
        b"candidate=persistent-root-dtb-control-v7\n"
        b"manifest_sha256="
        b"c4cef9e256708d219c7c77f792dbff43336c5d446d0721048ff471b7c05969ee\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-usb-control-v6-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-usb-control-v6-live-v1\n"
        b"candidate=persistent-root-usb-control-v6\n"
        b"manifest_sha256="
        b"33715e0c566a5fc7e771f6b89ca81fd1fe0bb6325b926995a0ba5c5f81a44a5b\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-storage-read-v5-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-storage-read-v5-live-v1\n"
        b"candidate=persistent-root-storage-read-v5\n"
        b"manifest_sha256="
        b"1d64161dd213ced57b6761086629351ba116b30f894aa36afba9480873b4e3ab\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-storage-read-v4-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-storage-read-v4-live-v1\n"
        b"candidate=persistent-root-storage-read-v4\n"
        b"manifest_sha256="
        b"5d835b0986587c7ce174e66ccf03f82bb8c9e581e83384ce93c0ed455d053baa\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-storage-read-v3-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-storage-read-v3-live-v1\n"
        b"candidate=persistent-root-storage-read-v3\n"
        b"manifest_sha256="
        b"3bc4b40f7e230945249db08be19b5791c176e08aeb8b5cfca059f48db5b8ed73\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-storage-read-v2-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-storage-read-v2-live-v1\n"
        b"candidate=persistent-root-storage-read-v2\n"
        b"manifest_sha256="
        b"4b56111b2f40157b5173a24adfedf53341cb243a661fc744410673b1ab7aa567\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "persistent-root-storage-read-v1-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=persistent-root-storage-read-v1-live-v1\n"
        b"candidate=persistent-root-storage-read-v1\n"
        b"manifest_sha256="
        b"f82ea25ffb484668dd56cbd01b33b12062d26d29d40d14000b73afe41c857753\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-core-deployment-v1-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-core-deployment-v1-live-v1\n"
        b"candidate=headless-core-network-root-v2\n"
        b"manifest_sha256="
        b"f3884e6554f3d2c1bb437c45484f658817c006185d6c84a5ac4ef452b01bc02f\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-ssh-iproute-whitespace-v19-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"headless-diagnostic-ssh-iproute-whitespace-v19-live-v1\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-ssh-configfs-link-v18-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"headless-diagnostic-ssh-configfs-link-v18-live-v1\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-ssh-gadget-contract-v17-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"headless-diagnostic-ssh-gadget-contract-v17-live-v1\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-ssh-inert-block-v16-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"headless-diagnostic-ssh-inert-block-v16-live-v1\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-ssh-network-ready-v15-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"headless-diagnostic-ssh-network-ready-v15-live-v1\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-ssh-bootstrap-v14-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"headless-diagnostic-ssh-bootstrap-v14-live-v1\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-ssh-acceptance-v13-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile="
        b"headless-diagnostic-ssh-acceptance-v13-live-v1\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-generation11-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-generation11-live-v1\n"
        b"candidate=headless-netroot-early-diag-v1\n"
        b"manifest_sha256="
        b"4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-generation12-live-v1": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-generation12-live-v1\n"
        b"candidate=headless-netroot-early-diag-v1\n"
        b"manifest_sha256="
        b"4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v2": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v2\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v3": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v3\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v4": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v4\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v5": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v5\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v6": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v6\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v7": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v7\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v8": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v8\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v9": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v9\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "headless-diagnostic-host-rendezvous-v3-live-v10": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=headless-diagnostic-host-rendezvous-v3-live-v10\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v3-execution-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v3-observer-v1\n"
        b"cycle_sha256="
        b"d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078\n"
        b"claim_role=execution\n"
        b"recovery_profile=retention-host-rendezvous-v3-execution-v1\n"
        b"recovery_sha256="
        b"cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d\n"
        b"peer_recovery_sha256="
        b"3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v3-observer-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v3-observer-v1\n"
        b"cycle_sha256="
        b"d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078\n"
        b"claim_role=observer\n"
        b"recovery_profile=retention-host-rendezvous-v3-observer-v1\n"
        b"recovery_sha256="
        b"3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b\n"
        b"peer_recovery_sha256="
        b"cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v3-observer-v2": (
        b"format=rog5-temporary-boot-consumption-v1\n"
        b"recovery_profile=retention-host-rendezvous-v3-observer-v2\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v11-mainline-udc-execution-v2": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v11-mainline-udc-observer-v2\n"
        b"cycle_sha256="
        b"c8f21939d83777ed7cc56782441f1a2f35261dd3746b9aa41d07ce5e1f99e405\n"
        b"claim_role=execution\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v11-mainline-udc-execution-v2\n"
        b"recovery_sha256="
        b"2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb\n"
        b"peer_recovery_sha256="
        b"c416e39445495bb99a8da50da6e5f59d8297779b69f5eada37983f12c735a47e\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"ddccf8025190097219f5a7bd8ef32f2b8ad9feed024ae00ecd07e0f446520034\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v11-mainline-udc-observer-v2": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v11-mainline-udc-observer-v2\n"
        b"cycle_sha256="
        b"c8f21939d83777ed7cc56782441f1a2f35261dd3746b9aa41d07ce5e1f99e405\n"
        b"claim_role=observer\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v11-mainline-udc-observer-v2\n"
        b"recovery_sha256="
        b"c416e39445495bb99a8da50da6e5f59d8297779b69f5eada37983f12c735a47e\n"
        b"peer_recovery_sha256="
        b"2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"ddccf8025190097219f5a7bd8ef32f2b8ad9feed024ae00ecd07e0f446520034\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v12-nfs-xattr-execution-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v12-nfs-xattr-observer-v1\n"
        b"cycle_sha256="
        b"e8195fccf25370f1fa28f015b66f08786df4b7d3f2e0758363c12e396750e53c\n"
        b"claim_role=execution\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v12-nfs-xattr-execution-v1\n"
        b"recovery_sha256="
        b"f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2\n"
        b"peer_recovery_sha256="
        b"9cf1163d1fce5a0c3c8858c5d961d4ad072e83995e0ffe836e987513fb528f69\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"325aa8fb76444b5c01bc517a22ad2483c016837cc1fcb46c203ab5288b916854\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "retention-host-rendezvous-v12-nfs-xattr-observer-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=host-rendezvous-v12-nfs-xattr-observer-v1\n"
        b"cycle_sha256="
        b"e8195fccf25370f1fa28f015b66f08786df4b7d3f2e0758363c12e396750e53c\n"
        b"claim_role=observer\n"
        b"recovery_profile="
        b"retention-host-rendezvous-v12-nfs-xattr-observer-v1\n"
        b"recovery_sha256="
        b"9cf1163d1fce5a0c3c8858c5d961d4ad072e83995e0ffe836e987513fb528f69\n"
        b"peer_recovery_sha256="
        b"f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2\n"
        b"candidate=headless-netroot-early-diag-v2\n"
        b"manifest_sha256="
        b"325aa8fb76444b5c01bc517a22ad2483c016837cc1fcb46c203ab5288b916854\n"
        b"state=BOOT_CLAIMED\n"
    ),
    "local-image-stage-ncm-v9-generation118-observer-v1": (
        b"format=rog5-retention-boot-consumption-v1\n"
        b"retention_profile=local-image-stage-ncm-v9-generation118-postmortem-v1\n"
        b"cycle_sha256="
        b"5b49c45578d578df82422dba92f21d2adc283e526ce16d00c295dbd21364c8c7\n"
        b"claim_role=observer\n"
        b"recovery_profile="
        b"local-image-stage-ncm-v9-generation118-observer-v1\n"
        b"recovery_sha256="
        b"4fef0b9acd38bf06009db1c26314e6ec910b32a06f251012b4efc2910c13325c\n"
        b"peer_recovery_sha256="
        b"6e1fc8bf8e2c5f65d0e391c6b5275c8dceaf9f1c236d9feee23367a27e4ae1dc\n"
        b"candidate=local-image-stage-ncm-v9\n"
        b"manifest_sha256="
        b"ec657d94aea6a71aa7efab80bcddba7794256209609ddc7031bd37764c17a4b5\n"
        b"state=BOOT_CLAIMED\n"
    ),
}


class ClaimError(RuntimeError):
    """The durable claim cannot be safely entered."""


def fail(message: str) -> None:
    raise ClaimError(message)


def expected_record(profile: str) -> bytes:
    try:
        return CLAIMS[profile]
    except KeyError as error:
        raise ClaimError("claim profile is not repository-owned") from error


def canonical_claim_root() -> Path:
    account_home = Path(pwd.getpwuid(os.geteuid()).pw_dir)
    if not account_home.is_absolute():
        fail("lifecycle account home must be absolute")
    try:
        account_home = account_home.resolve(strict=True)
    except OSError as error:
        raise ClaimError("lifecycle account home is unsafe or absent") from error
    return account_home / ".local/state/rog5-temporary-boot-consumption"


def canonical_claim_anchor() -> Path:
    try:
        return Path(pwd.getpwuid(os.geteuid()).pw_dir).resolve(strict=True)
    except OSError as error:
        raise ClaimError("lifecycle claim anchor is unsafe or absent") from error


def anchor_parent_is_replace_protected(
    parent_fd: int,
    metadata: os.stat_result,
) -> bool:
    if metadata.st_uid == os.geteuid():
        return False
    mode = stat.S_IMODE(metadata.st_mode)
    groups = {os.getegid(), *os.getgroups()}
    if metadata.st_gid in groups:
        mode_protected = not mode & stat.S_IWGRP
    else:
        mode_protected = not mode & stat.S_IWOTH
    return mode_protected and not os.access(
        f"/proc/self/fd/{parent_fd}",
        os.W_OK,
        effective_ids=True,
    )


def open_claim_anchor(anchor: Path) -> tuple[int, int]:
    if not anchor.is_absolute():
        fail("lifecycle claim anchor must be absolute")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    parent = anchor.parent
    if parent == anchor:
        fail("lifecycle claim anchor parent is unsafe")
    try:
        parent_fd = os.open(parent, flags | nofollow)
    except OSError as error:
        raise ClaimError("lifecycle claim anchor parent is unsafe") from error
    try:
        parent_metadata = os.fstat(parent_fd)
        opened_parent = Path(f"/proc/self/fd/{parent_fd}").resolve(strict=True)
        if (
            opened_parent != parent
            or not stat.S_ISDIR(parent_metadata.st_mode)
            or not anchor_parent_is_replace_protected(
                parent_fd,
                parent_metadata,
            )
        ):
            fail("lifecycle claim anchor parent is replaceable")
        anchor_fd = os.open(anchor.name, flags | nofollow, dir_fd=parent_fd)
        metadata = os.fstat(anchor_fd)
        opened_path = Path(f"/proc/self/fd/{anchor_fd}").resolve(strict=True)
        if (
            opened_path != anchor
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            fail("lifecycle claim anchor is unsafe or absent")
    except (ClaimError, OSError):
        if "anchor_fd" in locals():
            os.close(anchor_fd)
        os.close(parent_fd)
        raise
    return anchor_fd, parent_fd


def open_claim_root(root: Path) -> int:
    if not root.is_absolute():
        fail("lifecycle claim state root must be absolute")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(root, flags | nofollow)
    except OSError as error:
        raise ClaimError("lifecycle claim root is unsafe or absent") from error
    try:
        metadata = os.fstat(directory_fd)
        opened_path = Path(f"/proc/self/fd/{directory_fd}").resolve(strict=True)
        if (
            opened_path != root
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
        ):
            fail("lifecycle claim root is unsafe or absent")
    except (ClaimError, OSError):
        os.close(directory_fd)
        raise
    return directory_fd


def verify_claim_root_path(root: Path, directory_fd: int) -> None:
    opened = os.fstat(directory_fd)
    try:
        current = os.stat(root, follow_symlinks=False)
    except OSError as error:
        raise ClaimError("lifecycle claim root changed during entry") from error
    if (
        current.st_dev != opened.st_dev
        or current.st_ino != opened.st_ino
        or not stat.S_ISDIR(current.st_mode)
        or current.st_uid != os.geteuid()
        or stat.S_IMODE(current.st_mode) != 0o700
    ):
        fail("lifecycle claim root changed during entry")


def verify_claim_anchor_path(
    anchor: Path,
    anchor_fd: int,
    parent_fd: int,
) -> None:
    opened = os.fstat(anchor_fd)
    opened_parent = os.fstat(parent_fd)
    try:
        current_parent = os.stat(anchor.parent, follow_symlinks=False)
        current = os.stat(
            anchor.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except OSError as error:
        raise ClaimError("lifecycle claim anchor changed during entry") from error
    if (
        current_parent.st_dev != opened_parent.st_dev
        or current_parent.st_ino != opened_parent.st_ino
        or not stat.S_ISDIR(current_parent.st_mode)
        or not anchor_parent_is_replace_protected(parent_fd, current_parent)
        or current.st_dev != opened.st_dev
        or current.st_ino != opened.st_ino
        or not stat.S_ISDIR(current.st_mode)
        or current.st_uid != os.geteuid()
        or stat.S_IMODE(current.st_mode) & 0o022
    ):
        fail("lifecycle claim anchor changed during entry")


def verify_source_path(
    record_name: str,
    directory_fd: int,
    source_fd: int,
    expected: bytes,
) -> None:
    try:
        named = os.stat(
            record_name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except OSError as error:
        raise ClaimError(
            "source BOOT_CLAIMED record changed during entry"
        ) from error
    opened = os.fstat(source_fd)
    if (
        named.st_dev != opened.st_dev
        or named.st_ino != opened.st_ino
        or not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != os.geteuid()
        or stat.S_IMODE(opened.st_mode) != 0o600
        or opened.st_nlink != 1
    ):
        fail("source BOOT_CLAIMED record changed during entry")
    os.lseek(source_fd, 0, os.SEEK_SET)
    content = os.read(source_fd, len(expected) + 1)
    if content != expected or os.read(source_fd, 1):
        fail("source BOOT_CLAIMED record changed during entry")


def existing_guard_is_exact(
    guard_name: str,
    anchor_fd: int,
    expected: bytes,
) -> bool:
    flags = os.O_RDONLY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        guard_fd = os.open(guard_name, flags | nofollow, dir_fd=anchor_fd)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise ClaimError("global BOOT_CLAIMED guard is unsafe") from error
    try:
        opened = os.fstat(guard_fd)
        named = os.stat(guard_name, dir_fd=anchor_fd, follow_symlinks=False)
        content = os.read(guard_fd, len(expected) + 1)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or named.st_dev != opened.st_dev
            or named.st_ino != opened.st_ino
            or content != expected
            or os.read(guard_fd, 1)
        ):
            fail("global BOOT_CLAIMED guard is unsafe")
    finally:
        os.close(guard_fd)
    return True


def create_entered_record(
    entered_name: str,
    directory_fd: int,
    expected: bytes,
) -> int:
    flags = os.O_RDWR | os.O_CLOEXEC | os.O_CREAT | os.O_EXCL
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        entered_fd = os.open(
            entered_name,
            flags | nofollow,
            0o600,
            dir_fd=directory_fd,
        )
    except FileExistsError as error:
        raise ClaimError(
            "durable BOOT_CLAIMED record is already entered"
        ) from error
    except OSError as error:
        raise ClaimError("cannot enter durable BOOT_CLAIMED record") from error
    try:
        os.fchmod(entered_fd, 0o600)
        remaining = memoryview(expected)
        while remaining:
            written = os.write(entered_fd, remaining)
            if written <= 0:
                fail("cannot write entered BOOT_CLAIMED record")
            remaining = remaining[written:]
        os.fsync(entered_fd)
        os.lseek(entered_fd, 0, os.SEEK_SET)
        metadata = os.fstat(entered_fd)
        content = os.read(entered_fd, len(expected) + 1)
        named = os.stat(
            entered_name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or named.st_dev != metadata.st_dev
            or named.st_ino != metadata.st_ino
            or content != expected
            or os.read(entered_fd, 1)
        ):
            fail("entered BOOT_CLAIMED record is not exact")
    except Exception:
        os.close(entered_fd)
        raise
    return entered_fd


def verify_entered_file(
    name: str,
    directory_fd: int,
    expected: bytes,
    label: str,
) -> None:
    flags = os.O_RDONLY | os.O_CLOEXEC
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as error:
        raise ClaimError(f"{label} is unsafe or absent") from error
    try:
        opened = os.fstat(descriptor)
        named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        content = os.read(descriptor, len(expected) + 1)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or named.st_dev != opened.st_dev
            or named.st_ino != opened.st_ino
            or content != expected
            or os.read(descriptor, 1)
        ):
            fail(f"{label} is not exact")
    finally:
        os.close(descriptor)


def verify_entered(profile: str, root: Path | None = None) -> None:
    expected = expected_record(profile)
    record_name = f"{profile}.record"
    entered_name = f"{record_name}.entered"
    if root is None:
        root = canonical_claim_root()
        anchor = canonical_claim_anchor()
    else:
        anchor = root.parent
    guard_name = f".rog5-temporary-boot-consumption.{profile}.entered"
    anchor_fd, anchor_parent_fd = open_claim_anchor(anchor)
    try:
        directory_fd = open_claim_root(root)
    except Exception:
        os.close(anchor_fd)
        os.close(anchor_parent_fd)
        raise
    try:
        try:
            os.stat(record_name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise ClaimError("source BOOT_CLAIMED record is unsafe") from error
        else:
            fail("source BOOT_CLAIMED record still exists")
        verify_entered_file(
            entered_name,
            directory_fd,
            expected,
            "entered BOOT_CLAIMED record",
        )
        if not existing_guard_is_exact(guard_name, anchor_fd, expected):
            fail("global BOOT_CLAIMED guard is absent")
        verify_claim_root_path(root, directory_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
    finally:
        os.close(directory_fd)
        os.close(anchor_fd)
        os.close(anchor_parent_fd)


def consume(profile: str, root: Path | None = None) -> None:
    expected = expected_record(profile)
    record_name = f"{profile}.record"
    entered_name = f"{record_name}.entered"
    if root is None:
        root = canonical_claim_root()
        anchor = canonical_claim_anchor()
    else:
        anchor = root.parent
    guard_name = f".rog5-temporary-boot-consumption.{profile}.entered"
    anchor_fd, anchor_parent_fd = open_claim_anchor(anchor)
    try:
        directory_fd = open_claim_root(root)
    except Exception:
        os.close(anchor_fd)
        os.close(anchor_parent_fd)
        raise
    flags = os.O_RDONLY | os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    source_fd = -1
    entered_fd = -1
    guard_fd = -1
    try:
        if existing_guard_is_exact(guard_name, anchor_fd, expected):
            fail("durable BOOT_CLAIMED record is already entered")

        try:
            os.stat(entered_name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        except OSError as error:
            raise ClaimError("entered BOOT_CLAIMED record is unsafe") from error
        else:
            fail("durable BOOT_CLAIMED record is already entered")

        try:
            source_fd = os.open(
                record_name,
                flags | nofollow,
                dir_fd=directory_fd,
            )
        except OSError as error:
            raise ClaimError(
                "durable BOOT_CLAIMED record is unsafe or absent"
            ) from error
        metadata = os.fstat(source_fd)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
        ):
            fail("durable BOOT_CLAIMED record is unsafe or absent")
        content = os.read(source_fd, len(expected) + 1)
        if content != expected or os.read(source_fd, 1):
            fail("durable BOOT_CLAIMED record is not exact")

        verify_source_path(record_name, directory_fd, source_fd, expected)
        verify_claim_root_path(root, directory_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
        guard_fd = create_entered_record(
            guard_name,
            anchor_fd,
            expected,
        )
        os.fsync(anchor_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
        entered_fd = create_entered_record(
            entered_name,
            directory_fd,
            expected,
        )
        os.fsync(directory_fd)

        verify_source_path(
            record_name,
            directory_fd,
            source_fd,
            expected,
        )
        try:
            os.unlink(record_name, dir_fd=directory_fd)
        except OSError as error:
            raise ClaimError(
                "durable BOOT_CLAIMED record entered but source cleanup failed"
            ) from error
        if os.fstat(source_fd).st_nlink != 0:
            fail("source BOOT_CLAIMED record changed during entry")
        os.fsync(directory_fd)
        verify_claim_root_path(root, directory_fd)
        verify_claim_anchor_path(anchor, anchor_fd, anchor_parent_fd)
    finally:
        if entered_fd >= 0:
            os.close(entered_fd)
        if guard_fd >= 0:
            os.close(guard_fd)
        if source_fd >= 0:
            os.close(source_fd)
        os.close(directory_fd)
        os.close(anchor_fd)
        os.close(anchor_parent_fd)


def main() -> int:
    if len(sys.argv) == 2:
        profile = sys.argv[1]
        consume(profile)
        print(f"PASS exact durable BOOT_CLAIMED record entered: {profile}")
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "--verify-entered":
        profile = sys.argv[2]
        verify_entered(profile)
        print(f"PASS exact durable BOOT_CLAIMED record verified: {profile}")
        return 0
    fail(
        "exact-record claim consumer requires a repository-owned profile "
        "or --verify-entered PROFILE"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ClaimError, OSError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
