#include "common.h"
#define USB_ROLE_DEVICE 2
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; };
struct dwc3 { struct device *dev; bool role_vbus_gated; int requested_role; };
struct dwc3_qcom { struct mutex bw_lock; bool bw_device_role,bw_role_hold; struct device *dev; struct delayed_work bw_work; };
static int reset,start,run,apply,cancel;
#define to_delayed_work(work) container_of(work,struct delayed_work,work)
static int dwc3_core_soft_reset(struct dwc3 *dwc) {reset++;return 0;}
static void dwc3_event_buffers_setup(struct dwc3 *dwc) { }
static void __dwc3_gadget_start(struct dwc3 *dwc) {start++;}
static int dwc3_gadget_run_stop(struct dwc3 *dwc,bool on) {run++;return 0;}
static void cancel_delayed_work(struct delayed_work *work) {cancel++;}
static void dwc3_qcom_bw_prune(struct dwc3_qcom *q) { }
static void dwc3_qcom_bw_apply(struct dwc3_qcom *q) {apply++;}
/* DRIVER_FUNCTIONS */
int main(void) {
 struct dwc3_qcom q={.bw_role_hold=true}; struct device parent={.data=&q},dev={.parent=&parent};
 struct dwc3 dwc={.dev=&dev,.role_vbus_gated=true};
 assert(dwc3_gadget_soft_connect(&dwc)==0 && reset==0 && start==0 && run==0);
 dwc.requested_role=1;assert(dwc3_gadget_soft_connect(&dwc)==0 && run==0);
 dwc.requested_role=2;assert(dwc3_gadget_soft_connect(&dwc)==0 && run==1);
 /* A timer expiry under a stalled role worker retains FULL. */
 dwc3_qcom_bw_work(&q.bw_work.work);assert(q.bw_role_hold && apply==0);
 dwc3_qcom_legacy_post_gadget_stop(&dwc);assert(!q.bw_role_hold && apply==1 && cancel==1);
 q.bw_device_role=true;q.bw_role_hold=true;
 dwc3_qcom_legacy_post_gadget_stop(&dwc);assert(q.bw_role_hold && apply==1);
 return 0;
}
