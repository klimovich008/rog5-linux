/* Offline GLib signal/observer fixture. No GTK, display or phone qualification. */
#include <gio/gio.h>
#include <glib-unix.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/prctl.h>
#include <unistd.h>

typedef struct { GApplication parent; } SignalApplication;
typedef struct { GApplicationClass parent; } SignalApplicationClass;
G_DEFINE_TYPE(SignalApplication, signal_application, G_TYPE_APPLICATION)
static guint signal_source;
static guint signals_seen;
static guint shutdowns;
static gboolean delay_shutdown;

static void mark(const char *stage)
{
    printf("SIGNAL_FIXTURE stage=%s pid=%ld monotonic_us=%" G_GINT64_FORMAT "\n",
           stage, (long)getpid(), g_get_monotonic_time());
}
static gboolean terminate(gpointer app)
{
    signals_seen++;
    signal_source = 0;
    mark("signal-callback");
    g_application_quit(app);
    return G_SOURCE_REMOVE;
}
static gboolean ready(gpointer unused)
{
    (void)unused;
    mark("ready");
    return G_SOURCE_REMOVE;
}
static void activate(GApplication *app)
{
    g_application_hold(app);
    signal_source = g_unix_signal_add(SIGTERM, terminate, app);
    if (!signal_source) _exit(3);
    g_idle_add(ready, NULL);
}
static void shutdown_app(GApplication *app)
{
    shutdowns++;
    mark("shutdown-enter");
    g_settings_sync();
    mark("external-sync-returned");
    /* Creates a known capture interval, not an application fix or larger grace. */
    if (delay_shutdown) g_usleep(250000);
    G_APPLICATION_CLASS(signal_application_parent_class)->shutdown(app);
    mark("shutdown-return");
}
static void signal_application_class_init(SignalApplicationClass *klass)
{
    GApplicationClass *app = G_APPLICATION_CLASS(klass);
    app->activate = activate;
    app->shutdown = shutdown_app;
}
static void signal_application_init(SignalApplication *self) { (void)self; }
int main(int argc, char **argv)
{
    if (argc != 2 || (strcmp(argv[1], "immediate") && strcmp(argv[1], "delayed"))) return 2;
    delay_shutdown = !strcmp(argv[1], "delayed");
    setvbuf(stdout, NULL, _IONBF, 0);
    /* Exercise the production identity guard; this remains a named fixture. */
    if (prctl(PR_SET_NAME, "mousepad", 0, 0, 0)) return 3;
    GApplication *app = g_object_new(signal_application_get_type(),
        "application-id", "org.rog5.SignalFixture", "flags", G_APPLICATION_NON_UNIQUE, NULL);
    int result = g_application_run(app, 1, argv);
    if (signal_source) g_source_remove(signal_source);
    g_object_unref(app);
    mark("run-return");
    return result || signals_seen != 1 || shutdowns != 1 ? 4 : 0;
}
