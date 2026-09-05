#!/usr/bin/env python3
"""Exercise the exact added C and changed transport functions without hardware."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[2]
PATCH=REPO/'patches/linux-7.1.4/0035-soc-qcom-rpmh-timeout-safe-readback.patch'

def postimages():
    result={}; path=None; hunk=False
    for line in PATCH.read_text().splitlines():
        if line.startswith('diff --git '):
            path=line.split()[-1][2:];result[path]=[];hunk=False
        elif line.startswith('@@ '):hunk=True
        elif hunk and line[:1] in ('+',' '):result[path].append(line[1:])
    return {p:'\n'.join(lines)+'\n' for p,lines in result.items()}

def function(text,name):
    for m in re.finditer(r'\b'+re.escape(name)+r'\(',text):
        at=m.end();depth=1
        while depth:
            depth+=(text[at]=='(')-(text[at]==')');at+=1
        while text[at].isspace():at+=1
        if text[at]!='{':continue
        start=text.rfind('\n',0,m.start())+1;end=at+1;depth=1
        while depth:
            depth+=(text[end]=='{')-(text[end]=='}');end+=1
        return text[start:end]
    raise AssertionError('complete function absent: '+name)

def compile_run(source,sanitize=False):
    with tempfile.TemporaryDirectory(prefix='rog5-rpmh-test-') as tmp:
        c=Path(tmp)/'test.c';out=Path(tmp)/'test';c.write_text(source)
        flags=['-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror',
               '-Wno-unused-parameter','-Wno-unused-function','-Wno-unused-variable',
               '-Wno-sign-compare','-pthread']
        if sanitize:flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        built=subprocess.run(['cc',*flags,str(c),'-o',str(out)],capture_output=True,text=True)
        if built.returncode:raise AssertionError(built.stderr)
        return subprocess.run([str(out)],capture_output=True,text=True,timeout=20)

API_STUB=r'''
#include <assert.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdatomic.h>
#include <pthread.h>
#include <sched.h>
#include <errno.h>
typedef uint32_t u32;
typedef struct { atomic_int value; } refcount_t;
struct completion { atomic_bool done; };
enum rpmh_state { RPMH_SLEEP_STATE, RPMH_WAKE_ONLY_STATE, RPMH_ACTIVE_ONLY_STATE };
struct tcs_cmd { u32 addr,data,wait; };
struct tcs_request { enum rpmh_state state; u32 wait_for_compl,num_cmds; bool is_read; struct tcs_cmd *cmds; };
struct device { struct device *parent; void *data; };
struct rpmh_request { struct tcs_request msg; struct tcs_cmd cmd[16]; struct completion *completion; const struct device *dev; bool needs_free; };
struct rsc_drv { int unused; };
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
#define GFP_KERNEL 1
#define EXPORT_SYMBOL_GPL(x)
#define msecs_to_jiffies(x) (x)
static int mode,send_error,allocation_error,sends;
static atomic_int alive,frees;
static const struct tcs_request *pending;
static pthread_t irq_thread;
void rpmh_read_tx_done(const struct tcs_request *msg);
static void *kzalloc(size_t n,int flags) { if(allocation_error)return NULL;atomic_fetch_add(&alive,1);return calloc(1,n); }
static void kfree(void *p) { assert(atomic_fetch_sub(&alive,1)==1);atomic_fetch_add(&frees,1);free(p); }
static void *dev_get_drvdata(const struct device *d) { return d->data; }
static void init_completion(struct completion *c) { atomic_init(&c->done,false); }
static void complete(struct completion *c) { atomic_store_explicit(&c->done,true,memory_order_release); }
static void refcount_set(refcount_t *r,int n) { atomic_init(&r->value,n); }
static bool refcount_dec_and_test(refcount_t *r) { int old=atomic_fetch_sub(&r->value,1);assert(old>0);return old==1; }
static void irq_finish(void) {
 const struct tcs_request *p=pending;assert(p && atomic_load(&alive)==1);pending=NULL;
 p->cmds[0].data=0x4e8;rpmh_read_tx_done(p);
}
static void *race_irq(void *ignored) { sched_yield();irq_finish();return NULL; }
static int rpmh_rsc_send_data(struct rsc_drv *drv,const struct tcs_request *msg) {
 sends++;assert(msg->is_read && msg->num_cmds==1 && msg->wait_for_compl);
 assert(msg->state==RPMH_ACTIVE_ONLY_STATE && msg->cmds[0].addr==0x40100);
 assert(msg->cmds[0].data==0 && msg->cmds[0].wait==0);
 if(send_error)return send_error;
 pending=msg;
 if(mode==1)irq_finish();
 if(mode==5)assert(!pthread_create(&irq_thread,NULL,race_irq,NULL));
 return 0;
}
static unsigned long wait_for_completion_timeout(struct completion *c,unsigned long timeout) {
 assert(timeout==10000);
 if(mode==2)irq_finish();
 if(mode==3)return 0;
 if(mode==4){irq_finish();return 0;} /* completion races the expired wait */
 if(mode==5)sched_yield();
 return atomic_load_explicit(&c->done,memory_order_acquire)?1:0;
}
'''

API_MAIN=r'''
static void reset(void) { assert(atomic_load(&alive)==0);sends=send_error=allocation_error=0;atomic_store(&frees,0);pending=NULL; }
int main(void) {
 struct rsc_drv drv={0};struct device parent={.data=&drv},dev={.parent=&parent};
 struct tcs_cmd cmd={.addr=0x40100,.data=0xdeadbeef,.wait=1};
 assert(rpmh_read(NULL,&cmd)==-EINVAL && rpmh_read(&dev,NULL)==-EINVAL);
 struct device no_parent={0};assert(rpmh_read(&no_parent,&cmd)==-EINVAL);
 parent.data=NULL;assert(rpmh_read(&dev,&cmd)==-ENODEV);parent.data=&drv;
 allocation_error=1;assert(rpmh_read(&dev,&cmd)==-ENOMEM && sends==0);reset();
 for(int e=0;e<2;e++) { reset();send_error=e?-EINVAL:-EAGAIN;
  assert(rpmh_read(&dev,&cmd)==send_error && sends==1 && !pending);
  assert(atomic_load(&alive)==0 && atomic_load(&frees)==1 && cmd.data==0xdeadbeef); }
 for(mode=1;mode<=5;mode++) {
  for(int round=0;round<(mode==5?500:1);round++) {
   reset();cmd.data=0xdeadbeef;int ret=rpmh_read(&dev,&cmd);
   if(mode==1 || mode==2)assert(ret==0 && cmd.data==0x4e8);
   if(mode==3) { assert(ret==-ETIMEDOUT && cmd.data==0xdeadbeef);
    assert(atomic_load(&alive)==1 && atomic_load(&frees)==0);
    cmd.data=0x12345678;irq_finish();assert(cmd.data==0x12345678); }
   if(mode==4)assert(ret==-ETIMEDOUT && cmd.data==0xdeadbeef);
   if(mode==5) { assert(ret==0 || ret==-ETIMEDOUT);
    if(ret==-ETIMEDOUT)cmd.data=0x12345678;
    assert(!pthread_join(irq_thread,NULL));
    assert(cmd.data==(ret?0x12345678:0x4e8)); }
   assert(atomic_load(&alive)==0 && atomic_load(&frees)==1);
  }
 }
 return 0;
}
'''

RSC_STUB=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
typedef uint32_t u32;
enum rpmh_state { RPMH_SLEEP_STATE,RPMH_WAKE_ONLY_STATE,RPMH_ACTIVE_ONLY_STATE };
enum { SLEEP_TCS,WAKE_TCS,ACTIVE_TCS,CONTROL_TCS,TCS_TYPE_NR };
enum { RSC_DRV_CMD_MSGID,RSC_DRV_CMD_ADDR,RSC_DRV_CMD_DATA,RSC_DRV_CMD_ENABLE };
#define CMD_MSGID_LEN 8
#define CMD_MSGID_WRITE (1U<<16)
#define CMD_MSGID_RESP_REQ (1U<<8)
#define BIT(n) (1UL<<(n))
struct tcs_cmd { u32 addr,data,wait; };
struct tcs_request { enum rpmh_state state; u32 wait_for_compl,num_cmds; bool is_read; struct tcs_cmd *cmds; };
struct rsc_drv;
struct tcs_group { struct rsc_drv *drv; int type;u32 mask,offset;int num_tcs;const struct tcs_request *req[3]; };
struct rsc_drv {struct tcs_group tcs[4];unsigned long tcs_in_use[1];int lock,tcs_wait;u32 *regs;};
static int busy,claims,waits,locked,writes_data,triggers,buffer_calls;
static u32 msgid_seen,addr_seen,data_seen;
static void might_sleep(void) {}
#define IS_ERR(p) false
#define PTR_ERR(p) (-EINVAL)
static struct tcs_group *get_tcs_for_msg(struct rsc_drv *d,const struct tcs_request *m) {
 /* Reproduce the real active-to-WAKE substitution, not an always-ACTIVE stub. */
 struct tcs_group *g=&d->tcs[m->state==RPMH_ACTIVE_ONLY_STATE?ACTIVE_TCS:
                            m->state==RPMH_WAKE_ONLY_STATE?WAKE_TCS:SLEEP_TCS];
 if(m->state==RPMH_ACTIVE_ONLY_STATE && !g->num_tcs)g=&d->tcs[WAKE_TCS];
 return g;
}
static void spin_lock_irq(int *p) { assert(!locked);locked=1; }
static void spin_unlock_irq(int *p) { assert(locked);locked=0; }
static int claim_tcs_for_req(struct rsc_drv *d,struct tcs_group *g,const struct tcs_request *m) {claims++;if(busy){busy--;return -EBUSY;}return g->offset;}
#define wait_event_lock_irq(q,cond,l) do { waits++;while(!(cond)){assert(claims<4);} } while(0)
static void set_bit(int i,unsigned long *bits) {*bits|=BIT(i);}
static u32 read_tcs_reg(const struct rsc_drv *d,int reg,int id) {return 0;}
static void write_tcs_cmd(const struct rsc_drv *d,int reg,int id,int cmd,u32 value) {
 assert(locked==0);
 if(reg==RSC_DRV_CMD_DATA){writes_data++;data_seen=value;}
 if(reg==RSC_DRV_CMD_MSGID)msgid_seen=value;
 if(reg==RSC_DRV_CMD_ADDR)addr_seen=value;
}
static void trace_rpmh_send_msg(const struct rsc_drv *d,int id,int state,int cmd,u32 msgid,struct tcs_cmd *p) {}
static void write_tcs_reg(const struct rsc_drv *d,int reg,int id,u32 value) {}
static void write_tcs_reg_sync(const struct rsc_drv *d,int reg,int id,u32 value) {}
static void enable_tcs_irq(struct rsc_drv *d,int id,bool value) {}
static void __tcs_set_trigger(struct rsc_drv *d,int id,bool value) {triggers++;}
'''

RSC_MAIN=r'''
int main(void) {
 u32 regs[]={0,1,2,3};struct rsc_drv d={.regs=regs};
 d.tcs[ACTIVE_TCS]=(struct tcs_group){.drv=&d,.type=ACTIVE_TCS,.mask=1,.num_tcs=2};
 struct tcs_cmd cmd={.addr=0x40100,.data=0xa5a5};
 struct tcs_request req={.state=RPMH_ACTIVE_ONLY_STATE,.wait_for_compl=1,.num_cmds=1,.is_read=true,.cmds=&cmd};
 assert(offsetof(struct tcs_request,cmds)==16 && offsetof(struct tcs_request,is_read)==12);
 assert(!rpmh_rsc_send_data(&d,&req));
 assert(msgid_seen==0x108 && addr_seen==0x40100 && writes_data==0 && triggers==1 && waits==0);
 assert(get_req_from_tcs(&d,0)==&req && get_req_from_tcs(&d,0)==NULL);
 claims=waits=triggers=0;d.tcs_in_use[0]=0;busy=1;
 assert(rpmh_rsc_send_data(&d,&req)==-EAGAIN);
 assert(claims==1 && !waits && !triggers && !locked && !d.tcs_in_use[0]);
 d.tcs[ACTIVE_TCS].num_tcs=0;
 d.tcs[WAKE_TCS]=(struct tcs_group){.drv=&d,.type=WAKE_TCS,.mask=4,.offset=2,.num_tcs=1};
 busy=claims=triggers=0;d.tcs[WAKE_TCS].req[0]=&req;
 assert(get_tcs_for_msg(&d,&req)==&d.tcs[WAKE_TCS]);
 assert(rpmh_rsc_send_data(&d,&req)==-EOPNOTSUPP);
 assert(!claims && !triggers && !waits && !locked && d.tcs[WAKE_TCS].req[0]==&req);
 d.tcs[ACTIVE_TCS].num_tcs=2;
 busy=0;req.num_cmds=2;assert(rpmh_rsc_send_data(&d,&req)==-EINVAL);
 req.num_cmds=1;req.wait_for_compl=0;assert(rpmh_rsc_send_data(&d,&req)==-EINVAL);
 req.wait_for_compl=1;req.state=RPMH_SLEEP_STATE;assert(rpmh_rsc_send_data(&d,&req)==-EINVAL);
 req.state=RPMH_ACTIVE_ONLY_STATE;req.is_read=false;busy=1;claims=0;
 assert(!rpmh_rsc_send_data(&d,&req));
 assert(waits==1 && claims==2 && msgid_seen==0x10108 && writes_data==1 && data_seen==0xa5a5);
 assert(get_req_from_tcs(&d,0)==&req && get_req_from_tcs(&d,0)==&req);
 return 0;
}
'''

class RpmhReadbackTest(unittest.TestCase):
    def test_lifetime_errors_and_completion_races(self):
        code=postimages()['drivers/soc/qcom/rpmh-read.c']
        code=re.sub(r'^#include[^\n]*\n','',code,flags=re.M)
        result=compile_run(API_STUB+code+API_MAIN,True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        # The same harness must reject freeing the request at its first put.
        broken=code.replace('if (refcount_dec_and_test(&read->refs))','if (true)')
        self.assertNotEqual(broken,code)
        result=compile_run(API_STUB+broken+API_MAIN,True)
        self.assertNotEqual(result.returncode,0,'early-free mutation escaped')

    def test_read_opcode_busy_admission_and_write_preservation(self):
        source=postimages()['drivers/soc/qcom/rpmh-rsc.c']
        code='\n'.join(function(source,n) for n in ('get_req_from_tcs','__tcs_buffer_write','rpmh_rsc_send_data'))
        result=compile_run(RSC_STUB+code+RSC_MAIN)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        broken=code.replace('if (!msg->is_read)','if (true)')
        result=compile_run(RSC_STUB+broken+RSC_MAIN)
        self.assertNotEqual(result.returncode,0,'write-opcode mutation escaped')

    def test_patch_does_not_change_regulator_initialization(self):
        images=postimages()
        self.assertFalse(any(p.startswith(('drivers/regulator/','arch/','fs/')) for p in images))
        read=images['drivers/soc/qcom/rpmh-read.c']
        active=re.sub(r'/\*.*?\*/','',read,flags=re.S)
        self.assertNotRegex(active,r'\b(?:__rpmh_write|cache_rpm_request|regulator_enable|regulator_set_voltage)\s*\(')
        self.assertNotIn('DECLARE_COMPLETION_ONSTACK',active)
        self.assertIn('rpmh-read.o',images['drivers/soc/qcom/Makefile'])
        self.assertIn('req->msg.is_read = false;',function(images['drivers/soc/qcom/rpmh.c'],'__fill_rpmh_msg'))
        # git's C function-context heuristic treats the unindented skip label
        # as a new context. Only this complete IRQ prefix is needed here.
        source=images['drivers/soc/qcom/rpmh-rsc.c']
        irq=source[source.index('static irqreturn_t tcs_tx_done'):source.index('static void __tcs_buffer_write')]
        self.assertLess(irq.index('RSC_DRV_CMD_RESP_DATA'),irq.index('trace_rpmh_tx_done'))
        ctrl=function(images['drivers/soc/qcom/rpmh-rsc.c'],'rpmh_rsc_write_ctrl_data')
        self.assertLess(ctrl.index('if (msg->is_read)'),ctrl.index('get_tcs_for_msg'))

if __name__=='__main__':unittest.main()
