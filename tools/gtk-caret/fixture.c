/* Host adapters for executing extracted GTK functions; no Wayland/GTK runtime.
 * Protocol sinks, window coordinates and retrieve-surrounding are simulated.
 * Tests use short ASCII surrounding text; UTF-8 clipping is outside this seam. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#define TRUE 1
#define FALSE 0
#define ABS(x) abs(x)
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
typedef int gboolean;
typedef int gint;
typedef char gchar;
typedef struct {int x,y,width,height;} GdkRectangle;
typedef GdkRectangle cairo_rectangle_int_t;
struct zwp_text_input_v3 {int token;};
enum zwp_text_input_v3_change_cause {ZWP_TEXT_INPUT_V3_CHANGE_CAUSE_INPUT_METHOD, ZWP_TEXT_INPUT_V3_CHANGE_CAUSE_OTHER};
typedef struct Context {
 int enabled;void *window,*gesture;
 GdkRectangle cursor_rect;
 struct {char *text;int cursor_idx,anchor_idx;} surrounding;
 enum zwp_text_input_v3_change_cause surrounding_change;
 char *pending_commit;
 struct {char *text;} pending_preedit,current_preedit;
} GtkIMContextWayland;
typedef GtkIMContextWayland GtkIMContext;
typedef struct {GtkIMContext *current;int focused;struct zwp_text_input_v3 *text_input;unsigned serial,done_serial;} GtkIMContextWaylandGlobal;
static GtkIMContextWaylandGlobal *global;
#define GTK_IM_CONTEXT(x) (x)
#define GTK_IM_CONTEXT_WAYLAND(x) (x)
#define GTK_EVENT_CONTROLLER(x) (x)
#define GTK_IM_CONTEXT_CLASS(x) (x)
static void parent_reset(GtkIMContext *c) {(void)c;}
static struct {void (*reset)(GtkIMContext *);} parent_storage={parent_reset},*parent_class=&parent_storage;
static int commits,resets,retrieves,reenter,callback_action;
static GdkRectangle pending_rect,committed_rect;
static char pending_text[128],committed_text[128];
static int pending_cursor,committed_cursor,pending_cause,committed_cause;
static const char *app_text="line-01";static int app_cursor;
static void gtk_im_context_wayland_set_cursor_location(GtkIMContext *,GdkRectangle *);
static void gtk_im_context_wayland_set_surrounding(GtkIMContext *,const gchar *,gint,gint);
static void commit_state(GtkIMContextWayland *);
static void notify_surrounding_text(GtkIMContextWayland *);
static void notify_cursor_location(GtkIMContextWayland *);
static void notify_im_change(GtkIMContextWayland *,enum zwp_text_input_v3_change_cause);
static void notify_content_type(GtkIMContextWayland *c) {(void)c;}
static void gtk_event_controller_reset(void *p) {(void)p;resets++;}
static void gdk_window_get_root_coords(void *w,int x,int y,int *rx,int *ry) {(void)w;*rx=x+26;*ry=y+23;}
static void g_signal_emit_by_name(GtkIMContext *c,const char *name,gboolean *result) {
 if(strcmp(name,"retrieve-surrounding")) abort();retrieves++;
 gtk_im_context_wayland_set_surrounding(c,app_text,(int)strlen(app_text),app_cursor);
 if(reenter) {GdkRectangle rect=c->cursor_rect;gtk_im_context_wayland_set_cursor_location(c,&rect);}
 if(callback_action==1)global->current=NULL;
 if(callback_action==2)c->enabled=0;
 *result=TRUE;
}
static void zwp_text_input_v3_set_cursor_rectangle(struct zwp_text_input_v3 *p,int x,int y,int w,int h) {(void)p;pending_rect=(GdkRectangle){x,y,w,h};}
static void zwp_text_input_v3_set_surrounding_text(struct zwp_text_input_v3 *p,const char *text,int cursor,int anchor) {
 (void)p;(void)anchor;if(strlen(text)>=sizeof pending_text) abort();strcpy(pending_text,text);pending_cursor=cursor;
}
static void zwp_text_input_v3_set_text_change_cause(struct zwp_text_input_v3 *p,int cause) {(void)p;pending_cause=cause;}
static void zwp_text_input_v3_commit(struct zwp_text_input_v3 *p) {(void)p;commits++;committed_rect=pending_rect;strcpy(committed_text,pending_text);committed_cursor=pending_cursor;committed_cause=pending_cause;}
static void zwp_text_input_v3_enable(struct zwp_text_input_v3 *p) {(void)p;}
static void g_free(void *p) {free(p);}
static char *g_strndup(const char *p,size_t n) {return strndup(p,n);}
static const char *g_utf8_next_char(const char *p) {(void)p;abort();}
static const char *g_utf8_find_prev_char(const char *p,const char *end) {(void)p;(void)end;abort();}
static void g_warn_if_reached(void) {abort();}
static int g_strcmp0(const char *a,const char *b) {return a==b?0:!a?-1:!b?1:strcmp(a,b);}
static void text_input_delete_surrounding_text_apply(GtkIMContextWaylandGlobal *g) {(void)g;}
static void text_input_commit_apply(GtkIMContextWaylandGlobal *g) {(void)g;}
static void text_input_preedit_apply(GtkIMContextWaylandGlobal *g) {(void)g;}
/* INSERT_PRODUCTION */
static void check(int ok,const char *why) {if(!ok){fprintf(stderr,"FAIL: %s\n",why);exit(1);}}
int main(int argc,char **argv) {
 if(argc!=2)return 2;const char *name=argv[1];
 static struct zwp_text_input_v3 proxy={0};
 static GtkIMContextWayland c={.enabled=1,.window=&proxy,.gesture=&proxy,.cursor_rect={3,67,0,20}},other={0};
 static GtkIMContextWaylandGlobal state={.current=&c,.focused=1,.text_input=&proxy};global=&state;
 GdkRectangle low={65,1047,0,20};
 if(!strcmp(name,"reset-then-low")) {
  gtk_im_context_wayland_reset(&c);check(committed_rect.y==90,"reset publishes old spot");app_text="line-55";app_cursor=4;
  gtk_im_context_wayland_set_cursor_location(&c,&low);
  check(commits==2 && committed_rect.y==1070 && committed_rect.x==91,"new low spot must commit without release/key/focus");
  check(!strcmp(committed_text,"line-55") && committed_cursor==4 && committed_cause==1,"surrounding and cause must match geometry");check(resets==1,"large jump retains gesture reset");
 } else if(!strcmp(name,"unchanged")) {
  gtk_im_context_wayland_set_cursor_location(&c,&c.cursor_rect);check(!commits && !retrieves && !resets,"equal rectangle is no-op");
 } else if(!strcmp(name,"small-move")) {
  GdkRectangle small={4,68,0,20};gtk_im_context_wayland_set_cursor_location(&c,&small);check(commits==1 && committed_rect.y==91 && !resets,"small moves publish without gesture reset");
 } else if(!strcmp(name,"pending-done")) {
  state.serial=9;state.done_serial=3;gtk_im_context_wayland_set_cursor_location(&c,&low);check(commits==1 && state.serial==10 && state.done_serial==3,"outstanding done must not starve geometry");
  text_input_done(&state,&proxy,9);text_input_done(&state,&proxy,10);check(commits==1 && state.done_serial==10,"pure acknowledgements must not cause loop");
 } else if(!strcmp(name,"reentry")) {
  reenter=1;gtk_im_context_wayland_set_cursor_location(&c,&low);check(commits==1 && retrieves==1,"same-rect retrieval reentry terminates");
 } else if(!strcmp(name,"retrieve-focus-out") || !strcmp(name,"retrieve-disabled")) {
  callback_action=!strcmp(name,"retrieve-focus-out")?1:2;gtk_im_context_wayland_set_cursor_location(&c,&low);
  check(retrieves==1 && commits==0,"retrieval state change stops publication");
 } else if(!strcmp(name,"disabled-enable")) {
  c.enabled=0;gtk_im_context_wayland_set_cursor_location(&c,&low);check(!commits && c.cursor_rect.y==low.y,"disabled state caches only");enable(&c);check(commits==1 && committed_rect.y==1070,"enable publishes latest cached geometry");
 } else {
  if(!strcmp(name,"no-global"))global=NULL;
  else if(!strcmp(name,"no-proxy"))state.text_input=NULL;
  else if(!strcmp(name,"no-current"))state.current=NULL;
  else if(!strcmp(name,"wrong-current"))state.current=&other;
  else if(!strcmp(name,"unfocused"))state.focused=0;
  else if(!strcmp(name,"no-window"))c.window=NULL;
  else if(!strcmp(name,"disabled"))c.enabled=0;
  else return 2;
  gtk_im_context_wayland_set_cursor_location(&c,&low);check(!commits && !retrieves && c.cursor_rect.y==low.y,"inactive context must cache without protocol traffic");
 }
 free(c.surrounding.text);printf("PASS %s\n",name);return 0;
}
