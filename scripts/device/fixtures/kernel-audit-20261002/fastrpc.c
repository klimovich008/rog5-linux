#include "common.h"
struct list_head {int unused;};
#define INIT_LIST_HEAD(head) ((void)(head))
#define mutex_init(lock) ((void)(lock))
#define mutex_destroy(lock) ((void)(lock))
#define kzalloc_obj(value) calloc(1,sizeof(value))
#define kfree(p) free(p)
struct fastrpc_channel_ctx {int refs;};
struct fastrpc_user {struct fastrpc_channel_ctx *cctx;};
struct fastrpc_buf {
 struct list_head attachments,node;struct mutex lock;struct fastrpc_channel_ctx *cctx;
 void *virt;u64 dma_addr,size,raddr;struct device *dev;
};
struct dma_buf {void *priv;};
static bool allocation_fail;static int freed;
static void put_device(struct device *dev) {assert(dev->refs>0);dev->refs--;}
static u64 fastrpc_ipa_to_dma_addr(struct fastrpc_channel_ctx *c,u64 addr) {assert(c->refs>0);return addr;}
static void *dma_alloc_coherent(struct device *dev,u64 size,u64 *addr,int flags) {assert(dev->refs>0);*addr=99;return allocation_fail?NULL:malloc(size);}
static void dma_free_coherent(struct device *dev,u64 size,void *virt,u64 addr) {assert(dev->refs>0 && addr==99);free(virt);freed++;}
static void fastrpc_channel_ctx_put(struct fastrpc_channel_ctx *c) {assert(c->refs>0);c->refs--;}
/* DRIVER_FUNCTIONS */
int main(void) {
 struct device dev={.refs=1};struct fastrpc_channel_ctx cctx={.refs=2};struct fastrpc_user user={&cctx};struct fastrpc_buf *buf=NULL;
 assert(__fastrpc_buf_alloc(&user,&dev,64,&buf)==0 && dev.refs==2);
 /* Drop the platform/user's ownership, keep the exported dma-buf only. */
 put_device(&dev);cctx.refs--;struct dma_buf dma={.priv=buf};
 fastrpc_release(&dma);assert(dev.refs==0 && cctx.refs==0 && freed==1);
 dev.refs=1;cctx.refs=1;allocation_fail=true;
 assert(__fastrpc_buf_alloc(&user,&dev,64,&buf)==-ENOMEM && dev.refs==1 && freed==1);
 return 0;
}
