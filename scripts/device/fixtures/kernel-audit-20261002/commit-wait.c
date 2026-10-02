#include "common.h"
struct drm_crtc_state { bool enable, active; };
struct drm_crtc { struct drm_device *dev; struct drm_crtc_state *state; int idx; struct drm_crtc *next; };
struct drm_encoder { struct drm_crtc *crtc; struct drm_encoder *next; int result, calls; };
struct drm_device { struct drm_encoder *first; struct drm_crtc *crtcs; };
struct dpu_kms { struct drm_device *dev; };
struct msm_kms { struct dpu_kms *backend; bool completed[2]; };
#define to_dpu_kms(kms) ((kms)->backend)
#define DPU_ERROR(...) ((void)0)
#define DPU_DEBUG(...) ((void)0)
#define trace_dpu_kms_wait_for_commit_done(...) ((void)0)
#define drm_atomic_crtc_effectively_active(state) ((state)->active)
#define list_for_each_entry(pos, head, member) for (pos=dev->first;pos;pos=pos->next)
#define for_each_crtc_mask(dev, crtc, mask) for(crtc=(dev)->crtcs;crtc;crtc=crtc->next) if((mask)&BIT(crtc->idx))
static int dpu_encoder_wait_for_commit_done(struct drm_encoder *encoder) { encoder->calls++;return encoder->result; }
static void msm_kms_fb_unpin_waited(struct msm_kms *kms, struct drm_crtc *crtc, bool done) { kms->completed[crtc->idx]=done; }
/* DRIVER_FUNCTIONS */
int main(void) {
 struct drm_crtc_state state={true,true};struct drm_device dev={0};
 struct drm_crtc a={.dev=&dev,.state=&state,.idx=0},b={.dev=&dev,.state=&state,.idx=1};a.next=&b;dev.crtcs=&a;
 struct drm_encoder one={.crtc=&a,.result=-ETIMEDOUT},two={.crtc=&b,.result=0};one.next=&two;dev.first=&one;
 struct dpu_kms dpu={&dev};struct msm_kms kms={.backend=&dpu};
 assert(dpu_kms_wait_for_commit_done(NULL,&a)==-EINVAL);
 dpu_kms_wait_flush(&kms,3);assert(!kms.completed[0] && kms.completed[1]);
 assert(one.calls==1 && two.calls==1);
 one.result=-EWOULDBLOCK;dpu_kms_wait_flush(&kms,1);assert(kms.completed[0] && two.calls==1);
 one.result=-EIO;dpu_kms_wait_flush(&kms,1);assert(!kms.completed[0]);
 one.result=0;dpu_kms_wait_flush(&kms,1);assert(kms.completed[0]);
 state.enable=false;one.result=-ETIMEDOUT;dpu_kms_wait_flush(&kms,1);assert(kms.completed[0]);
 return 0;
}
