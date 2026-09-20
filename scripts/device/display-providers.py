"""Read-only provider checkpoints for the exact production display successor.

The admitted outer owner supplies identity(boot), including its exact artifact
and device binding. These observations confer no activation authority and prove
neither DMA execution, firmware execution, panel preparation nor physical output.
No driver probe, module insertion, DRM open or sysfs write occurs here.
"""
import copy
import os
from pathlib import Path
import re
import stat

SYS = Path('/sys')
PROC = Path('/proc')
OWNER_UID = 0
RELEASE = '7.1.4-rog5-production'
BOOT = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
# Actual composed-2.dtb, SHA256 deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57.
NODES = {
    '88e7000.regulator': ('regulator@88e7000', b'qcom,sm8350-refgen-regulator\0qcom,sm8250-refgen-regulator\0'),
    '3d90000.clock-controller': ('clock-controller@3d90000', b'qcom,sm8350-gpucc\0'),
    '3da0000.iommu': ('iommu@3da0000', b'qcom,sm8350-smmu-500\0qcom,adreno-smmu\0qcom,smmu-500\0arm,mmu-500\0'),
    '3d00000.gpu': ('gpu@3d00000', b'qcom,adreno-660.1\0qcom,adreno\0'),
    '3d6a000.gmu': ('gmu@3d6a000', b'qcom,adreno-gmu-660.1\0qcom,adreno-gmu\0'),
}
STREAMS = {
    '3d00000.gpu': bytes.fromhex('000000590000000000000400000000590000000100000400'),
    '3d6a000.gmu': bytes.fromhex('000000590000000500000400'),
}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def read(path, limit=256):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        need(stat.S_ISREG(st.st_mode) and st.st_uid == OWNER_UID, 'provider attribute type/owner')
        data = os.read(fd, limit + 1)
        need(len(data) <= limit, 'provider attribute bound')
        return data
    finally:
        os.close(fd)


def entries(path, maximum):
    result = []
    with os.scandir(path) as scan:
        for entry in scan:
            need(len(result) < maximum, 'provider inventory bound')
            result.append(Path(entry.path))
    return result


def node(device):
    name, compatible = NODES[device]
    path = SYS/'bus/platform/devices'/device
    real = path.resolve(strict=True)
    need(real.is_relative_to(SYS/'devices') and real.is_dir(), 'provider device ancestry')
    dt = SYS/'firmware/devicetree/base/soc@0'/name
    need((path/'of_node').is_symlink() and (path/'of_node').resolve(strict=True) == dt,
         'provider DT ancestry')
    need(read(dt/'compatible') == compatible, 'provider compatible changed')
    if device == '3d00000.gpu':
        need(read(dt/'status', 16) == b'okay\0', 'GPU status changed')
    else:
        # Current REFGEN/GPUCC/SMMU/GMU nodes omit status: DT defaults
        # them to enabled. Do not manufacture a nonexistent "okay" property.
        need(not os.path.lexists(dt/'status'), 'provider default-enabled status changed')
    return path, real, dt


def bound(device, driver):
    path, real, dt = node(device)
    expected = SYS/'bus/platform/drivers'/driver
    need((path/'driver').is_symlink() and (path/'driver').resolve(strict=True) == expected,
         'provider driver not bound: ' + device)
    need((expected/device).is_symlink() and (expected/device).resolve(strict=True) == real,
         'provider driver reciprocal membership')
    return path, real, dt


def module(name):
    path = SYS/'module'/name
    need(path.is_dir() and not path.is_symlink(), 'provider module absent: ' + name)


def panel_absent():
    need(not os.path.lexists(SYS/'module/panel_asus_rog5_ams678'), 'panel present before final insertion')
    need(not entries(SYS/'class/backlight', 8), 'premature backlight')
    need(all(p.name == 'fbcon' for p in entries(SYS/'class/graphics', 8)), 'premature framebuffer')


def refgen():
    module('qcom_refgen_regulator')
    _, provider, dt = bound('88e7000.regulator', 'qcom-refgen-regulator')
    need(read(dt/'phandle', 4) == bytes.fromhex('00000081'), 'REFGEN phandle changed')
    host = SYS/'firmware/devicetree/base/soc@0/display-subsystem@ae00000/dsi@ae94000'
    need(read(host/'status', 16) == b'okay\0', 'DSI host status changed')
    need(read(host/'refgen-supply', 4) == bytes.fromhex('00000081'), 'DSI host REFGEN supply changed')
    matches = [p for p in entries(SYS/'class/regulator', 256) if read(p/'name', 128) == b'refgen\n']
    need(len(matches) == 1, 'REFGEN regulator count')
    regulator = matches[0].resolve(strict=True)
    need(regulator != provider and regulator.is_relative_to(provider) and regulator.is_dir(),
         'REFGEN regulator provider ancestry')


def gpu_providers():
    module('gpucc_sm8350')
    bound('3d90000.clock-controller', 'sm8350-gpucc')
    _, _, dt = bound('3da0000.iommu', 'arm-smmu')
    need(read(dt/'phandle', 4) == bytes.fromhex('00000059')
         and read(dt/'#iommu-cells', 4) == bytes.fromhex('00000002'), 'SMMU DT provider changed')
    for device, streams in STREAMS.items():
        path, real, dt = node(device)
        need(read(dt/'iommus', 64) == streams, 'IOMMU streams changed')
        link = path/'iommu_group'
        need(link.is_symlink(), 'IOMMU group absent: ' + device)
        group = link.resolve(strict=True)
        need(group.parent == SYS/'kernel/iommu_groups' and group.is_dir()
             and re.fullmatch(r'0|[1-9][0-9]*', group.name), 'IOMMU group ancestry')
        reciprocal = group/'devices'/device
        need(reciprocal.is_symlink() and reciprocal.resolve(strict=True) == real,
             'IOMMU reciprocal membership')


def checkpoint(phase, boot, identity):
    """Observe one bounded checkpoint; return True only after both identity checks.

    Usage: checkpoint(phase, boot, E.identity). The outer owner must recheck
    health and ownership around actions; this snapshot is not a binding lease.
    GPUCC phase deliberately does not require Adreno/MSM or a GMU driver link.
    """
    need(phase in ('refgen', 'gpucc', 'msm'), 'unknown provider phase')
    need(type(boot) is str and BOOT.fullmatch(boot) and callable(identity), 'provider boot/identity callback')
    before = copy.deepcopy(identity(boot))
    need(type(before) is dict and before.get('release') == RELEASE, 'production identity required')
    need(read(PROC/'sys/kernel/random/boot_id', 64) == (boot+'\n').encode(), 'provider boot changed')
    need(read(PROC/'sys/kernel/osrelease', 96) == (RELEASE+'\n').encode(), 'provider release changed')
    panel_absent()
    refgen()
    if phase in ('gpucc', 'msm'):
        gpu_providers()
    if phase == 'msm':
        module('msm')
        bound('3d00000.gpu', 'adreno')
        # Exact v7.1.4 param_get_bool emits Y/N followed by newline.
        for name, value in (('modeset', b'Y\n'), ('skip_gpu', b'N\n'), ('separate_gpu_kms', b'N\n')):
            need(read(SYS/'module/msm/parameters'/name, 8) == value, 'MSM parameter changed: ' + name)
    panel_absent()
    need(read(PROC/'sys/kernel/random/boot_id', 64) == (boot+'\n').encode(), 'provider boot changed')
    need(identity(boot) == before, 'provider identity changed')
    return True


if __name__ == '__main__':
    raise SystemExit('Import-only read checkpoints; requires admitted outer identity and ownership')
