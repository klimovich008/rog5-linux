// SPDX-License-Identifier: GPL-2.0-only
/*
 * Copyright (c) 2022-2024 Qualcomm Innovation Center, Inc. All rights reserved.
 */

#include <linux/module.h>
#include <media/v4l2-mem2mem.h>

#include "iris_hfi_gen1.h"
#include "iris_hfi_gen1_defines.h"
#include "iris_instance.h"
#include "iris_vpu_buffer.h"

/*
 * ROG5: firmware debug-queue message mask sent after SYS_INIT (HFI debug
 * config, queue mode). 0x18 = errors and fatal messages, what the stock
 * msm_vidc driver requests by default (FW_ERROR | FW_FATAL); 0 sends nothing.
 */
static unsigned int fw_debug = 0x18;
module_param(fw_debug, uint, 0644);
MODULE_PARM_DESC(fw_debug, "HFI firmware debug mask after SYS_INIT (0x18 = error|fatal, 0 = off)");

/*
 * ROG5: eos_buffer: the drain (V4L2_DEC_CMD_STOP / V4L2_ENC_CMD_STOP) sends a
 * real 4 KiB DMA buffer as the EOS packet, like the stock msm_vidc driver
 * (msm_vidc_common.c:4339), instead of upstream's dummy address 0xdeadb000.
 * Always on for SM8350 (iris_oem_quirks.eos_buffer): its OEM firmware takes
 * an exception on the dummy address (k115 trial A); the parameter only
 * matters for other gen1 platforms. The firmware's inter-frame power
 * collapse stays enabled: disabling it alone (k115's interframe_pc=0) left
 * the host's hardware-controlled GDSC mode inconsistent and the firmware
 * stopped answering, so that switch is gone.
 *
 * ubwc_config: send the stock HFI_PROPERTY_SYS_UBWC_CONFIG after SYS_INIT on
 * platforms that provide it (SM8350: LPDDR5 values); read at each firmware
 * load. Off by default: decode works without it, and it changes how the
 * firmware addresses UBWC buffers.
 */
static bool eos_buffer;
module_param(eos_buffer, bool, 0644);
MODULE_PARM_DESC(eos_buffer, "drain with a real 4 KiB EOS buffer instead of 0xdeadb000 (always on for SM8350)");

static bool ubwc_config;
module_param(ubwc_config, bool, 0644);
MODULE_PARM_DESC(ubwc_config, "send the stock gen1 UBWC config at firmware load (SM8350)");

static bool iris_hfi_gen1_eos_buffer(struct iris_inst *inst)
{
	const struct iris_oem_quirks *oem = inst->core->iris_platform_data->oem;

	return READ_ONCE(eos_buffer) || (oem && oem->eos_buffer);
}

/* ROG5: the real EOS buffer of this session, allocated on first use */
static int iris_hfi_gen1_get_eos_buffer(struct iris_inst *inst, u32 *daddr)
{
	struct iris_core *core = inst->core;

	if (!inst->eos_vaddr)
		inst->eos_vaddr = dma_alloc_attrs(core->dev, SZ_4K, &inst->eos_daddr,
						  GFP_KERNEL, 0);
	if (!inst->eos_vaddr)
		return -ENOMEM;
	if (!iris_dma_range_ok(core, inst->eos_daddr, SZ_4K, "EOS buffer"))
		return -EINVAL;
	*daddr = lower_32_bits(inst->eos_daddr);

	return 0;
}

static u32 iris_hfi_gen1_buf_type_from_driver(enum iris_buffer_type buffer_type)
{
	switch (buffer_type) {
	case BUF_INPUT:
		return HFI_BUFFER_INPUT;
	case BUF_OUTPUT:
		return HFI_BUFFER_OUTPUT;
	case BUF_PERSIST:
		return HFI_BUFFER_INTERNAL_PERSIST_1;
	case BUF_BIN:
		return HFI_BUFFER_INTERNAL_SCRATCH;
	case BUF_SCRATCH_1:
		return HFI_BUFFER_INTERNAL_SCRATCH_1;
	case BUF_SCRATCH_2:
		return HFI_BUFFER_INTERNAL_SCRATCH_2;
	case BUF_ARP:
		return HFI_BUFFER_INTERNAL_PERSIST;
	default:
		return -EINVAL;
	}
}

/*
 * ROG5: stock HFI_PROPERTY_SYS_UBWC_CONFIG (hfi_packetization.c:250):
 * property data = struct hfi_cmd_sys_set_ubwc_config_packet_type, whose own
 * size/packet_type words stock leaves unset (zero here); 16 + 40 + 4 = 60
 * bytes as stock declares.
 */
static int iris_hfi_gen1_sys_ubwc_config(struct iris_core *core)
{
	const struct iris_oem_quirks *oem = core->iris_platform_data->oem;
	const struct iris_gen1_ubwc_config *cfg = oem ? oem->ubwc : NULL;
	struct {
		struct hfi_pkt_hdr hdr;
		u32 num_properties;
		u32 property;
		u32 size;
		u32 packet_type;
		u32 override_bits;
		u32 max_channels;
		u32 mal_length;
		u32 highest_bank_bit;
		u32 bank_swzl_level;
		u32 bank_spreading;
		u32 reserved[2];
		u32 pad;
	} __packed pkt = {};

	BUILD_BUG_ON(sizeof(pkt) != 60);
	if (!cfg || !READ_ONCE(ubwc_config))
		return 0;

	pkt.hdr.size = sizeof(pkt);
	pkt.hdr.pkt_type = HFI_CMD_SYS_SET_PROPERTY;
	pkt.num_properties = 1;
	pkt.property = HFI_PROPERTY_SYS_UBWC_CONFIG;
	pkt.override_bits = cfg->override_bits;
	pkt.max_channels = cfg->max_channels;
	pkt.mal_length = cfg->mal_length;
	pkt.highest_bank_bit = cfg->highest_bank_bit;
	pkt.bank_swzl_level = cfg->bank_swzl_level;
	pkt.bank_spreading = cfg->bank_spreading;
	dev_info(core->dev, "UBWC config: channels %u, MAL %u, HBB %u (overrides %#x)\n",
		 pkt.max_channels, pkt.mal_length, pkt.highest_bank_bit, pkt.override_bits);

	return iris_hfi_queue_cmd_write_locked(core, &pkt, pkt.hdr.size);
}

static int iris_hfi_gen1_sys_init(struct iris_core *core)
{
	struct hfi_sys_init_pkt sys_init_pkt;
	struct {
		struct hfi_pkt_hdr hdr;
		u32 num_properties;
		u32 property;
		struct hfi_debug_config cfg;
		u32 reserved;	/* stock declares 28 bytes */
	} __packed dbg = {};
	int ret;

	sys_init_pkt.hdr.size = sizeof(sys_init_pkt);
	sys_init_pkt.hdr.pkt_type = HFI_CMD_SYS_INIT;
	sys_init_pkt.arch_type = HFI_VIDEO_ARCH_OX;

	ret = iris_hfi_queue_cmd_write_locked(core, &sys_init_pkt, sys_init_pkt.hdr.size);
	if (ret)
		return ret;
	if (!fw_debug)
		return iris_hfi_gen1_sys_ubwc_config(core);

	dbg.hdr.size = sizeof(dbg);
	dbg.hdr.pkt_type = HFI_CMD_SYS_SET_PROPERTY;
	dbg.num_properties = 1;
	dbg.property = HFI_PROPERTY_SYS_DEBUG_CONFIG;
	dbg.cfg.debug_config = fw_debug;
	dbg.cfg.debug_mode = HFI_DEBUG_MODE_QUEUE;

	ret = iris_hfi_queue_cmd_write_locked(core, &dbg, dbg.hdr.size);
	if (ret)
		return ret;

	return iris_hfi_gen1_sys_ubwc_config(core);
}

static int iris_hfi_gen1_sys_image_version(struct iris_core *core)
{
	struct hfi_sys_get_property_pkt packet;

	packet.hdr.size = sizeof(packet);
	packet.hdr.pkt_type = HFI_CMD_SYS_GET_PROPERTY;
	packet.num_properties = 1;
	packet.data = HFI_PROPERTY_SYS_IMAGE_VERSION;

	return iris_hfi_queue_cmd_write_locked(core, &packet, packet.hdr.size);
}

