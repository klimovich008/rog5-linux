// SPDX-License-Identifier: MIT

/*
 * Freestanding AArch64 ALSA probe for initramfs captures without libasound:
 * raw control and PCM ioctls, no libc.
 *
 *   rog5-alsa-probe list CARD                   control numids, types, names
 *   rog5-alsa-probe get CARD NAME               current values
 *   rog5-alsa-probe set CARD NAME VALUE         integer, or enum item name
 *   rog5-alsa-probe play CARD DEVICE SECONDS AMPLITUDE
 *                                               48 kHz S16_LE stereo triangle
 *   rog5-alsa-probe fill CARD DEVICE SECONDS AMPLITUDE
 *                                               the same, but only copy one
 *                                               buffer in: the start threshold
 *                                               is never reached, so the stream
 *                                               never starts
 *   rog5-alsa-probe mmaptest CARD DEVICE
 *                                               write the mmapped buffer after
 *                                               hw_params (before the DSP map),
 *                                               then again after prepare
 *
 * Every step is written to /dev/kmsg as well as stdout, so a log that ends
 * abruptly still shows the last step reached.
 */

typedef unsigned long size_t;
typedef long ssize_t;

#define NR_OPENAT 56
#define NR_CLOSE 57
#define NR_WRITE 64
#define NR_IOCTL 29
#define NR_EXIT 93
#define NR_NANOSLEEP 101
#define NR_MMAP 222
#define LONG_MAX_ 0x7fffffffffffffffL
#define AT_FDCWD -100
#define O_RDWR 2
#define O_WRONLY 1

#ifdef ROG5_ALSA_PROBE_HOST_TEST
/* scripts/device/test-rog5-alsa-probe.py: a host build with fake syscalls */
long sys3(long n, long a, long b, long c);
long sys4(long n, long a, long b, long c, long d);
long sys6(long n, long a, long b, long c, long d, long e, long f);
#else
static long sys3(long n, long a, long b, long c)
{
	register long x0 __asm__("x0") = a;
	register long x1 __asm__("x1") = b;
	register long x2 __asm__("x2") = c;
	register long x8 __asm__("x8") = n;

	__asm__ volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x8) : "memory");
	return x0;
}

static long sys4(long n, long a, long b, long c, long d)
{
	register long x0 __asm__("x0") = a;
	register long x1 __asm__("x1") = b;
	register long x2 __asm__("x2") = c;
	register long x3 __asm__("x3") = d;
	register long x8 __asm__("x8") = n;

	__asm__ volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x8) : "memory");
	return x0;
}

static long sys6(long n, long a, long b, long c, long d, long e, long f)
{
	register long x0 __asm__("x0") = a;
	register long x1 __asm__("x1") = b;
	register long x2 __asm__("x2") = c;
	register long x3 __asm__("x3") = d;
	register long x4 __asm__("x4") = e;
	register long x5 __asm__("x5") = f;
	register long x8 __asm__("x8") = n;

	__asm__ volatile("svc #0" : "+r"(x0) : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8)
			 : "memory");
	return x0;
}

void *memset(void *d, int c, size_t n)
{
	unsigned char *p = d;

	while (n--)
		*p++ = (unsigned char)c;
	return d;
}

void *memcpy(void *d, const void *s, size_t n)
{
	unsigned char *p = d;
	const unsigned char *q = s;

	while (n--)
		*p++ = *q++;
	return d;
}

#endif

static size_t slen(const char *s)
{
	size_t n = 0;

	while (s[n])
		n++;
	return n;
}

static int seq(const char *a, const char *b)
{
	while (*a && *a == *b) {
		a++;
		b++;
	}
	return *a == *b;
}

static int kmsg = -1;

static void out(const char *s)
{
	sys3(NR_WRITE, 1, (long)s, (long)slen(s));
}

static char line[512];
static size_t used;

static void put(const char *s)
{
	while (*s && used < sizeof(line) - 2)
		line[used++] = *s++;
}

static void putn(long v)
{
	char b[24];
	int i = 0;
	unsigned long u = v < 0 ? -(unsigned long)v : (unsigned long)v;

	do {
		b[i++] = '0' + u % 10;
		u /= 10;
	} while (u);
	if (v < 0)
		b[i++] = '-';
	while (i && used < sizeof(line) - 2)
		line[used++] = b[--i];
}

