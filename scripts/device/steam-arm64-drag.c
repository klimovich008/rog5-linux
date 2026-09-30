/*
 * steam-arm64-drag.so: LD_PRELOAD shim that lets Steam windows be moved by
 * their title bar and resized by their edges under X11/Xwayland.
 *
 * steamwebhelper draws each Steam window as an SDL3 window with CEF's own X
 * window mapped over all of it. Title-bar drag and edge resize are an SDL
 * hit test on the SDL window (draggable rects from CEF, 4 px edges), so they
 * need clicks to fall through CEF's window. steamwebhelper has the code for
 * that (cut the draggable rects and edges out of the CEF window's ShapeInput),
 * but it runs only when a per-window byte is set, and nothing in the client
 * sets it (arm64 and x86_64 build 1788652215 alike). This shim sets it:
 *  - SDL_SetWindowHitTest(window, callback, userdata): when callback is
 *    steamwebhelper's hit test, userdata is the window object; set the byte.
 *  - SDL_GetWindowSize right after the one place that clears the byte again
 *    (return address checked): set it again for that window's object.
 * It does nothing unless the process is steamwebhelper with the exact build
 * ID and code bytes below; everything else only forwards to libSDL3. A
 * steamwebhelper it does not recognise (a Steam update) gets one line on
 * stderr (Steam's log / the journal) and plain forwarding.
 *
 * Build: cc -O2 -shared -fPIC -Wl,--version-script=<(echo 'SDL3_0.0.0 {
 *   global: SDL_SetWindowHitTest; SDL_GetWindowSize; local: *; };') -o
 *   steam-arm64-drag.so steam-arm64-drag.c   (see steam-arm64-install)
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <unistd.h>

/* steamwebhelper (steamrtarm64) of Steam client 1788652215 */
static const unsigned char build_id[20] = {
	0xb2, 0xd7, 0x22, 0x8f, 0x7e, 0x1e, 0x53, 0xb2, 0x30, 0xc7,
	0x93, 0xc5, 0xb7, 0x2f, 0xf5, 0x0d, 0xc1, 0xcc, 0xaf, 0xb2,
};
#define HIT_TEST_CB 0x211e00      /* SDL hit-test callback, userdata = window object */
#define SHAPE_UPDATE 0x212068     /* ldrb w1, [x0, #0x4c8]; cbz w1, ... */
#define FLAG_CLEAR 0x2158a4       /* strb wzr, [x19, #0x4c8] */
#define AFTER_CLEAR_RET 0x2158c8  /* return address of the SDL_GetWindowSize call after it */
#define FLAG_OFFSET 0x4c8
static const struct { uintptr_t off; unsigned char code[8]; } expect[] = {
	{ HIT_TEST_CB, { 0xfd, 0x7b, 0xb9, 0xa9, 0xfd, 0x03, 0x00, 0x91 } },
	{ SHAPE_UPDATE, { 0x01, 0x20, 0x53, 0x39, 0x41, 0x0c, 0x00, 0x34 } },
	{ FLAG_CLEAR, { 0x7f, 0x22, 0x13, 0x39, 0x61, 0x76, 0x42, 0xb9 } },
	{ AFTER_CLEAR_RET - 4, { 0xcf, 0xd7, 0xfa, 0x97, 0xe1, 0x73, 0x40, 0xb9 } },
};

static uintptr_t base;
static bool active;
static struct { void *window, *object; } map[128];
static unsigned next;

static bool is_browser_process(void)
{
	char exe[4096], args[4096];
	ssize_t n = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
	if (n <= 0)
		return false;
	exe[n] = 0;
	const char *slash = strrchr(exe, '/');
	if (!slash || strcmp(slash + 1, "steamwebhelper"))
		return false;
	int fd = open("/proc/self/cmdline", O_RDONLY | O_CLOEXEC);
	if (fd < 0)
		return false;
	n = read(fd, args, sizeof(args) - 1);
	close(fd);
	if (n <= 0)
		return false;
	for (ssize_t i = 0; i < n; i += strlen(args + i) + 1)
		if (!strncmp(args + i, "--type=", 7))
			return false; /* renderer, GPU, zygote, ... */
	return true;
}

