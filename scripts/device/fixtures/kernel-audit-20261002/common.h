/* Host mocks for driver function failure/interleaving cases. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
#include <stdarg.h>
typedef uint32_t u32;
typedef uint64_t u64;
typedef uint16_t __le16;
typedef uint32_t __le32;
typedef int spinlock_t;
struct mutex { int unused; };
struct device { void *data; struct device *parent; int refs; };
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define BIT(n) (1U << (n))
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x, value) ((x) = (value))
#define spin_lock_irqsave(lock, flags) do { (void)(lock); (flags) = 0; } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(lock); (void)(flags); } while (0)
#define spin_lock(lock) ((void)(lock))
#define spin_unlock(lock) ((void)(lock))
#define mutex_lock(lock) ((void)(lock))
#define mutex_unlock(lock) ((void)(lock))
#define lockdep_assert_held(lock) ((void)(lock))
#define container_of(p, type, member) ((type *)((char *)(p) - offsetof(type, member)))
#define __free(x) __attribute__((cleanup(test_free)))
static inline void test_free(void *p) { free(*(void **)p); }
#define GFP_KERNEL 0
#define kzalloc(size, flags) calloc(1, (size))
#define cpu_to_le32(x) (x)
#define le32_to_cpu(x) (x)
#define dev_err(...) ((void)0)
#define dev_warn(...) ((void)0)
#define dev_dbg(...) ((void)0)
#define drm_err_ratelimited(...) ((void)0)
#define dev_get_drvdata(dev) ((dev)->data)
static inline struct device *get_device(struct device *dev) { dev->refs++; return dev; }
#define msecs_to_jiffies(x) (x)
#define strscpy(dst, src, size) snprintf((dst),(size),"%s",(src))
#define EXPORT_SYMBOL(x)
