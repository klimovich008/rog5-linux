#include "common.h"
#define CS35L45_BOOST_LPMODE_CFG 1
#define CS35L45_BST_BPE_IL_LIM_THLD 2
#define CS35L45_LDPM_CONFIG 3
#define CS35L45_MIXER_PILOT0_INPUT 4
#define CS35L45_BLOCK_ENABLES2 5
#define CS35L45_GLOBAL_ENABLES 6
#define CS35L45_BBPE_EN_MASK 4
#define CS35L45_GLOBAL_EN_MASK 1
#define CS35L45_PCM_SRC_ZERO 0
#define CS35L45_PCM_SRC_DSP_TX2 9
#define CS35L45_POST_GLOBAL_EN_US 0
#define CS35L45_PRE_GLOBAL_DIS_US 0
#define SND_SOC_DAPM_POST_PMU 1
#define SND_SOC_DAPM_PRE_PMD 2
struct reg_sequence { unsigned int reg, def; };
struct regmap { unsigned int hw[8], cache[8]; bool corrupt_read, cached_read; int op, fail_at; };
struct cs35l45_private {
 struct device *dev; struct regmap *regmap; bool prot_regs_set, prot_fault, reset_held;
 struct { struct { bool running; } cs_dsp; } dsp;
 int *reset_gpio;
};
struct snd_kcontrol { int unused; };
struct snd_soc_component { struct cs35l45_private *data; };
struct snd_soc_dapm_widget { struct snd_soc_component *dapm; };
#define snd_soc_dapm_to_component(dapm) (dapm)
#define snd_soc_component_get_drvdata(component) ((component)->data)
#define usleep_range(a,b) ((void)0)
static int op(struct regmap *m) { return ++m->op == m->fail_at ? -EIO : 0; }
static int regmap_write(struct regmap *m, unsigned reg, unsigned val) {
 m->cache[reg]=val; if (op(m)) return -EIO; m->hw[reg]=val; return 0;
}
static int regmap_multi_reg_write(struct regmap *m, const struct reg_sequence *r, size_t n) {
 for (size_t i=0;i<n;i++) if (regmap_write(m,r[i].reg,r[i].def)) return -EIO;
 return 0;
}
static int regmap_write_bits(struct regmap *m, unsigned reg, unsigned mask, unsigned val) {
 return regmap_write(m,reg,(m->cache[reg]&~mask)|val);
}
static int read_register(struct regmap *m, unsigned reg, unsigned *val, bool cached) {
 if(op(m)) return -EIO;
 *val=cached?m->cache[reg]:m->hw[reg]; if(m->corrupt_read && !cached) *val ^= 1; return 0;
}
#define regmap_read_bypassed(m,r,v) read_register(m,r,v,false)
#define regmap_read_cached(m,r,v) read_register(m,r,v,true)
#define gpiod_set_value_cansleep(gpio,value) (*(gpio)=(value))
static int cs35l45_set_prot_regs(struct cs35l45_private *cs35l45, bool vendor);
static void cs35l45_prot_restore_failed(struct cs35l45_private *cs35l45);
/* DRIVER_FUNCTIONS */
int main(void) {
 struct regmap m={0}; int reset=1;
 struct cs35l45_private amp={.regmap=&m,.reset_gpio=&reset};
 struct snd_soc_component c={&amp}; struct snd_soc_dapm_widget w={&c};
 assert(cs35l45_set_prot_regs(&amp,true)==0 && amp.prot_regs_set);
 for(int fault=1;fault<=10;fault++) {
  amp.prot_regs_set=true; m.fail_at=fault; m.op=0;
  assert(cs35l45_set_prot_regs(&amp,false)==-EIO);
  assert(amp.prot_fault && amp.prot_regs_set);
  m.fail_at=0; cs35l45_prot_restore_failed(&amp); assert(m.hw[6]==0);
  assert(cs35l45_set_prot_regs(&amp,false)==0 && !amp.prot_fault);
 }
 /* Cached BBPE is clear while hardware still has it: force the write. */
 amp.prot_regs_set=true; m.cache[5]=0; m.hw[5]=4; m.op=0;
 assert(cs35l45_set_prot_regs(&amp,false)==0 && m.hw[5]==0);
 amp.prot_regs_set=true; m.corrupt_read=true;
 assert(cs35l45_set_prot_regs(&amp,false)==-EIO && amp.prot_fault);
 /* Firmware running must not bypass a latched restore fault. */
 amp.dsp.cs_dsp.running=true; m.hw[6]=0;
 assert(cs35l45_global_en_ev(&w,NULL,SND_SOC_DAPM_POST_PMU)==-EIO && m.hw[6]==0);
 m.corrupt_read=false; m.fail_at=m.op+1;
 cs35l45_prot_restore_failed(&amp); assert(amp.reset_held && reset==0);
 m.fail_at=0;
 assert(cs35l45_global_en_ev(&w,NULL,SND_SOC_DAPM_POST_PMU)==-EIO && m.hw[6]==0);
 assert(cs35l45_set_prot_regs(&amp,false)==-EIO);
 return 0;
}
