/* SPDX-License-Identifier: GPL-2.0-or-later */
/* ncm_tx_timeout excerpt: Linux f_ncm.c.
 * Copyright (C) 2010 Nokia Corporation; contact Yauheni Kaliuta.
 * Driver borrows from f_ecm.c, Copyright (C) 2003-2005,2008 David Brownell
 * and Copyright (C) 2008 Nokia Corporation.
 * Surrounding code is a timer/queue fixture,
 * not a replacement gadget implementation or physical USB simulation.
 */
#include <stddef.h>
#include <stdio.h>

typedef int netdev_tx_t;
enum hrtimer_restart { HRTIMER_NORESTART, HRTIMER_RESTART };
enum { NETDEV_TX_OK = 0, NETDEV_TX_BUSY = 0x10 };
#define TX_TIMEOUT_NSECS 300000
#define READ_ONCE(value) (value)
#define container_of(ptr, type, member) \
	((type *)((char *)(ptr) - offsetof(type, member)))
struct hrtimer { unsigned forwards, interval; };
struct net_device;
struct net_device_ops {
	netdev_tx_t (*ndo_start_xmit)(void *, struct net_device *);
};
struct net_device { const struct net_device_ops *netdev_ops; };
struct f_ncm { struct hrtimer task_timer; struct net_device *netdev; };
static unsigned calls, busy, pending, sent;
static void __attribute__((unused))
hrtimer_forward_now(struct hrtimer *timer, unsigned interval)
{
	timer->forwards++;
	timer->interval = interval;
}
static netdev_tx_t transmit(void *skb, struct net_device *netdev)
{
	(void)netdev;
	if (skb) return -1;
	calls++;
	if (busy) { busy--; return NETDEV_TX_BUSY; }
	if (pending) { pending = 0; sent++; }
	return NETDEV_TX_OK;
}

/* source: ncm_tx_timeout */
static enum hrtimer_restart ncm_tx_timeout(struct hrtimer *data)
{
	struct f_ncm *ncm = container_of(data, struct f_ncm, task_timer);
	struct net_device *netdev = READ_ONCE(ncm->netdev);

	if (netdev) {
		/* XXX This allowance of a NULL skb argument to ndo_start_xmit
		 * XXX is not sane.  The gadget layer should be redesigned so
		 * XXX that the dev->wrap() invocations to build SKBs is transparent
		 * XXX and performed in some way outside of the ndo_start_xmit
		 * XXX interface.
		 *
		 * This will call directly into u_ether's eth_start_xmit()
		 */
		netdev->netdev_ops->ndo_start_xmit(NULL, netdev);
	}
	return HRTIMER_NORESTART;
}
/* end: ncm_tx_timeout */

int main(void)
{
	const struct net_device_ops ops = { .ndo_start_xmit = transmit };
	struct net_device netdev = { .netdev_ops = &ops };
	struct f_ncm ncm = { .netdev = &netdev };

	/* A completed flush must not be duplicated. */
	pending = 1;
	if (ncm_tx_timeout(&ncm.task_timer) != HRTIMER_NORESTART ||
	    pending || calls != 1 || sent != 1 || ncm.task_timer.forwards)
		return 2;

	/* No new traffic arrives to fill the pending NTB. Timer owns retry. */
	calls = sent = 0; pending = 1; busy = 2;
	for (unsigned tick = 0; tick < 3; tick++) {
		enum hrtimer_restart state = ncm_tx_timeout(&ncm.task_timer);
		if (pending && state == HRTIMER_NORESTART) {
			fprintf(stderr, "FAIL pending NTB stranded: calls=%u busy=%u\n", calls, busy);
			return 1;
		}
		if (!pending) {
			if (state != HRTIMER_NORESTART) return 3;
			break;
		}
	}
	if (pending || calls != 3 || sent != 1 || ncm.task_timer.forwards != 2 ||
	    ncm.task_timer.interval != TX_TIMEOUT_NSECS) return 4;

	/* Repeated BUSY retains data; removing netdev stops further callbacks. */
	busy = 10; pending = 1;
	for (unsigned tick = 0; tick < 10; tick++)
		if (ncm_tx_timeout(&ncm.task_timer) != HRTIMER_RESTART || !pending)
			return 5;
	ncm.netdev = NULL;
	unsigned before = calls, forwarded = ncm.task_timer.forwards;
	if (ncm_tx_timeout(&ncm.task_timer) != HRTIMER_NORESTART ||
	    calls != before || ncm.task_timer.forwards != forwarded) return 6;
	puts("PASS busy flush retries at 300us, success stops, absent device stops");
	return 0;
}