static int iris_hfi_gen1_sys_interframe_powercollapse(struct iris_core *core)
{
	struct hfi_sys_set_property_pkt *pkt;
	struct hfi_enable *hfi;
	u32 packet_size;
	int ret;

	packet_size = struct_size(pkt, data, 1) + sizeof(*hfi);
	pkt = kzalloc(packet_size, GFP_KERNEL);
	if (!pkt)
		return -ENOMEM;

	hfi = (struct hfi_enable *)&pkt->data[1];

	pkt->hdr.size = packet_size;
	pkt->hdr.pkt_type = HFI_CMD_SYS_SET_PROPERTY;
	pkt->num_properties = 1;
	pkt->data[0] = HFI_PROPERTY_SYS_CODEC_POWER_PLANE_CTRL;
	hfi->enable = true;

	ret = iris_hfi_queue_cmd_write_locked(core, pkt, pkt->hdr.size);
	kfree(pkt);

	return ret;
}

static int iris_hfi_gen1_sys_pc_prep(struct iris_core *core)
{
	struct hfi_sys_pc_prep_pkt pkt;

	pkt.hdr.size = sizeof(struct hfi_sys_pc_prep_pkt);
	pkt.hdr.pkt_type = HFI_CMD_SYS_PC_PREP;

	return iris_hfi_queue_cmd_write_locked(core, &pkt, pkt.hdr.size);
}

/*
 * ROG5: the next wait on inst->completion is for this answer only. After
 * SESSION_END nothing else is sent (iris_hfi_queue_session_cmd_write()
 * refuses it), so its expectation and completion are left alone for close.
 */
static void iris_hfi_gen1_expect(struct iris_inst *inst, u32 msg)
{
	if (inst->end_sent)
		return;
	inst->expected_msg = msg;
	reinit_completion(&inst->completion);
}

static int hfi_gen1_set_property(struct iris_inst *inst, u32 packet_type,
				 void *payload, u32 payload_size);

static int iris_hfi_gen1_session_open(struct iris_inst *inst)
{
	const struct iris_oem_quirks *oem = inst->core->iris_platform_data->oem;
	struct hfi_session_open_pkt packet;
	u32 codec = 0;
	int ret;

	if (inst->state != IRIS_INST_DEINIT)
		return -EALREADY;

	/* ROG5: never open a session the platform keeps disabled */
	if (inst->domain == ENCODER && !inst->core->enc_enabled)
		return -EOPNOTSUPP;
	if (inst->domain == DECODER && inst->codec == V4L2_PIX_FMT_VP9 &&
	    inst->core->dec_fmts_size <= IRIS_FMT_VP9)
		return -EOPNOTSUPP;

	switch (inst->codec) {
	case V4L2_PIX_FMT_H264:
		codec = HFI_VIDEO_CODEC_H264;
		break;
	case V4L2_PIX_FMT_HEVC:
		codec = HFI_VIDEO_CODEC_HEVC;
		break;
	case V4L2_PIX_FMT_VP9:
		codec = HFI_VIDEO_CODEC_VP9;
		break;
	}

	packet.shdr.hdr.size = sizeof(struct hfi_session_open_pkt);
	packet.shdr.hdr.pkt_type = HFI_CMD_SYS_SESSION_INIT;
	packet.shdr.session_id = inst->session_id;

	if (inst->domain == DECODER)
		packet.session_domain = HFI_SESSION_TYPE_DEC;
	else
		packet.session_domain = HFI_SESSION_TYPE_ENC;

	packet.session_codec = codec;

	iris_hfi_gen1_expect(inst, HFI_MSG_SYS_SESSION_INIT);

	ret = iris_hfi_queue_session_cmd_write(inst, &packet, packet.shdr.hdr.size);
	if (ret)
		return ret;

	ret = iris_wait_for_session_response(inst, false);
	if (ret)
		return ret;

	/*
	 * ROG5: the OEM firmware leaves its content-protection mode unknown
	 * unless told (VP9 then failed with "CP breached - buffer type 5/6/7").
	 * Stock sends this for every non-secure session before any buffer.
	 */
	if (oem && oem->secure_session_off) {
		u32 secure = 0;

		ret = hfi_gen1_set_property(inst, HFI_PROPERTY_PARAM_SECURE_SESSION,
					    &secure, sizeof(secure));
		if (ret)
			dev_err(inst->core->dev, "session %#x: SECURE_SESSION=0 failed: %d\n",
				inst->session_id, ret);
	}

	return ret;
}

static void iris_hfi_gen1_packet_session_cmd(struct iris_inst *inst,
					     struct hfi_session_pkt *packet,
					     u32 ptype)
{
	packet->shdr.hdr.size = sizeof(*packet);
	packet->shdr.hdr.pkt_type = ptype;
	packet->shdr.session_id = inst->session_id;
}

static int iris_hfi_gen1_session_close(struct iris_inst *inst)
{
	struct hfi_session_pkt packet;
	int ret;

	/* ROG5: one SESSION_END per session (a failed streamoff already sends it) */
	if (inst->end_sent)
		return 0;

	iris_hfi_gen1_packet_session_cmd(inst, &packet, HFI_CMD_SYS_SESSION_END);
	iris_hfi_gen1_expect(inst, HFI_MSG_SYS_SESSION_END);

	ret = iris_hfi_queue_session_cmd_write(inst, &packet, packet.shdr.hdr.size);
	if (!ret)
		inst->end_sent = true;

	return ret;
}

static int iris_hfi_gen1_session_start(struct iris_inst *inst, u32 plane)
{
	struct hfi_session_pkt packet;
	int ret;

	/*
	 * ROG5, experimental SM8350 encoder only: like stock, configure both
	 * ports before LOAD_RESOURCES/START (the CAPTURE port's properties,
	 * frame rate included, used to arrive after START when the raw port
	 * streamed on first), and set the work route (4 pipes) explicitly.
	 */
	if (iris_enc_start_gated(inst)) {
		struct vb2_queue *dst_q = v4l2_m2m_get_dst_vq(inst->m2m_ctx);
		struct vb2_queue *src_q = v4l2_m2m_get_src_vq(inst->m2m_ctx);
		u32 route = inst->core->iris_platform_data->num_vpp_pipe;

		if (V4L2_TYPE_IS_OUTPUT(plane) && !vb2_start_streaming_called(dst_q)) {
			inst->enc_start_deferred = true;
			return 0;
		}
		/*
		 * CAPTURE: start once the raw port streams, also when CAPTURE
		 * alone was stopped (STOP/RELEASE) and is restarted.
		 */
		if (!V4L2_TYPE_IS_OUTPUT(plane) && !vb2_start_streaming_called(src_q))
			return 0;
		inst->enc_start_deferred = false;
		if (inst->sub_state & IRIS_INST_SUB_LOAD_RESOURCES)
			return 0;
		ret = hfi_gen1_set_property(inst, HFI_PROPERTY_PARAM_WORK_ROUTE,
					    &route, sizeof(route));
		if (ret)
			return ret;
	} else {
		if (!V4L2_TYPE_IS_OUTPUT(plane))
			return 0;

		if (inst->sub_state & IRIS_INST_SUB_LOAD_RESOURCES)
			return 0;
	}

	iris_hfi_gen1_expect(inst, HFI_MSG_SESSION_LOAD_RESOURCES);
	iris_hfi_gen1_packet_session_cmd(inst, &packet, HFI_CMD_SESSION_LOAD_RESOURCES);

	ret = iris_hfi_queue_session_cmd_write(inst, &packet, packet.shdr.hdr.size);
	if (ret)
		return ret;

	ret = iris_wait_for_session_response(inst, false);
	if (ret)
		return ret;

	iris_hfi_gen1_expect(inst, HFI_MSG_SESSION_START);
	iris_hfi_gen1_packet_session_cmd(inst, &packet, HFI_CMD_SESSION_START);

	ret = iris_hfi_queue_session_cmd_write(inst, &packet, packet.shdr.hdr.size);
	if (ret == -ECANCELED) {
		/*
		 * ROG5, enc_stop_before START: LOAD_RESOURCES was acknowledged
		 * but no sub-state records it; release it here, as a stream-off
		 * would after STOP.
		 */
		iris_hfi_gen1_expect(inst, HFI_MSG_SESSION_RELEASE_RESOURCES);
		iris_hfi_gen1_packet_session_cmd(inst, &packet, HFI_CMD_SESSION_RELEASE_RESOURCES);
		ret = iris_hfi_queue_session_cmd_write(inst, &packet, packet.shdr.hdr.size);
		if (!ret)
			ret = iris_wait_for_session_response(inst, false);
		if (ret) {
			dev_err(inst->core->dev,
				"session %#x: release after the cancelled START failed: %d\n",
				inst->session_id, ret);
			return ret;
		}
		return -ECANCELED;
	}
	if (ret)
		return ret;

	ret = iris_wait_for_session_response(inst, false);
	if (ret)
		return ret;

	return iris_inst_change_sub_state(inst, 0, IRIS_INST_SUB_LOAD_RESOURCES);
}

