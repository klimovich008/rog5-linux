#include "common.h"
#define DP_LINK_STATUS_SIZE 6
#define DP_TRAINING_NONE 0
#define DP_TRAINING_1 1
#define DP_TRAINING_2 2
typedef uint8_t u8;
struct phy { int count; };
struct msm_dp_ctrl { int unused; };
struct msm_dp_ctrl_private {struct msm_dp_ctrl msm_dp_ctrl;struct phy *phy;bool phy_initialized;struct {struct {int num_lanes;} link_params;} *link;void *aux;};
static int init_error,exit_error,training_error=-EIO,tries,reinitialisations;
static int phy_init(struct phy *phy) {if(init_error)return init_error;phy->count++;return 0;}
static int phy_exit(struct phy *phy) {if(exit_error)return exit_error;phy->count--;assert(phy->count>=0);return 0;}
static void msm_dp_ctrl_phy_reset(struct msm_dp_ctrl_private *ctrl) { }
static int msm_dp_ctrl_setup_main_link(struct msm_dp_ctrl_private *ctrl,unsigned int *step) {tries++;*step=0;return training_error;}
static int msm_dp_aux_is_link_connected(void *aux) {return true;}
static void drm_dp_dpcd_read_link_status(void *aux,u8 *status) { }
static int msm_dp_ctrl_link_rate_down_shift(struct msm_dp_ctrl_private *ctrl) {return 0;}
static int msm_dp_ctrl_link_lane_down_shift(struct msm_dp_ctrl_private *ctrl) {return 0;}
static bool msm_dp_ctrl_clock_recovery_any_ok(u8 *status,int lanes) {return true;}
static bool drm_dp_clock_recovery_ok(u8 *status,int lanes) {return true;}
#define DP_PHY_DPRX 0
static void msm_dp_ctrl_clear_training_pattern(struct msm_dp_ctrl_private *ctrl,int phy) { }
static int msm_dp_ctrl_reinitialize_mainlink(struct msm_dp_ctrl_private *ctrl) {reinitialisations++;return 0;}
#define DRM_ERROR(...) ((void)0)
/* DRIVER_FUNCTIONS */
int main(void) {
 struct phy phy={0};struct msm_dp_ctrl_private ctrl={.phy=&phy};
 assert(msm_dp_ctrl_train_link_downshift(&ctrl)==-ETIMEDOUT);
 assert(tries==4 && reinitialisations==4);
 training_error=0;assert(msm_dp_ctrl_train_link_downshift(&ctrl)==0 && tries==5);
 init_error=-EIO;assert(msm_dp_ctrl_phy_init(&ctrl.msm_dp_ctrl)==-EIO && !ctrl.phy_initialized && phy.count==0);
 assert(msm_dp_ctrl_phy_exit(&ctrl.msm_dp_ctrl)==0 && phy.count==0);
 init_error=0;assert(msm_dp_ctrl_phy_init(&ctrl.msm_dp_ctrl)==0 && phy.count==1);
 assert(msm_dp_ctrl_phy_init(&ctrl.msm_dp_ctrl)==0 && phy.count==1);
 exit_error=-EIO;assert(msm_dp_ctrl_phy_exit(&ctrl.msm_dp_ctrl)==-EIO && ctrl.phy_initialized && phy.count==1);
 exit_error=0;assert(msm_dp_ctrl_phy_exit(&ctrl.msm_dp_ctrl)==0 && phy.count==0);
 assert(msm_dp_ctrl_phy_init(&ctrl.msm_dp_ctrl)==0 && phy.count==1);
 return 0;
}
