#!/usr/bin/env python3
"""Replace the ARM64 kernel payload in a legacy Android boot.img.

Preserves the original boot header, ramdisk and DTB/DTBO payload exactly.
Only kernel_size and the kernel payload are changed.
"""
import argparse, struct

PAGE = 36
KERNEL_SIZE = 8
RAMDISK_SIZE = 16
DT_SIZE = 40
MAGIC = b'ANDROID!'

def align(x, page):
    return (x + page - 1) // page * page

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stock_boot')
    ap.add_argument('kernel')
    ap.add_argument('output')
    args = ap.parse_args()

    boot = bytearray(open(args.stock_boot, 'rb').read())
    kernel = open(args.kernel, 'rb').read()
    if boot[:8] != MAGIC:
        raise SystemExit('ERROR: not an Android boot image')
    page = struct.unpack_from('<I', boot, PAGE)[0]
    if page not in (512, 1024, 2048, 4096, 8192):
        raise SystemExit(f'ERROR: unsupported page size {page}')

    old_ks = struct.unpack_from('<I', boot, KERNEL_SIZE)[0]
    rs = struct.unpack_from('<I', boot, RAMDISK_SIZE)[0]
    ds = struct.unpack_from('<I', boot, DT_SIZE)[0]

    ko = page
    ro = ko + align(old_ks, page)
    do = ro + align(rs, page)
    if do + ds > len(boot):
        raise SystemExit('ERROR: boot image payload is truncated')

    ramdisk = bytes(boot[ro:ro + rs])
    dt = bytes(boot[do:do + ds])

    # Samsung A260G uses a legacy Android boot header. Rebuild it while
    # retaining all fields, command line, id and unused vendor data.
    header = bytes(boot[:page])
    header = bytearray(header)
    struct.pack_into('<I', header, KERNEL_SIZE, len(kernel))

    out = bytearray(header)
    out += kernel
    out += b'\0' * (align(len(kernel), page) - len(kernel))
    out += ramdisk
    out += b'\0' * (align(len(ramdisk), page) - len(ramdisk))
    out += dt
    out += b'\0' * (align(len(dt), page) - len(dt))

    with open(args.output, 'wb') as f:
        f.write(out)

    print(f'old kernel: {old_ks} bytes')
    print(f'new kernel: {len(kernel)} bytes')
    print(f'ramdisk:    {rs} bytes')
    print(f'dtb:        {ds} bytes')
    print(f'page size:  {page}')
    print(f'output:     {args.output} ({len(out)} bytes)')

if __name__ == '__main__':
    main()
