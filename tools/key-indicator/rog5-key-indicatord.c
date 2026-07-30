#define _GNU_SOURCE

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/signalfd.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/timerfd.h>
#include <time.h>
#include <unistd.h>

#define INPUT_CLASS_DIRECTORY "/sys/class/input"
#define INPUT_DEVICE_DIRECTORY "/dev/input"
#define INPUT_DEVICE_NAME "pmic_pwrkey"
#define LED_CLASS_DIRECTORY "/sys/class/leds/green:status"
#define LED_DEVICE_NAME "green:status"
#define LED_DRIVER_NAME "qcom-spmi-lpg"
#define LED_OF_NODE_SUFFIX \
	"/soc@0/spmi@c440000/pmic@2/pwm/led@2"
#define LED_MAX_BRIGHTNESS 511U
#define LED_PULSE_MILLISECONDS 180U
#define EVENT_BATCH_COUNT 16U
#define TEXT_MAX 4096U

/*
 * Stable Linux evdev UAPI subset. Keeping these definitions local lets the
 * static AArch64 build use the pinned minimal toolchain without installing a
 * full kernel-header package.
 */
struct input_event {
	struct timeval time;
	uint16_t type;
	uint16_t code;
	int32_t value;
};

#define EV_KEY 0x01U
#define EV_MAX 0x1fU
#define KEY_POWER 116U
#define KEY_MAX 0x2ffU
#define EVIOCGNAME(length) _IOC(_IOC_READ, 'E', 0x06, (length))
#define EVIOCGBIT(event_type, length) \
	_IOC(_IOC_READ, 'E', 0x20 + (event_type), (length))

#define BITS_PER_LONG (sizeof(unsigned long) * 8U)
#define BIT_WORD(bit) ((bit) / BITS_PER_LONG)
#define BIT_MASK(bit) (1UL << ((bit) % BITS_PER_LONG))

struct led_device {
	char directory[PATH_MAX];
	char brightness_path[PATH_MAX];
	char of_node[PATH_MAX];
	char driver[PATH_MAX];
	char trigger[TEXT_MAX];
	unsigned int max_brightness;
	unsigned int initial_brightness;
	unsigned int pulse_brightness;
};

static int contract_error(const char *reason, int error_number)
{
	fprintf(stderr, "contract_error=%s\n", reason);
	errno = error_number;
	return -1;
}

static bool has_path_suffix(const char *path, const char *suffix)
{
	size_t path_length = strlen(path);
	size_t suffix_length = strlen(suffix);

	return path_length >= suffix_length &&
		memcmp(path + path_length - suffix_length,
		       suffix, suffix_length) == 0;
}

static int join_path(char *output, size_t output_size,
		     const char *left, const char *right)
{
	int length = snprintf(output, output_size, "%s/%s", left, right);

	if (length < 0 || (size_t)length >= output_size) {
		errno = ENAMETOOLONG;
		return -1;
	}
	return 0;
}

static int read_text_file(const char *path, char *output, size_t output_size)
{
	ssize_t length;
	int descriptor;

	if (output_size < 2U) {
		errno = EINVAL;
		return -1;
	}
	descriptor = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (descriptor < 0)
		return -1;
	length = read(descriptor, output, output_size - 1U);
	if (length < 0) {
		int saved_errno = errno;

		close(descriptor);
		errno = saved_errno;
		return -1;
	}
	if ((size_t)length == output_size - 1U) {
		char extra;
		ssize_t extra_length = read(descriptor, &extra, 1U);

		if (extra_length != 0) {
			int saved_errno = extra_length < 0 ? errno : EOVERFLOW;

			close(descriptor);
			errno = saved_errno;
			return -1;
		}
	}
	if (close(descriptor) < 0)
		return -1;
	while (length > 0 &&
	       (output[length - 1] == '\n' ||
		output[length - 1] == '\r' ||
		output[length - 1] == ' ' ||
		output[length - 1] == '\t'))
		length--;
	output[length] = '\0';
	return 0;
}

