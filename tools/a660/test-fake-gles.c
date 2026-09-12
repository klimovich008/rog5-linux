#define _GNU_SOURCE
/* ABI fixture for the actual Rust executable; never a hardware renderer. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <dlfcn.h>
#include <poll.h>
#include <stdarg.h>
#include <sys/eventfd.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <sys/resource.h>
#include <linux/sync_file.h>
typedef void *H;
static const char *stage;
static int requested_major, requested_minor;
static int fence_fd=-1, consumer_fd=-1, import_fd=-1, poll_calls;
static void closed(int fd,const char *label);
static H current_context;
static int dma_fd=-1, dma_backing=-1, texture_count, framebuffer_count;
static unsigned bound_texture, attached_texture;
static int import_bound;
static unsigned char dma_pixels[64];
static int producer_created, consumer_created;
static int fault(const char *name) {
 const char *value = getenv("ROG5_FAKE_GLES_FAIL");
 fprintf(stderr, "CALL %s\n", name);
 stage = name;
 return value && !strcmp(value, name);
}
const char *eglQueryString(H d, int n) {
 (void)n;
 if (d && fault("dma_extension")) return "EGL_MESA_image_dma_buf_export_suffix EGL_EXT_image_dma_buf_import EGL_EXT_image_dma_buf_import_modifiers";
 if (d) return fault("native_extension")?"EGL_ANDROID_native_fence_sync_suffix EGL_KHR_fence_sync":"EGL_ANDROID_native_fence_sync EGL_KHR_fence_sync EGL_MESA_image_dma_buf_export EGL_EXT_image_dma_buf_import EGL_EXT_image_dma_buf_import_modifiers";
 return fault("extensions") ? "EGL_MESA_platform_surfaceless_suffix" : "EGL_MESA_platform_surfaceless";
}
H eglGetPlatformDisplay(unsigned p, H d, const intptr_t *a) { (void)p; (void)d; (void)a; return fault("display") ? NULL : (H)1; }
unsigned eglInitialize(H d, int *a, int *b) { (void)d; *a=1; *b=fault("version")?4:5; return !fault("initialize"); }
unsigned eglBindAPI(unsigned a) { (void)a; return !fault("bind"); }
unsigned eglChooseConfig(H d, const int *a, H *c, int size, int *n) { (void)d; (void)size; for (int i=0;a[i]!=0x3038;i+=2) if (a[i]==0x3040) fprintf(stderr,"REQUEST_CONFIG_ES %d\n",a[i+1]); *c=(H)2; *n=fault("no_config")?0:1; return !fault("config"); }
H eglCreatePbufferSurface(H d, H c, const int *a) { (void)d; (void)c; (void)a; return consumer_created ? (fault("consumer_surface")?NULL:(H)13) : (fault("surface")?NULL:(H)3); }
H eglCreateContext(H d, H c, H share, const int *a) {
 (void)d; (void)c; if (share) abort();
 if (producer_created) {
  if (fault("consumer_context")) return NULL;
  consumer_created=1; return (H)14;
 }
 requested_major=1; requested_minor=0;
 for (int i=0;a[i]!=0x3038;i+=2) {
  if (a[i]==0x3098) requested_major=a[i+1];
  if (a[i]==0x30fb) requested_minor=a[i+1];
 }
 fprintf(stderr,"REQUEST_CONTEXT %d.%d\n",requested_major,requested_minor);
 if (requested_major==3 && requested_minor==2 && fault("context32")) return NULL;
 if (fault("context")) return NULL;
 producer_created=1; return (H)4;
}
unsigned eglGetError(void) { return 0x3009; }
void glGetIntegerv(unsigned name, int *value) {
 int low=fault("gles2"), below=fault("below_requested"), negative=fault("negative_version");
 *value = name==0x821b ? (low?2:requested_major) : (low?0:below?1:negative?-1:requested_minor);
 fault("version_query");
}
unsigned eglMakeCurrent(H d, H r, H w, H c) {
 (void)d;
 if (r!=w || (c==(H)14 && r!=(H)13) || (c==(H)4 && r!=(H)3)) abort();
 const char *name=!c?"unbind":c==(H)14?"consumer_current":current_context==(H)14?"restore_current":"current";
 if (fault(name)) return 0;
 current_context=c; return 1;
}
unsigned eglDestroyContext(H d, H c) { (void)d; (void)c; return !fault(c==(H)14?"consumer_destroy":"destroy_context"); }
unsigned eglDestroySurface(H d, H s) { (void)d; (void)s; return !fault(s==(H)13?"consumer_surface_destroy":"destroy_surface"); }
unsigned eglTerminate(H d) {
 (void)d;
 const char *value=getenv("ROG5_FAKE_GLES_FAIL");
 if (value && !strcmp(value,"import_destroy") && import_fd>=0) {
  if (fcntl(import_fd,F_GETFD)==-1 || close(import_fd)) abort();
  closed(import_fd,"IMPORT_FD_CLOSED_AT_TERMINATE"); import_fd=-1;
 }
 return !fault("terminate");
}
const char *glGetString(unsigned n) {
 if (fault("identity_null")) return NULL;
 if (n==0x1f01) {
  const char *renderer=getenv("ROG5_FAKE_GLES_RENDERER");
  return renderer?renderer:"llvmpipe (ABI fixture)";
 }
 return n==0x1f00?"offline fixture":requested_major==2?"OpenGL ES 2.0 fixture":"OpenGL ES 3.x fixture";
}
unsigned glGetError(void) {
 const char *dma_fault=getenv("ROG5_FAKE_GLES_FAIL");
 if (dma_fault && stage && !strcmp(dma_fault,stage) &&
     (!strcmp(stage,"texture_allocate") || !strcmp(stage,"image_texture") ||
      !strcmp(stage,"dma_finish") || !strcmp(stage,"texture_delete") || !strcmp(stage,"framebuffer_delete"))) return 0x502;
 const char *value=getenv("ROG5_FAKE_GLES_FAIL");
 return value && ((!strcmp(value,"consumer_flush") && stage && !strcmp(stage,"consumer_flush")) || (!strcmp(value,"flush") && stage && !strcmp(stage,"flush")) || (!strcmp(value,"version_query") && stage && !strcmp(stage,"version_query")) || (!strcmp(value,"draw_error") && stage && !strcmp(stage,"draw")) || (!strcmp(value,"cleanup_error") && stage && !strcmp(stage,"delete_program")) || (!strcmp(value,"read_error") && stage && !strcmp(stage,"read")))?0x502:0;
}
unsigned glCreateShader(unsigned kind) { return fault(kind==0x8b31?"vertex_create":"fragment_create")?0:kind; }
void glShaderSource(unsigned s, int n, const char **p, const int *len) { (void)s; (void)n; (void)p; (void)len; }
void glCompileShader(unsigned s) { (void)s; }
void glGetShaderiv(unsigned s, unsigned p, int *v) { (void)p; *v=!fault(s==0x8b31?"vertex_compile":"fragment_compile"); }
void glDeleteShader(unsigned s) { if (current_context!=(H)4) abort(); (void)s; fault("delete_shader"); }
unsigned glCreateProgram(void) { return fault("program_create")?0:5; }
void glAttachShader(unsigned p, unsigned s) { (void)p; (void)s; }
void glBindAttribLocation(unsigned p, unsigned i, const char *n) { (void)p; (void)i; (void)n; }
void glLinkProgram(unsigned p) { (void)p; }
void glGetProgramiv(unsigned p, unsigned n, int *v) { (void)p; (void)n; *v=!fault("link"); }
void glUseProgram(unsigned p) { (void)p; }
void glDeleteProgram(unsigned p) { if (current_context!=(H)4) abort(); (void)p; fault("delete_program"); }
void glViewport(int x, int y, int w, int h) { (void)x; (void)y; (void)w; (void)h; }
void glDisable(unsigned x) { (void)x; }
void glClearColor(float r, float g, float b, float a) { (void)r; (void)g; (void)b; (void)a; }
void glClear(unsigned x) { (void)x; }
void glVertexAttribPointer(unsigned i, int n, unsigned t, unsigned char norm, int stride, const void *p) { (void)i; (void)n; (void)t; (void)norm; (void)stride; (void)p; }
void glEnableVertexAttribArray(unsigned i) { (void)i; }
void glDrawArrays(unsigned m, int first, int n) { (void)m; (void)first; (void)n; fault("draw");
 if (attached_texture==11) {
  for (int y=0;y<4;y++) for (int x=0;x<4;x++) {
   int i=(y*4+x)*4;
   dma_pixels[i]=(unsigned char)((x+0.5)*255/4+0.5);
   dma_pixels[i+1]=(unsigned char)((y+0.5)*255/4+0.5);
   dma_pixels[i+2]=64;dma_pixels[i+3]=255;
  }
 }
}
void glReadPixels(int x, int y, int w, int h, unsigned fmt, unsigned type, void *data) {
 (void)x; (void)y; (void)w; (void)h; (void)fmt; (void)type;
 unsigned char *out=data;
 if (fault("stall")) { for (;;) pause(); }
 int corrupt=fault("read");
 if (attached_texture==12) {
  if (dma_backing<0 || pread(dma_backing,data,64,0)!=64) abort();
  if (fault("dma_corrupt")) out[20]^=32;
  return;
 }
 for (int j=0;j<4;j++) for (int i=0;i<4;i++) {
  *out++ = corrupt?0:(unsigned char)((i+0.5)*255/4+0.5);
  *out++ = (unsigned char)((j+0.5)*255/4+0.5);
  *out++ = 64; *out++ = 255;
 }
}

void glFlush(void) { fault(current_context==(H)14?"consumer_flush":"flush"); }
H eglCreateSync(H display, unsigned type, const intptr_t *attributes) {
 (void)display;
 if (type!=0x3144) abort();
 if (attributes) {
  if (current_context!=(H)14 || attributes[0]!=0x3145 || attributes[2]!=0x3038 || attributes[1]<0) abort();
  import_fd=(int)attributes[1];
  if (import_fd==fence_fd || fcntl(import_fd,F_GETFD)==-1) abort();
  return fault("fence_import")?NULL:(H)29;
 }
 if (current_context==(H)14) return fault("consumer_fence_create")?NULL:(H)19;
 return fault("fence_create")?NULL:(H)9;
}
unsigned eglWaitSync(H display,H sync,int flags) {
 (void)display;
 if (current_context!=(H)14 || sync!=(H)29 || flags) abort();
 if (fault("server_stall")) { for (;;) pause(); }
 return !fault("server_wait");
}
static int export_fence(H display, H sync) {
 (void)display;
 int consumer=sync==(H)19;
 if (fault(consumer?"consumer_export":"fence_export")) return -1;
 const char *value=getenv("ROG5_FAKE_GLES_FAIL");
 int fd=eventfd(value && !strcmp(value,consumer?"consumer_timeout":"fence_timeout")?0:1,EFD_CLOEXEC|EFD_NONBLOCK);
 if (consumer) consumer_fd=fd; else fence_fd=fd;
 if (value && !strcmp(value,"duplicate_fd") && !consumer) {
  struct rlimit limit;
  if (fd<0 || getrlimit(RLIMIT_NOFILE,&limit)) abort();
  limit.rlim_cur=(rlim_t)fd+1;
  if (setrlimit(RLIMIT_NOFILE,&limit)) abort();
 }
 return fd;
}
static unsigned dma_query(H,H,int *,int *,uint64_t *);
static unsigned dma_export(H,H,int *,int *,int *);
static void image_texture(unsigned,H);
H eglGetProcAddress(const char *name) {
 if (!strcmp(name,"eglExportDMABUFImageQueryMESA")) return fault("dma_symbol")?NULL:(H)dma_query;
 if (!strcmp(name,"eglExportDMABUFImageMESA")) return fault("dma_symbol")?NULL:(H)dma_export;
 if (!strcmp(name,"glEGLImageTargetTexture2DOES")) return fault("dma_symbol")?NULL:(H)image_texture;
 if (strcmp(name,"eglDupNativeFenceFDANDROID")) abort();
 return fault("fence_symbol")?NULL:(H)export_fence;
}
static void closed(int fd,const char *label) {
 if (fd<0) return;
 if (fcntl(fd,F_GETFD)!=-1 || errno!=EBADF) abort();
 fprintf(stderr,"%s\n",label);
}
unsigned eglDestroySync(H display, H sync) {
 (void)display;
 if (sync==(H)29) {
  if (fault("import_destroy")) return 0;
  if (close(import_fd)) abort();
  closed(import_fd,"IMPORT_FD_CLOSED"); import_fd=-1; return 1;
 }
 if (sync==(H)19) {
  closed(consumer_fd,"CONSUMER_FD_CLOSED");consumer_fd=-1;
  return !fault("consumer_fence_destroy");
 }
 const char *value=getenv("ROG5_FAKE_GLES_FAIL");
 if (value && !strcmp(value,"fence_import")) closed(import_fd,"IMPORT_FD_CLOSED");
 closed(fence_fd,"FENCE_FD_CLOSED");
 return !fault("fence_destroy");
}
int poll(struct pollfd *fds,nfds_t count,int timeout) {
 const char *value=getenv("ROG5_FAKE_GLES_FAIL");
 if (count==1 && fds[0].fd==fence_fd) {
  if (value && !strcmp(value,"fence_eintr") && poll_calls++==0) { errno=EINTR; return -1; }
  if (value && !strcmp(value,"fence_poll_error")) { fds[0].revents=POLLIN|POLLERR; return 1; }
 }
 int (*real_poll)(struct pollfd *,nfds_t,int)=dlsym(RTLD_NEXT,"poll");
 if (!real_poll) abort();
 return real_poll(fds,count,timeout);
}
int ioctl(int fd,unsigned long request,...) {
 va_list args;va_start(args,request);struct sync_file_info *info=va_arg(args,void *);va_end(args);
 if ((fd!=fence_fd && fd!=consumer_fd) || request!=SYNC_IOC_FILE_INFO) { errno=ENOTTY;return -1; }
 if (info->flags || info->num_fences || info->pad || info->sync_fence_info) abort();
 int pending=fault(fd==consumer_fd?"consumer_pending":"fence_pending"),negative=fault(fd==consumer_fd?"consumer_negative":"fence_negative");
 if (fault(fd==consumer_fd?"consumer_info":"fence_info")) { errno=EINVAL;return -1; }
 info->status=pending?0:negative?-5:1;info->num_fences=1;return 0;
}

void glFinish(void) { fault("dma_finish"); }
void glGenTextures(int count,unsigned *texture) {
 if (count!=1) abort();
 *texture=fault("texture_create")?0:(unsigned)(11+texture_count++);
}
void glBindTexture(unsigned target,unsigned texture) { if (target!=0x0de1) abort();bound_texture=texture; }
void glTexParameteri(unsigned target,unsigned name,int value) { (void)target;(void)name;(void)value; }
void glTexImage2D(unsigned target,int level,int format,int width,int height,int border,unsigned external,unsigned type,const void *data) {
 if (target!=0x0de1 || level || format!=0x8058 || width!=4 || height!=4 || border || external!=0x1908 || type!=0x1401 || data) abort();
 memset(dma_pixels,0,sizeof(dma_pixels));fault("texture_allocate");
}
void glDeleteTextures(int count,const unsigned *texture) { (void)texture;if (count!=1 || current_context!=(H)4) abort();fault("texture_delete"); }
void glGenFramebuffers(int count,unsigned *framebuffer) { if (count!=1) abort();*framebuffer=fault("framebuffer_create")?0:(unsigned)(31+framebuffer_count++); }
void glBindFramebuffer(unsigned target,unsigned framebuffer) { (void)framebuffer;if (target!=0x8d40) abort(); }
void glFramebufferTexture2D(unsigned target,unsigned attachment,unsigned textarget,unsigned texture,int level) {
 if (target!=0x8d40 || attachment!=0x8ce0 || textarget!=0x0de1 || level) abort();
 attached_texture=texture;
}
unsigned glCheckFramebufferStatus(unsigned target) { (void)target;return (fault("framebuffer_incomplete") || (attached_texture==12 && !import_bound))?0x8cd6:0x8cd5; }
void glDeleteFramebuffers(int count,const unsigned *framebuffer) { (void)framebuffer;if (count!=1 || current_context!=(H)4) abort();fault("framebuffer_delete"); }
H eglCreateImage(H display,H context,unsigned target,H buffer,const intptr_t *attributes) {
 (void)display;
 if (target==0x30b1) {
  if (context!=(H)4 || buffer!=(H)11 || attributes[0]!=0x30bc || attributes[1] || attributes[2]!=0x30d2 || attributes[3]!=1 || attributes[4]!=0x3038) abort();
  return fault("source_image")?NULL:(H)21;
 }
 if (target!=0x3270 || context || buffer) abort();
 intptr_t expected[]={0x3057,4,0x3056,4,0x3271,0x34324241,0x3272,dma_fd,0x3273,0,0x3274,16,0x3443,0,0x3444,0,0x3038};
 if (memcmp(attributes,expected,sizeof(expected))) abort();
 if (fault("dma_import")) return NULL;
 dma_backing=dup(dma_fd);if (dma_backing<0) abort();return (H)22;
}
unsigned eglDestroyImage(H display,H image) {
 (void)display;
 closed(dma_fd,"DMA_FD_CLOSED");
 if (image==(H)22) { if (close(dma_backing)) abort();dma_backing=-1; }
 return !fault("dma_destroy");
}
static unsigned dma_query(H display,H image,int *fourcc,int *planes,uint64_t *modifiers) {
 (void)display;if (image!=(H)21) abort();
 *fourcc=fault("dma_format")?0:0x34324241;*planes=fault("dma_planes")?4:1;
 for (int i=0;i<*planes;i++) modifiers[i]=fault("dma_modifier")?1:0;
 return !fault("dma_query");
}
static unsigned dma_export(H display,H image,int *fd,int *stride,int *offset) {
 (void)display;if (image!=(H)21) abort();
 if (fault("dma_export")) return 0;
 *stride=fault("dma_stride")?1:16;*offset=fault("dma_offset")?-1:0;
 if (fault("dma_fd")) { *fd=-1;return 1; }
 dma_fd=memfd_create("dma-buf-ABI-fixture",MFD_CLOEXEC);
 if (dma_fd<0 || write(dma_fd,dma_pixels,sizeof(dma_pixels))!=sizeof(dma_pixels)) abort();
 *fd=dma_fd;return !fault("dma_export_partial");
}
static void image_texture(unsigned target,H image) {
 if (target!=0x0de1 || image!=(H)22 || bound_texture!=12) abort();
 if (!fault("image_texture")) import_bound=1;
}
