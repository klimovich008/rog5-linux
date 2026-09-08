#!/usr/bin/env python3
"""Bounded read-only reset observations; missing records never prove recovery."""
import re


def need(value,message):
    if not value:raise ValueError(message)


def script(identity,loader_sha256,busybox_sha256):
    need(set(identity)=={'boot_id','bundle','release'}
         and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',identity['boot_id'])
         and all(re.fullmatch(r'[A-Za-z0-9._-]{1,96}',identity[key]) for key in ('bundle','release')),
         'invalid reset observation identity')
    need(all(re.fullmatch('[0-9a-f]{64}',value) for value in (loader_sha256,busybox_sha256)),
         'invalid sealed diagnostics tools')
    prefix='set -eu\nloader=/run/initramfs/lib/ld-musl-aarch64.so.1\nbusybox=/run/initramfs/bin/busybox\n'
    prefix+='test ! -L "$loader";test ! -L "$busybox";test -f "$loader";test -f "$busybox"\n'
    for name,pin in (('loader',loader_sha256),('busybox',busybox_sha256)):
        prefix+='test "$(sha256sum "$'+name+'" | cut -d " " -f 1)" = '+pin+'\n'
    prefix+='exec "$loader" "$busybox" sh -s -- '+identity['boot_id']+' '+identity['release']+' '+identity['bundle']+" <<'R01_RESET_OBSERVATION'\n"
    return prefix+r'''set -eu
set -o pipefail
export LC_ALL=C
loader=/run/initramfs/lib/ld-musl-aarch64.so.1
busybox=/run/initramfs/bin/busybox
bb() { "$loader" "$busybox" "$@"; }
hex() { bb od -An -v -tx1 | bb tr -d ' \n'; }
expected_boot=$1; expected_release=$2; expected_bundle=$3
test "$(bb cat /proc/sys/kernel/random/boot_id)" = "$expected_boot"
test "$(bb uname -r)" = "$expected_release"
cmdline=$(bb timeout -s KILL 3 "$loader" "$busybox" head -c 4097 /proc/cmdline)
test "${#cmdline}" -le 4096
count=$(printf '%s\n' "$cmdline" | bb awk -v bundle="rog5.bundle=$expected_bundle" '{for(i=1;i<=NF;i++)if($i==bundle)n++}END{print n+0}')
test "$count" = 1
printf 'format|rog5-r01-reset-observation-v1\nidentity|%s|%s|%s\n' "$expected_boot" "$expected_release" "$expected_bundle"
printf 'cmdline|';printf '%s' "$cmdline" | hex;printf '\n'
count=0
for directory in /sys/fs/pstore /mnt/pstore; do
 if test -L "$directory"; then printf 'directory|%s|error\n' "$directory";continue;fi
 if ! test -e "$directory"; then printf 'directory|%s|absent\n' "$directory";continue;fi
 if ! test -d "$directory"; then printf 'directory|%s|error\n' "$directory";continue;fi
 if ! mounted=$(bb awk -v path="$directory" '$2==path&&$3=="pstore"{n++}END{print n+0}' /proc/mounts 2>/dev/null);then printf 'directory|%s|error\n' "$directory";continue;fi
 if test "$mounted" != 1; then printf 'directory|%s|unsupported\n' "$directory";continue;fi
 printf 'directory|%s|present\n' "$directory"
 for file in "$directory"/* "$directory"/.[!.]* "$directory"/..?*; do
  if ! test -e "$file" && ! test -L "$file";then continue;fi
  count=$((count+1))
  if test "$count" -gt 16;then printf 'overflow|%s\n' "$directory";break;fi
  name=${file##*/};name_hex=$(printf '%s' "$name" | hex)
  if test -L "$file" || ! test -f "$file";then printf 'record|%s|%s|error|\n' "$directory" "$name_hex";continue;fi
  if data=$(bb timeout -s KILL 3 "$loader" "$busybox" head -c 4097 "$file" 2>/dev/null | hex);then
   status=present
   if test "${#data}" -gt 8192;then status=truncated;fi
   printf 'record|%s|%s|%s|%s\n' "$directory" "$name_hex" "$status" "$data"
  else printf 'record|%s|%s|error|\n' "$directory" "$name_hex";fi
 done
done
test "$(bb cat /proc/sys/kernel/random/boot_id)" = "$expected_boot"
printf 'boot_after|%s\n' "$expected_boot"
R01_RESET_OBSERVATION
'''


def replay(raw,identity):
    need(type(raw) is bytes and 0<len(raw)<=160000 and raw.endswith(b'\n'),'reset evidence framing/bound')
    lines=[line.split('|') for line in raw.decode('ascii').splitlines()]
    need(lines[0]==['format','rog5-r01-reset-observation-v1'] and
         lines[1]==['identity',identity['boot_id'],identity['release'],identity['bundle']] and
         lines[-1]==['boot_after',identity['boot_id']],'reset observation belongs to another boot')
    def data(value,limit):
        need(len(value)<=limit*2 and len(value)%2==0 and re.fullmatch('[0-9a-f]*',value),'reset data encoding/bound')
        return bytes.fromhex(value)
    need(len(lines[2])==2 and lines[2][0]=='cmdline','reset command line missing')
    cmdline=data(lines[2][1],4096)
    need(cmdline.split().count(('rog5.bundle='+identity['bundle']).encode())==1,'reset command line identity differs')
    directories={};records=[];overflow=[];seen=set()
    for row in lines[3:-1]:
        if row[0]=='directory':
            need(len(row)==3 and row[1] in ('/sys/fs/pstore','/mnt/pstore') and row[1] not in directories
                 and row[2] in ('present','absent','unsupported','error'),'reset directory frame')
            directories[row[1]]=row[2]
        elif row[0]=='record':
            need(len(row)==5 and directories.get(row[1])=='present' and row[3] in ('present','truncated','error'),
                 'reset record frame')
            name=data(row[2],255);payload=data(row[4],4097)
            need(name not in (b'',b'.',b'..') and b'/' not in name and b'\0' not in name
                 and (row[1],name) not in seen,'unsafe or duplicate reset record name')
            seen.add((row[1],name))
            need((row[3]!='error' or not payload) and (row[3]!='present' or len(payload)<=4096)
                 and (row[3]!='truncated' or len(payload)==4097),'reset record status differs from bytes')
            records.append(dict(directory=row[1],name_hex=row[2],status=row[3],bytes=len(payload)))
        elif row[0]=='overflow':
            need(len(row)==2 and directories.get(row[1])=='present' and row[1] not in overflow,'reset overflow frame')
            overflow.append(row[1])
        else:raise ValueError('unknown reset evidence frame')
    need(set(directories)=={'/sys/fs/pstore','/mnt/pstore'} and len(records)<=16,'reset inventory incomplete or oversized')
    return dict(status='OBSERVED',identity=identity,directories=directories,records=records,overflow=overflow,
                reset_cause_proven=False,empty_pstore_inconclusive=True)
