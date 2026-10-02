#include "common.h"
struct list_head { struct list_head *next,*prev; };
#define INIT_LIST_HEAD(head) ((head)->next=(head),(head)->prev=(head))
static void list_add_tail(struct list_head *node,struct list_head *head) {node->prev=head->prev;node->next=head;head->prev->next=node;head->prev=node;}
static bool list_empty(struct list_head *head) {return head->next==head;}
static void list_del_init(struct list_head *node) {node->prev->next=node->next;node->next->prev=node->prev;INIT_LIST_HEAD(node);}
#define list_for_each_entry(pos,head,member) for(pos=container_of((head)->next,__typeof__(*pos),member); &(pos)->member!=(head); pos=container_of((pos)->member.next,__typeof__(*pos),member))
struct msm_kms_fb_unpin {spinlock_t lock;struct list_head fbs;bool off;u64 queued_seq,flushed_seq;};
struct drm_framebuffer {int refs;struct {u32 id;} base;};
struct drm_crtc {struct drm_device *dev;int idx;u64 count;struct {u32 id;} base;};
struct drm_device {void *dev_private;struct drm_crtc *crtc;};
struct msm_kms {struct drm_device *dev;struct msm_kms_fb_unpin fb_unpin[1];};
struct msm_drm_private {struct msm_kms *kms;};
struct kthread_work {int unused;};
struct drm_vblank_work {struct kthread_work work;};
struct msm_fb_unpin_work {struct drm_vblank_work base;struct list_head node;struct msm_kms_fb_unpin *pending;struct drm_crtc *crtc;struct drm_framebuffer *fb;u64 required_seq,target_vbl;};
#define to_drm_vblank_work(work) container_of(work,struct drm_vblank_work,work)
#define drm_crtc_index(crtc) ((crtc)->idx)
#define drm_crtc_vblank_count(crtc) ((crtc)->count)
#define for_each_crtc_mask(dev,crtc,mask) for(crtc=(dev)->crtc;crtc && (mask);crtc=NULL)
static int schedule_result=1,releases,waits;static u64 scheduled;
static int drm_vblank_work_schedule(struct drm_vblank_work *work,u64 target,bool next) {scheduled=target;return schedule_result;}
static void msm_kms_fb_unpin_release(struct msm_fb_unpin_work *work) {releases++;}
static bool msm_crtc_wait_one_vblank(struct drm_crtc *crtc) {waits++;return true;}
static void drm_framebuffer_get(struct drm_framebuffer *fb) {fb->refs++;}
/* DRIVER_FUNCTIONS */
int main(void) {
 struct drm_device dev={0};struct drm_crtc crtc={.dev=&dev,.count=10};dev.crtc=&crtc;
 struct msm_kms kms={.dev=&dev};struct msm_drm_private priv={&kms};dev.dev_private=&priv;
 struct msm_kms_fb_unpin *p=&kms.fb_unpin[0];INIT_LIST_HEAD(&p->fbs);
 struct drm_framebuffer fb={0};
 msm_kms_fb_unpin_queued(&kms,1);assert(p->queued_seq==1 && p->flushed_seq==0);
 struct msm_fb_unpin_work unpin={.crtc=&crtc,.pending=p,.required_seq=1};list_add_tail(&unpin.node,&p->fbs);
 /* A vblank before an in-flight async flush cannot release the buffer. */
 msm_kms_fb_unpin_work(&unpin.base.work);assert(releases==0 && scheduled==11);
 assert(msm_crtc_fb_unpin_fallback(&crtc,&fb) && fb.refs==1 && waits==0);
 crtc.count=11;msm_kms_fb_unpin_flushed(&kms,1);assert(unpin.target_vbl==12);
 msm_kms_fb_unpin_queued(&kms,1);crtc.count=12;msm_kms_fb_unpin_flushed(&kms,1);
 assert(unpin.target_vbl==12); /* New flush cannot postpone old retirement. */
 msm_kms_fb_unpin_work(&unpin.base.work);assert(releases==1 && list_empty(&p->fbs));
 /* Failed self-rearm keeps the list ownership and pin for the off drain. */
 struct msm_fb_unpin_work failed={.crtc=&crtc,.pending=p,.required_seq=3};list_add_tail(&failed.node,&p->fbs);
 schedule_result=-EIO;msm_kms_fb_unpin_work(&failed.base.work);
 assert(releases==1 && !list_empty(&failed.node));
 p->off=true;assert(!msm_crtc_fb_unpin_fallback(&crtc,&fb) && waits==0);
 p->off=false;p->flushed_seq=p->queued_seq;assert(!msm_crtc_fb_unpin_fallback(&crtc,&fb) && waits==1);
 return 0;
}
