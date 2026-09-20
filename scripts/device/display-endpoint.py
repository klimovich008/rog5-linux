"""Import-only production OLED endpoint; the sole write is verified brightness zero.

An admitted outer owner supplies identity_check(boot), binding exact device,
artifacts, signing and ownership. Local identity checks do not grant admission.
No framebuffer/DRM device open, module loading, reprobe or illumination occurs.
"""
import copy
import hashlib
import os
from pathlib import Path
import re
import stat

SYS = Path('/sys')
PROC = Path('/proc')
DESCRIPTOR = Path('/run/rog5-native-wifi/trial-descriptor')
RELEASE = '7.1.4-rog5-production'
BOARD = 'deeb77287d20393c207469c8debf441c6b451aa1aad3cd764dd4e5e4156cdc57'
NAME = 'ae94000.dsi.0'
PANEL_DT = 'soc@0/display-subsystem@ae00000/dsi@ae94000/panel@0'
DPU_DT = 'soc@0/display-subsystem@ae00000/display-controller@ae01000'
DRIVER = 'panel-ams678-er2-plus-dsc'
BOOT = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
FIELDS = {'boot_id', 'release', 'bundle', 'descriptor_sha256', 'board_dtb_sha256', 'owner'}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def stamp(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid,
            st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def read(path, limit=4096, descriptor=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_uid == 0, 'attribute type/owner')
        if descriptor:
            need(before.st_gid == 0 and not before.st_mode & 0o022
                 and 0 < before.st_size <= limit, 'descriptor metadata')
        raw = os.read(fd, limit + 1)
        need(len(raw) <= limit, 'attribute length')
        need(stamp(before) == stamp(os.fstat(fd)) == stamp(path.lstat()), 'attribute replaced/changed')
        if descriptor:
            need(len(raw) == before.st_size, 'descriptor short read')
        return raw
    finally:
        os.close(fd)


def resolved(path, below):
    result = path.resolve(strict=True)
    need(result.is_relative_to(below) and result != below and result.is_dir(), 'endpoint ancestry')
    return result


def names(path):
    result = []
    with os.scandir(path) as scan:
        for entry in scan:
            need(len(result) < 8, 'endpoint inventory bound')
            result.append(entry.name)
    return result


def link(path, target):
    need(path.is_symlink() and path.resolve(strict=True) == target, 'endpoint link changed: ' + path.name)


class Endpoint:
    NAME = NAME

    def __init__(self, identity_check):
        need(callable(identity_check), 'admitted identity callback required')
        self.identity_check = identity_check
        self._binding = None

    @property
    def SYS(self):
        return SYS

    def identity(self, boot):
        need(type(boot) is str and BOOT.fullmatch(boot), 'expected boot')
        need(os.geteuid() == 0, 'endpoint requires root')
        value = copy.deepcopy(self.identity_check(boot))
        need(type(value) is dict and set(value) == FIELDS
             and all(type(v) is str for v in value.values()), 'admitted identity schema')
        need(value['boot_id'] == boot and value['release'] == RELEASE
             and value['board_dtb_sha256'] == BOARD, 'production artifact identity')
        need(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,95}', value['bundle'])
             and re.fullmatch(r'[0-9a-f]{32}', value['owner'])
             and re.fullmatch(r'[0-9a-f]{64}', value['descriptor_sha256']), 'admitted identity value')
        need(read(PROC/'sys/kernel/random/boot_id', 64) == (boot+'\n').encode(), 'boot changed')
        need(read(PROC/'sys/kernel/osrelease', 96) == (RELEASE+'\n').encode(), 'kernel changed')
        tokens = read(PROC/'cmdline', 8192).split()
        need([t for t in tokens if t.startswith(b'rog5.bundle=')] ==
             [('rog5.bundle='+value['bundle']).encode()], 'bundle command line mismatch')
        need(hashlib.sha256(read(DESCRIPTOR, 1024, descriptor=True)).hexdigest()
             == value['descriptor_sha256'], 'descriptor changed')
        # Copy twice: caller-owned mutable dictionaries cannot change a verified
        # binding retroactively, nor can a returned identity mutate this owner.
        if self._binding is None:
            self._binding = copy.deepcopy(value)
        need(value == self._binding, 'admitted identity changed')
        return value

    def backlight(self, boot):
        who = self.identity(boot)
        root = SYS/'class/backlight'
        need(names(root) == [NAME], 'unexpected backlight inventory')
        p = resolved(root/NAME, SYS/'devices')
        link(root/NAME, p)
        need(p.name == NAME and p.parent.name == 'backlight', 'backlight ancestry')
        panel = p.parent.parent
        need(panel.name == NAME and panel.parent.name == 'ae94000.dsi'
             and panel.parent.parent.name == 'ae00000.display-subsystem', 'panel ancestry')
        link(p/'device', panel)
        driver = SYS/'bus/mipi-dsi/drivers'/DRIVER
        link(panel/'driver', driver); link(driver/NAME, panel)
        dt = SYS/'firmware/devicetree/base'/PANEL_DT
        link(panel/'of_node', dt)
        need(read(dt/'compatible', 128) == b'asus,rog5-ams678-er2\0', 'panel compatible changed')
        need(read(p/'max_brightness', 16) == b'1023\n'
             and read(p/'type', 16) == b'raw\n', 'backlight range/type changed')
        raw = read(p/'brightness', 16)
        need(re.fullmatch(rb'(0|[1-9][0-9]{0,3})\n', raw) and int(raw) <= 1023, 'brightness value')
        for name in ('panel_asus_rog5_ams678', 'qcom_refgen_regulator', 'gpucc_sm8350', 'msm'):
            module = SYS/'module'/name
            need(module.is_dir() and not module.is_symlink(), 'display module absent')
        link(root/NAME, p)
        need(self.identity(boot) == who, 'backlight identity changed')
        return dict(identity=who, path=str(p), panel=str(panel), driver=DRIVER,
                    dt_node=PANEL_DT, maximum=1023, brightness=int(raw))

    def same_file(self, fd, path):
        held, current = os.fstat(fd), path.lstat()
        need(stat.S_ISREG(held.st_mode) and held.st_uid == 0
             and (held.st_dev, held.st_ino, held.st_mode, held.st_uid, held.st_gid)
             == (current.st_dev, current.st_ino, current.st_mode, current.st_uid, current.st_gid),
             'brightness endpoint replaced')

    def blank(self, boot, authorize):
        need(callable(authorize) and authorize() is True, 'blank authorization required')
        before = self.backlight(boot); who = copy.deepcopy(before['identity'])
        path = Path(before['path'])/'brightness'
        fd = os.open(path, os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            self.same_file(fd, path)
            need(authorize() is True, 'blank authorization changed')
            current = self.backlight(boot)
            need({k: v for k, v in current.items() if k != 'brightness'} ==
                 {k: v for k, v in before.items() if k != 'brightness'}, 'backlight changed before blank')
            self.same_file(fd, path)
            need(os.write(fd, b'0\n') == 2, 'short brightness write')
            self.same_file(fd, path)
            after = self.backlight(boot)
            need(after['path'] == before['path'] and after['brightness'] == 0
                 and after['identity'] == who, 'zero brightness readback/identity failed')
            need(authorize() is True, 'blank authorization lost after write')
            need(self.identity(boot) == who, 'blank identity changed')
            return dict(status='PASS_ZERO_BRIGHTNESS_COMMAND', before=before, after=after,
                        write_bytes=2, brightness_readback=0, physical_darkness_verified=False,
                        full_health_verified=False, framebuffer_qualified=False)
        finally:
            os.close(fd)

    def framebuffer(self, boot):
        """Read metadata after default-zero observation; no preparation/scanout proof."""
        bl = self.backlight(boot); who = copy.deepcopy(bl['identity'])
        need(bl['brightness'] == 0, 'framebuffer requires default-zero property')
        inventory = set(names(SYS/'class/graphics'))
        need(inventory <= {'fbcon', 'fb0'} and 'fb0' in inventory, 'unexpected framebuffer inventory')
        master_name = 'ae01000.display-controller'
        master = resolved(SYS/'bus/platform/devices'/master_name, SYS/'devices')
        need(master == Path(bl['panel']).parent.parent/master_name, 'framebuffer DPU ancestry')
        driver = SYS/'bus/platform/drivers/msm_dpu'
        link(master/'driver', driver); link(driver/master_name, master)
        link(master/'of_node', SYS/'firmware/devicetree/base'/DPU_DT)
        p = resolved(SYS/'class/graphics/fb0', SYS/'devices')
        need(p == master/'graphics/fb0', 'framebuffer exact DPU parent')
        link(p/'device', master); link(SYS/'class/graphics/fb0', p)
        need(read(p/'name', 64) == b'msmdrmfb\n', 'framebuffer driver changed')
        need(read(p/'virtual_size', 32) == b'1080,2448\n', 'framebuffer dimensions changed')
        mode = read(p/'modes', 256)
        need(re.fullmatch(rb'[UDVS]:1080x2448p-60\n', mode), 'framebuffer mode changed')
        need(read(p/'bits_per_pixel', 8) == b'32\n', 'framebuffer pixel depth changed')
        after = self.backlight(boot)
        need(after == bl and self.identity(boot) == who, 'framebuffer endpoint/identity changed')
        link(SYS/'class/graphics/fb0', p); link(p/'device', master)
        return dict(status='PASS_FRAMEBUFFER_SYSFS', identity=who, path=str(p), name='msmdrmfb',
                    virtual_size=[1080,2448], mode=mode.decode().strip(), bits_per_pixel=32,
                    physical_scanout_verified=False, pixel_layout_verified=False, device_opened=False)
