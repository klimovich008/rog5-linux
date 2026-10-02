/*
 * Malformed-request tests of hexagonrpcd's FastRPC listener (the pinned
 * third_party/hexagonrpc archive with our patches), built by
 * scripts/device/test-hexagonrpcd-listener.py with AddressSanitizer when the
 * compiler has it. listener.c is included so its static validation and
 * allocation functions can be called directly; no FastRPC device is used.
 *
 * Audit 2026-10-02 (07-device-rest): count_sizes4() did not count the
 * primary output buffer, so a request with one output buffer for a method
 * that needs two (apps_std_fread, remotectl_close) passed and
 * alloc_outbufs4() wrote past its array.
 */
#include "listener.c"
#include "localctl.h"

#include <string.h>

static int failures;

#define CHECK(cond, what) do { \
	if (cond) { printf("PASS %s\n", what); } \
	else { printf("FAIL %s\n", what); failures++; } \
} while (0)

static struct fastrpc_io_buffer *bufs(size_t n, const size_t *sizes, const void *const *data)
{
	struct fastrpc_io_buffer *b = calloc(n ? n : 1, sizeof(*b));
	size_t i;

	for (i = 0; i < n; i++) {
		b[i].s = sizes[i];
		b[i].p = malloc(sizes[i] ? sizes[i] : 1);
		if (data && data[i])
			memcpy(b[i].p, data[i], sizes[i]);
	}
	return b;
}

/* remotectl_close and apps_std_fread, as in the interface definitions */
static const struct hrpc_arg_def_interp4 close_args[] = {
	{ HRPC_ARG_WORD, sizeof(uint32_t) },
	{ HRPC_ARG_OUT_BLOB_SEQ, sizeof(char) },
	{ HRPC_ARG_OUT_BLOB, sizeof(uint32_t) },
};
static const struct hrpc_method_def_interp4 close_def = {
	.msg_id = 1, .n_args = 3, .args = close_args,
};
static const struct hrpc_arg_def_interp4 fread_args[] = {
	{ HRPC_ARG_WORD, sizeof(uint32_t) },
	{ HRPC_ARG_OUT_BLOB, sizeof(uint32_t) },
	{ HRPC_ARG_OUT_BLOB, sizeof(uint32_t) },
	{ HRPC_ARG_OUT_BLOB_SEQ, sizeof(char) },
};
static const struct hrpc_method_def_interp4 fread_def = {
	.msg_id = 4, .n_args = 4, .args = fread_args,
};
/* an extended method ID (> 30) with an output sequence */
static const struct hrpc_arg_def_interp4 ext_args[] = {
	{ HRPC_ARG_OUT_BLOB_SEQ, sizeof(char) },
};
static const struct hrpc_method_def_interp4 ext_def = {
	.msg_id = 31, .n_args = 1, .args = ext_args,
};
/* a sequence of an output type that holds a sequence */
static const struct hrpc_arg_def_interp4 inner_args[] = {
	{ HRPC_ARG_BLOB_SEQ, sizeof(char) },
};
static const struct hrpc_inner_type_def_interp4 inner_types[] = {
	{ 1, inner_args },
};
static const struct hrpc_arg_def_interp4 tseq_args[] = {
	{ HRPC_ARG_OUT_TYPE_SEQ, 0 },
};
static const struct hrpc_method_def_interp4 tseq_def = {
	.msg_id = 5, .n_args = 1, .args = tseq_args,
	.n_inner_types = 1, .inner_types = inner_types,
};
static const struct hrpc_arg_def_interp4 bad_index_args[] = {
	{ HRPC_ARG_OUT_TYPE, 3 },
};
static const struct hrpc_method_def_interp4 bad_index_def = {
	.msg_id = 6, .n_args = 1, .args = bad_index_args,
	.n_inner_types = 1, .inner_types = inner_types,
};

