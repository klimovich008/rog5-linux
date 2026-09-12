/* Standalone virtual-guest experiment, not Denial or phone qualification.
 * Each mode runs in a fresh process. The exit mode deliberately omits worker
 * EGL release to measure this implementation's behavior after pthread_join.
 * One owner reads eglGetError immediately after each measured operation.
 */
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <gbm.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static EGLDisplay display;
static EGLContext context;
static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition = PTHREAD_COND_INITIALIZER;
static int ready, proceed;
static const char *mode;

static void require(int ok, const char *stage)
{
    if (!ok) {
        fprintf(stderr, "FAIL EGL thread probe: %s\n", stage);
        exit(1);
    }
}

static EGLBoolean measure(const char *stage, EGLBoolean ok)
{
    EGLint error = eglGetError();
    printf("EGL_THREAD mode=%s stage=%s ok=%u error=0x%04x\n",
           mode, stage, ok, error);
    fflush(stdout);
    require((ok && error == EGL_SUCCESS) || (!ok && error != EGL_SUCCESS),
            "EGL result/error disagree");
    return ok;
}

static void *worker(void *unused)
{
    (void)unused;
    require(measure("worker-api", eglBindAPI(EGL_OPENGL_ES_API)), "worker API");
    require(measure("worker-bind", eglMakeCurrent(display, EGL_NO_SURFACE,
                                                 EGL_NO_SURFACE, context)), "worker bind");
    const char *renderer = (const char *)glGetString(GL_RENDERER);
    require(renderer != NULL && glGetError() == GL_NO_ERROR, "GL renderer query");
    printf("EGL_THREAD_RENDERER %s\n", renderer);
    require(strstr(renderer, "virgl") != NULL, "probe requires virtual VirGL renderer");
    require(pthread_mutex_lock(&mutex) == 0, "worker lock");
    ready = 1;
    require(pthread_cond_signal(&condition) == 0, "worker ready");
    while (!proceed)
        require(pthread_cond_wait(&condition, &mutex) == 0, "worker wait");
    require(pthread_mutex_unlock(&mutex) == 0, "worker unlock");
    if (!strcmp(mode, "unbind"))
        require(measure("worker-release", eglMakeCurrent(display, EGL_NO_SURFACE,
                                                        EGL_NO_SURFACE, EGL_NO_CONTEXT)),
                "worker unbind");
    else if (!strcmp(mode, "release"))
        require(measure("worker-release", eglReleaseThread()), "worker release");
    return NULL;
}

int main(int argc, char **argv)
{
    require(argc == 2, "expected exit, unbind or release mode");
    mode = argv[1];
    require(!strcmp(mode, "exit") || !strcmp(mode, "unbind") || !strcmp(mode, "release"),
            "unknown mode");
    /* Refuse accidental execution outside the explicitly marked virtual guest. */
    char cmdline[4096] = {0};
    FILE *input = fopen("/proc/cmdline", "r");
    require(input != NULL, "guest cmdline");
    require(fgets(cmdline, sizeof(cmdline), input) != NULL, "read guest cmdline");
    fclose(input);
    require(strstr(cmdline, "rog5.virtual_drm=1") != NULL, "virtual guest marker");
    int fd = open("/dev/dri/card0", O_RDWR | O_CLOEXEC);
    require(fd >= 0, "open guest DRM");
    struct gbm_device *gbm = gbm_create_device(fd);
    require(gbm != NULL, "GBM device");
    display = eglGetPlatformDisplay(EGL_PLATFORM_GBM_KHR, gbm, NULL);
    require(display != EGL_NO_DISPLAY, "GBM EGL display");
    EGLint major, minor;
    require(measure("initialize", eglInitialize(display, &major, &minor)), "initialize");
    require(measure("main-api", eglBindAPI(EGL_OPENGL_ES_API)), "main API");
    const char *extensions = eglQueryString(display, EGL_EXTENSIONS);
    require(extensions && strstr(extensions, "EGL_KHR_surfaceless_context") &&
            strstr(extensions, "EGL_KHR_no_config_context"), "surfaceless configless support");
    const EGLint attributes[] = {EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE};
    context = eglCreateContext(display, NULL, EGL_NO_CONTEXT, attributes);
    require(measure("create", context != EGL_NO_CONTEXT), "create GLES3 context");
    pthread_t thread;
    require(pthread_create(&thread, NULL, worker, NULL) == 0, "create worker");
    require(pthread_mutex_lock(&mutex) == 0, "main lock");
    while (!ready)
        require(pthread_cond_wait(&condition, &mutex) == 0, "main wait");
    EGLBoolean collision = eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, context);
    EGLint collision_error = eglGetError();
    printf("EGL_THREAD mode=%s stage=live-collision ok=%u error=0x%04x\n",
           mode, collision, collision_error);
    require(!collision && collision_error == EGL_BAD_ACCESS, "live owner must refuse transfer");
    proceed = 1;
    require(pthread_cond_signal(&condition) == 0, "release worker wait");
    require(pthread_mutex_unlock(&mutex) == 0, "main unlock");
    require(pthread_join(thread, NULL) == 0, "join worker");
    EGLBoolean acquired = measure("after-join", eglMakeCurrent(display, EGL_NO_SURFACE,
                                                             EGL_NO_SURFACE, context));
    if (strcmp(mode, "exit"))
        require(acquired, "explicit release must permit transfer");
    if (acquired) {
        require(eglGetCurrentContext() == context, "transferred context identity");
        require(measure("main-release", eglReleaseThread()), "main release");
    }
    require(measure("destroy", eglDestroyContext(display, context)), "destroy context");
    require(measure("terminate", eglTerminate(display)), "terminate display");
    gbm_device_destroy(gbm);
    close(fd);
    printf("PASS EGL thread probe mode=%s\n", mode);
    return 0;
}
