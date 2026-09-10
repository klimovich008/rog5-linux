#define main indicator_main
#include "rog5-key-indicatord.c"
#undef main

int main(int argc, char **argv)
{
	struct led_device led;
	char retained[PATH_MAX];
	int descriptor;

	if (argc != 2 || validate_led_device(argv[1], &led, false) < 0)
		return 2;
	if (join_path(retained, sizeof(retained), argv[1], "brightness-retained") < 0 ||
	    rename(led.brightness_path, retained) < 0)
		return 3;
	descriptor = open(led.brightness_path, O_CREAT | O_EXCL | O_WRONLY, 0600);
	if (descriptor < 0 || write_all(descriptor, "0000000031\n", 11) < 0)
		return 4;
	close(descriptor);
	descriptor = open_led_brightness(&led, false);
	if (descriptor >= 0) {
		close(descriptor);
		return 5;
	}
	return 0;
}
