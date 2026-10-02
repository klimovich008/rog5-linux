#!/usr/bin/env python3
"""Replay successor patches and execute actual Iris functions with inert APIs."""
import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / 'scripts/host/fixtures/iris-k117'
IRIS = 'drivers/media/platform/qcom/iris/'


def patched_sources():
    pins = json.loads((FIXTURES / 'source-pins.json').read_text())
    for name, digest in pins.items():
        if hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() != digest:
            raise AssertionError('k117 fixture drift: ' + name)
    sources = {IRIS + p.name: p.read_text().splitlines(True)
               for p in FIXTURES.glob('*.c')}
    for patch in sorted((REPO / 'patches/linux-7.2.7').glob('017[2-8]-*.patch')):
        lines = patch.read_text().splitlines(True)
        target = None
        delta = 0
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('diff --git '):
                target = line.split(' b/', 1)[1].strip()
                delta = 0
            elif line.startswith('--- /dev/null'):
                sources[target] = []
            elif line.startswith('@@ ') and target in sources:
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                pos = int(match[1]) - 1 + delta if int(match[1]) else 0
                before, after = [], []
                i += 1
                while i < len(lines) and lines[i][:1] in (' ', '+', '-') and not lines[i].startswith(('--- ', '+++ ')):
                    item = lines[i]
                    if item[0] in (' ', '-'):
                        before.append(item[1:])
                    if item[0] in (' ', '+'):
                        after.append(item[1:])
                    i += 1
                if sources[target][pos:pos + len(before)] != before:
                    raise AssertionError(f'patch context mismatch: {patch.name}: {target}:{pos}')
                sources[target][pos:pos + len(before)] = after
                delta += len(after) - len(before)
                continue
            i += 1
    return {p: ''.join(lines) for p, lines in sources.items()}


def function(source, name):
    declaration = re.search(r'^(?:static )?(?:int|bool|void)\s+' +
                            re.escape(name) + r'\(', source, re.M)
    if not declaration:
        raise AssertionError('function declaration missing: ' + name)
    start = declaration.start()
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


def run_c(code, *args):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'test.c').write_text(code)
        result = subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        '-Wno-unused-parameter', str(root / 'test.c'), '-o', str(root / 'test')],
                       capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        return subprocess.check_output([str(root / 'test'), *map(str, args)], text=True, timeout=10)


class IrisSuccessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = patched_sources()

    def test_builtin_trace_scope_and_no_sleep_in_atomic_context(self):
        source = self.sources['drivers/base/rog5_iris_trace.c']
        source = '\n'.join(line for line in source.splitlines() if not line.startswith('#include'))
        code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#define EXPORT_SYMBOL_GPL(x)
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, v) ((x) = (v))
#define min(x, y) ((x) < (y) ? (x) : (y))
struct device { const char *of_node; };
struct va_format { const char *fmt; va_list *va; };
static int atomic_context, disabled_irqs, logs, sleeps;
static unsigned int delay;
static int in_atomic(void) { return atomic_context; }
static int irqs_disabled(void) { return disabled_irqs; }
static void msleep(unsigned int ms) { sleeps++; delay = ms; }
static bool of_device_is_compatible(const char *node, const char *name) {
    return node && !strcmp(node, name);
}
#define dev_warn(dev, fmt, arg) ((void)(arg), logs++)
#define pr_warn(...) (logs++)
''' + source + r'''
int main(void) {
    struct device iris = {"qcom,sm8350-iris"}, other = {"qcom,sm8250-venus"};
    rog5_iris_remove_mark(&iris, "inactive"); assert(!logs && !sleeps);
    rog5_iris_remove_trace_set(true, 2000);
    rog5_iris_remove_mark(&other, "wrong board"); assert(!logs);
    rog5_iris_remove_mark(NULL, "null"); assert(!logs);
    rog5_iris_remove_mark(&iris, "enabled"); assert(logs == 1 && sleeps == 1 && delay == 1000);
    atomic_context = 1; rog5_iris_remove_mark(&iris, "atomic"); assert(sleeps == 1);
    atomic_context = 0; disabled_irqs = 1;
    rog5_iris_domain_mark("mvs0_gdsc", "irq disabled", true); assert(sleeps == 1);
    disabled_irqs = 0; rog5_iris_domain_mark("mvs0c_gdsc", "locked", false); assert(sleeps == 1);
    int before = logs;
    rog5_iris_domain_mark("unrelated_gdsc", "ignored", true); assert(logs == before);
    rog5_iris_domain_mark("mx", "unlocked", true); assert(sleeps == 2);
    rog5_iris_remove_trace_set(false, 200);
    rog5_iris_remove_mark(&iris, "disarmed"); assert(sleeps == 2);
    puts("trace scope and atomic context: PASS");
}
'''
        self.assertIn('PASS', run_c(code))

    def test_ftb_wire_fields_gates_allocation_reuse_and_failures(self):
        source = self.sources[IRIS + 'iris_hfi_gen1_command.c']
        funcs = ''.join(function(source, name) for name in
                        ('iris_hfi_gen1_vp9_dpb_extra', 'iris_hfi_gen1_get_dpb_extra',
                         'iris_hfi_gen1_queue_output_buffer'))
        code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define DECODER 1
#define BUF_DPB 8
#define BUF_OUTPUT 2
#define V4L2_PIX_FMT_VP9 9
#define HFI_CMD_SESSION_FILL_BUFFER 0x211005
#define SZ_16K 16384
#define GFP_KERNEL 0
#define lower_32_bits(x) ((uint32_t)(x))
#define iris_mark(...) ((void)0)
struct device {};
struct platform { void *oem; };
struct iris_core { struct device *dev; struct platform *iris_platform_data; };
struct format { struct { struct { unsigned int pixelformat; } pix_mp; } fmt; };
struct iris_inst { struct iris_core *core; struct format *fmt_src; int domain, split;
    uint32_t session_id; void *dpb_extra_vaddr; uint64_t dpb_extra_daddr; };
struct iris_buffer { int type; uint64_t device_addr; uint32_t buffer_size, data_size, data_offset, index; };
struct hfi_session_fill_buffer_pkt {
    struct { struct { uint32_t size, pkt_type; } hdr; uint32_t session_id; } shdr;
    uint32_t stream_id, offset, alloc_len, filled_len, output_tag, packet_buffer, extradata_buffer, data;
};
static bool vp9_dpb_extra;
static int allocs, submissions, alloc_fail;
static uint64_t allocated_address = 0xc0000000;
static struct hfi_session_fill_buffer_pkt sent;
static bool iris_split_mode_enabled(struct iris_inst *i) { return i->split; }
static bool iris_dma_range_ok(struct iris_core *c, uint64_t addr, uint32_t sz, const char *role) {
    return addr >= 0x25800000 && addr < 0xe0000000 && sz <= 0xe0000000 - addr;
}
static void *dma_alloc_attrs(struct device *dev, unsigned int sz, uint64_t *addr, int flags, int attrs) {
    assert(sz == SZ_16K); allocs++;
    if (alloc_fail) return NULL;
    *addr = allocated_address; return (void *)1;
}
static int iris_hfi_queue_session_cmd_write(struct iris_inst *i, void *pkt, uint32_t sz) {
    assert(sz == 44); memcpy(&sent, pkt, sz); submissions++; return 0;
}
''' + funcs + r'''
int main(void) {
    struct platform p = {(void *)1}; struct iris_core core = {NULL, &p};
    struct format fmt = {{{V4L2_PIX_FMT_VP9}}};
    struct iris_inst i = { .core=&core, .fmt_src=&fmt, .domain=DECODER, .split=1, .session_id=0x1234 };
    struct iris_buffer b = {BUF_DPB, 0xb8c00000, 0x312000, 0, 0, 7};
    assert(!iris_hfi_gen1_queue_output_buffer(&i, &b));
    assert(sent.stream_id == 0 && sent.packet_buffer == b.device_addr && sent.alloc_len == b.buffer_size);
    assert(sent.output_tag == 7 && !sent.extradata_buffer && !sent.data && !allocs);
    vp9_dpb_extra = true;
    assert(!iris_hfi_gen1_queue_output_buffer(&i, &b));
    assert(sent.stream_id == 0 && sent.extradata_buffer == 0xc0000000 && sent.data == SZ_16K && allocs == 1);
    assert(!iris_hfi_gen1_queue_output_buffer(&i, &b) && allocs == 1);
    b.type=BUF_OUTPUT; assert(!iris_hfi_gen1_queue_output_buffer(&i, &b));
    assert(sent.stream_id == 1 && !sent.extradata_buffer && !sent.data);
    b.type=BUF_DPB;
    fmt.fmt.pix_mp.pixelformat=1; assert(!iris_hfi_gen1_queue_output_buffer(&i, &b)); assert(!sent.data);
    fmt.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_VP9;
    p.oem=NULL; assert(!iris_hfi_gen1_queue_output_buffer(&i, &b)); assert(!sent.data);
    p.oem=(void *)1; i.domain=2; assert(!iris_hfi_gen1_queue_output_buffer(&i, &b)); assert(!sent.data);
    i.domain=DECODER; i.split=0; assert(!iris_hfi_gen1_queue_output_buffer(&i, &b)); assert(!sent.data);
    i.split=1; i.dpb_extra_vaddr=NULL; alloc_fail=1;
    int before=submissions;
    assert(iris_hfi_gen1_queue_output_buffer(&i, &b) == -ENOMEM && submissions == before);
    alloc_fail=0; allocated_address=0x10000000;
    assert(iris_hfi_gen1_queue_output_buffer(&i, &b) == -EINVAL && submissions == before);
    i.dpb_extra_vaddr=NULL; allocated_address=0xc0000000; b.device_addr=0xdffff000;
    before=allocs; assert(iris_hfi_gen1_queue_output_buffer(&i, &b) == -EINVAL && allocs == before);
    puts("FTB wire fields and fault paths: PASS");
}
'''
        self.assertIn('PASS', run_c(code))

    def test_remove_guard_and_order(self):
        source = self.sources[IRIS + 'iris_probe.c']
        funcs = function(source, 'iris_runtime_disable') + function(source, 'iris_remove')
        code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define READ_ONCE(x) (x)