/*
 * ROG5: STOP, then RELEASE_RESOURCES only if STOP succeeded; the first
 * failure is the result (it used to be overwritten by the second command).
 */
static int iris_hfi_gen1_stop_release(struct iris_inst *inst)
{
	struct hfi_session_pkt pkt;
	int ret;

	iris_hfi_gen1_expect(inst, HFI_MSG_SESSION_STOP);
	iris_hfi_gen1_packet_session_cmd(inst, &pkt, HFI_CMD_SESSION_STOP);
	ret = iris_hfi_queue_session_cmd_write(inst, &pkt, pkt.shdr.hdr.size);
	if (!ret)
		ret = iris_wait_for_session_response(inst, false);

	if (!ret) {
		iris_hfi_gen1_expect(inst, HFI_MSG_SESSION_RELEASE_RESOURCES);
		iris_hfi_gen1_packet_session_cmd(inst, &pkt, HFI_CMD_SESSION_RELEASE_RESOURCES);
		ret = iris_hfi_queue_session_cmd_write(inst, &pkt, pkt.shdr.hdr.size);
		if (!ret)
			ret = iris_wait_for_session_response(inst, false);
	}
	if (ret)
		dev_err(inst->core->dev, "session %#x: stop/release failed: %d\n",
			inst->session_id, ret);

	iris_inst_change_sub_state(inst, IRIS_INST_SUB_LOAD_RESOURCES, 0);

	return ret;
}

static int iris_hfi_gen1_session_stop(struct iris_inst *inst, u32 plane)
{
	struct hfi_session_flush_pkt flush_pkt;
	u32 flush_type = 0;
	int ret = 0;

	if (inst->domain == DECODER) {
		if (inst->state == IRIS_INST_STREAMING) {
			if (V4L2_TYPE_IS_OUTPUT(plane))
				flush_type = HFI_FLUSH_ALL;
			else if (V4L2_TYPE_IS_CAPTURE(plane))
				flush_type = HFI_FLUSH_OUTPUT;

			reinit_completion(&inst->flush_completion);

			flush_pkt.shdr.hdr.size = sizeof(struct hfi_session_flush_pkt);
			flush_pkt.shdr.hdr.pkt_type = HFI_CMD_SESSION_FLUSH;
			flush_pkt.shdr.session_id = inst->session_id;
			flush_pkt.flush_type = flush_type;

			ret = iris_hfi_queue_session_cmd_write(inst, &flush_pkt, flush_pkt.shdr.hdr.size);
			if (!ret) {
				inst->flush_responses_pending++;
				ret = iris_wait_for_session_response(inst, true);
			}
		} else if (inst->sub_state & IRIS_INST_SUB_LOAD_RESOURCES) {
			ret = iris_hfi_gen1_stop_release(inst);
			/*
			 * ROG5: each queue returns its own buffers in
			 * iris_vb2_stop_streaming(); the other queue stopped
			 * earlier, and completing it again here hit buffers vb2
			 * no longer owned.
			 */
		}
	} else {
		/*
		 * ROG5, experimental SM8350 encoder: a deferred start is
		 * cancelled by any stream-off, and a session the firmware never
		 * loaded/started gets no STOP/RELEASE.
		 */
		if (iris_enc_start_gated(inst)) {
			inst->enc_start_deferred = false;
			if (!(inst->sub_state & IRIS_INST_SUB_LOAD_RESOURCES))
				goto return_buffers;
		}
		if (inst->state == IRIS_INST_STREAMING ||
		    inst->state == IRIS_INST_INPUT_STREAMING ||
		    inst->state == IRIS_INST_ERROR) {
			ret = iris_hfi_gen1_stop_release(inst);
		}

return_buffers:
		iris_helper_buffers_done(inst, V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE,
					 VB2_BUF_STATE_ERROR);
		iris_helper_buffers_done(inst, V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE,
					 VB2_BUF_STATE_ERROR);
	}

	return ret;
}

static int iris_hfi_gen1_session_continue(struct iris_inst *inst, u32 plane)
{
	struct hfi_session_pkt packet;

	iris_hfi_gen1_packet_session_cmd(inst, &packet, HFI_CMD_SESSION_CONTINUE);

	return iris_hfi_queue_session_cmd_write(inst, &packet, packet.shdr.hdr.size);
}

static int iris_hfi_gen1_queue_input_buffer(struct iris_inst *inst, struct iris_buffer *buf)
{
	/* ROG5: no field left unset (extradata_buffer, data, ...) */
	struct hfi_session_empty_buffer_compressed_pkt com_ip_pkt = {};
	struct hfi_session_empty_buffer_uncompressed_pkt uncom_ip_pkt = {};

	if (!iris_dma_range_ok(inst->core, buf->device_addr, buf->buffer_size, "input buffer"))
		return -EINVAL;

	if (inst->domain == DECODER) {
		com_ip_pkt.shdr.hdr.size = sizeof(struct hfi_session_empty_buffer_compressed_pkt);
		com_ip_pkt.shdr.hdr.pkt_type = HFI_CMD_SESSION_EMPTY_BUFFER;
		com_ip_pkt.shdr.session_id = inst->session_id;
		com_ip_pkt.time_stamp_hi = upper_32_bits(buf->timestamp);
		com_ip_pkt.time_stamp_lo = lower_32_bits(buf->timestamp);
		com_ip_pkt.flags = 0;
		com_ip_pkt.mark_target = 0;
		com_ip_pkt.mark_data = 0;
		com_ip_pkt.offset = buf->data_offset;
		com_ip_pkt.alloc_len = buf->buffer_size;
		com_ip_pkt.filled_len = buf->data_size;
		com_ip_pkt.input_tag = buf->index;
		com_ip_pkt.packet_buffer = buf->device_addr;
		return iris_hfi_queue_session_cmd_write(inst, &com_ip_pkt,
						com_ip_pkt.shdr.hdr.size);
	} else {
		uncom_ip_pkt.shdr.hdr.size =
			sizeof(struct hfi_session_empty_buffer_uncompressed_pkt);
		uncom_ip_pkt.shdr.hdr.pkt_type = HFI_CMD_SESSION_EMPTY_BUFFER;
		uncom_ip_pkt.shdr.session_id = inst->session_id;
		uncom_ip_pkt.time_stamp_hi = upper_32_bits(buf->timestamp);
		uncom_ip_pkt.time_stamp_lo = lower_32_bits(buf->timestamp);
		uncom_ip_pkt.view_id = 0;
		uncom_ip_pkt.flags = buf->flags;
		uncom_ip_pkt.mark_target = 0;
		uncom_ip_pkt.mark_data = 0;
		uncom_ip_pkt.offset = buf->data_offset;
		uncom_ip_pkt.alloc_len = buf->buffer_size;
		uncom_ip_pkt.filled_len = buf->data_size;
		uncom_ip_pkt.input_tag = buf->index;
		uncom_ip_pkt.packet_buffer = buf->device_addr;
		return iris_hfi_queue_session_cmd_write(inst, &uncom_ip_pkt,
						uncom_ip_pkt.shdr.hdr.size);
	}
}

