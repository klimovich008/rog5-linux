/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef ROG5_FTS_PROTOCOL_H
#define ROG5_FTS_PROTOCOL_H

#ifdef __KERNEL__
#include <linux/errno.h>
#include <linux/string.h>
#include <linux/types.h>
#else
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
#endif

#define ROG5_FTS_POINTS		10
#define ROG5_FTS_FRAME_BYTES	62
#define ROG5_FTS_SIZE_X		(1080 * 16)
#define ROG5_FTS_SIZE_Y		(2448 * 16)

struct rog5_fts_point {
	u16 x;
	u16 y;
	u8 slot;
	u8 event;
	u8 area;
	u8 rate;
};

struct rog5_fts_frame {
	struct rog5_fts_point points[ROG5_FTS_POINTS];
	u16 active;
	u8 count;
	u8 records;
};

/* FTS3658U normal-firmware ID only; no 3518 or boot-ROM fallback. */
static inline int rog5_fts_normal_id(u8 high, u8 low)
{
	return high == 0x56 && low == 0x52;
}

/* Both register-write and read messages must complete. */
static inline int rog5_fts_transfer_result(int result)
{
	return result == 2 ? 0 : (result < 0 ? result : -EIO);
}

/* Decode atomically: output remains unchanged when any record is invalid. */
static inline int rog5_fts_decode(const u8 *data, size_t size,
				  struct rog5_fts_frame *output)
{
	struct rog5_fts_frame frame = { 0 };
	u16 seen = 0;
	unsigned int i;

	if (!data || !output || size != ROG5_FTS_FRAME_BYTES)
		return -EINVAL;

	frame.count = data[1] & 0x0f;
	if (frame.count > ROG5_FTS_POINTS)
		return -EPROTO;

	for (i = 0; i < ROG5_FTS_POINTS; i++) {
		const u8 *record = data + 2 + i * 6;
		struct rog5_fts_point *point = &frame.points[i];
		u8 slot = record[2] >> 4;
		u8 event = record[0] >> 6;

		/* Exactly the vendor FTS_MAX_ID sentinel rule. */
		if (slot >= ROG5_FTS_POINTS)
			break;
		if (event == 3 || (seen & (1U << slot)))
			return -EPROTO;
		seen |= 1U << slot;
		point->slot = slot;
		point->event = event;
		point->x = ((record[0] & 0x0f) << 12) |
			   (record[1] << 4) | (record[4] >> 4);
		point->y = ((record[2] & 0x0f) << 12) |
			   (record[3] << 4) | (record[4] & 0x0f);
		point->area = record[5] >> 4;
		point->rate = record[5] & 0x0f;
		if (event == 0 || event == 2) {
			if (point->x >= ROG5_FTS_SIZE_X ||
			    point->y >= ROG5_FTS_SIZE_Y)
				return -ERANGE;
			if (!frame.count)
				return -EPROTO;
			frame.active |= 1U << slot;
		}
		frame.records++;
	}
	if (frame.count && !frame.records)
		return -EPROTO;

	*output = frame;
	return 0;
}
#endif
