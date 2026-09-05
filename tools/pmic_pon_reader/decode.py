#!/usr/bin/env python3
"""Decode the fixed read-only PMK8350 FIFO snapshot, oldest to newest."""
import json
from pathlib import Path
import sys

RESET = {0x80:'KPDPWR_N_S2',0x81:'RESIN_N_S2',0x82:'KPDPWR_AND_RESIN_S2',
         0x83:'PMIC_WATCHDOG_S2',0x84:'PS_HOLD',0x85:'SW_RESET',
         0x21e3:'PMIC_SID2_BCL_ALARM',0x31f5:'PMIC_SID3_BCL_ALARM',
         0x11d0:'PMIC_SID1_OCP',0x21d0:'PMIC_SID2_OCP',
         0x41d0:'PMIC_SID4_OCP',0x51d0:'PMIC_SID5_OCP'}
PON = {0x84:'PS_HOLD',0x85:'HARD_RESET',0x86:'RESIN_N',0x87:'KPDPWR_N',
       0x621:'RTC_ALARM',0x640:'SMPL',0x18c0:'PMIC_SID1_GPIO5',0x31c2:'USB_CHARGER'}
FAULT1 = ['GP_FAULT0','GP_FAULT1','GP_FAULT2','GP_FAULT3','MBG_FAULT','OVLO','UVLO','AVDD_RB']
FAULT2 = ['UNKNOWN0','UNKNOWN1','UNKNOWN2','FAULT_N','FAULT_WATCHDOG','PBS_NACK','RESTART_PON','OVERTEMP_STAGE3']


def decode(blob):
    if len(blob) != 125 or blob[:5] != b'RPON\x01' or blob[7] != 117:
        raise ValueError('wrong snapshot format/size')
    push = blob[5]
    if push != blob[6] or not 0x4b <= push <= 0xbf:
        raise ValueError('FIFO changed or push pointer invalid')
    fifo = blob[8:]
    start = (push - 0x4b - 29 * 4) % 117
    records = []
    for index in range(29):
        state, event, high, low = (fifo[(start + index * 4 + i) % 117] for i in range(4))
        if not any((state, event, high, low)):
            continue
        data = high * 256 + low
        item = {'state':state,'event':event,'data':data}
        if event == 1:
            item['pon_trigger'] = PON.get(data, f'UNKNOWN_{data:04x}')
        elif event == 6:
            item['reset_trigger'] = RESET.get(data, f'UNKNOWN_{data:04x}')
        elif event == 7:
            item['reset_type'] = {1:'WARM_RESET',4:'SHUTDOWN',7:'HARD_RESET'}.get(low, f'UNKNOWN_{low}')
        elif event == 8:
            item['warm_reset_count'] = data
        elif event == 9 or 0x10 <= event <= 0x14:
            item['faults'] = [n for i,n in enumerate(FAULT1) if low & (1 << i)]
            item['faults'] += [n for i,n in enumerate(FAULT2) if high & (1 << i)]
            if event >= 0x10:
                item['pmic_sid'] = event - 0x10 + 1
        elif event == 0x15:
            item['vreg_fault'] = bool(data)
        records.append(item)
    return {'format':'rog5-pon-history-v1','push_pointer':push,'records':records,
            'lineage':'history only; correlate before/after snapshots and observed resets',
            'empty_is_inconclusive':True}


if __name__ == '__main__':
    print(json.dumps(decode(Path(sys.argv[1]).read_bytes()), indent=2))
