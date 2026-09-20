"""Offline successor for the current production display module cohort.

Import-only: no CLI, auto-discovery, boot, reprobe, unload or retries. The enclosing
admitted owner must supply its exact production endpoint, firmware input owner,
read-only provider checkpoints, durable entry, health and independent cleanup.
No matching live endpoint/admission composition is issued by this source change.
The old sealed controller is deliberately not imported or altered.
"""
import hashlib
import os
from pathlib import Path
import selectors
import stat
import subprocess
import time

PAYLOAD = Path('/run/rog5-native-wifi')
RELEASE = '7.1.4-rog5-production'
HELPER = ('module-once', 219912, '744361997ed149b6bae2df502f0d3bcf849de1a3f0bd70f450e8cc82adbac939', 0o755)
INSERT_SECONDS = 5.0
DISCOVERY_SECONDS = 5.0
TOTAL_SECONDS = 85.0
clock = time.monotonic
pause = time.sleep
# Pins from the qualified inert production archive. Activation order differs:
# MSM registers Adreno before the panel is permitted to complete the component
# master. GPUCC/SMMU checks do not require Adreno before MSM exists.
MODULES = (
    ('qcom_refgen_regulator', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/regulator/qcom-refgen-regulator.ko', 10968, '10b6ab323bde093168d622139c505d77bb197aed45b75c4a2c23fcea9c0788c0'),
    ('gpucc_sm8350', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/clk/qcom/gpucc-sm8350.ko', 23680, 'f6655f793067d2f968e90e3d9e25df00a2c9ab07c4305ade6da87257ff067f94'),
    ('drm_kms_helper', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/gpu/drm/drm_kms_helper.ko', 266248, '58c42af96596f2d3f8de1872c6fff12ecbee4281dbc08a8c26753fc38a848560'),
    ('cec', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/media/cec/core/cec.ko', 75920, '9768836a5ced017d5de6ede06198c2307d7bb8ab1033d3864d6efc329cda85f8'),
    ('drm_display_helper', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/gpu/drm/display/drm_display_helper.ko', 287712, 'c898ec6877e0cc8f8982d95eda43a1f88f32dee688544a32bebf04fb42680f85'),
    ('drm_client_lib', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/gpu/drm/clients/drm_client_lib.ko', 11752, '4bb90e10be99f08c26d133d88c503f008aa34e1fa45fa4f4b4a88cf447b46b85'),
    ('drm_dp_aux_bus', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/gpu/drm/display/drm_dp_aux_bus.ko', 14256, '354572b78d90c289306222dd97361fdfdce30be5743c3048c0ebc5eef27b7932'),
    ('drm_exec', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/gpu/drm/drm_exec.ko', 11296, '0d229a2ba442285c46c6781c6bd5bd1c51e1b14f160e70d43fde5b43abb3dfb2'),
    ('drm_gpuvm', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/gpu/drm/drm_gpuvm.ko', 49896, 'd0fa46f8efc6da80351850598b618ad5ba2d864d231b461ab3aad00dacc8539c'),
    ('gpu_sched', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/gpu/drm/scheduler/gpu-sched.ko', 79352, 'cca61e1ac9bb3f148e4627fdd6a38e9f3d266e181001171aca634f50f30b4ae4'),
    ('mdt_loader', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/soc/qcom/mdt_loader.ko', 11088, '24c4d100d127a23354751f4e44b1d4cd1af206862627de863a60436ee84f2232'),
    ('ubwc_config', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/soc/qcom/ubwc_config.ko', 19840, 'a34259b12cd3781037f8179c3793eea4956d54f0abbc42eb7dbad43e2e0cec8a'),
    ('msm', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/gpu/drm/msm/msm.ko', 2097264, '39980ab3f730c680e493dade37316133cd6d5047a55a49664a9ead39a822e703'),
    ('panel_asus_rog5_ams678', 'modules/lib/modules/7.1.4-rog5-production/kernel/drivers/gpu/drm/panel/panel-asus-rog5-ams678.ko', 23128, '79dc4d21db7726fd939acd10d35ce0f681fee07a847074734485c11008d72994'),
)

def need(ok, why):
    if not ok:
        raise ValueError(why)

def stamp(st):
    return (st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid,
            st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)

def open_directory(path):
    """Hold each no-symlink directory; root-sticky /run protects root children."""
    need(path.is_absolute() and '..' not in path.parts, 'payload directory path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    current = Path('/')
    try:
        for part in path.parts[1:]:
            current = current / part
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            try:
                st = os.fstat(child)
                named = os.stat(part, dir_fd=fd, follow_symlinks=False)
                mode = stat.S_IMODE(st.st_mode)
                sticky_run = current == Path('/run') and mode == 0o1777
                need(st.st_uid == st.st_gid == 0
                     and (not mode & 0o022 or sticky_run), 'payload directory owner/mode')
                need((st.st_dev, st.st_ino, st.st_mode, st.st_uid, st.st_gid)
                     == (named.st_dev, named.st_ino, named.st_mode, named.st_uid, named.st_gid),
                     'payload directory replaced')
            except BaseException:
                os.close(child)
                raise
            os.close(fd)
            fd = child
        result, fd = fd, None
        return result
    finally:
        if fd is not None:
            os.close(fd)

def exact_file(directory, name, size, pin, mode):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
    try:
        st = os.fstat(fd)
        need(stat.S_ISREG(st.st_mode) and st.st_uid == st.st_gid == 0
             and st.st_nlink == 1 and st.st_size == size
             and stat.S_IMODE(st.st_mode) == mode, 'payload file metadata: '+name)
        digest = hashlib.sha256()
        total = 0
        while data := os.read(fd, 65536):
            total += len(data)
            need(total <= size, 'payload grew')
            digest.update(data)
        need(total == size and digest.hexdigest() == pin, 'payload digest: '+name)
        need(stamp(st) == stamp(os.fstat(fd))
             == stamp(os.stat(name, dir_fd=directory, follow_symlinks=False)), 'payload replaced: '+name)
        os.lseek(fd, 0, os.SEEK_SET)
        result, fd = fd, None
        return result, stamp(st)
    finally:
        if fd is not None:
            os.close(fd)

def command(helper_fd, directory_fd, filename):
    # module-once rejects a final symlink. Its leaf is an actual regular file
    # below our held directory descriptor, not a /proc/.../fd module symlink.
    return ['/proc/self/fd/'+str(helper_fd), '/proc/self/fd/'+str(directory_fd)+'/'+filename]

def insert(helper_fd, directory_fd, filename, authorize, observe=None):
    start = clock()
    child = None
    streams = {'stdout': bytearray(), 'stderr': bytearray()}
    error = None
    try:
        need(authorize() is True, 'module authorization before spawn')
        child = subprocess.Popen(command(helper_fd, directory_fd, filename), stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 pass_fds=(helper_fd, directory_fd),
                                 env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
        with selectors.DefaultSelector() as selector:
            for name in streams:
                stream = getattr(child, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            deadline = start+INSERT_SECONDS
            while selector.get_map() or child.poll() is None:
                if observe is not None:
                    observe()
                need(clock() < deadline, 'module insertion deadline')
                need(authorize() is True, 'module authorization during insertion')
                for key, _ in selector.select(min(.05, max(0, deadline-clock()))):
                    data = os.read(key.fd, 4097)
                    if not data:
                        selector.unregister(key.fileobj)
                    else:
                        need(len(streams[key.data])+len(data) <= 4096, 'module output bound')
                        streams[key.data].extend(data)
            child.wait(timeout=max(.001, deadline-clock()))
            need(child.returncode == 0 and not any(streams.values()), 'module insertion exit/output')
    except Exception as exc:
        error = dict(type=type(exc).__name__, reason=str(exc)[:512])
    finally:
        if child is not None:
            try:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=2)
            except Exception as exc:
                error = dict(type=type(exc).__name__, reason='module child cleanup: '+str(exc)[:400], prior=error)
            finally:
                for name in streams:
                    getattr(child, name).close()
    return dict(status='PASS_INSERTION' if error is None else 'FAIL_INSERTION',
                filename=filename, seconds=clock()-start, pid=child.pid if child else None,
                returncode=child.returncode if child else None,
                reaped=child is not None and child.poll() is not None,
                stdout=bytes(streams['stdout']).decode(errors='replace'),
                stderr=bytes(streams['stderr']).decode(errors='replace'), error=error,
                retry_allowed=False)

class LoadError(ValueError):
    def __init__(self, evidence):
        super().__init__('OLED module load failed: '+str(evidence))
        self.evidence = evidence

class Loader:
    """One bounded attempt; callbacks never confer admission by themselves.

    checkpoint(phase, boot) must return True after exact, read-only observations:
    refgen: DSI-host REFGEN provider bound;
    gpucc: GPUCC and SMMU bound, GPU/GMU reciprocal groups, no Adreno required;
    msm: Adreno bound, both groups and default shared-DRM parameters verified.
    No checkpoint may perform reprobe, DRM open or retry. These target adapters
    still require an exact admitted composition; tests supply explicit fixtures.
    """
    def __init__(self, endpoint, firmware_factory, checkpoint):
        self.endpoint = endpoint
        self.firmware_factory = firmware_factory
        self.checkpoint = checkpoint
        self.attempted = False

    def load_once(self, boot, authorize, enter, cleanup_authorize):
        E = self.endpoint
        start = clock()
        fds = []; rows = []; inventory = []; checkpoints = []; preconsumer_checks = []
        firmware = None
        entered = panel_attempted = False
        blank = cleanup_blank = endpoint = error = registration = None
        cleanup_errors = []
        identity = None

        def gate():
            need(clock() < start + TOTAL_SECONDS, 'production load total deadline')
            need(E.identity(boot) == identity, 'production boot identity changed')
            need(authorize() is True and cleanup_authorize() is True,
                 'production health/monitor/cleanup ownership lost')
            if firmware is not None:
                need(firmware.check() is True, 'firmware input check failed')
            return True

        def zero():
            receipt = E.blank(boot, cleanup_authorize)
            need(type(receipt) is dict and receipt.get('status') == 'PASS_ZERO_BRIGHTNESS_COMMAND'
                 and type(receipt.get('write_bytes')) is int and receipt['write_bytes'] == 2
                 and type(receipt.get('brightness_readback')) is int and receipt['brightness_readback'] == 0
                 and receipt.get('physical_darkness_verified') is False,
                 'zero brightness command receipt missing or invalid')
            return receipt

        def observe_panel():
            nonlocal registration
            if os.path.lexists(E.SYS/'class/backlight'/E.NAME):
                need(cleanup_authorize() is True, 'module cleanup ownership lost')
                registration = E.backlight(boot)
                need(registration['brightness'] == 0, 'panel did not register default-dark')

        try:
            need(not self.attempted, 'production load object already attempted')
            need(all(callable(f) for f in (authorize, enter, cleanup_authorize,
                                          self.firmware_factory, self.checkpoint)),
                 'production load callbacks required')
            identity = E.identity(boot)
            need(identity['release'] == RELEASE, 'production release required')
            gate()
            for name, *_ in MODULES:
                need(not os.path.lexists(E.SYS/'module'/name), 'production module already present: '+name)
            need(not list((E.SYS/'class/backlight').iterdir())
                 and not os.path.lexists(E.SYS/'class/graphics/fb0'), 'display already active')
            firmware = self.firmware_factory()
            need(firmware is not None and callable(getattr(firmware, 'check', None))
                 and callable(getattr(firmware, 'close', None)), 'firmware input owner required')
            gate()
            parent = open_directory(PAYLOAD); fds.append(parent)
            helper, helper_metadata = exact_file(parent, *HELPER); fds.append(helper)
            for name, path, size, pin in MODULES:
                p = Path(path)
                directory = open_directory(PAYLOAD/'display-modules'/p.parent); fds.append(directory)
                fd, metadata = exact_file(directory, p.name, size, pin, 0o644); fds.append(fd)
                inventory.append(dict(module=name, filename=p.name, path=path, bytes=size,
                                      sha256=pin, directory=directory, descriptor=fd, metadata=metadata))
            gate()
            self.attempted = True
            intent = dict(identity=identity,
                          modules=[{k:v for k,v in row.items() if k not in ('directory','descriptor','metadata')}
                                   for row in inventory], helper_sha256=HELPER[2],
                          maximum_insertions=len(inventory), per_module_seconds=INSERT_SECONDS,
                          total_seconds=TOTAL_SECONDS, cleanup_brightness=0, retries=0,
                          driver_reprobes=0, drm_opens=0)
            need(enter(intent) is True, 'durable production entry not acknowledged')
            entered = True
            for row in inventory:
                gate()
                need(stamp(os.fstat(helper)) == helper_metadata
                     == stamp(os.stat(HELPER[0], dir_fd=parent, follow_symlinks=False)), 'module helper changed')
                need(stamp(os.fstat(row['descriptor'])) == row['metadata']
                     == stamp(os.stat(row['filename'], dir_fd=row['directory'], follow_symlinks=False)),
                     'module file changed')
                need(not os.path.lexists(E.SYS/'module'/row['module']), 'module appeared before insertion')
                # No display ownership may appear before the panel step.
                need(not list((E.SYS/'class/backlight').iterdir())
                     and not os.path.lexists(E.SYS/'class/graphics/fb0'), 'premature display activation')
                prerequisite = {'msm':'gpucc', 'panel_asus_rog5_ams678':'msm'}.get(row['module'])
                if prerequisite:
                    need(self.checkpoint(prerequisite, boot) is True,
                         'production provider lost before consumer: '+row['module'])
                    preconsumer_checks.append(row['module'])
                    gate()
                if row['module'] == 'panel_asus_rog5_ams678':
                    panel_attempted = True
                result = insert(helper, row['directory'], row['filename'], gate,
                                observe_panel if panel_attempted else None)
                rows.append(result)
                need(result['status'] == 'PASS_INSERTION' and result['reaped'], 'module insertion failed; no retry')
                need((E.SYS/'module'/row['module']).is_dir(), 'inserted module absent')
                phase = {'qcom_refgen_regulator':'refgen', 'gpucc_sm8350':'gpucc', 'msm':'msm'}.get(row['module'])
                if phase:
                    gate()
                    need(self.checkpoint(phase, boot) is True, 'production provider checkpoint: '+phase)
                    checkpoints.append(phase)
                    gate()
            deadline = clock()+DISCOVERY_SECONDS
            while True:
                gate(); observe_panel()
                if registration is not None and os.path.lexists(E.SYS/'class/graphics/fb0'):
                    break
                need(clock() < deadline, 'production display discovery deadline')
                pause(.05)
            # The registered endpoint/property is not a completed preparation.
            # A failed zero (including EPERM) stays failed without startup retry.
            endpoint = E.framebuffer(boot)
            need(type(endpoint) is dict and endpoint.get('status') == 'PASS_FRAMEBUFFER_SYSFS'
                 and endpoint.get('identity') == identity and endpoint.get('device_opened') is False
                 and endpoint.get('physical_scanout_verified') is False,
                 'framebuffer observation receipt missing or invalid')
            blank = zero()
            gate()
        except Exception as exc:
            error = dict(type=type(exc).__name__, reason=str(exc)[:1000])
        finally:
            # Independent owner may still clean up when health/firmware fails.
            # Never gate this on the main authorization or overwrite its error.
            if panel_attempted and (blank is None or error is not None):
                try:
                    cleanup_blank = zero()
                except Exception as exc:
                    cleanup_errors.append(dict(stage='independent-zero', type=type(exc).__name__, reason=str(exc)[:512]))
            for fd in reversed(fds):
                try: os.close(fd)
                except OSError as exc: cleanup_errors.append(dict(stage='close', reason=str(exc)[:512]))
            if firmware is not None:
                try: firmware.close()
                except Exception as exc: cleanup_errors.append(dict(stage='firmware-close', reason=str(exc)[:512]))
        result = dict(status='PASS_MODULES_AND_BLANK' if error is None and not cleanup_errors else 'FAIL_MODULE_LOAD',
                      seconds=clock()-start, entered=entered, panel_attempted=panel_attempted,
                      insertions=rows, checkpoints=checkpoints, preconsumer_checks=preconsumer_checks, registration=registration, blank=blank,
                      cleanup_blank=cleanup_blank, endpoint=endpoint, error=error, cleanup_errors=cleanup_errors,
                      retry_allowed=False, driver_reprobes=0, drm_opens=0,
                      physical_scanout_verified=False, physical_darkness_verified=False,
                      full_health_verified=False, admission_granted=False)
        if result['status'] != 'PASS_MODULES_AND_BLANK': raise LoadError(result)
        return result


if __name__ == '__main__':
    raise SystemExit('Import-only: no admitted production endpoint/owner composition has been issued')