static int iris_hfi_gen1_queue_output_buffer(struct iris_inst *inst, struct iris_buffer *buf)
{
	struct hfi_session_fill_buffer_pkt op_pkt = {};

	if (!iris_dma_range_ok(inst->core, buf->device_addr, buf->buffer_size, "output buffer"))
		return -EINVAL;

	op_pkt.shdr.hdr.size = sizeof(struct hfi_session_fill_buffer_pkt);
	op_pkt.shdr.hdr.pkt_type = HFI_CMD_SESSION_FILL_BUFFER;
	op_pkt.shdr.session_id = inst->session_id;
	op_pkt.output_tag = buf->index;
	op_pkt.packet_buffer = buf->device_addr;
	op_pkt.extradata_buffer = 0;
	op_pkt.alloc_len = buf->buffer_size;
	op_pkt.filled_len = buf->data_size;
	op_pkt.offset = buf->data_offset;
	op_pkt.data = 0;

	if (buf->type == BUF_OUTPUT && iris_split_mode_enabled(inst))
		op_pkt.stream_id = 1;
	else
		op_pkt.stream_id = 0;

	return iris_hfi_queue_session_cmd_write(inst, &op_pkt, op_pkt.shdr.hdr.size);
}

static int iris_hfi_gen1_queue_internal_buffer(struct iris_inst *inst, struct iris_buffer *buf)
{
	struct hfi_session_set_buffers_pkt *int_pkt;
	u32 buffer_type, i;
	u32 packet_size;
	int ret;

	if (!iris_dma_range_ok(inst->core, buf->device_addr, buf->buffer_size, "internal buffer"))
		return -EINVAL;

	packet_size = struct_size(int_pkt, buffer_info, 1);
	int_pkt = kzalloc(packet_size, GFP_KERNEL);
	if (!int_pkt)
		return -ENOMEM;

	int_pkt->shdr.hdr.pkt_type = HFI_CMD_SESSION_SET_BUFFERS;
	int_pkt->shdr.session_id = inst->session_id;
	int_pkt->buffer_size = buf->buffer_size;
	int_pkt->min_buffer_size = buf->buffer_size;
	int_pkt->num_buffers = 1;
	int_pkt->extradata_size = 0;
	int_pkt->shdr.hdr.size = packet_size;
	for (i = 0; i < int_pkt->num_buffers; i++)
		int_pkt->buffer_info[i] = buf->device_addr;
	buffer_type = iris_hfi_gen1_buf_type_from_driver(buf->type);
	if (buffer_type == -EINVAL) {
		ret = -EINVAL;
		goto exit;
	}

	int_pkt->buffer_type = buffer_type;
	ret = iris_hfi_queue_session_cmd_write(inst, int_pkt, int_pkt->shdr.hdr.size);

exit:
	kfree(int_pkt);

	return ret;
}

static int iris_hfi_gen1_session_queue_buffer(struct iris_inst *inst, struct iris_buffer *buf)
{
	switch (buf->type) {
	case BUF_INPUT:
		return iris_hfi_gen1_queue_input_buffer(inst, buf);
	case BUF_OUTPUT:
	case BUF_DPB:
		return iris_hfi_gen1_queue_output_buffer(inst, buf);
	case BUF_PERSIST:
	case BUF_BIN:
	case BUF_SCRATCH_1:
	case BUF_SCRATCH_2:
	case BUF_ARP:
		return iris_hfi_gen1_queue_internal_buffer(inst, buf);
	default:
		return -EINVAL;
	}
}

static int iris_hfi_gen1_session_unset_buffers(struct iris_inst *inst, struct iris_buffer *buf)
{
	struct hfi_session_release_buffer_pkt *pkt;
	u32 packet_size, buffer_type, i;
	int ret;

	buffer_type = iris_hfi_gen1_buf_type_from_driver(buf->type);
	if (buffer_type == -EINVAL)
		return -EINVAL;

	if (buffer_type == HFI_BUFFER_INPUT)
		return 0;

	packet_size = sizeof(*pkt) + sizeof(struct hfi_buffer_info);
	pkt = kzalloc(packet_size, GFP_KERNEL);
	if (!pkt)
		return -ENOMEM;

	pkt->shdr.hdr.pkt_type = HFI_CMD_SESSION_RELEASE_BUFFERS;
	pkt->shdr.session_id = inst->session_id;
	pkt->buffer_size = buf->buffer_size;
	pkt->num_buffers = 1;

	if (buffer_type == HFI_BUFFER_OUTPUT ||
	    buffer_type == HFI_BUFFER_OUTPUT2) {
		struct hfi_buffer_info *bi;

		bi = (struct hfi_buffer_info *)pkt->buffer_info;
		for (i = 0; i < pkt->num_buffers; i++) {
			bi->buffer_addr = buf->device_addr;
			bi->extradata_addr = 0;
		}
		pkt->shdr.hdr.size = packet_size;
	} else {
		for (i = 0; i < pkt->num_buffers; i++)
			pkt->buffer_info[i] = buf->device_addr;
		pkt->extradata_size = 0;
		pkt->shdr.hdr.size =
				sizeof(struct hfi_session_set_buffers_pkt) +
				((pkt->num_buffers) * sizeof(u32));
	}

	pkt->response_req = true;
	pkt->buffer_type = buffer_type;

	/* ROG5: this wait had no reinit before; a stale completion satisfied it */
	iris_hfi_gen1_expect(inst, HFI_MSG_SESSION_RELEASE_BUFFERS);
	ret = iris_hfi_queue_session_cmd_write(inst, pkt, pkt->shdr.hdr.size);
	if (ret)
		goto exit;

	ret = iris_wait_for_session_response(inst, false);
	if (!ret)
		ret = iris_destroy_internal_buffer(inst, buf);

exit:
	kfree(pkt);

	return ret;
}

static int iris_hfi_gen1_session_drain(struct iris_inst *inst, u32 plane)
{
	if (inst->domain == DECODER) {
		struct hfi_session_empty_buffer_compressed_pkt ip_pkt = {0};

		ip_pkt.shdr.hdr.size = sizeof(struct hfi_session_empty_buffer_compressed_pkt);
		ip_pkt.shdr.hdr.pkt_type = HFI_CMD_SESSION_EMPTY_BUFFER;
		ip_pkt.shdr.session_id = inst->session_id;
		ip_pkt.flags = HFI_BUFFERFLAG_EOS;
		ip_pkt.packet_buffer = 0xdeadb000;

		if (iris_hfi_gen1_eos_buffer(inst)) {
			int ret = iris_hfi_gen1_get_eos_buffer(inst, &ip_pkt.packet_buffer);

			if (ret)
				return ret;
			ip_pkt.alloc_len = SZ_4K;
			ip_pkt.filled_len = 0;
		}
		dev_dbg(inst->core->dev, "session %#x: drain, EOS buffer %#x\n",
			inst->session_id, ip_pkt.packet_buffer);

		return iris_hfi_queue_session_cmd_write(inst, &ip_pkt, ip_pkt.shdr.hdr.size);
	}

	if (inst->domain == ENCODER) {
		struct hfi_session_empty_buffer_uncompressed_pkt ip_pkt = {0};

		/* ROG5: no EOS before the experimental encoder's session started */
		if (iris_enc_start_gated(inst) &&
		    !(inst->sub_state & IRIS_INST_SUB_LOAD_RESOURCES))
			return -EBUSY;

		ip_pkt.shdr.hdr.size = sizeof(struct hfi_session_empty_buffer_uncompressed_pkt);
		ip_pkt.shdr.hdr.pkt_type = HFI_CMD_SESSION_EMPTY_BUFFER;
		ip_pkt.shdr.session_id = inst->session_id;
		ip_pkt.flags = HFI_BUFFERFLAG_EOS;
		ip_pkt.packet_buffer = 0xdeadb000;

		/* ROG5: the encoder drain too (stock uses one EOS path) */
		if (iris_hfi_gen1_eos_buffer(inst)) {
			int ret = iris_hfi_gen1_get_eos_buffer(inst, &ip_pkt.packet_buffer);

			if (ret)
				return ret;
			ip_pkt.alloc_len = SZ_4K;
			ip_pkt.filled_len = 0;
		}

		return iris_hfi_queue_session_cmd_write(inst, &ip_pkt, ip_pkt.shdr.hdr.size);
	}

	return -EINVAL;
}