int main(void)
{
	struct fastrpc_io_buffer *in, *out;
	uint32_t prim2[2] = { 3, 16 };          /* fd, length */
	uint32_t prim_ext[2] = { 31, 5 };       /* method ID, length */
	uint32_t prim_tseq[1] = { 2 };          /* two instances */
	uint32_t inst[2] = { 4, 6 };            /* their sequence lengths */
	size_t s8[1] = { 8 }, s_tseq[2] = { 4, 8 };
	const void *d2[1] = { prim2 }, *dext[1] = { prim_ext };
	const void *dtseq[2] = { prim_tseq, inst };

	in = bufs(1, s8, d2);
	CHECK(count_sizes4(&close_def, 1, 1, in) != 0,
	      "remotectl_close with one output buffer (needs two) is refused");
	CHECK(count_sizes4(&close_def, 1, 2, in) == 0,
	      "remotectl_close with two output buffers is accepted");
	out = alloc_outbufs4(&close_def, in, 1, 2);
	CHECK(out && out[0].s == 4 && out[1].s == 16,
	      "remotectl_close: primary 4 bytes, sequence 16 bytes");
	if (out)
		iobuf_free(2, out);

	CHECK(count_sizes4(&fread_def, 1, 1, in) != 0,
	      "apps_std_fread with one output buffer (needs two) is refused");
	CHECK(count_sizes4(&fread_def, 1, 0, in) != 0,
	      "apps_std_fread without output buffers is refused");
	CHECK(count_sizes4(&fread_def, 1, 2, in) == 0,
	      "apps_std_fread with two output buffers is accepted");
	iobuf_free(1, in);

	in = bufs(0, NULL, NULL);
	CHECK(count_sizes4(&fread_def, 0, 2, in) != 0,
	      "a request without its primary input buffer is refused");
	iobuf_free(0, in);

	in = bufs(1, s8, dext);
	CHECK(count_sizes4(&ext_def, 1, 1, in) == 0, "extended method ID: accepted");
	out = alloc_outbufs4(&ext_def, in, 1, 1);
	CHECK(out && out[0].s == 5,
	      "extended method ID: the size is read after the ID word, as validated");
	if (out)
		iobuf_free(1, out);
	iobuf_free(1, in);

	prim2[1] = 0xffffffff;
	in = bufs(1, s8, d2);
	CHECK(alloc_outbufs4(&fread_def, in, 1, 2) == NULL,
	      "a 4 GiB output sequence is not allocated");
	iobuf_free(1, in);

	in = bufs(2, s_tseq, dtseq);
	/* instances buffer + one sequence per instance = 3 */
	CHECK(count_sizes4(&tseq_def, 2, 2, in) != 0,
	      "type sequence: one output buffer short is refused");
	CHECK(count_sizes4(&tseq_def, 2, 3, in) == 0,
	      "type sequence: instances buffer plus one per sequence is accepted");
	out = alloc_outbufs4(&tseq_def, in, 2, 3);
	CHECK(out && out[1].s == 4 && out[2].s == 6,
	      "type sequence: sequence buffers sized from the instances");
	if (out)
		iobuf_free(3, out);
	iobuf_free(2, in);

	in = bufs(1, s8, d2);
	CHECK(count_sizes4(&bad_index_def, 1, 4, in) != 0,
	      "an inner type index outside the definition is refused");
	iobuf_free(1, in);

	{
		/*
		 * remotectl_close through its real handler: the handle (first
		 * word) is 4096, the error buffer (second word) 1 byte. The
		 * handler used the handle as the memset length (review of 0002).
		 */
		uint32_t prim_close[2] = { 4096, 1 };
		const void *dclose[1] = { prim_close };
		struct fastrpc_interface *lc = fastrpc_localctl_init(0, NULL);
		uint32_t r;

		in = bufs(1, s8, dclose);
		CHECK(count_sizes4(&close_def, 1, 2, in) == 0, "remotectl_close request accepted");
		out = alloc_outbufs4(&close_def, in, 1, 2);
		CHECK(out && out[1].s == 1, "remotectl_close: a 1-byte error buffer");
		r = lc->procs[1].impl(lc->data, in, out);
		CHECK(r == 0 && *(uint32_t *) out[0].p == 0,
		      "remotectl_close clears only the allocated error buffer (ASan would trap)");
		iobuf_free(2, out);
		iobuf_free(1, in);
		fastrpc_localctl_deinit(lc);
	}

	{
		/* inbuf decoder: an empty buffer is complete after its size */
		struct fastrpc_decoder_context *ctx = inbuf_decode_start(REMOTE_SCALARS_MAKE(0, 2, 0));
		unsigned char wire[16] = { 0, 0, 0, 0, 3, 0, 0, 0, 'a', 'b', 0 };
		struct fastrpc_io_buffer *dec;

		CHECK(ctx && inbuf_decode(ctx, 11, wire) == 0 && inbuf_decode_is_complete(ctx),
		      "decoder: an empty input buffer followed by another decodes completely");
		dec = inbuf_decode_finish(ctx);
		CHECK(dec[0].s == 0 && dec[1].s == 3 && !memcmp(dec[1].p, "ab", 3),
		      "decoder: sizes and contents");
		iobuf_free(2, dec);
	}

	return failures ? 1 : 0;
}
