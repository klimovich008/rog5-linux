#!/usr/bin/env python3
"""Read a private identity profile; this grants no device-operation authority."""
import json
import os
from pathlib import Path
import re
import stat


def load(path):
    path=Path(path)
    if not path.is_absolute() or not path.name.endswith('.local.json'):
        raise ValueError('an absolute ignored .local.json profile is required')
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or stat.S_IMODE(before.st_mode)!=0o600 or before.st_nlink!=1 or before.st_size>4096:
            raise ValueError('unsafe private profile metadata')
        raw=os.read(descriptor,4097)
        after=os.fstat(descriptor)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError('private profile changed while reading')
    finally:
        os.close(descriptor)
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('duplicate private identity field')
            result[key]=value
        return result
    result=json.loads(raw,object_pairs_hook=unique)
    if set(result)!={'schema','serial','product','usb_path','expected_slot','rescue_slot','authority'} or result['schema']!=1:
        raise ValueError('unsupported private identity schema')
    if not re.fullmatch('[A-Za-z0-9.-]{4,64}',result['serial']) or result['serial'].startswith('REPLACE'):
        raise ValueError('unconfigured serial')
    if not re.fullmatch(r'[0-9]+-[0-9]+(?:\.[0-9]+)*',result['usb_path']):
        raise ValueError('unconfigured USB topology')
    if result['product']!='lahaina' or result['expected_slot']!='b' or result['rescue_slot']!='a' or result['authority']!='identity only; no operation authorization':
        raise ValueError('device/rescue scope changed')
    return result


if __name__=='__main__':
    raise SystemExit('Import-only identity reader; do not print private identity into shared logs')