static void flush(void)
{
	line[used++] = '\n';
	sys3(NR_WRITE, 1, (long)line, (long)used);
	if (kmsg >= 0) {
		static const char tag[] = "rog5-alsa-probe: ";
		char k[sizeof(tag) + sizeof(line)];

		memcpy(k, tag, sizeof(tag) - 1);
		memcpy(k + sizeof(tag) - 1, line, used);
		sys3(NR_WRITE, kmsg, (long)k, (long)(sizeof(tag) - 1 + used));
	}
	used = 0;
}

/* A decimal long; *ok = 0 for anything else, including values out of range */
static long parse(const char *s, int *ok)
{
	unsigned long v = 0, limit;
	int neg = *s == '-';

	*ok = 0;
	if (neg)
		s++;
	if (!*s)
		return 0;
	limit = neg ? (unsigned long)LONG_MAX_ + 1 : (unsigned long)LONG_MAX_;
	while (*s >= '0' && *s <= '9') {
		unsigned long d = (unsigned long)(*s++ - '0');

		if (v > (limit - d) / 10)
			return 0;
		v = v * 10 + d;
	}
	if (*s)
		return 0;
	*ok = 1;
	if (neg)
		return v == (unsigned long)LONG_MAX_ + 1 ? -LONG_MAX_ - 1 : -(long)v;
	return (long)v;
}

static void pause_ms(long ms)
{
	long ts[2] = { ms / 1000, (ms % 1000) * 1000000 };

	sys3(NR_NANOSLEEP, (long)ts, 0, 0);
}

#define IOWR(t, n, s) ((3UL << 30) | ((unsigned long)(s) << 16) | ((t) << 8) | (n))
#define IOW(t, n, s) ((1UL << 30) | ((unsigned long)(s) << 16) | ((t) << 8) | (n))
#define IO(t, n) (((t) << 8) | (n))

/* include/uapi/sound/asound.h (LP64 layouts; sizes are part of the ioctl numbers). */
struct elem_id {
	unsigned int numid;
	int iface;
	unsigned int device, subdevice;
	unsigned char name[44];
	unsigned int index;
};

struct elem_list {
	unsigned int offset, space, used, count;
	struct elem_id *pids;
	unsigned char reserved[50];
};

struct elem_info {
	struct elem_id id;
	int type;
	unsigned int access, count;
	int owner;
	union {
		struct { long min, max, step; } integer;
		struct {
			unsigned int items, item;
			char name[64];
			unsigned long names_ptr;
			unsigned int names_length;
		} enumerated;
		unsigned char reserved[128];
	} value;
	unsigned char reserved[64];
};

struct elem_value {
	struct elem_id id;
	unsigned int indirect;
	union {
		long integer[128];
		unsigned int enumerated[128];
		unsigned char bytes[512];
	} value;
	long tstamp[2];
	unsigned char reserved[112];
};

_Static_assert(sizeof(struct elem_id) == 64, "elem_id");
_Static_assert(sizeof(struct elem_list) == 80, "elem_list");
_Static_assert(sizeof(struct elem_info) == 272, "elem_info");
_Static_assert(sizeof(struct elem_value) == 1224, "elem_value");

#define CTL_LIST IOWR('U', 0x10, sizeof(struct elem_list))
#define CTL_INFO IOWR('U', 0x11, sizeof(struct elem_info))
#define CTL_READ IOWR('U', 0x12, sizeof(struct elem_value))
#define CTL_WRITE IOWR('U', 0x13, sizeof(struct elem_value))
#define TYPE_BOOLEAN 1
#define TYPE_INTEGER 2
#define TYPE_ENUMERATED 3
/* value.integer[] and value.enumerated[] hold 128 entries */
#define MAX_VALUES 128

struct mask { unsigned int bits[8]; };
struct interval {
	unsigned int min, max;
	unsigned int flags;	/* openmin:1 openmax:1 integer:1 empty:1 */
};

