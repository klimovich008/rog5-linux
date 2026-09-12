#!/usr/bin/env python3
"""Execute the actual patched UFS predicate offline, without opening devices.

Optional --linux-source checks extraction against an already patched tree.
This documents the present boundary; it does not certify storage containment.
"""
import argparse
import hashlib
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATCHES = ROOT / "patches/linux-7.1.4"
NAME = "ufshcd_discovery_scsi_allowed"


def extract(text):
    return re.search(r"static bool " + NAME + r"\([^\n]+\)\n\{.*?\n\}",
                     text, re.S).group(0) + "\n"


def predicate():
    first = next(PATCHES.glob("0001-*.patch")).read_text()
    source = extract("\n".join(line[1:] for line in first.splitlines()
                               if line.startswith("+") and not line.startswith("+++")))
    counts = []
    for pattern in ("0002-*.patch", "0033-*.patch"):
        count = 0
        for hunk in re.split(r"(?m)^@@[^\n]*\n", next(PATCHES.glob(pattern)).read_text())[1:]:
            lines = []
            for line in hunk.splitlines(keepends=True):
                if not line.startswith((" ", "+", "-")) or line.startswith(("---", "+++", "-- \n")):
                    break
                lines.append(line)
            old = "".join(line[1:] for line in lines if line[0] in " -")
            new = "".join(line[1:] for line in lines if line[0] in " +")
            # Keep only hunks whose complete context belongs to this function.
            # A hunk may begin just before its declaration (0033).
            if NAME in old:
                old = old[old.index("static bool " + NAME):]
                new = new[new.index("static bool " + NAME):]
            if old and old in source and old != new:
                assert source.count(old) == 1
                source = source.replace(old, new)
                count += 1
        counts.append(count)
    assert counts == [2, 1], counts
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linux-source", type=pathlib.Path)
    parser.add_argument("--scratch", type=pathlib.Path, default=ROOT / "build/review-correctness-r1")
    args = parser.parse_args()
    function = predicate()
    if args.linux_source:
        actual = extract((args.linux_source / "drivers/ufs/core/ufshcd.c").read_text())
        assert function == actual, "patched source predicate differs"
    # Constants from Linux v7.1.4 include/scsi/scsi_proto.h. Compare them with
    # the supplied source as well, so these tests execute real opcode bytes.
    opcodes = dict(TEST_UNIT_READY=0x00, REQUEST_SENSE=0x03, READ_6=0x08,
                   INQUIRY=0x12, MODE_SENSE=0x1a, READ_FORMAT_CAPACITIES=0x23,
                   READ_CAPACITY=0x25, READ_10=0x28, LOG_SENSE=0x4d,
                   MODE_SENSE_10=0x5a, REPORT_LUNS=0xa0,
                   SECURITY_PROTOCOL_IN=0xa2, READ_12=0xa8, READ_16=0x88,
                   ZBC_IN=0x95, SERVICE_ACTION_IN_16=0x9e)
    if args.linux_source:
        header = (args.linux_source / "include/scsi/scsi_proto.h").read_text()
        for name, value in opcodes.items():
            found = re.search(r"^#define\s+" + name + r"\s+(0x[0-9a-fA-F]+)", header, re.M)
            assert found and int(found[1], 16) == value, name
    defines = "\n".join(f"#define {name} {value}" for name, value in opcodes.items())
    prelude = """
#include <stdbool.h>
#include <stdio.h>
#define IS_ENABLED(x) (x)
#define DMA_TO_DEVICE 1
#define DMA_BIDIRECTIONAL 0
#define DMA_FROM_DEVICE 2
#define DMA_NONE 3
#define SAI_READ_CAPACITY_16 16
#define ZI_REPORT_ZONES 0
struct scsi_cmnd { unsigned char cmnd[32]; int sc_data_direction; };
"""
    harness = """
int main(void) {
    struct scsi_cmnd c = {0};
    const unsigned char read_opcodes[] = {
        TEST_UNIT_READY, REQUEST_SENSE, INQUIRY, MODE_SENSE, MODE_SENSE_10,
        READ_FORMAT_CAPACITIES, READ_CAPACITY, READ_6, READ_10, READ_12,
        READ_16, REPORT_LUNS, SECURITY_PROTOCOL_IN, LOG_SENSE
    };
    for (int d = 0; d != 4; d++) {
        c.sc_data_direction = d;
        for (int op = 0; op != 256; op++) {
            c.cmnd[0] = op;
            for (int action = 0; action != 32; action++) {
                c.cmnd[1] = action;
                bool got = ufshcd_discovery_scsi_allowed(&c);
                bool want = true;
                if (CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY &&
                    !CONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE) {
                    bool read_opcode = false;
                    for (unsigned int i = 0; i < sizeof(read_opcodes); i++)
                        read_opcode |= op == read_opcodes[i];
                    want = d != DMA_TO_DEVICE && d != DMA_BIDIRECTIONAL &&
                        (read_opcode ||
                         (op == SERVICE_ACTION_IN_16 && action == SAI_READ_CAPACITY_16) ||
                         (op == ZBC_IN && action == ZI_REPORT_ZONES));
                }
                if (got != want) return 1;
            }
        }
    }
    return 0;
}
"""
    args.scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ufs-gate-", dir=args.scratch) as tmp:
        path = pathlib.Path(tmp)
        (path / "gate.c").write_text(prelude + defines + "\n" + function + harness)
        for readonly, write in ((1, 0), (1, 1), (0, 0)):
            subprocess.run(["cc", "-Wall", "-Wextra", "-Werror", "-O2",
                            f"-DCONFIG_SCSI_UFS_DISCOVERY_READ_ONLY={readonly}",
                            f"-DCONFIG_SCSI_UFS_DISCOVERY_DATA_WRITE={write}",
                            str(path / "gate.c"), "-o", str(path / "gate")], check=True, timeout=30)
            subprocess.run([str(path / "gate")], check=True, timeout=5)
            print(f"PASS predicate READ_ONLY={readonly} DATA_WRITE={write}: 32768 cases")
    print("predicate_sha256=" + hashlib.sha256(function.encode()).hexdigest())
    print("PASS exact patched source comparison" if args.linux_source else
          "NOT RUN exact patched source comparison (supply --linux-source)")
    print("NOT RUN physical storage; DATA_WRITE permits all SCSI opcodes at this gate")


if __name__ == "__main__":
    main()