static int
iris_hfi_gen1_packet_session_set_property(struct hfi_session_set_property_pkt *packet,
					  struct iris_inst *inst, u32 ptype, void *pdata)
{
	void *prop_data = &packet->data[1];

	packet->shdr.hdr.size = sizeof(*packet) + sizeof(ptype);
	packet->shdr.hdr.pkt_type = HFI_CMD_SESSION_SET_PROPERTY;
	packet->shdr.session_id = inst->session_id;
	packet->num_properties = 1;
	packet->data[0] = ptype;

	switch (ptype) {
	case HFI_PROPERTY_PARAM_FRAME_SIZE: {
		struct hfi_framesize *in = pdata, *fsize = prop_data;

		fsize->buffer_type = in->buffer_type;
		fsize->height = in->height;
		fsize->width = in->width;
		packet->shdr.hdr.size += sizeof(*fsize);
		break;
	}
	case HFI_PROPERTY_CONFIG_VIDEOCORES_USAGE: {
		struct hfi_videocores_usage_type *in = pdata, *cu = prop_data;

		cu->video_core_enable_mask = in->video_core_enable_mask;
		packet->shdr.hdr.size += sizeof(*cu);
		break;
	}
	case HFI_PROPERTY_PARAM_UNCOMPRESSED_FORMAT_SELECT: {
		struct hfi_uncompressed_format_select *in = pdata;
		struct hfi_uncompressed_format_select *hfi = prop_data;

		hfi->buffer_type = in->buffer_type;
		hfi->format = in->format;
		packet->shdr.hdr.size += sizeof(*hfi);
		break;
	}
	case HFI_PROPERTY_PARAM_UNCOMPRESSED_PLANE_ACTUAL_CONSTRAINTS_INFO: {
		struct hfi_uncompressed_plane_actual_constraints_info *info = prop_data;
		struct hfi_uncompressed_plane_actual_constraints_info *in = pdata;

		/*
		 * ROG5: send the caller's constraints (the only caller,
		 * iris_hfi_gen1_set_format_constraints(), filled the same
		 * values this used to hard-code, except the SM8350 luma
		 * alignment).
		 */
		*info = *in;
		if (info->num_planes > 2)
			return -EINVAL;

		packet->shdr.hdr.size += sizeof(*info);
		break;
	}
	case HFI_PROPERTY_PARAM_BUFFER_COUNT_ACTUAL: {
		struct hfi_buffer_count_actual *in = pdata;
		struct hfi_buffer_count_actual *count = prop_data;

		count->type = in->type;
		count->count_actual = in->count_actual;
		count->count_min_host = in->count_min_host;
		packet->shdr.hdr.size += sizeof(*count);
		break;
	}
	case HFI_PROPERTY_PARAM_VDEC_MULTI_STREAM: {
		struct hfi_multi_stream *in = pdata;
		struct hfi_multi_stream *multi = prop_data;

		multi->buffer_type = in->buffer_type;
		multi->enable = in->enable;
		packet->shdr.hdr.size += sizeof(*multi);
		break;
	}
	case HFI_PROPERTY_PARAM_BUFFER_SIZE_ACTUAL: {
		struct hfi_buffer_size_actual *in = pdata, *sz = prop_data;

		sz->size = in->size;
		sz->type = in->type;
		packet->shdr.hdr.size += sizeof(*sz);
		break;
	}
	case HFI_PROPERTY_PARAM_SECURE_SESSION: {
		u32 *in = pdata;

		packet->data[1] = *in;
		packet->shdr.hdr.size += sizeof(u32);
		break;
	}
	case HFI_PROPERTY_PARAM_WORK_ROUTE: {
		struct hfi_video_work_route *wr = prop_data;
		u32 *in = pdata;

		wr->video_work_route = *in;
		packet->shdr.hdr.size += sizeof(*wr);
		break;
	}
	case HFI_PROPERTY_PARAM_WORK_MODE: {
		struct hfi_video_work_mode *wm = prop_data;
		u32 *in = pdata;

		wm->video_work_mode = *in;
		packet->shdr.hdr.size += sizeof(*wm);
		break;
	}
	case HFI_PROPERTY_PARAM_PROFILE_LEVEL_CURRENT: {
		struct hfi_profile_level *in = pdata, *pl = prop_data;

		pl->level = in->level;
		pl->profile = in->profile;
		if (pl->profile <= 0)
			/* Profile not supported, falling back to high */
			pl->profile = V4L2_MPEG_VIDEO_H264_PROFILE_HIGH;

		if (!pl->level)
			/* Level not supported, falling back to 1 */
			pl->level = 1;

		packet->shdr.hdr.size += sizeof(*pl);
		break;
	}
	case HFI_PROPERTY_CONFIG_VENC_SYNC_FRAME_SEQUENCE_HEADER: {
		struct hfi_enable *en = prop_data;
		u32 *in = pdata;

		en->enable = *in;
		packet->shdr.hdr.size += sizeof(*en);
		break;
	}
	case HFI_PROPERTY_CONFIG_VENC_TARGET_BITRATE: {
		struct hfi_bitrate *in = pdata, *brate = prop_data;

		brate->bitrate = in->bitrate;
		brate->layer_id = in->layer_id;
		packet->shdr.hdr.size += sizeof(*brate);
		break;
	}
	case HFI_PROPERTY_PARAM_VENC_RATE_CONTROL: {
		u32 *in = pdata;

		switch (*in) {
		case HFI_RATE_CONTROL_OFF:
		case HFI_RATE_CONTROL_CBR_CFR:
		case HFI_RATE_CONTROL_CBR_VFR:
		case HFI_RATE_CONTROL_VBR_CFR:
		case HFI_RATE_CONTROL_VBR_VFR:
		case HFI_RATE_CONTROL_CQ:
			break;
		default:
			return -EINVAL;
		}

		packet->data[1] = *in;
		packet->shdr.hdr.size += sizeof(u32);
		break;
	}
	case HFI_PROPERTY_PARAM_VENC_H264_ENTROPY_CONTROL: {
		struct hfi_h264_entropy_control *entropy = prop_data;
		u32 *in = pdata;

		entropy->entropy_mode = *in;
		if (entropy->entropy_mode == HFI_H264_ENTROPY_CABAC)
			entropy->cabac_model = HFI_H264_CABAC_MODEL_0;
		packet->shdr.hdr.size += sizeof(*entropy);
		break;
	}
	case HFI_PROPERTY_PARAM_VENC_SESSION_QP_RANGE_V2: {
		struct hfi_quantization_range_v2 *range = prop_data;
		struct hfi_quantization_range_v2 *in = pdata;
		u32 min_qp, max_qp;

		min_qp = in->min_qp.qp_packed;
		max_qp = in->max_qp.qp_packed;

		/* We'll be packing in the qp, so make sure we
		 * won't be losing data when masking
		 */
		if (min_qp > 0xff || max_qp > 0xff)
			return -ERANGE;

		range->min_qp.layer_id = 0xFF;
		range->max_qp.layer_id = 0xFF;
		range->min_qp.qp_packed = (min_qp & 0xFF) | ((min_qp & 0xFF) << 8) |
			((min_qp & 0xFF) << 16);
		range->max_qp.qp_packed = (max_qp & 0xFF) | ((max_qp & 0xFF) << 8) |
			((max_qp & 0xFF) << 16);
		range->min_qp.enable = 7;
		range->max_qp.enable = 7;
		packet->shdr.hdr.size += sizeof(*range);
		break;
	}
	case HFI_PROPERTY_CONFIG_FRAME_RATE: {
		struct hfi_framerate *frate = prop_data;
		struct hfi_framerate *in = pdata;

		frate->buffer_type = in->buffer_type;
		frate->framerate = in->framerate;
		packet->shdr.hdr.size += sizeof(*frate);
		break;
	}
	case HFI_PROPERTY_PARAM_UNCOMPRESSED_PLANE_ACTUAL_INFO: {
		struct hfi_uncompressed_plane_actual_info *plane_actual_info = prop_data;
		struct hfi_uncompressed_plane_actual_info *in = pdata;

		plane_actual_info->buffer_type = in->buffer_type;
		plane_actual_info->num_planes = in->num_planes;
		plane_actual_info->plane_format[0] = in->plane_format[0];
		if (in->num_planes > 1)
			plane_actual_info->plane_format[1] = in->plane_format[1];
		packet->shdr.hdr.size += sizeof(*plane_actual_info);
		break;
	}
	case HFI_PROPERTY_PARAM_VENC_INTRA_REFRESH: {
		struct hfi_intra_refresh *in = pdata, *intra_refresh = prop_data;

		intra_refresh->mode = in->mode;
		intra_refresh->mbs = in->mbs;
		packet->shdr.hdr.size += sizeof(*intra_refresh);
		break;
	}
	case HFI_PROPERTY_PARAM_VENC_LTRMODE: {
		struct hfi_ltr_mode *in = pdata, *ltr_mode = prop_data;

		ltr_mode->mode = in->mode;
		ltr_mode->count = in->count;
		ltr_mode->trust_mode = in->trust_mode;
		packet->shdr.hdr.size += sizeof(*ltr_mode);
		break;
	}
	case HFI_PROPERTY_CONFIG_VENC_USELTRFRAME: {
		struct hfi_ltr_use *in = pdata, *ltr_use = prop_data;

		ltr_use->frames = in->frames;
		ltr_use->ref_ltr = in->ref_ltr;
		ltr_use->use_constrnt = in->use_constrnt;
		packet->shdr.hdr.size += sizeof(*ltr_use);
		break;
	}
	case HFI_PROPERTY_CONFIG_VENC_MARKLTRFRAME: {
		struct hfi_ltr_mark *in = pdata, *ltr_mark = prop_data;

		ltr_mark->mark_frame = in->mark_frame;
		packet->shdr.hdr.size += sizeof(*ltr_mark);
		break;
	}
	case HFI_PROPERTY_CONFIG_VENC_INTRA_PERIOD: {
		struct hfi_intra_period *in = pdata, *intra_period = prop_data;

		intra_period->pframes = in->pframes;
		intra_period->bframes = in->bframes;
		packet->shdr.hdr.size += sizeof(*intra_period);
		break;
	}
	case HFI_PROPERTY_PARAM_VENC_HIER_P_MAX_NUM_ENH_LAYER: {
		u32 *in = pdata;

		packet->data[1] = *in;
		packet->shdr.hdr.size += sizeof(u32);
		break;
	}
	case HFI_PROPERTY_CONFIG_VENC_HIER_P_ENH_LAYER: {
		u32 *in = pdata;

		packet->data[1] = *in;
		packet->shdr.hdr.size += sizeof(u32);
		break;
	}
	default:
		return -EINVAL;
	}

