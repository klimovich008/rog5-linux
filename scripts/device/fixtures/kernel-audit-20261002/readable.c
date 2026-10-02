#include "common.h"
#include "readable-registers.h"
/* DRIVER_FUNCTIONS */
int main(void) {
 struct device dev = {0};
 assert(cs35l45_readable_reg(&dev, CS35L45_BOOST_LPMODE_CFG));
 assert(cs35l45_readable_reg(&dev, CS35L45_BST_BPE_IL_LIM_THLD));
 assert(cs35l45_readable_reg(&dev, CS35L45_LDPM_CONFIG));
 assert(cs35l45_readable_reg(&dev, CS35L45_MIXER_PILOT0_INPUT));
 assert(cs35l45_readable_reg(&dev, CS35L45_BLOCK_ENABLES2));
 assert(!cs35l45_readable_reg(&dev, 0x3814));
 assert(!cs35l45_readable_reg(&dev, 0x3c28));
 return 0;
}