struct hw_params {
	unsigned int flags;
	struct mask masks[3];
	struct mask mres[5];
	struct interval intervals[12];
	struct interval ires[9];
	unsigned int rmask, cmask, info, msbits, rate_num, rate_den;
	unsigned long fifo_size;
	unsigned char reserved[64];
};

struct sw_params {
	int tstamp_mode;
	unsigned int period_step, sleep_min;
	unsigned long avail_min, xfer_align, start_threshold, stop_threshold;
	unsigned long silence_threshold, silence_size, boundary;
	unsigned int proto, tstamp_type;
	unsigned char reserved[56];
};

struct xferi {
	long result;
	void *buf;
	unsigned long frames;
};

_Static_assert(sizeof(struct hw_params) == 608, "hw_params");
_Static_assert(sizeof(struct xferi) == 24, "xferi");
_Static_assert(sizeof(struct sw_params) == 136, "sw_params");

#define PCM_HW_PARAMS IOWR('A', 0x11, sizeof(struct hw_params))
#define PCM_SW_PARAMS IOWR('A', 0x13, sizeof(struct sw_params))
#define PCM_PREPARE IO('A', 0x40)
#define PCM_DRAIN IO('A', 0x44)
#define PCM_WRITEI IOW('A', 0x50, sizeof(struct xferi))
#define I_CHANNELS (10 - 8)
#define I_RATE (11 - 8)
#define I_PERIOD_SIZE (13 - 8)
#define I_PERIODS (15 - 8)

static char path[64];

static int open_node(const char *prefix, const char *card, const char *suffix)
{
	size_t n = 0;

	for (const char *p = prefix; *p; p++)
		path[n++] = *p;
	for (const char *p = card; *p && n < 40; p++)
		path[n++] = *p;
	for (const char *p = suffix; *p && n < 60; p++)
		path[n++] = *p;
	path[n] = 0;
	return (int)sys4(NR_OPENAT, AT_FDCWD, (long)path, O_RDWR, 0);
}

/* The Lahaina card has several thousand controls (routing mixers). */
#define MAX_IDS 16384
static struct elem_id ids[MAX_IDS];
static struct elem_info info;
static struct elem_value val;

static int ctl_count(int fd)
{
	struct elem_list l;
	unsigned int got = 0;

	do {
		memset(&l, 0, sizeof(l));
		l.offset = got;
		l.space = 1024;
		l.pids = ids + got;
		if (sys3(NR_IOCTL, fd, CTL_LIST, (long)&l) < 0)
			return -1;
		got += l.used;
	} while (l.used && got < l.count && got + 1024 <= MAX_IDS);
	return (int)got;
}

static int ctl_find(int fd, const char *name)
{
	int n = ctl_count(fd);

	for (int i = 0; i < n; i++)
		if (seq((const char *)ids[i].name, name))
			return i;
	return -1;
}

static int ctl_info(int fd, int i)
{
	memset(&info, 0, sizeof(info));
	info.id = ids[i];
	return (int)sys3(NR_IOCTL, fd, CTL_INFO, (long)&info);
}

/*
 * get/set handle BOOLEAN, INTEGER and ENUMERATED controls of at most
 * MAX_VALUES values only: a BYTES control may have 512 values (and IEC958 or
 * INTEGER64 use other layouts), which the long/unsigned int arrays of
 * struct elem_value cannot hold. Leaves the control's info in "info".
 */
static int ctl_scalar(int fd, int i, const char *name)
{
	if (ctl_info(fd, i) < 0) {
		put("no info for ");
		put(name);
		flush();
		return 0;
	}
	if ((info.type != TYPE_BOOLEAN && info.type != TYPE_INTEGER &&
	     info.type != TYPE_ENUMERATED) || info.count == 0 || info.count > MAX_VALUES) {
		put("unsupported control ");
		put(name);
		put(" type=");
		putn(info.type);
		put(" count=");
		putn(info.count);
		flush();
		return 0;
	}
	return 1;
}