	return 0;
}

/*
 * ROG5: the packetizer writes the property's wire structure, which is not
 * always what the caller passed as payload_size: profile/level came with
 * 4 bytes for an 8-byte structure and the H.264 entropy control with 4 for
 * 8 (entropy_mode + cabac_model), so both packets ran 4 bytes past their
 * allocation. Allocate room for the largest gen1 property structure and
 * check the written size against it before the packet is queued.
 */
#define IRIS_HFI_GEN1_PROP_MAX	128

static int hfi_gen1_set_property(struct iris_inst *inst, u32 packet_type,
				 void *payload, u32 payload_size)
{
	struct hfi_session_set_property_pkt *pkt;
	u32 packet_size;
	int ret;

	BUILD_BUG_ON(sizeof(struct hfi_uncompressed_plane_actual_constraints_info) >
		     IRIS_HFI_GEN1_PROP_MAX);
	BUILD_BUG_ON(sizeof(struct hfi_uncompressed_plane_actual_info) > IRIS_HFI_GEN1_PROP_MAX);
	BUILD_BUG_ON(sizeof(struct hfi_quantization_range_v2) > IRIS_HFI_GEN1_PROP_MAX);
	BUILD_BUG_ON(sizeof(struct hfi_buffer_count_actual) > IRIS_HFI_GEN1_PROP_MAX);
	BUILD_BUG_ON(sizeof(struct hfi_ltr_use) > IRIS_HFI_GEN1_PROP_MAX);

	packet_size = sizeof(*pkt) + sizeof(u32) +
		      max_t(u32, payload_size, IRIS_HFI_GEN1_PROP_MAX);
	pkt = kzalloc(packet_size, GFP_KERNEL);
	if (!pkt)
		return -ENOMEM;

	ret = iris_hfi_gen1_packet_session_set_property(pkt, inst, packet_type, payload);
	if (ret == -EOPNOTSUPP) {
		ret = 0;
		goto exit;
	}
	if (ret)
		goto exit;

	if (WARN_ONCE(pkt->shdr.hdr.size > packet_size,
		      "iris: property %#x wrote %u bytes into %u\n",
		      packet_type, pkt->shdr.hdr.size, packet_size)) {
		ret = -EOVERFLOW;
		goto exit;
	}

	ret = iris_hfi_queue_session_cmd_write(inst, pkt, pkt->shdr.hdr.size);

exit:
	kfree(pkt);

	return ret;
}

static int iris_hfi_gen1_session_set_property(struct iris_inst *inst, u32 packet_type,
					      u32 flag, u32 plane, u32 payload_type,
					      void *payload, u32 payload_size)
{
	return hfi_gen1_set_property(inst, packet_type, payload, payload_size);
}

static int iris_hfi_gen1_set_resolution(struct iris_inst *inst, u32 plane)
{
	u32 ptype = HFI_PROPERTY_PARAM_FRAME_SIZE;
	struct hfi_framesize fs;
	int ret;

	if (!iris_drc_pending(inst) && !(inst->sub_state & IRIS_INST_SUB_FIRST_IPSC)) {
		fs.buffer_type = HFI_BUFFER_INPUT;
		fs.width = inst->fmt_src->fmt.pix_mp.width;
		fs.height = inst->fmt_src->fmt.pix_mp.height;

		ret = hfi_gen1_set_property(inst, ptype, &fs, sizeof(fs));
		if (ret)
			return ret;
	}
	if (inst->domain == DECODER)
		fs.buffer_type = HFI_BUFFER_OUTPUT2;
	else
		fs.buffer_type = HFI_BUFFER_OUTPUT;

	fs.width = inst->fmt_dst->fmt.pix_mp.width;
	fs.height = inst->fmt_dst->fmt.pix_mp.height;

	return hfi_gen1_set_property(inst, ptype, &fs, sizeof(fs));
}

static int iris_hfi_gen1_decide_core(struct iris_inst *inst, u32 plane)
{
	const u32 ptype = HFI_PROPERTY_CONFIG_VIDEOCORES_USAGE;
	struct hfi_videocores_usage_type cu;

	cu.video_core_enable_mask = HFI_CORE_ID_1;

	return hfi_gen1_set_property(inst, ptype, &cu, sizeof(cu));
}

static int iris_hfi_gen1_set_raw_format(struct iris_inst *inst, u32 plane)
{
	const u32 ptype = HFI_PROPERTY_PARAM_UNCOMPRESSED_FORMAT_SELECT;
	struct hfi_uncompressed_format_select fmt;
	u32 pixelformat;
	int ret;

	if (inst->domain == DECODER) {
		pixelformat = inst->fmt_dst->fmt.pix_mp.pixelformat;
		if (iris_split_mode_enabled(inst)) {
			fmt.buffer_type = HFI_BUFFER_OUTPUT;
			fmt.format = HFI_COLOR_FORMAT_NV12_UBWC;

			ret = hfi_gen1_set_property(inst, ptype, &fmt, sizeof(fmt));
			if (ret)
				return ret;

			fmt.buffer_type = HFI_BUFFER_OUTPUT2;
			fmt.format = pixelformat == V4L2_PIX_FMT_NV12 ?
				HFI_COLOR_FORMAT_NV12 : HFI_COLOR_FORMAT_NV12_UBWC;

			ret = hfi_gen1_set_property(inst, ptype, &fmt, sizeof(fmt));
		} else {
			fmt.buffer_type = HFI_BUFFER_OUTPUT;
			fmt.format = pixelformat == V4L2_PIX_FMT_NV12 ?
				HFI_COLOR_FORMAT_NV12 : HFI_COLOR_FORMAT_NV12_UBWC;

			ret = hfi_gen1_set_property(inst, ptype, &fmt, sizeof(fmt));
		}
	} else {
		pixelformat = inst->fmt_src->fmt.pix_mp.pixelformat;
		fmt.buffer_type = HFI_BUFFER_INPUT;
		fmt.format = pixelformat == V4L2_PIX_FMT_NV12 ?
			HFI_COLOR_FORMAT_NV12 : HFI_COLOR_FORMAT_NV12_UBWC;
		ret = hfi_gen1_set_property(inst, ptype, &fmt, sizeof(fmt));
	}

	return ret;
}

