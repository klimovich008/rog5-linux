// SPDX-License-Identifier: GPL-2.0
/* Hardware boundaries are fault fixtures. Included kernel statements are exact. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define EPROBE_DEFER 517
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
#define IS_ERR(x) ((intptr_t)(x) < 0)
#define PTR_ERR(x) ((int)(intptr_t)(x))
static int stub_error(int error) { return error; }
#define dev_err_probe(dev, error, ...) stub_error(error)
#define dev_err(...) ((void)0)
#define dev_dbg(...) ((void)0)
#define pr_debug(...) ((void)0)
#define BITS_PER_BYTE 8
#define PACKING_BYTES_PW 4
#define GENI_IF_DISABLE_RO 0x64
#define FIFO_IF_DISABLE 1
#define GFP_KERNEL 0
#define I2C_M_RD 1
#define I2C_M_DMA_SAFE 0x0200
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, #x); exit(1); } } while (0)
typedef uint8_t u8;
enum geni_se_protocol_type { GENI_SE_NONE, GENI_SE_SPI, GENI_SE_UART, GENI_SE_I2C,
                            GENI_SE_I3C, GENI_SE_SPI_SLAVE, GENI_SE_INVALID_PROTO = 255 };
enum geni_se_xfer_mode { GENI_SE_INVALID, GENI_SE_FIFO, GENI_SE_DMA, GENI_GPI_DMA };
struct device { void *of_node; };
struct wrapper { struct device *dev; };
struct geni_se { struct device *dev; struct wrapper *wrapper; char *base; };
struct geni_i2c_dev { struct geni_se se; void *tx_c, *rx_c; bool no_dma, gpi_mode; unsigned tx_wm; };
struct descriptor { bool no_dma_support; unsigned tx_fifo_depth; };
struct firmware { int unused; };
struct i2c_msg { unsigned addr, len, flags; u8 *buf; };
static struct device device;
static char registers[0x68];
static struct wrapper wrapper = { &device };
static const char *protocol_name[] = { "none", "spi", "uart", "i2c", "i3c", "spi-slave" };
static struct { int proto, fifo, depth, tx_error, rx_error, name_error, request_error,
    load_error, tx_calls, rx_calls, releases, names, requests, loads, mode, configured;
    bool gsi; } f;
static unsigned geni_se_read_proto(struct geni_se *se) { return f.proto; }
static unsigned readl_relaxed(char *address) { CHECK(address == registers + 0x64); return f.fifo; }
static unsigned geni_se_get_tx_fifo_depth(struct geni_se *se) { return f.depth; }
static void geni_se_select_mode(struct geni_se *se, int mode) { f.mode = mode; }
static void geni_se_init(struct geni_se *se, unsigned watermark, unsigned depth) { f.configured++; }
static void geni_se_config_packing(struct geni_se *se, int bits, int bytes, bool a, bool b, bool c) {}
static void *dma_request_chan(struct device *dev, const char *name)
{
    if (!strcmp(name, "tx")) { f.tx_calls++; return f.tx_error ? (void *)(intptr_t)f.tx_error : (void *)1; }
    f.rx_calls++; return f.rx_error ? (void *)(intptr_t)f.rx_error : (void *)2;
}
static void dma_release_channel(void *channel) { CHECK(channel == (void *)1); f.releases++; }
static int device_property_read_string(struct device *dev, const char *key, const char **name)
{ CHECK(!strcmp(key, "firmware-name")); f.names++; *name = "fixture-never-loaded"; return f.name_error; }
static bool of_property_read_bool(void *node, const char *key)
{ CHECK(!strcmp(key, "qcom,enable-gsi-dma")); return f.gsi; }
static int request_firmware(const struct firmware **fw, const char *name, struct device *dev)
{ static struct firmware inert; f.requests++; *fw = &inert; return f.request_error; }
static int geni_load_se_fw(struct geni_se *se, const struct firmware *fw, int mode, int protocol)
{ f.loads++; f.mode = mode; return f.load_error; }
static void release_firmware(const struct firmware *fw) {}
static void *kzalloc(size_t size, int flags) { return calloc(1, size); }
static void *kmemdup(void *source, size_t size, int flags)
{ void *p = malloc(size); if (p) memcpy(p, source, size); return p; }
#include "firmware.inc"
#include "setup.inc"
#include "buffer.inc"
/* Only the contiguous mode-selection block of probe is exercised here.
 * Prior clock/IRQ setup and later adapter registration/cleanup are not modeled. */