/* The name of enumerated item "item" in info.value.enumerated.name; 0 on error */
static int enum_name(int fd, int i, unsigned int item)
{
	if (ctl_info(fd, i) < 0)
		return 0;
	info.value.enumerated.item = item;
	info.value.enumerated.name[0] = 0;
	if (sys3(NR_IOCTL, fd, CTL_INFO, (long)&info) < 0 || info.type != TYPE_ENUMERATED ||
	    info.value.enumerated.item != item) {
		put("no name for item ");
		putn(item);
		flush();
		return 0;
	}
	info.value.enumerated.name[sizeof(info.value.enumerated.name) - 1] = 0;
	return 1;
}

static int cmd_list(const char *card)
{
	int fd = open_node("/dev/snd/controlC", card, ""), n;

	kmsg = -1;	/* thousands of lines: stdout only, keep the kernel log */

	if (fd < 0)
		return 2;
	n = ctl_count(fd);
	put("controls=");
	putn(n);
	flush();
	for (int i = 0; i < n; i++) {
		ctl_info(fd, i);
		putn(ids[i].numid);
		put(" type=");
		putn(info.type);
		put(" count=");
		putn(info.count);
		put(" ");
		put((const char *)ids[i].name);
		flush();
	}
	return 0;
}

static int cmd_get(const char *card, const char *name)
{
	int fd = open_node("/dev/snd/controlC", card, ""), i;

	if (fd < 0 || (i = ctl_find(fd, name)) < 0)
		return 2;
	if (!ctl_scalar(fd, i, name))
		return 4;
	memset(&val, 0, sizeof(val));
	val.id = ids[i];
	if (sys3(NR_IOCTL, fd, CTL_READ, (long)&val) < 0)
		return 3;
	put(name);
	put(" =");
	for (unsigned int k = 0; k < info.count && k < 8; k++) {
		put(" ");
		if (info.type == TYPE_ENUMERATED) {
			unsigned int item = val.value.enumerated[k];

			if (!enum_name(fd, i, item))
				return 3;
			put(info.value.enumerated.name);
		} else {
			putn(val.value.integer[k]);
		}
	}
	flush();
	return 0;
}

static int cmd_set(const char *card, const char *name, const char *value)
{
	int fd = open_node("/dev/snd/controlC", card, ""), i, ok;
	long v;
	long rc;

	if (fd < 0 || (i = ctl_find(fd, name)) < 0) {
		put("no control ");
		put(name);
		flush();
		return 2;
	}
	if (!ctl_scalar(fd, i, name))
		return 4;
	memset(&val, 0, sizeof(val));
	val.id = ids[i];
	if (info.type == TYPE_ENUMERATED) {
		unsigned int items = info.value.enumerated.items, item = items;

		for (unsigned int k = 0; k < items; k++) {
			if (!enum_name(fd, i, k))
				return 3;
			if (seq(info.value.enumerated.name, value))
				item = k;
		}
		if (!ctl_scalar(fd, i, name))
			return 4;
		if (item == items) {
			v = parse(value, &ok);
			if (!ok || v < 0 || (unsigned long)v >= items)
				return 4;
			item = (unsigned int)v;
		}
		for (unsigned int k = 0; k < info.count; k++)
			val.value.enumerated[k] = item;
	} else {
		long lo = 0, hi = 1;

		if (info.type == TYPE_INTEGER) {
			lo = info.value.integer.min;
			hi = info.value.integer.max;
		}
		v = parse(value, &ok);
		if (!ok || v < lo || v > hi) {
			put("value out of range ");
			putn(lo);
			put("..");
			putn(hi);
			flush();
			return 4;
		}
		for (unsigned int k = 0; k < info.count; k++)
			val.value.integer[k] = v;
	}
	rc = sys3(NR_IOCTL, fd, CTL_WRITE, (long)&val);
	put("set ");
	put(name);
	put(" = ");
	put(value);
	put(" rc=");
	putn(rc);
	flush();
	return rc < 0 ? 3 : 0;
}

static void any_mask(struct mask *m)
{
	for (int i = 0; i < 8; i++)
		m->bits[i] = ~0U;
}

static void only(struct mask *m, unsigned int bit)
{
	memset(m, 0, sizeof(*m));
	m->bits[bit / 32] = 1U << (bit % 32);
}

static void range(struct interval *iv, unsigned int lo, unsigned int hi)
{
	iv->min = lo;
	iv->max = hi;
	iv->flags = 0;
}

static short frames[2 * 960];
static struct hw_params hw;