static bool build_matches(void)
{
	const Elf64_Phdr *ph = (const Elf64_Phdr *)getauxval(AT_PHDR);
	size_t phnum = getauxval(AT_PHNUM);
	if (!ph)
		return false;
	for (size_t i = 0; i < phnum; i++)
		if (ph[i].p_type == PT_PHDR)
			base = (uintptr_t)ph - ph[i].p_vaddr;
	if (!base || memcmp((void *)base, ELFMAG, SELFMAG))
		return false;
	bool id = false;
	for (size_t i = 0; i < phnum; i++) {
		if (ph[i].p_type != PT_NOTE)
			continue;
		const unsigned char *p = (const unsigned char *)(base + ph[i].p_vaddr), *end = p + ph[i].p_memsz;
		while (p + sizeof(Elf64_Nhdr) <= end) {
			const Elf64_Nhdr *nh = (const Elf64_Nhdr *)p;
			const unsigned char *name = p + sizeof(*nh), *desc = name + ((nh->n_namesz + 3) & ~3u);
			if (nh->n_type == NT_GNU_BUILD_ID && nh->n_namesz == 4 && !memcmp(name, "GNU", 4) &&
			    nh->n_descsz == sizeof(build_id) && !memcmp(desc, build_id, sizeof(build_id)))
				id = true;
			p = desc + ((nh->n_descsz + 3) & ~3u);
		}
	}
	if (!id)
		return false;
	for (size_t i = 0; i < sizeof(expect) / sizeof(expect[0]); i++)
		if (memcmp((void *)(base + expect[i].off), expect[i].code, sizeof(expect[i].code)))
			return false;
	return true;
}

__attribute__((constructor)) static void init(void)
{
	static const char off[] = "steam-arm64-drag: unknown steamwebhelper build; "
				  "title-bar drag and edge resize stay off (shim needs updating)\n";
	if (!is_browser_process())
		return;
	active = build_matches();
	if (!active) {
		ssize_t r = write(2, off, sizeof(off) - 1);
		(void)r;
	}
	/* ROG5_STEAM_DRAG_PROBE=1 steamwebhelper: report and exit before main() */
	const char *probe = getenv("ROG5_STEAM_DRAG_PROBE");
	if (probe && *probe == '1') {
		static const char on[] = "steam-arm64-drag: active\n";
		ssize_t r = active ? write(1, on, sizeof(on) - 1) : 0;
		(void)r;
		_exit(active ? 0 : 1);
	}
}

static void enable(void *object)
{
	*(volatile unsigned char *)((char *)object + FLAG_OFFSET) = 1;
}

bool SDL_SetWindowHitTest(void *window, void *callback, void *data)
{
	static bool (*real)(void *, void *, void *);
	if (!real)
		real = (bool (*)(void *, void *, void *))dlsym(RTLD_NEXT, "SDL_SetWindowHitTest");
	if (active && window && data && (uintptr_t)callback == base + HIT_TEST_CB) {
		unsigned i;
		for (i = 0; i < sizeof(map) / sizeof(map[0]) && map[i].window != window; i++)
			;
		if (i == sizeof(map) / sizeof(map[0]))
			i = next++ % (sizeof(map) / sizeof(map[0]));
		map[i].window = window;
		map[i].object = data;
		enable(data);
	}
	return real(window, callback, data);
}

bool SDL_GetWindowSize(void *window, int *w, int *h)
{
	static bool (*real)(void *, int *, int *);
	if (!real)
		real = (bool (*)(void *, int *, int *))dlsym(RTLD_NEXT, "SDL_GetWindowSize");
	/* mask off pointer-authentication bits of the return address */
	if (active && ((uintptr_t)__builtin_return_address(0) & 0xffffffffffffULL) == base + AFTER_CLEAR_RET)
		for (unsigned i = 0; i < sizeof(map) / sizeof(map[0]); i++)
			if (map[i].window == window)
				enable(map[i].object);
	return real(window, w, h);
}
