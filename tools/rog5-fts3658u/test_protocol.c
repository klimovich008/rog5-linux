/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdio.h>
#include <stdlib.h>
#include "rog5_fts_protocol.h"

static unsigned int checks;
#define CHECK(v) do { \
	checks++; \
	if (!(v)) { \
		fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #v); \
		exit(1); \
	} \
} while (0)

static void empty(u8 *b, u8 count)
{
	memset(b, 0xff, ROG5_FTS_FRAME_BYTES);
	b[0] = 0;
	b[1] = count;
}

static void point(u8 *b, unsigned int index, u8 slot, u8 event,
		  u16 x, u16 y, u8 area, u8 rate)
{
	u8 *p = b + 2 + index * 6;

	p[0] = (event << 6) | ((x >> 12) & 15);
	p[1] = (x >> 4) & 255;
	p[2] = (slot << 4) | ((y >> 12) & 15);
	p[3] = (y >> 4) & 255;
	p[4] = ((x & 15) << 4) | (y & 15);
	p[5] = (area << 4) | rate;
}

static void refused(const u8 *b, size_t size, int error)
{
	struct rog5_fts_frame f, before;

	memset(&f, 0x5a, sizeof(f));
	before = f;
	CHECK(rog5_fts_decode(b, size, &f) == error);
	CHECK(memcmp(&f, &before, sizeof(f)) == 0);
}

static void identities(void)
{
	unsigned int h, l, accepted = 0;

	for (h = 0; h < 256; h++)
		for (l = 0; l < 256; l++)
			if (rog5_fts_normal_id(h, l)) {
				CHECK(h == 0x56 && l == 0x52);
				accepted++;
			}
	CHECK(accepted == 1);
}

static void transfers(void)
{
	int r;

	for (r = -4095; r <= 5; r++)
		CHECK(rog5_fts_transfer_result(r) ==
		      (r == 2 ? 0 : (r < 0 ? r : -EIO)));
}

static void frames(void)
{
	struct rog5_fts_frame f;
	u8 b[ROG5_FTS_FRAME_BYTES];
	unsigned int i, x, y, seed = 0x3658;

	/* Empty release, then all ten native-coordinate contacts. */
	empty(b, 0);
	CHECK(!rog5_fts_decode(b, sizeof(b), &f));
	CHECK(!f.active && !f.records);
	empty(b, 10);
	for (i = 0; i < 10; i++)
		point(b, i, i, i & 1 ? 2 : 0, i * 1601, i * 3501, i, i);
	CHECK(!rog5_fts_decode(b, sizeof(b), &f));
	CHECK(f.active == 1023 && f.records == 10 && f.count == 10);
	for (i = 0; i < 10; i++) {
		CHECK(f.points[i].slot == i);
		CHECK(f.points[i].x == i * 1601);
		CHECK(f.points[i].y == i * 3501);
		CHECK(f.points[i].area == i && f.points[i].rate == i);
	}
	/* Final valid fractional coordinate and UP with zero active count. */
	empty(b, 1);
	point(b, 0, 9, 2, ROG5_FTS_SIZE_X - 1, ROG5_FTS_SIZE_Y - 1, 15, 15);
	CHECK(!rog5_fts_decode(b, sizeof(b), &f));
	CHECK(f.points[0].x == 17279 && f.points[0].y == 39167);
	point(b, 0, 9, 1, 100, 200, 0, 0);
	b[1] = 0;
	CHECK(!rog5_fts_decode(b, sizeof(b), &f));
	CHECK(f.active == 0 && f.records == 1);
	/* Vendor count is not compared to all records (UP is not active). */
	empty(b, 1);
	point(b, 0, 2, 2, 100, 200, 1, 2);
	point(b, 1, 3, 1, 101, 201, 1, 2);
	CHECK(!rog5_fts_decode(b, sizeof(b), &f));
	CHECK(f.count == 1 && f.records == 2 && f.active == 4);
	/* UP coordinates are unused; do not discard another valid contact. */
	point(b, 1, 3, 1, 65535, 65535, 15, 15);
	CHECK(!rog5_fts_decode(b, sizeof(b), &f));
	CHECK(f.count == 1 && f.records == 2 && f.active == 4);
	/* Preserve source behavior: no undocumented active/count equality. */
	b[1] = 2;
	CHECK(!rog5_fts_decode(b, sizeof(b), &f));
	CHECK(f.count == 2 && f.active == 4);
	/* Every sentinel stops before trailing stale records. */
	for (i = 10; i < 16; i++) {
		empty(b, 0);
		point(b, 0, i, 3, 65535, 65535, 15, 15);
		CHECK(!rog5_fts_decode(b, sizeof(b), &f));
		CHECK(!f.records);
	}
	/* Deterministic varying native coordinates preserve every low nibble. */
	for (i = 0; i < 10000; i++) {
		seed = seed * 1664525U + 1013904223U;
		x = seed % ROG5_FTS_SIZE_X;
		seed = seed * 1664525U + 1013904223U;
		y = seed % ROG5_FTS_SIZE_Y;
		empty(b, 1);
		point(b, 0, i % 10, 2, x, y, i % 16, (i / 16) % 16);
		CHECK(!rog5_fts_decode(b, sizeof(b), &f));
		CHECK(f.points[0].x == x && f.points[0].y == y);
	}
}

static void errors(void)
{
	u8 b[ROG5_FTS_FRAME_BYTES];
	unsigned int i;

	empty(b, 1);
	point(b, 0, 0, 0, 123, 456, 1, 1);
	for (i = 0; i < 62; i++)
		refused(b, i, -EINVAL);
	refused(b, 63, -EINVAL);
	refused(NULL, 62, -EINVAL);
	CHECK(rog5_fts_decode(b, 62, NULL) == -EINVAL);
	memset(b, 0xff, sizeof(b));
	refused(b, sizeof(b), -EPROTO);
	for (i = 11; i <= 15; i++) {
		empty(b, i);
		refused(b, sizeof(b), -EPROTO);
	}
	empty(b, 1); /* Positive count without any records. */
	refused(b, sizeof(b), -EPROTO);
	point(b, 0, 3, 2, 1, 2, 0, 0);
	point(b, 1, 3, 1, 1, 2, 0, 0);
	refused(b, sizeof(b), -EPROTO);
	empty(b, 1);
	point(b, 0, 0, 3, 1, 2, 0, 0);
	refused(b, sizeof(b), -EPROTO);
	point(b, 0, 0, 0, ROG5_FTS_SIZE_X, 2, 0, 0);
	refused(b, sizeof(b), -ERANGE);
	point(b, 0, 0, 0, 1, ROG5_FTS_SIZE_Y, 0, 0);
	refused(b, sizeof(b), -ERANGE);
	point(b, 0, 0, 2, 1, 2, 0, 0);
	b[1] = 0;
	refused(b, sizeof(b), -EPROTO);
	/* A late bad record cannot publish a valid prefix. */
	empty(b, 10);
	for (i = 0; i < 10; i++)
		point(b, i, i, 2, i, i, 0, 0);
	point(b, 9, 9, 3, 10, 20, 0, 0);
	refused(b, sizeof(b), -EPROTO);
}

int main(void)
{
	identities();
	transfers();
	frames();
	errors();
	printf("PASS %u checks: IDs, transfer errors, native frames, malformed input\n",
	       checks);
	return 0;
}