static int cmd_play(const char *card, const char *device, const char *seconds, const char *amplitude,
		    int fill_only)
{
	int ok, fd;
	long secs = parse(seconds, &ok), amp;
	long rc;
	char suffix[16];
	size_t n = 0;

	if (!ok || secs < 1 || secs > 30)
		return 4;
	amp = parse(amplitude, &ok);
	if (!ok || amp < 0 || amp > 32767)
		return 4;
	suffix[n++] = 'D';
	for (const char *p = device; *p && n < 12; p++)
		suffix[n++] = *p;
	suffix[n++] = 'p';
	suffix[n] = 0;
	put("open");
	flush();
	fd = open_node("/dev/snd/pcmC", card, suffix);
	if (fd < 0) {
		put("open failed ");
		putn(fd);
		flush();
		return 2;
	}
	memset(&hw, 0, sizeof(hw));
	for (int i = 0; i < 3; i++)
		any_mask(&hw.masks[i]);
	for (int i = 0; i < 12; i++)
		range(&hw.intervals[i], 0, ~0U);
	only(&hw.masks[0], 3);	/* RW_INTERLEAVED */
	only(&hw.masks[1], 2);	/* S16_LE */
	only(&hw.masks[2], 0);	/* STD */
	range(&hw.intervals[I_CHANNELS], 2, 2);
	range(&hw.intervals[I_RATE], 48000, 48000);
	range(&hw.intervals[I_PERIOD_SIZE], 960, 960);
	range(&hw.intervals[I_PERIODS], 4, 4);
	hw.rmask = ~0U;
	rc = sys3(NR_IOCTL, fd, PCM_HW_PARAMS, (long)&hw);
	put("hw_params rc=");
	putn(rc);
	flush();
	if (rc < 0)
		return 3;
	if (fill_only) {
		struct sw_params sw;

		memset(&sw, 0, sizeof(sw));
		sw.avail_min = 960;
		sw.start_threshold = 1UL << 62;	/* never reached */
		sw.stop_threshold = 4 * 960;
		rc = sys3(NR_IOCTL, fd, PCM_SW_PARAMS, (long)&sw);
		put("sw_params (no auto start) rc=");
		putn(rc);
		flush();
		if (rc < 0)
			return 3;
	}
	rc = sys3(NR_IOCTL, fd, PCM_PREPARE, 0);
	put("prepare rc=");
	putn(rc);
	flush();
	if (rc < 0)
		return 3;
	/* 480-frame triangle period: 100 Hz at 48 kHz, both channels. */
	for (int i = 0; i < 960; i++) {
		int phase = i % 480;
		long s = phase < 240 ? phase : 480 - phase;
		short v = (short)((s * 4 - 480) * amp / 480);

		frames[2 * i] = v;
		frames[2 * i + 1] = v;
	}
	if (fill_only) {
		put("fill: copying one buffer (4 periods), stream stays stopped");
		flush();
		pause_ms(1500);
		for (int chunk = 0; chunk < 4; chunk++) {
			struct xferi x = { 0, frames, 960 };

			rc = sys3(NR_IOCTL, fd, PCM_WRITEI, (long)&x);
			put("fill chunk ");
			putn(chunk);
			put(" rc=");
			putn(rc);
			put(" result=");
			putn(x.result);
			flush();
			if (rc < 0)
				return 3;
		}
		pause_ms(secs * 1000);
		put("filled, never started");
		flush();
		return 0;
	}
	put("write (starts the stream)");
	flush();
	pause_ms(1500);
	for (long chunk = 0; chunk < secs * 50; chunk++) {
		struct xferi x = { 0, frames, 960 };

		rc = sys3(NR_IOCTL, fd, PCM_WRITEI, (long)&x);
		if (chunk == 0 || rc < 0) {
			put("writei chunk ");
			putn(chunk);
			put(" rc=");
			putn(rc);
			put(" result=");
			putn(x.result);
			flush();
		}
		if (rc < 0)
			return 3;
	}
	rc = sys3(NR_IOCTL, fd, PCM_DRAIN, 0);
	put("drain rc=");
	putn(rc);
	flush();
	sys3(NR_CLOSE, fd, 0, 0);
	put("played");
	flush();
	return 0;
}