static int select_probe_mode(struct geni_i2c_dev *gi2c)
{
    struct descriptor *desc = NULL;
    struct device *dev = gi2c->se.dev;
    unsigned proto, tx_depth;
    bool fifo_disable;
    int ret;
    (void)dev;
#include "protocol.inc"
    return 0;
err_resources:
    return ret;
}
static void *select_message_buffer(struct geni_i2c_dev *gi2c, struct i2c_msg *msg)
{
    struct geni_se *se = &gi2c->se;
    void *dma_buf;
#include "buffer-select.inc"
    return dma_buf;
}
static struct geni_i2c_dev fresh(void)
{
    memset(&f, 0, sizeof(f)); f.proto = GENI_SE_I2C; f.depth = 16;
    return (struct geni_i2c_dev){ .se = { &device, &wrapper, registers } };
}
int main(void)
{
    struct geni_i2c_dev d;
    u8 data[62] = {0};
    struct i2c_msg msg = { .addr = 0x38, .len = 1, .flags = I2C_M_RD, .buf = data };
    void *buffer;
    d = fresh(); f.proto = GENI_SE_SPI;
    CHECK(select_probe_mode(&d) == -ENXIO); CHECK(!f.names && !f.tx_calls && !f.configured);
    d = fresh(); f.proto = GENI_SE_INVALID_PROTO; f.name_error = -EINVAL;
    CHECK(select_probe_mode(&d) == -EINVAL); CHECK(f.names == 1 && !f.requests && !f.tx_calls);
    d = fresh(); f.proto = GENI_SE_INVALID_PROTO; f.request_error = -ENOENT;
    CHECK(select_probe_mode(&d) == -EPROBE_DEFER); CHECK(f.requests == 1 && !f.loads);
    d = fresh(); f.proto = GENI_SE_INVALID_PROTO; f.request_error = -EIO;
    CHECK(select_probe_mode(&d) == -EIO); CHECK(!f.loads);
    d = fresh(); f.proto = GENI_SE_INVALID_PROTO; f.load_error = -EINVAL;
    CHECK(select_probe_mode(&d) == -EINVAL); CHECK(f.loads == 1 && !f.tx_calls);
    d = fresh(); f.proto = GENI_SE_INVALID_PROTO;
    CHECK(!select_probe_mode(&d)); CHECK(f.loads == 1 && f.mode == GENI_SE_FIFO);
    d = fresh(); f.fifo = FIFO_IF_DISABLE; f.tx_error = -EPROBE_DEFER;
    CHECK(select_probe_mode(&d) == -EPROBE_DEFER); CHECK(f.tx_calls == 1 && !f.rx_calls && !f.releases);
    d = fresh(); f.fifo = FIFO_IF_DISABLE; f.rx_error = -EPROBE_DEFER;
    CHECK(select_probe_mode(&d) == -EPROBE_DEFER); CHECK(f.tx_calls == 1 && f.rx_calls == 1 && f.releases == 1);
    d = fresh(); f.fifo = FIFO_IF_DISABLE;
    CHECK(!select_probe_mode(&d)); CHECK(d.gpi_mode && f.mode == GENI_GPI_DMA && f.tx_calls == 1 && f.rx_calls == 1);
    d = fresh(); f.depth = 0;
    CHECK(select_probe_mode(&d) == -EINVAL); CHECK(!f.configured);
    d = fresh();
    CHECK(!select_probe_mode(&d)); CHECK(!d.gpi_mode && d.tx_wm == 15 && f.configured == 1);
    CHECK(!f.names && !f.requests && !f.tx_calls && !f.rx_calls);
    CHECK(!select_message_buffer(&d, &msg)); CHECK(f.mode == GENI_SE_FIFO);
    msg.len = 62; buffer = select_message_buffer(&d, &msg);
    CHECK(buffer && f.mode == GENI_SE_DMA); free(buffer);
    msg.len = 31; CHECK(!select_message_buffer(&d, &msg));
    msg.len = 32; buffer = select_message_buffer(&d, &msg); CHECK(buffer); free(buffer);
    msg.len = 62; d.no_dma = true;
    CHECK(!select_message_buffer(&d, &msg)); CHECK(f.mode == GENI_SE_FIFO);
    puts("PASS 11 GENI protocol/provider paths and 5 FIFO/SE-DMA buffer cases");
    return 0;
}