static int parse_unsigned(const char *text, unsigned int *value)
{
	char *end = NULL;
	unsigned long parsed;

	errno = 0;
	parsed = strtoul(text, &end, 10);
	if (errno != 0 || end == text || *end != '\0' || parsed > UINT_MAX) {
		errno = EINVAL;
		return -1;
	}
	*value = (unsigned int)parsed;
	return 0;
}

static int read_unsigned_file(const char *path, unsigned int *value)
{
	char text[64];

	if (read_text_file(path, text, sizeof(text)) < 0)
		return -1;
	return parse_unsigned(text, value);
}

static int resolve_required_link(const char *path, char *resolved,
				 size_t resolved_size)
{
	char buffer[PATH_MAX];

	if (!realpath(path, buffer))
		return -1;
	if (strlen(buffer) >= resolved_size) {
		errno = ENAMETOOLONG;
		return -1;
	}
	strcpy(resolved, buffer);
	return 0;
}

static int validate_led_device(const char *directory,
			       struct led_device *led,
			       bool require_initially_off)
{
	char path[PATH_MAX];
	struct stat status;

	if (strlen(directory) >= sizeof(led->directory)) {
		errno = ENAMETOOLONG;
		return -1;
	}
	strcpy(led->directory, directory);

	if (join_path(path, sizeof(path), directory, "of_node") < 0 ||
	    resolve_required_link(path, led->of_node, sizeof(led->of_node)) < 0)
		return contract_error("led.of_node_resolve", errno);
	if (!has_path_suffix(led->of_node, LED_OF_NODE_SUFFIX)) {
		return contract_error("led.of_node", ENODEV);
	}

	if (join_path(path, sizeof(path), directory, "device/driver") < 0 ||
	    resolve_required_link(path, led->driver, sizeof(led->driver)) < 0)
		return contract_error("led.driver_resolve", errno);
	if (!has_path_suffix(led->driver, "/" LED_DRIVER_NAME)) {
		return contract_error("led.driver", ENODEV);
	}

	if (join_path(path, sizeof(path), directory, "max_brightness") < 0 ||
	    read_unsigned_file(path, &led->max_brightness) < 0)
		return -1;
	if (led->max_brightness != LED_MAX_BRIGHTNESS) {
		return contract_error("led.max_brightness", ERANGE);
	}

	if (join_path(path, sizeof(path), directory, "brightness") < 0)
		return -1;
	if (lstat(path, &status) < 0)
		return -1;
	if (!S_ISREG(status.st_mode))
		return contract_error("led.brightness_type", EINVAL);
	if (read_unsigned_file(path, &led->initial_brightness) < 0)
		return -1;
	if (require_initially_off && led->initial_brightness != 0U) {
		return contract_error("led.initial_brightness", EBUSY);
	}
	strcpy(led->brightness_path, path);

	if (join_path(path, sizeof(path), directory, "trigger") < 0 ||
	    read_text_file(path, led->trigger, sizeof(led->trigger)) < 0)
		return -1;
	if (!strstr(led->trigger, "[none]")) {
		return contract_error("led.trigger", EBUSY);
	}

	led->pulse_brightness = led->max_brightness / 16U;
	if (led->pulse_brightness == 0U)
		led->pulse_brightness = 1U;
	return 0;
}

static bool is_event_directory_name(const char *name)
{
	const char *cursor;

	if (strncmp(name, "event", 5U) != 0 || name[5] == '\0')
		return false;
	for (cursor = name + 5; *cursor; cursor++) {
		if (*cursor < '0' || *cursor > '9')
			return false;
	}
	return true;
}

static bool bit_is_set(const unsigned long *bits, unsigned int bit)
{
	return (bits[BIT_WORD(bit)] & BIT_MASK(bit)) != 0U;
}