static int cmd_mmaptest(const char *card, const char *device)
{
	char suffix[16];
	size_t n = 0;
	long rc, fd;
	volatile unsigned char *buf;
	unsigned long bytes = 4 * 960 * 4;

	suffix[n++] = 'D';
	for (const char *p = device; *p && n < 12; p++)
		suffix[n++] = *p;
	suffix[n++] = 'p';
	suffix[n] = 0;
	fd = open_node("/dev/snd/pcmC", card, suffix);
	put("open fd=");
	putn(fd);
	flush();
	if (fd < 0)
		return 2;
	memset(&hw, 0, sizeof(hw));
	for (int i = 0; i < 3; i++)
		any_mask(&hw.masks[i]);
	for (int i = 0; i < 12; i++)
		range(&hw.intervals[i], 0, ~0U);
	only(&hw.masks[0], 0);	/* MMAP_INTERLEAVED */
	only(&hw.masks[1], 2);	/* S16_LE */
	only(&hw.masks[2], 0);
	range(&hw.intervals[I_CHANNELS], 2, 2);
	range(&hw.intervals[I_RATE], 48000, 48000);
	range(&hw.intervals[I_PERIOD_SIZE], 960, 960);
	range(&hw.intervals[I_PERIODS], 4, 4);
	hw.rmask = ~0U;
	rc = sys3(NR_IOCTL, fd, PCM_HW_PARAMS, (long)&hw);
	put("hw_params (mmap) rc=");
	putn(rc);
	flush();
	if (rc < 0)
		return 3;
	/* PROT_READ | PROT_WRITE, MAP_SHARED, offset SNDRV_PCM_MMAP_OFFSET_DATA */
	buf = (volatile unsigned char *)sys6(NR_MMAP, 0, (long)bytes, 3, 1, fd, 0);
	put("mmap=");
	putn((long)buf);
	flush();
	if ((long)buf < 0 && (long)buf > -4096)
		return 3;
	pause_ms(1500);
	put("writing the buffer before prepare (before the DSP map)");
	flush();
	pause_ms(1500);
	for (unsigned long i = 0; i < bytes; i++)
		buf[i] = 0;
	put("pre-prepare write done");
	flush();
	pause_ms(1500);
	rc = sys3(NR_IOCTL, fd, PCM_PREPARE, 0);
	put("prepare rc=");
	putn(rc);
	flush();
	pause_ms(1500);
	put("writing the buffer after prepare (after the DSP map)");
	flush();
	pause_ms(1500);
	for (unsigned long i = 0; i < bytes; i++)
		buf[i] = 0;
	put("post-prepare write done");
	flush();
	pause_ms(2000);
	return 0;
}

static int run(int argc, char **argv)
{
	kmsg = (int)sys4(NR_OPENAT, AT_FDCWD, (long)"/dev/kmsg", O_WRONLY, 0);
	if (argc == 3 && seq(argv[1], "list"))
		return cmd_list(argv[2]);
	if (argc == 4 && seq(argv[1], "get"))
		return cmd_get(argv[2], argv[3]);
	if (argc == 5 && seq(argv[1], "set"))
		return cmd_set(argv[2], argv[3], argv[4]);
	if (argc == 6 && seq(argv[1], "play"))
		return cmd_play(argv[2], argv[3], argv[4], argv[5], 0);
	if (argc == 4 && seq(argv[1], "mmaptest"))
		return cmd_mmaptest(argv[2], argv[3]);
	if (argc == 6 && seq(argv[1], "fill"))
		return cmd_play(argv[2], argv[3], argv[4], argv[5], 1);
	out("usage: rog5-alsa-probe list|get|set|play ...\n");
	return 1;
}

#ifndef ROG5_ALSA_PROBE_HOST_TEST
__attribute__((used)) static void start_c(unsigned long *sp)
{
	sys3(NR_EXIT, run((int)sp[0], (char **)(sp + 1)), 0, 0);
	for (;;)
		__asm__ volatile("wfe");
}

__attribute__((naked)) void _start(void)
{
	__asm__ volatile("mov x0, sp\n\tb start_c");
}
#endif
