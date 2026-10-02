#include "common.h"
#define PMIC_GLINK_OWNER_BATTMGR 1
#define PMIC_GLINK_OWNER_ASUS_ROG5 2
#define PMIC_GLINK_REQ_RESP 1
#define PMIC_GLINK_NOTIFY 2
#define BATTMGR_NOTIFICATION 9
#define BATTMGR_REQUEST_NOTIFICATION 10
#define BATTMGR_BAT_PROPERTY_GET 11
#define BATTMGR_USB_PROPERTY_GET 12
#define BATTMGR_WLS_PROPERTY_GET 13
#define QCOM_BATTMGR_SC8280XP 1
#define QCOM_BATTMGR_X1E80100 2
#define ASUS_ROG5_SET_BTM_OTG 20
struct pmic_glink_hdr {u32 owner,type,opcode;};
struct qcom_battmgr_message {struct pmic_glink_hdr hdr;struct {u32 property,value,result;} intval;};
struct qcom_battmgr_asus_btm_otg_msg {struct pmic_glink_hdr hdr;u32 on;};
struct qcom_battmgr {
 spinlock_t request_lock;u32 request_opcode,request_property;
 bool request_poisoned;int error,ack,variant;
 struct device *dev;struct mutex lock,asus_chg_lock;
 bool oem_service_up,oem_request_poisoned;u32 oem_service_generation,btm_otg_generation;
 int btm_otg_confirmed;void *oem_client;
 unsigned asus_chg_end;bool asus_chg_paused;int asus_chg_work;
};
static int decoded,notifications,sends,raw_off,request_error,pause_error,kicks;
static void complete(int *ack) {(*ack)++;}
static void qcom_battmgr_notification(struct qcom_battmgr *b,const void *data,size_t len) {notifications++;}
static void qcom_battmgr_sm8350_callback(struct qcom_battmgr *b,const struct qcom_battmgr_message *data,size_t len) {decoded++;b->error=0;}
static void qcom_battmgr_sc8280xp_callback(struct qcom_battmgr *b,const struct qcom_battmgr_message *data,size_t len) {decoded++;b->error=0;}
static int qcom_battmgr_asus_request_locked(struct qcom_battmgr *b,void *data,size_t len) {sends++;return request_error;}
static int pmic_glink_send(void *client,void *data,size_t len) {struct qcom_battmgr_asus_btm_otg_msg *m=data;assert(m->on==0);raw_off++;return 0;}
static void cancel_delayed_work_sync(int *work) { }
static int qcom_battmgr_asus_set_bypass(struct qcom_battmgr *b,bool pause) {assert(pause);return pause_error;}
static void qcom_battmgr_asus_chg_kick(struct qcom_battmgr *b,bool reassert) {kicks++;}
struct regulator_dev {struct qcom_battmgr *data;};
#define rdev_get_drvdata(rdev) ((rdev)->data)
/* DRIVER_FUNCTIONS */
int main(void) {
 struct qcom_battmgr b={.request_opcode=11,.request_property=77,.oem_client=(void *)1,.oem_service_up=true,.oem_service_generation=3,.asus_chg_end=80};
 struct qcom_battmgr_message m={.hdr={1,1,10},.intval={77,0,0}};
 qcom_battmgr_callback(&m,sizeof(m),&b);assert(b.ack==0 && decoded==0);
 m.hdr.opcode=11;m.intval.property=78;qcom_battmgr_callback(&m,sizeof(m),&b);assert(b.ack==0);
 m.intval.property=77;qcom_battmgr_callback(&m,sizeof(m),&b);assert(b.ack==1 && decoded==1 && b.request_opcode==0);
 qcom_battmgr_callback(&m,sizeof(m),&b);assert(b.ack==1 && decoded==1);
 b.request_opcode=11;qcom_battmgr_callback(&m,sizeof(m.hdr),&b);assert(b.ack==2 && b.request_poisoned && b.error==-EPROTO);
 /* Tiny headers never read past the supplied message. */
 qcom_battmgr_callback(&m,1,&b);assert(b.ack==2);
 struct regulator_dev rdev={&b};
 assert(qcom_battmgr_btm_otg_send_locked(&b,true)==0 && b.btm_otg_confirmed==1 && b.btm_otg_generation==3);
 request_error=-ETIMEDOUT;b.oem_request_poisoned=true;
 assert(qcom_battmgr_btm_otg_send_locked(&b,false)==-ETIMEDOUT && raw_off==1);
 assert(qcom_battmgr_btm_otg_is_enabled(&rdev)==-EIO);
 request_error=0;b.oem_request_poisoned=false;b.oem_service_generation=4;
 assert(qcom_battmgr_btm_otg_is_enabled(&rdev)==-EIO);
 assert(qcom_battmgr_btm_otg_send_locked(&b,false)==0 && qcom_battmgr_btm_otg_is_enabled(&rdev)==0);
 struct device dev={.data=&b};
 assert(qcom_battmgr_suspend(&dev)==0 && b.asus_chg_paused);
 pause_error=-ETIMEDOUT;assert(qcom_battmgr_suspend(&dev)==-ETIMEDOUT && kicks==1);
 b.asus_chg_end=100;assert(qcom_battmgr_suspend(&dev)==0);
 return 0;
}
