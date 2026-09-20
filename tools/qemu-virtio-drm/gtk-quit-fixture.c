/* Host-only ARM64 GTK fixture: distinguish quit return from an application hold. */
#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>

static GtkWidget *window;
static gboolean delayed_hold;

static void mark(const char *phase)
{
	g_print("GTK_QUIT_FIXTURE phase=%s monotonic_us=%" G_GINT64_FORMAT "\n",
		phase, g_get_monotonic_time());
}

static gboolean release_hold(gpointer data)
{
	mark("RELEASE_HOLD");
	g_application_release(G_APPLICATION(data));
	return G_SOURCE_REMOVE;
}

static void quit_action(GSimpleAction *action, GVariant *parameter, gpointer data)
{
	(void)action;
	(void)parameter;
	if (delayed_hold)
		g_application_hold(G_APPLICATION(data));
	gtk_widget_destroy(window);
	window = NULL;
	mark("DESTROY_RETURN");
	if (delayed_hold)
		g_timeout_add(250, release_hold, data);
	else
		g_usleep(250000);
	mark("QUIT_HANDLER_RETURN");
}

static gboolean request_quit(gpointer data)
{
	g_action_group_activate_action(G_ACTION_GROUP(data), "quit", NULL);
	mark("QUIT_CALL_RETURN");
	return G_SOURCE_REMOVE;
}

static void activate(GtkApplication *application, gpointer data)
{
	(void)data;
	window = gtk_application_window_new(application);
	gtk_window_set_title(GTK_WINDOW(window), "ROG5 quit boundary fixture");
	gtk_window_set_default_size(GTK_WINDOW(window), 200, 100);
	gtk_widget_show_all(window);
	g_timeout_add(100, request_quit, application);
}

static void shutdown_app(GApplication *application, gpointer data)
{
	(void)application;
	(void)data;
	mark("SHUTDOWN");
	g_settings_sync();
}

int main(int argc, char **argv)
{
	if (argc != 2 || (strcmp(argv[1], "inside") && strcmp(argv[1], "hold")))
		return 2;
	delayed_hold = !strcmp(argv[1], "hold");
	GtkApplication *app = gtk_application_new("org.rog5.QuitFixture",
						G_APPLICATION_NON_UNIQUE);
	GSimpleAction *action = g_simple_action_new("quit", NULL);
	g_signal_connect(action, "activate", G_CALLBACK(quit_action), app);
	g_action_map_add_action(G_ACTION_MAP(app), G_ACTION(action));
	g_object_unref(action);
	g_signal_connect(app, "activate", G_CALLBACK(activate), NULL);
	/* The probe adds its ordinary BEFORE and later AFTER handlers in run().
	 * Keep our explicit sync between those markers without replacing GTK's
	 * class closure; this fixture uses an after-handler, unlike Mousepad.
	 */
	g_signal_connect_after(app, "shutdown", G_CALLBACK(shutdown_app), NULL);
	int result = g_application_run(G_APPLICATION(app), 1, argv);
	mark("RUN_RETURN");
	g_object_unref(app);
	return result;
}