static int validate_input_descriptor(int descriptor)
{
	unsigned long event_bits[BIT_WORD(EV_MAX) + 1U];
	unsigned long key_bits[BIT_WORD(KEY_MAX) + 1U];
	char name[256];

	memset(name, 0, sizeof(name));
	if (ioctl(descriptor, EVIOCGNAME(sizeof(name) - 1U), name) < 0)
		return -1;
	if (strcmp(name, INPUT_DEVICE_NAME) != 0) {
		return contract_error("input.name", ENODEV);
	}

	memset(event_bits, 0, sizeof(event_bits));
	if (ioctl(descriptor, EVIOCGBIT(0, sizeof(event_bits)), event_bits) < 0)
		return -1;
	if (!bit_is_set(event_bits, EV_KEY)) {
		return contract_error("input.ev_key", ENODEV);
	}

	memset(key_bits, 0, sizeof(key_bits));
	if (ioctl(descriptor, EVIOCGBIT(EV_KEY, sizeof(key_bits)), key_bits) < 0)
		return -1;
	if (!bit_is_set(key_bits, KEY_POWER)) {
		return contract_error("input.key_power", ENODEV);
	}
	return 0;
}

static int discover_input_device(char *selected_path,
				 size_t selected_path_size)
{
	DIR *directory;
	struct dirent *entry;
	unsigned int matches = 0U;
	int selected_descriptor = -1;
	int readdir_error = 0;

	directory = opendir(INPUT_CLASS_DIRECTORY);
	if (!directory)
		return -1;
	for (;;) {
		char name_path[PATH_MAX];
		char device_path[PATH_MAX];
		char name[256];
		struct stat status;
		int descriptor;
		int length;

		errno = 0;
		entry = readdir(directory);
		if (!entry) {
			readdir_error = errno;
			break;
		}

		if (!is_event_directory_name(entry->d_name))
			continue;
		length = snprintf(name_path, sizeof(name_path),
				  "%s/%s/device/name",
				  INPUT_CLASS_DIRECTORY, entry->d_name);
		if (length < 0 || (size_t)length >= sizeof(name_path))
			continue;
		if (read_text_file(name_path, name, sizeof(name)) < 0 ||
		    strcmp(name, INPUT_DEVICE_NAME) != 0)
			continue;
		length = snprintf(device_path, sizeof(device_path), "%s/%s",
				  INPUT_DEVICE_DIRECTORY, entry->d_name);
		if (length < 0 || (size_t)length >= sizeof(device_path))
			continue;
		if (stat(device_path, &status) < 0 ||
		    !S_ISCHR(status.st_mode))
			continue;
		descriptor = open(device_path,
				  O_RDONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
		if (descriptor < 0)
			continue;
		if (validate_input_descriptor(descriptor) < 0) {
			close(descriptor);
			continue;
		}
		matches++;
		if (matches == 1U) {
			if (strlen(device_path) >= selected_path_size) {
				close(descriptor);
				closedir(directory);
				errno = ENAMETOOLONG;
				return -1;
			}
			strcpy(selected_path, device_path);
			selected_descriptor = descriptor;
		} else {
			close(descriptor);
		}
	}
	if (readdir_error != 0) {
		if (selected_descriptor >= 0)
			close(selected_descriptor);
		closedir(directory);
		errno = readdir_error;
		return -1;
	}
	if (closedir(directory) < 0) {
		int saved_errno = errno;

		if (selected_descriptor >= 0)
			close(selected_descriptor);
		errno = saved_errno;
		return -1;
	}
	if (matches != 1U) {
		if (selected_descriptor >= 0)
			close(selected_descriptor);
		return contract_error("input.count",
				      matches == 0U ? ENODEV : EEXIST);
	}
	return selected_descriptor;
}

static int write_all(int descriptor, const char *buffer, size_t length)
{
	size_t offset = 0U;

	while (offset < length) {
		ssize_t written = write(descriptor, buffer + offset,
					length - offset);

		if (written < 0) {
			if (errno == EINTR)
				continue;
			return -1;
		}
		if (written == 0) {
			errno = EIO;
			return -1;
		}
		offset += (size_t)written;
	}
	return 0;
}

static int write_brightness(int descriptor, unsigned int brightness)
{
	char value[16];
	int length;

	length = snprintf(value, sizeof(value), "%010u\n", brightness);
	if (length < 0 || (size_t)length >= sizeof(value)) {
		errno = EOVERFLOW;
		return -1;
	}
	if (lseek(descriptor, 0, SEEK_SET) < 0)
		return -1;
	return write_all(descriptor, value, (size_t)length);
}

static int force_led_off(int descriptor)
{
	unsigned int attempt;
	int saved_errno = EIO;

	for (attempt = 0U; attempt < 3U; attempt++) {
		struct timespec delay = {
			.tv_nsec = 10000000L,
		};

		if (write_brightness(descriptor, 0U) == 0)
			return 0;
		saved_errno = errno;
		while (nanosleep(&delay, &delay) < 0 && errno == EINTR)
			;
	}
	return contract_error("led.off_write", saved_errno);
}

static int arm_pulse_timer(int descriptor, unsigned int milliseconds)
{
	struct itimerspec timer = {
		.it_value = {
			.tv_sec = milliseconds / 1000U,
			.tv_nsec = (long)(milliseconds % 1000U) * 1000000L,
		},
	};

	return timerfd_settime(descriptor, 0, &timer, NULL);
}

static int read_timer_expiration(int descriptor)
{
	uint64_t expirations;
	ssize_t length;

	do {
		length = read(descriptor, &expirations, sizeof(expirations));
	} while (length < 0 && errno == EINTR);
	if (length != (ssize_t)sizeof(expirations)) {
		if (length >= 0)
			errno = EIO;
		return -1;
	}
	return 0;
}

static int run_event_loop(int input_descriptor,
			  const struct led_device *led,
			  unsigned int pulse_milliseconds,
			  bool fixture_mode,
			  unsigned int expected_pulses
#ifdef ROG5_INDICATOR_TESTING
			  , bool inject_timer_failure
#endif
			  )
{
	struct pollfd descriptors[3];
	sigset_t stop_signals;
	unsigned int pulse_count = 0U;
	bool input_complete = false;
	bool led_active = false;
	int brightness_descriptor = -1;
	int signal_descriptor = -1;
	int timer_descriptor = -1;
	int result = -1;

	if (sigemptyset(&stop_signals) < 0 ||
	    sigaddset(&stop_signals, SIGINT) < 0 ||
	    sigaddset(&stop_signals, SIGTERM) < 0 ||
	    sigprocmask(SIG_BLOCK, &stop_signals, NULL) < 0)
		goto out;
	signal_descriptor = signalfd(-1, &stop_signals,
				     SFD_CLOEXEC | SFD_NONBLOCK);
	if (signal_descriptor < 0)
		goto out;
	brightness_descriptor = open(led->brightness_path,
				     O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
	if (brightness_descriptor < 0)
		goto out;
	timer_descriptor = timerfd_create(CLOCK_BOOTTIME,
					  TFD_CLOEXEC | TFD_NONBLOCK);
	if (timer_descriptor < 0)
		goto out;
	descriptors[0].fd = input_descriptor;
	descriptors[0].events = POLLIN;
	descriptors[1].fd = timer_descriptor;
	descriptors[1].events = POLLIN;
	descriptors[2].fd = signal_descriptor;
	descriptors[2].events = POLLIN;

	for (;;) {
		int ready = poll(descriptors, 3U, -1);

		if (ready < 0) {
			if (errno == EINTR)
				continue;
			goto out;
		}
		if (descriptors[1].revents &
		    (POLLERR | POLLHUP | POLLNVAL)) {
			errno = EIO;
			goto out;
		}
		if (descriptors[2].revents &
		    (POLLERR | POLLHUP | POLLNVAL)) {
			errno = EIO;
			goto out;
		}
		if (descriptors[2].revents & POLLIN) {
			struct signalfd_siginfo signal_info;
			ssize_t signal_length;

			do {
				signal_length = read(signal_descriptor, &signal_info,
						     sizeof(signal_info));
			} while (signal_length < 0 && errno == EINTR);
			if (signal_length != (ssize_t)sizeof(signal_info)) {
				if (signal_length >= 0)
					errno = EIO;
				goto out;
			}
			result = 0;
			goto out;
		}
		if (descriptors[1].revents & POLLIN) {
			if (read_timer_expiration(timer_descriptor) < 0 ||
			    force_led_off(brightness_descriptor) < 0)
				goto out;
			led_active = false;
			printf("state=off brightness=0 pulse=%u\n", pulse_count);
			fflush(stdout);
			if (fixture_mode && input_complete) {
				if (pulse_count != expected_pulses) {
					errno = EPROTO;
					goto out;
				}
				result = 0;
				goto out;
			}
		}
		if (descriptors[0].revents &
		    (POLLERR | POLLHUP | POLLNVAL)) {
			if (!fixture_mode) {
				errno = ENODEV;
				goto out;
			}
		}
		if (descriptors[0].revents & POLLIN) {
			struct input_event events[EVENT_BATCH_COUNT];
			ssize_t length;
			size_t count;
			size_t index;

			do {
				length = read(input_descriptor, events,
					      sizeof(events));
			} while (length < 0 && errno == EINTR);
			if (length < 0) {
				if (errno == EAGAIN)
					continue;
				goto out;
			}
			if (length == 0) {
				if (!fixture_mode) {
					errno = ENODEV;
					goto out;
				}
				input_complete = true;
				descriptors[0].fd = -1;
				if (!led_active) {
					if (pulse_count != expected_pulses) {
						errno = EPROTO;
						goto out;
					}
					result = 0;
					goto out;
				}
				continue;
			}
			if ((size_t)length % sizeof(events[0]) != 0U) {
				contract_error("input.event_alignment", EPROTO);
				goto out;
			}
			count = (size_t)length / sizeof(events[0]);
			for (index = 0U; index < count; index++) {
				const struct input_event *event = &events[index];

				if (event->type != EV_KEY ||
				    event->code != KEY_POWER ||
				    event->value != 1 ||
				    led_active)
					continue;
				if (write_brightness(brightness_descriptor,
						     led->pulse_brightness) < 0)
					goto out;
				led_active = true;
#ifdef ROG5_INDICATOR_TESTING
				if (inject_timer_failure) {
					close(timer_descriptor);
					timer_descriptor = -1;
					errno = EIO;
					goto out;
				}
#endif
				if (arm_pulse_timer(timer_descriptor,
						    pulse_milliseconds) < 0)
					goto out;
				pulse_count++;
				printf("state=on brightness=%u pulse=%u\n",
				       led->pulse_brightness, pulse_count);
				fflush(stdout);
				if (fixture_mode &&
				    pulse_count > expected_pulses) {
					errno = EPROTO;
					goto out;
				}
			}
		}
	}
out:
	if (led_active) {
		if (force_led_off(brightness_descriptor) < 0)
			result = -1;
		else {
			printf("state=off brightness=0 pulse=%u\n", pulse_count);
			fflush(stdout);
		}
	}
	if (timer_descriptor >= 0)
		close(timer_descriptor);
	if (signal_descriptor >= 0)
		close(signal_descriptor);
	if (brightness_descriptor >= 0)
		close(brightness_descriptor);
	return result;
}

static int print_probe(void)
{
	struct led_device led;
	char input_path[PATH_MAX];
	int input_descriptor;

	input_descriptor = discover_input_device(input_path, sizeof(input_path));
	if (input_descriptor < 0)
		return -1;
	if (validate_led_device(LED_CLASS_DIRECTORY, &led, true) < 0) {
		int saved_errno = errno;

		close(input_descriptor);
		errno = saved_errno;
		return -1;
	}
	close(input_descriptor);

	printf("format=rog5-buttons-indicator-runtime-v1\n");
	printf("input_name=%s\n", INPUT_DEVICE_NAME);
	printf("input_event=%s\n", input_path);
	printf("input_key_power=%u\n", KEY_POWER);
	printf("led_name=%s\n", LED_DEVICE_NAME);
	printf("led_of_node=%s\n", led.of_node);
	printf("led_of_node_contract=%s\n", LED_OF_NODE_SUFFIX);
	printf("led_driver=%s\n", led.driver);
	printf("led_driver_contract=%s\n", LED_DRIVER_NAME);
	printf("led_brightness=%u\n", led.initial_brightness);
	printf("led_max_brightness=%u\n", led.max_brightness);
	printf("led_trigger=%s\n", led.trigger);
	printf("action=none\n");
	return 0;
}

static int turn_led_off_at(const char *directory)
{
	struct led_device led;
	int descriptor;
	int result;

	if (validate_led_device(directory, &led, false) < 0)
		return -1;
	descriptor = open(led.brightness_path,
			  O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
	if (descriptor < 0)
		return -1;
	result = force_led_off(descriptor);
	close(descriptor);
	if (result == 0) {
		printf("state=off brightness=0 reason=explicit\n");
		fflush(stdout);
	}
	return result;
}

static int turn_led_off(void)
{
	return turn_led_off_at(LED_CLASS_DIRECTORY);
}

#ifdef ROG5_INDICATOR_TESTING
static int run_fixture(int argc, char **argv)
{
	struct led_device led;
	unsigned int expected_pulses;
	unsigned int pulse_milliseconds;
	bool inject_timer_failure = false;
	int input_descriptor;
	int result;

	if ((argc != 6 && argc != 7) ||
	    strcmp(argv[1], "--fixture") != 0) {
		errno = EINVAL;
		return -1;
	}
	if (argc == 7) {
		if (strcmp(argv[6], "timer-failure") != 0) {
			errno = EINVAL;
			return -1;
		}
		inject_timer_failure = true;
	}
	if (parse_unsigned(argv[4], &expected_pulses) < 0 ||
	    parse_unsigned(argv[5], &pulse_milliseconds) < 0 ||
	    pulse_milliseconds == 0U || pulse_milliseconds > 10000U)
		return -1;
	if (validate_led_device(argv[3], &led, true) < 0)
		return -1;
	input_descriptor = open(argv[2], O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (input_descriptor < 0)
		return -1;
	result = run_event_loop(input_descriptor, &led, pulse_milliseconds,
				true, expected_pulses, inject_timer_failure);
	close(input_descriptor);
	return result;
}
#endif

int main(int argc, char **argv)
{
	struct led_device led;
	char input_path[PATH_MAX];
	int input_descriptor;
	int result;

	if (sizeof(struct input_event) != 24U) {
		fprintf(stderr, "ERROR unexpected input_event size: %zu\n",
			sizeof(struct input_event));
		return EXIT_FAILURE;
	}
	if (argc == 2 && strcmp(argv[1], "--probe") == 0) {
		if (print_probe() < 0) {
			perror("ERROR runtime probe");
			return EXIT_FAILURE;
		}
		return EXIT_SUCCESS;
	}
	if (argc == 2 && strcmp(argv[1], "--off") == 0) {
		if (turn_led_off() < 0) {
			perror("ERROR LED off");
			return EXIT_FAILURE;
		}
		return EXIT_SUCCESS;
	}
#ifdef ROG5_INDICATOR_TESTING
	if (argc == 3 && strcmp(argv[1], "--fixture-off") == 0) {
		if (turn_led_off_at(argv[2]) < 0) {
			perror("ERROR fixture off");
			return EXIT_FAILURE;
		}
		return EXIT_SUCCESS;
	}
	if (argc >= 2 && strcmp(argv[1], "--fixture") == 0) {
		if (run_fixture(argc, argv) < 0) {
			perror("ERROR fixture");
			return EXIT_FAILURE;
		}
		return EXIT_SUCCESS;
	}
#endif
	if (argc != 1) {
		fprintf(stderr, "usage: rog5-key-indicatord [--probe|--off]\n");
		return EXIT_FAILURE;
	}

	input_descriptor = discover_input_device(input_path, sizeof(input_path));
	if (input_descriptor < 0) {
		perror("ERROR input discovery");
		return EXIT_FAILURE;
	}
	if (validate_led_device(LED_CLASS_DIRECTORY, &led, true) < 0) {
		perror("ERROR LED validation");
		close(input_descriptor);
		return EXIT_FAILURE;
	}
	printf("ready input=%s led=%s brightness=%u pulse_ms=%u\n",
	       input_path, LED_DEVICE_NAME, led.pulse_brightness,
	       LED_PULSE_MILLISECONDS);
	fflush(stdout);
	result = run_event_loop(input_descriptor, &led,
				LED_PULSE_MILLISECONDS, false, 0U
#ifdef ROG5_INDICATOR_TESTING
				, false
#endif
				);
	if (result < 0)
		perror("ERROR event loop");
	close(input_descriptor);
	return result == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
