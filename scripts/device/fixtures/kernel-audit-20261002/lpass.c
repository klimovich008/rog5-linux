#include "common.h"
#define AFE_LPASS_CORE_HW_BLOCK_MAX 8
#define APR_BASIC_RSP_RESULT 1
#define AFE_CMD_REMOTE_LPASS_CORE_HW_VOTE_REQUEST 2
#define AFE_CMD_RSP_REMOTE_LPASS_CORE_HW_VOTE_REQUEST 3
#define AFE_CMD_REMOTE_LPASS_CORE_HW_DEVOTE_REQUEST 4
#define APR_HDR_SIZE sizeof(struct apr_hdr)
#define APR_HDR_FIELD(a,b,c) 0
#define APR_HDR_LEN(a) 0
#define APR_MSG_TYPE_SEQ_CMD 0
#define APR_PKT_VER 0
#define TIMEOUT_MS 3
struct apr_hdr { u32 hdr_field,pkt_size,src_port,dest_port,token,opcode; };
struct apr_pkt { struct apr_hdr hdr; };
struct apr_resp_pkt { struct apr_hdr hdr; void *payload; size_t payload_size; };
struct aprv2_ibasic_rsp_result_t { u32 opcode,status; };
struct afe_cmd_remote_lpass_core_hw_vote_request { u32 hw_block_id; char client_name[16]; };
struct afe_cmd_remote_lpass_core_hw_devote_request { u32 hw_block_id,client_handle; };
struct q6afe {
 struct device *dev; struct mutex lock; int wait; spinlock_t hw_vote_lock;
 u32 hw_vote_seq,hw_vote_token,hw_vote_opcode,hw_vote_handle;
 int hw_vote_error; bool hw_vote_pending;
 struct { bool wanted,confirmed,uncertain; u32 handle; } hw_vote[8];
 struct q6afe *apr;
};
static int scenario;
static void q6afe_hw_vote_reply(struct q6afe *afe, const struct apr_resp_pkt *data);
static int apr_send_pkt(struct q6afe *afe, struct apr_pkt *pkt) {
 u32 handle=77; struct aprv2_ibasic_rsp_result_t basic={pkt->hdr.opcode,0};
 struct apr_resp_pkt reply={.hdr={.token=pkt->hdr.token,.opcode=3},.payload=&handle,.payload_size=4};
 if(scenario==1) return 1; /* timeout */
 if(scenario==2) { reply.hdr.token--; q6afe_hw_vote_reply(afe,&reply); assert(afe->hw_vote_pending); reply.hdr.token++; }
 if(scenario==3) handle=0;
 if(scenario==4) reply.payload_size=2;
 if(scenario==5) {reply.hdr.opcode=99; q6afe_hw_vote_reply(afe,&reply); assert(afe->hw_vote_pending); reply.hdr.opcode=3;}
 if(pkt->hdr.opcode==4) { reply.hdr.opcode=1; reply.payload=&basic; reply.payload_size=8; }
 q6afe_hw_vote_reply(afe,&reply); return 1;
}
#define wake_up(wait) ((void)(wait))
#define wait_event_timeout(wait,condition,timeout) ((condition)?1:0)
/* DRIVER_FUNCTIONS */
int main(void) {
 struct q6afe afe={0}; struct device parent={.data=&afe},dev={.parent=&parent}; afe.apr=&afe;
 u32 handle=0;
 for(int s=0;s<=5;s++) {
  memset(&afe.hw_vote,0,sizeof(afe.hw_vote)); scenario=s;
  int rc=q6afe_vote_lpass_core_hw(&dev,2,"macro",&handle);
  if(s==1) { assert(rc==-ETIMEDOUT && afe.hw_vote[2].uncertain); assert(q6afe_vote_lpass_core_hw(&dev,2,"macro",&handle)==-EIO); }
  else if(s==3 || s==4) assert(rc==-EPROTO && afe.hw_vote[2].uncertain);
  else { assert(rc==0 && handle==77 && afe.hw_vote[2].confirmed); assert(q6afe_unvote_lpass_core_hw(&dev,2,handle)==0); assert(!afe.hw_vote[2].confirmed && !afe.hw_vote[2].wanted); }
 }
 scenario=0; memset(&afe.hw_vote,0,sizeof(afe.hw_vote));
 assert(q6afe_vote_lpass_core_hw(&dev,3,"dcodec",&handle)==0);
 scenario=1; assert(q6afe_unvote_lpass_core_hw(&dev,3,handle)==-ETIMEDOUT);
 assert(afe.hw_vote[3].confirmed && !afe.hw_vote[3].wanted && afe.hw_vote[3].uncertain);
 assert(q6afe_vote_lpass_core_hw(&dev,3,"dcodec",&handle)==-EIO);
 /* Every send, including failures and cross-block retries, got a new token. */
 assert(afe.hw_vote_seq==11);
 return 0;
}