static int iris_hfi_gen1_set_format_constraints(struct iris_inst *inst, u32 plane)
{
	const u32 ptype = HFI_PROPERTY_PARAM_UNCOMPRESSED_PLANE_ACTUAL_CONSTRAINTS_INFO;
	struct hfi_uncompressed_plane_actual_constraints_info pconstraint;

	if (inst->fmt_dst->fmt.pix_mp.pixelformat == V4L2_PIX_FMT_QC08C)
		return 0;

	pconstraint.buffer_type = HFI_BUFFER_OUTPUT2;
	pconstraint.num_planes = 2;
	pconstraint.plane_format[0].stride_multiples = 128;
	pconstraint.plane_format[0].max_stride = 8192;
	pconstraint.plane_format[0].min_plane_buffer_height_multiple = 32;
	/* ROG5: stock (msm_vdec.c:501) aligns the luma plane to 512 */
	pconstraint.plane_format[0].buffer_alignment =
		inst->core->iris_platform_data->oem ? 512 : 256;

	pconstraint.plane_format[1].stride_multiples = 128;
	pconstraint.plane_format[1].max_stride = 8192;
	pconstraint.plane_format[1].min_plane_buffer_height_multiple = 16;
	pconstraint.plane_format[1].buffer_alignment = 256;

	return hfi_gen1_set_property(inst, ptype, &pconstraint, sizeof(pconstraint));
}

/*
 * ROG5, SM8350: off by default so that a VP9 result can be attributed to the
 * DPB size (0170) or to the counts; takes effect at the next stream start.
 */
static bool stock_buf_counts;
module_param(stock_buf_counts, bool, 0644);
MODULE_PARM_DESC(stock_buf_counts, "SM8350 decoder: buffer counts as stock (OUTPUT = DPBs, OUTPUT2 = CAPTURE)");

static int iris_hfi_gen1_set_num_bufs(struct iris_inst *inst, u32 plane)
{
	u32 ptype = HFI_PROPERTY_PARAM_BUFFER_COUNT_ACTUAL;
	struct hfi_buffer_count_actual buf_count;
	int ret;

	buf_count.type = HFI_BUFFER_INPUT;
	buf_count.count_actual = VIDEO_MAX_FRAME;
	buf_count.count_min_host = VIDEO_MAX_FRAME;

	ret = hfi_gen1_set_property(inst, ptype, &buf_count, sizeof(buf_count));
	if (ret)
		return ret;

	if (inst->domain == DECODER && inst->core->iris_platform_data->oem &&
	    READ_ONCE(stock_buf_counts) && iris_split_mode_enabled(inst)) {
		struct vb2_queue *dst_q = v4l2_m2m_get_dst_vq(inst->m2m_ctx);
		u32 min = inst->buffers[BUF_OUTPUT].min_count;

		/*
		 * ROG5, SM8350 OEM firmware, as stock (msm_vdec.c:1092): the
		 * firmware's OUTPUT port carries the DPBs (their count, which
		 * is what gets queued), OUTPUT2 the client's CAPTURE buffers
		 * (its minimum, and what is allocated). iris sent OUTPUT 32/32
		 * and the DPB count for OUTPUT2.
		 */
		buf_count.type = HFI_BUFFER_OUTPUT;
		buf_count.count_actual = iris_vpu_buf_count(inst, BUF_DPB);
		buf_count.count_min_host = buf_count.count_actual;
		ret = hfi_gen1_set_property(inst, ptype, &buf_count, sizeof(buf_count));
		if (ret)
			return ret;

		buf_count.type = HFI_BUFFER_OUTPUT2;
		buf_count.count_min_host = min;
		buf_count.count_actual = max_t(u32, min, vb2_get_num_buffers(dst_q));
		iris_mark(inst->core, "counts: DPB %u, CAPTURE min %u actual %u",
			  iris_vpu_buf_count(inst, BUF_DPB), min, buf_count.count_actual);

		return hfi_gen1_set_property(inst, ptype, &buf_count, sizeof(buf_count));
	}

	if (inst->domain == DECODER) {
		if (iris_split_mode_enabled(inst)) {
			buf_count.type = HFI_BUFFER_OUTPUT;
			buf_count.count_actual = VIDEO_MAX_FRAME;
			buf_count.count_min_host = VIDEO_MAX_FRAME;

			ret = hfi_gen1_set_property(inst, ptype, &buf_count, sizeof(buf_count));
			if (ret)
				return ret;

			buf_count.type = HFI_BUFFER_OUTPUT2;
			buf_count.count_actual = iris_vpu_buf_count(inst, BUF_DPB);
			buf_count.count_min_host = iris_vpu_buf_count(inst, BUF_DPB);

			ret = hfi_gen1_set_property(inst, ptype, &buf_count, sizeof(buf_count));
		} else {
			buf_count.type = HFI_BUFFER_OUTPUT;
			buf_count.count_actual = VIDEO_MAX_FRAME;
			buf_count.count_min_host = VIDEO_MAX_FRAME;

			ret = hfi_gen1_set_property(inst, ptype, &buf_count, sizeof(buf_count));
		}
	} else {
		buf_count.type = HFI_BUFFER_OUTPUT;
		buf_count.count_actual = VIDEO_MAX_FRAME;
		buf_count.count_min_host = VIDEO_MAX_FRAME;

		ret = hfi_gen1_set_property(inst, ptype, &buf_count, sizeof(buf_count));
	}

	return ret;
}

static int iris_hfi_gen1_set_multistream(struct iris_inst *inst, u32 plane)
{
	u32 ptype = HFI_PROPERTY_PARAM_VDEC_MULTI_STREAM;
	struct hfi_multi_stream multi = {0};
	int ret;

	if (iris_split_mode_enabled(inst)) {
		multi.buffer_type = HFI_BUFFER_OUTPUT;
		multi.enable = 0;

		ret = hfi_gen1_set_property(inst, ptype, &multi, sizeof(multi));
		if (ret)
			return ret;

		multi.buffer_type = HFI_BUFFER_OUTPUT2;
		multi.enable = 1;

		ret = hfi_gen1_set_property(inst, ptype, &multi, sizeof(multi));
	} else {
		multi.buffer_type = HFI_BUFFER_OUTPUT;
		multi.enable = 1;

		ret = hfi_gen1_set_property(inst, ptype, &multi, sizeof(multi));
		if (ret)
			return ret;

		multi.buffer_type = HFI_BUFFER_OUTPUT2;
		multi.enable = 0;

		ret = hfi_gen1_set_property(inst, ptype, &multi, sizeof(multi));
	}

	return ret;
}

static int iris_hfi_gen1_set_bufsize(struct iris_inst *inst, u32 plane)
{
	const u32 ptype = HFI_PROPERTY_PARAM_BUFFER_SIZE_ACTUAL;
	struct hfi_buffer_size_actual bufsz;
	int ret;

	if (iris_split_mode_enabled(inst)) {
		bufsz.type = HFI_BUFFER_OUTPUT;
		bufsz.size = inst->core->iris_firmware_desc->get_vpu_buffer_size(inst, BUF_DPB);

		ret = hfi_gen1_set_property(inst, ptype, &bufsz, sizeof(bufsz));
		if (ret)
			return ret;

		bufsz.type = HFI_BUFFER_OUTPUT2;
		bufsz.size = inst->buffers[BUF_OUTPUT].size;

		ret = hfi_gen1_set_property(inst, ptype, &bufsz, sizeof(bufsz));
	} else {
		bufsz.type = HFI_BUFFER_OUTPUT;
		bufsz.size = inst->buffers[BUF_OUTPUT].size;

		ret = hfi_gen1_set_property(inst, ptype, &bufsz, sizeof(bufsz));
		if (ret)
			return ret;

		bufsz.type = HFI_BUFFER_OUTPUT2;
		bufsz.size = 0;

		ret = hfi_gen1_set_property(inst, ptype, &bufsz, sizeof(bufsz));
	}

	return ret;
}

