#include "common.h"
#define Q6ASM_STREAM_STOPPED 1
#define Q6ASM_STREAM_RUNNING 2
#define CMD_CLOSE 3
struct snd_dma_buffer { void *area; size_t bytes; };
struct audio_client { int unused; };
struct q6asm_dai_rtd {
 int state; bool stream_open,mapped,routed,cleanup_failed;
 struct audio_client *audio_client; u32 stream_id; struct snd_dma_buffer dma_buffer;
};
struct snd_pcm_runtime { void *private_data; };
struct snd_soc_pcm_runtime { struct { int id; } *dai_link; };
struct snd_pcm_substream { struct snd_pcm_runtime *runtime; struct snd_soc_pcm_runtime *rtd; int stream; struct snd_dma_buffer dma_buffer; };
struct snd_soc_component { struct device *dev; };
#define snd_soc_substream_to_rtd(substream) ((substream)->rtd)
static int close_error,unmap_error,closes,unmaps,routes,quarantines,frees;
static int q6asm_cmd(struct audio_client *ac,u32 id,int cmd) { closes++;return close_error; }
static int q6asm_unmap_memory_regions(int dir,struct audio_client *ac) {unmaps++;return unmap_error;}
static void q6routing_stream_close(int id,int dir) {routes++;}
static void q6asm_audio_client_quarantine(struct audio_client *ac) {quarantines++;}
static void q6asm_audio_client_free(struct audio_client *ac) {frees++;}
#define kfree(p) free(p)
/* DRIVER_FUNCTIONS */
int main(void) {
 struct device dev={0}; struct snd_soc_component component={&dev};
 struct { int id; } link={1}; struct snd_soc_pcm_runtime rtd={.dai_link=(void *)&link};
 struct snd_pcm_runtime runtime={0}; char backing[8];
 struct snd_pcm_substream stream={.runtime=&runtime,.rtd=&rtd,.dma_buffer={backing,8}};
 struct q6asm_dai_rtd p={.stream_open=true,.mapped=true,.routed=true};runtime.private_data=&p;
 /* IDLE after a format rejection still owns the stream and mapping. */
 assert(q6asm_dai_pcm_cleanup(&component,&stream)==0);
 assert(closes==1 && unmaps==1 && routes==1 && !p.stream_open && !p.mapped && !p.routed);
 p.stream_open=p.mapped=p.routed=true;close_error=-ETIMEDOUT;
 assert(q6asm_dai_pcm_cleanup(&component,&stream)==-ETIMEDOUT);
 assert(p.cleanup_failed && quarantines==1 && unmaps==1);
 assert(stream.dma_buffer.area==NULL && stream.dma_buffer.bytes==0 && p.dma_buffer.area==backing);
 close_error=0;assert(q6asm_dai_pcm_cleanup(&component,&stream)==-EIO && closes==2);
 assert(q6asm_dai_close(&component,&stream)==-EIO && frees==0 && runtime.private_data==NULL);
 /* Confirmed close with failed unmap also quarantines; no second close. */
 memset(&p,0,sizeof(p));p.mapped=true;p.stream_open=true;runtime.private_data=&p;
 stream.dma_buffer=(struct snd_dma_buffer){backing,8};unmap_error=-ETIMEDOUT;
 assert(q6asm_dai_pcm_cleanup(&component,&stream)==-ETIMEDOUT && !p.stream_open && p.mapped);
 assert(stream.dma_buffer.area==NULL && quarantines==2);
 /* Healthy final close independently cleans an open IDLE stream and drains callbacks. */
 unmap_error=0;struct q6asm_dai_rtd *ok=calloc(1,sizeof(*ok));ok->stream_open=true;ok->mapped=true;runtime.private_data=ok;
 assert(q6asm_dai_close(&component,&stream)==0 && frees==1 && quarantines==3);
 return 0;
}
