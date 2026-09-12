/* ABI fixture for the actual Rust executable; never a hardware renderer. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef void *H;
static const char *stage;
static int requested_major, requested_minor;
static int fault(const char *name) {
 const char *value = getenv("ROG5_FAKE_GLES_FAIL");
 fprintf(stderr, "CALL %s\n", name);
 stage = name;
 return value && !strcmp(value, name);
}
const char *eglQueryString(H d, int n) {
 (void)d; (void)n;
 return fault("extensions") ? "EGL_MESA_platform_surfaceless_suffix" : "EGL_MESA_platform_surfaceless";
}
H eglGetPlatformDisplay(unsigned p, H d, const intptr_t *a) { (void)p; (void)d; (void)a; return fault("display") ? NULL : (H)1; }
unsigned eglInitialize(H d, int *a, int *b) { (void)d; *a=1; *b=fault("version")?4:5; return !fault("initialize"); }
unsigned eglBindAPI(unsigned a) { (void)a; return !fault("bind"); }
unsigned eglChooseConfig(H d, const int *a, H *c, int size, int *n) { (void)d; (void)size; for (int i=0;a[i]!=0x3038;i+=2) if (a[i]==0x3040) fprintf(stderr,"REQUEST_CONFIG_ES %d\n",a[i+1]); *c=(H)2; *n=fault("no_config")?0:1; return !fault("config"); }
H eglCreatePbufferSurface(H d, H c, const int *a) { (void)d; (void)c; (void)a; return fault("surface")?NULL:(H)3; }
H eglCreateContext(H d, H c, H share, const int *a) {
 (void)d; (void)c; (void)share;
 requested_major=1; requested_minor=0;
 for (int i=0;a[i]!=0x3038;i+=2) {
  if (a[i]==0x3098) requested_major=a[i+1];
  if (a[i]==0x30fb) requested_minor=a[i+1];
 }
 fprintf(stderr,"REQUEST_CONTEXT %d.%d\n",requested_major,requested_minor);
 if (requested_major==3 && requested_minor==2 && fault("context32")) return NULL;
 return fault("context")?NULL:(H)4;
}
unsigned eglGetError(void) { return 0x3009; }
void glGetIntegerv(unsigned name, int *value) {
 int low=fault("gles2"), below=fault("below_requested"), negative=fault("negative_version");
 *value = name==0x821b ? (low?2:requested_major) : (low?0:below?1:negative?-1:requested_minor);
 fault("version_query");
}
unsigned eglMakeCurrent(H d, H r, H w, H c) { (void)d; (void)r; (void)w; return !fault(c?"current":"unbind"); }
unsigned eglDestroyContext(H d, H c) { (void)d; (void)c; return !fault("destroy_context"); }
unsigned eglDestroySurface(H d, H s) { (void)d; (void)s; return !fault("destroy_surface"); }
unsigned eglTerminate(H d) { (void)d; return !fault("terminate"); }
const char *glGetString(unsigned n) {
 if (fault("identity_null")) return NULL;
 if (n==0x1f01) {
  const char *renderer=getenv("ROG5_FAKE_GLES_RENDERER");
  return renderer?renderer:"llvmpipe (ABI fixture)";
 }
 return n==0x1f00?"offline fixture":requested_major==2?"OpenGL ES 2.0 fixture":"OpenGL ES 3.x fixture";
}
unsigned glGetError(void) {
 const char *value=getenv("ROG5_FAKE_GLES_FAIL");
 return value && ((!strcmp(value,"version_query") && stage && !strcmp(stage,"version_query")) || (!strcmp(value,"draw_error") && stage && !strcmp(stage,"draw")) || (!strcmp(value,"cleanup_error") && stage && !strcmp(stage,"delete_program")) || (!strcmp(value,"read_error") && stage && !strcmp(stage,"read")))?0x502:0;
}
unsigned glCreateShader(unsigned kind) { return fault(kind==0x8b31?"vertex_create":"fragment_create")?0:kind; }
void glShaderSource(unsigned s, int n, const char **p, const int *len) { (void)s; (void)n; (void)p; (void)len; }
void glCompileShader(unsigned s) { (void)s; }
void glGetShaderiv(unsigned s, unsigned p, int *v) { (void)p; *v=!fault(s==0x8b31?"vertex_compile":"fragment_compile"); }
void glDeleteShader(unsigned s) { (void)s; fault("delete_shader"); }
unsigned glCreateProgram(void) { return fault("program_create")?0:5; }
void glAttachShader(unsigned p, unsigned s) { (void)p; (void)s; }
void glBindAttribLocation(unsigned p, unsigned i, const char *n) { (void)p; (void)i; (void)n; }
void glLinkProgram(unsigned p) { (void)p; }
void glGetProgramiv(unsigned p, unsigned n, int *v) { (void)p; (void)n; *v=!fault("link"); }
void glUseProgram(unsigned p) { (void)p; }
void glDeleteProgram(unsigned p) { (void)p; fault("delete_program"); }
void glViewport(int x, int y, int w, int h) { (void)x; (void)y; (void)w; (void)h; }
void glDisable(unsigned x) { (void)x; }
void glClearColor(float r, float g, float b, float a) { (void)r; (void)g; (void)b; (void)a; }
void glClear(unsigned x) { (void)x; }
void glVertexAttribPointer(unsigned i, int n, unsigned t, unsigned char norm, int stride, const void *p) { (void)i; (void)n; (void)t; (void)norm; (void)stride; (void)p; }
void glEnableVertexAttribArray(unsigned i) { (void)i; }
void glDrawArrays(unsigned m, int first, int n) { (void)m; (void)first; (void)n; fault("draw"); }
void glReadPixels(int x, int y, int w, int h, unsigned fmt, unsigned type, void *data) {
 (void)x; (void)y; (void)w; (void)h; (void)fmt; (void)type;
 unsigned char *out=data;
 if (fault("stall")) { for (;;) pause(); }
 int corrupt=fault("read");
 for (int j=0;j<4;j++) for (int i=0;i<4;i++) {
  *out++ = corrupt?0:(unsigned char)((i+0.5)*255/4+0.5);
  *out++ = (unsigned char)((j+0.5)*255/4+0.5);
  *out++ = 64; *out++ = 255;
 }
}