static int iris_hfi_gen1_set_frame_rate(struct iris_inst *inst, u32 plane)
{
	const u32 ptype = HFI_PROPERTY_CONFIG_FRAME_RATE;
	struct hfi_framerate frate;

	if (V4L2_TYPE_IS_OUTPUT(plane))
		return 0;

	frate.buffer_type = HFI_BUFFER_OUTPUT;
	frate.framerate = inst->frame_rate << 16;

	return hfi_gen1_set_property(inst, ptype, &frate, sizeof(frate));
}

static int iris_hfi_gen1_set_stride(struct iris_inst *inst, u32 plane)
{
	const u32 ptype = HFI_PROPERTY_PARAM_UNCOMPRESSED_PLANE_ACTUAL_INFO;
	struct hfi_uncompressed_plane_actual_info plane_actual_info;

	plane_actual_info.buffer_type = HFI_BUFFER_INPUT;
	plane_actual_info.num_planes = 2;
	plane_actual_info.plane_format[0].actual_stride =
		ALIGN(inst->fmt_src->fmt.pix_mp.width, 128);
	plane_actual_info.plane_format[0].actual_plane_buffer_height =
		ALIGN(inst->fmt_src->fmt.pix_mp.height, 32);
	plane_actual_info.plane_format[1].actual_stride =
		ALIGN(inst->fmt_src->fmt.pix_mp.width, 128);
	plane_actual_info.plane_format[1].actual_plane_buffer_height =
		(ALIGN(inst->fmt_src->fmt.pix_mp.height, 32)) / 2;

	return hfi_gen1_set_property(inst, ptype, &plane_actual_info, sizeof(plane_actual_info));
}

static int iris_hfi_gen1_session_set_config_params(struct iris_inst *inst, u32 plane)
{
	struct iris_hfi_prop_type_handle const *handler = NULL;
	u32 handler_size = 0;
	struct iris_core *core = inst->core;
	u32 config_params_size, i, j;
	const u32 *config_params;
	int ret;

	static const struct iris_hfi_prop_type_handle vdec_prop_type_handle_inp_arr[] = {
		{HFI_PROPERTY_PARAM_FRAME_SIZE,
			iris_hfi_gen1_set_resolution},
		{HFI_PROPERTY_CONFIG_VIDEOCORES_USAGE,
			iris_hfi_gen1_decide_core},
		{HFI_PROPERTY_PARAM_UNCOMPRESSED_FORMAT_SELECT,
			iris_hfi_gen1_set_raw_format},
		{HFI_PROPERTY_PARAM_UNCOMPRESSED_PLANE_ACTUAL_CONSTRAINTS_INFO,
			iris_hfi_gen1_set_format_constraints},
		{HFI_PROPERTY_PARAM_BUFFER_COUNT_ACTUAL,
			iris_hfi_gen1_set_num_bufs},
		{HFI_PROPERTY_PARAM_VDEC_MULTI_STREAM,
			iris_hfi_gen1_set_multistream},
		{HFI_PROPERTY_PARAM_BUFFER_SIZE_ACTUAL,
			iris_hfi_gen1_set_bufsize},
	};

	static const struct iris_hfi_prop_type_handle vdec_prop_type_handle_out_arr[] = {
		{HFI_PROPERTY_PARAM_FRAME_SIZE,
			iris_hfi_gen1_set_resolution},
		{HFI_PROPERTY_PARAM_UNCOMPRESSED_FORMAT_SELECT,
			iris_hfi_gen1_set_raw_format},
		{HFI_PROPERTY_PARAM_UNCOMPRESSED_PLANE_ACTUAL_CONSTRAINTS_INFO,
			iris_hfi_gen1_set_format_constraints},
		{HFI_PROPERTY_PARAM_BUFFER_COUNT_ACTUAL,
			iris_hfi_gen1_set_num_bufs},
		{HFI_PROPERTY_PARAM_VDEC_MULTI_STREAM,
			iris_hfi_gen1_set_multistream},
		{HFI_PROPERTY_PARAM_BUFFER_SIZE_ACTUAL,
			iris_hfi_gen1_set_bufsize},
	};

	static const struct iris_hfi_prop_type_handle venc_prop_type_handle_inp_arr[] = {
		{HFI_PROPERTY_CONFIG_FRAME_RATE,
			iris_hfi_gen1_set_frame_rate},
		{HFI_PROPERTY_PARAM_UNCOMPRESSED_PLANE_ACTUAL_INFO,
			iris_hfi_gen1_set_stride},
		{HFI_PROPERTY_PARAM_FRAME_SIZE,
			iris_hfi_gen1_set_resolution},
		{HFI_PROPERTY_PARAM_UNCOMPRESSED_FORMAT_SELECT,
			iris_hfi_gen1_set_raw_format},
		{HFI_PROPERTY_PARAM_BUFFER_COUNT_ACTUAL,
			iris_hfi_gen1_set_num_bufs},
	};

	if (inst->domain == DECODER) {
		config_params = core->iris_firmware_data->dec_input_config_params_default;
		config_params_size = core->iris_firmware_data->dec_input_config_params_default_size;
		if (V4L2_TYPE_IS_OUTPUT(plane)) {
			handler = vdec_prop_type_handle_inp_arr;
			handler_size = ARRAY_SIZE(vdec_prop_type_handle_inp_arr);
		} else if (V4L2_TYPE_IS_CAPTURE(plane)) {
			handler = vdec_prop_type_handle_out_arr;
			handler_size = ARRAY_SIZE(vdec_prop_type_handle_out_arr);
		}
	} else {
		config_params = core->iris_firmware_data->enc_input_config_params;
		config_params_size = core->iris_firmware_data->enc_input_config_params_size;
		handler = venc_prop_type_handle_inp_arr;
		handler_size = ARRAY_SIZE(venc_prop_type_handle_inp_arr);
	}

	for (i = 0; i < config_params_size; i++) {
		for (j = 0; j < handler_size; j++) {
			if (handler[j].type == config_params[i]) {
				ret = handler[j].handle(inst, plane);
				if (ret)
					return ret;
				break;
			}
		}
	}

	return 0;
}

static const struct iris_hfi_session_ops iris_hfi_gen1_session_ops = {
	.session_open = iris_hfi_gen1_session_open,
	.session_set_config_params = iris_hfi_gen1_session_set_config_params,
	.session_set_property = iris_hfi_gen1_session_set_property,
	.session_start = iris_hfi_gen1_session_start,
	.session_queue_buf = iris_hfi_gen1_session_queue_buffer,
	.session_release_buf = iris_hfi_gen1_session_unset_buffers,
	.session_resume_drc = iris_hfi_gen1_session_continue,
	.session_stop = iris_hfi_gen1_session_stop,
	.session_drain = iris_hfi_gen1_session_drain,
	.session_close = iris_hfi_gen1_session_close,
};

static struct iris_inst *iris_hfi_gen1_get_instance(void)
{
	struct iris_inst *out;

	out = kzalloc_obj(*out);
	if (!out)
		return NULL;

	out->hfi_session_ops = &iris_hfi_gen1_session_ops;

	return out;
}

static const struct iris_hfi_sys_ops iris_hfi_gen1_sys_ops = {
	.sys_init = iris_hfi_gen1_sys_init,
	.sys_image_version = iris_hfi_gen1_sys_image_version,
	.sys_interframe_powercollapse = iris_hfi_gen1_sys_interframe_powercollapse,
	.sys_pc_prep = iris_hfi_gen1_sys_pc_prep,

	.sys_hfi_response_handler = iris_hfi_gen1_response_handler,

	.sys_get_instance = iris_hfi_gen1_get_instance,
};

void iris_hfi_gen1_sys_ops_init(struct iris_core *core)
{
	core->hfi_sys_ops = &iris_hfi_gen1_sys_ops;
}