#define IRIS_CORE_DEINIT 0
#define iris_mark(...) ((void)0)
struct device {};
struct platform { void *oem; };
struct iris_core { struct device *dev; struct platform *iris_platform_data;
    int lock, sys_error_handler, openers, instances, state, irq;
    bool removing, powered, fw_held, fw_pinned;
    void *vdev_dec, *vdev_enc;
    struct { void *dev; } v4l2_dev;
};
struct platform_device { struct iris_core *core; };
static bool remove_quiesce, iris_markers;
static unsigned int iris_marker_delay_ms;
static char events[100]; static int count, lock_destroyed, registered;
static void event(char c) { events[count++]=c; events[count]=0; }
static struct iris_core *platform_get_drvdata(struct platform_device *p) { return p->core; }
static void rog5_iris_remove_trace_set(bool b, unsigned int ms) { event('T'); }
static void mutex_lock(int *l) { assert(!lock_destroyed); event('L'); }
static void mutex_unlock(int *l) { event('U'); }
static int atomic_read(int *v) { return *v; }
static int list_empty(int *l) { return !*l; }
static void cancel_delayed_work_sync(int *w) { event('C'); }
static void iris_core_deinit(struct iris_core *c) { event('D'); }
static void disable_irq(int irq) { event('I'); }
static void video_unregister_device(void *v) { event('V'); }
static void v4l2_device_unregister(void *d) { event('F'); }
static void pm_runtime_dont_use_autosuspend(struct device *d) { assert(!lock_destroyed); event('A'); }
static void pm_runtime_disable(struct device *d) { assert(!lock_destroyed); event('P'); }
static void devm_release_action(struct device *d, void (*fn)(void *), void *data) {
    assert(registered == 1); registered=0; fn(data);
}
static void mutex_destroy(int *l) { lock_destroyed=1; event('X'); }
''' + funcs + r'''
static void reset(void) { count=lock_destroyed=0; registered=1; memset(events,0,sizeof(events)); }
int main(void) {
    struct platform p = {(void *)1};
    struct iris_core c = { .iris_platform_data=&p }; struct platform_device dev = {&c};
    reset(); iris_remove(&dev); assert(!strcmp(events,"TLUCDIVVX") && registered);
    reset(); remove_quiesce=true; iris_remove(&dev); assert(!strcmp(events,"TLUCIVVAPX") && !registered);
    /* Every unsafe state must still run deinit. */
    for (int field=0; field<7; field++) {
        reset(); c.state=0; c.powered=false; c.fw_held=false; c.fw_pinned=false; c.openers=0; c.instances=0; p.oem=(void *)1;
        if (field==0) c.state=1; if (field==1) c.powered=1; if (field==2) c.fw_held=1;
        if (field==3) c.fw_pinned=1; if (field==4) c.openers=1; if (field==5) c.instances=1;
        if (field==6) p.oem=NULL;
        iris_remove(&dev); assert(strchr(events,'D'));
    }
    reset(); p.oem=(void *)1; c.v4l2_dev.dev=(void *)1;
    iris_remove(&dev); assert(strchr(events,'F'));
    reset(); dev.core=NULL; iris_remove(&dev); assert(!count);
    puts("remove order and unsafe-state guards: PASS");
}
'''
        # Multiple independent one-line guards deliberately share lines in the adapter.
        code = code.replace('; if (field', ';\n        if (field')
        self.assertIn('PASS', run_c(code))

    def test_extradata_freed_only_after_confirmed_release(self):
        source = self.sources[IRIS + 'iris_vidc.c']
        # Compile the actual guarded cleanup block with failure injection.
        begin = source.index('\tif (iris_session_memory_released(inst, end_ret)) {', source.index('end_ret = iris_session_close'))
        body = function('static void cleanup(void)\n' + source[begin:], 'cleanup')
        # function() finds the first brace: the release guard belongs inside cleanup.
        block = body[body.index('{'):]
        code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define SZ_4K 4096
#define SZ_16K 16384
#define V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE 1
#define V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE 2
struct iris_core { void *dev; };
struct iris_inst { struct iris_core *core; void *eos_vaddr, *dpb_extra_vaddr;
    unsigned long eos_daddr, dpb_extra_daddr; };
static struct iris_core core;
static struct iris_inst value = { .core=&core, .dpb_extra_vaddr=(void *)1 };
static struct iris_inst *inst=&value;
static int end_ret, allow, freed;
static bool iris_session_memory_released(struct iris_inst *i, int ret) { return allow; }
static void iris_destroy_all_internal_buffers(struct iris_inst *i, int p) {}
static void iris_check_num_queued_internal_buffers(struct iris_inst *i, int p) {}
static void dma_free_attrs(void *d, int size, void *v, unsigned long a, int attrs) {
    assert(size == SZ_16K); freed++;
}
static void cleanup(void) {
    if (iris_session_memory_released(inst, end_ret))
''' + block + r'''
}
int main(void) {
    allow=0; cleanup(); assert(!freed);
    allow=1; cleanup(); assert(freed==1);
    puts("firmware-held cleanup guard: PASS");
}
'''
        self.assertIn('PASS', run_c(code))

    def test_core_init_refuses_removing_before_any_hardware_or_fast_path(self):
        code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
typedef uint32_t u32;
#define IRIS_CORE_DEINIT 0
#define IRIS_CORE_INIT 1
#define IRIS_CORE_ERROR 2
#define iris_mark(...) ((void)0)
#define dev_err(...) ((void)0)
struct iris_core;
struct firmware_data { void (*init_hfi_ops)(struct iris_core *); };
struct iris_core { int lock, irq, state, core_init_done; u32 init_attempt;
    bool removing, fatal, fw_held; void *dev; struct firmware_data *iris_firmware_data; };
static int work, locks;
static void mutex_lock(int *lock) { locks++; }
static void mutex_unlock(int *lock) { locks--; }
static void reinit_completion(int *c) { work++; }
static int operation(struct iris_core *c) { work++; return 0; }
static void init_ops(struct iris_core *c) { work++; }
#define iris_hfi_queues_init operation
#define iris_vpu_power_on operation
#define iris_fw_load operation
#define iris_vpu_boot_firmware operation
#define iris_vpu_switch_to_hwmode operation
#define iris_hfi_core_init operation
#define iris_fw_unload operation
#define iris_vpu_power_off operation
#define iris_core_mark_held operation
#define iris_core_unpin operation
#define iris_hfi_queues_deinit operation
static int iris_wait_for_system_response(struct iris_core *c, u32 attempt) { work++; return 0; }
static void disable_irq(int irq) { work++; }
static void enable_irq(int irq) { work++; }
''' + function(self.sources[IRIS + 'iris_core.c'], 'iris_core_init') + r'''
int main(void) {
    struct firmware_data fw = {init_ops};
    struct iris_core core = { .iris_firmware_data=&fw, .removing=true };
    for (int state=0; state<3; state++) {
        core.state=state;
        assert(iris_core_init(&core) == -ENODEV && !work && !locks);
        assert(core.state == state && !core.init_attempt);
    }
    core.removing=false; core.state=IRIS_CORE_DEINIT; core.fatal=true;
    assert(iris_core_init(&core) == -EIO && !work && !locks);
    core.fatal=false; core.state=IRIS_CORE_INIT;
    assert(!iris_core_init(&core) && !work && !locks);
    core.state=IRIS_CORE_ERROR;
    assert(iris_core_init(&core) == -EINVAL && !work && !locks);
    core.state=IRIS_CORE_DEINIT;
    assert(!iris_core_init(&core) && work && !locks && core.init_attempt == 1);
    puts("removing init refusal and ordinary init: PASS");
}
'''
        self.assertIn('PASS', run_c(code))

    def test_default_gates_and_fixture_replay(self):
        self.assertIn('module_param(probe_no_video, bool, 0444);', self.sources[IRIS + 'iris_probe.c'])
        self.assertIn('module_param(remove_quiesce, bool, 0644);', self.sources[IRIS + 'iris_probe.c'])
        self.assertIn('static bool vp9_dpb_extra;', self.sources[IRIS + 'iris_hfi_gen1_command.c'])
        self.assertIn('module_param(vp9_dpb_extra, bool, 0444);', self.sources[IRIS + 'iris_hfi_gen1_command.c'])
        # No private prerequisite: always replay above; an explicitly supplied
        # source must match byte for byte rather than becoming an optional skip.
        if os.environ.get('ROG5_LINUX_SOURCE'):
            root = Path(os.environ['ROG5_LINUX_SOURCE'])
            for name in ('iris_probe.c', 'iris_hfi_gen1_command.c', 'iris_vidc.c', 'iris_core.c'):
                self.assertEqual((root / IRIS / name).read_text(), self.sources[IRIS + name])


if __name__ == '__main__':
    unittest.main()
