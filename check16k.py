import zipfile, struct, sys

# 使い方: python check16k.py <app-release.aab のパス>
#
# AABのパスは必ず引数で渡す。既定値を持たせてはいけない。
# 別アプリのAABを検査して「問題なし」と誤判定する事故が実際に起きている。
if len(sys.argv) < 2:
    sys.exit("使い方: python check16k.py <app-release.aab のパス>")
AAB = sys.argv[1]

def load_aligns(data):
    assert data[:4] == b'\x7fELF'
    is64 = data[4] == 2
    if is64:
        e_phoff = struct.unpack_from('<Q', data, 0x20)[0]
        e_phentsize = struct.unpack_from('<H', data, 0x36)[0]
        e_phnum = struct.unpack_from('<H', data, 0x38)[0]
    else:
        e_phoff = struct.unpack_from('<I', data, 0x1C)[0]
        e_phentsize = struct.unpack_from('<H', data, 0x2A)[0]
        e_phnum = struct.unpack_from('<H', data, 0x2C)[0]
    aligns = []
    for i in range(e_phnum):
        off = e_phoff + i*e_phentsize
        p_type = struct.unpack_from('<I', data, off)[0]
        if p_type == 1:  # PT_LOAD
            p_align = struct.unpack_from('<Q', data, off+0x30)[0] if is64 else struct.unpack_from('<I', data, off+0x1C)[0]
            aligns.append(p_align)
    return aligns

z = zipfile.ZipFile(AAB)
sos = [n for n in z.namelist() if n.startswith('base/lib/') and n.endswith('.so')]
print(f"{len(sos)} .so files in AAB\n")
bad = []
for n in sorted(sos):
    aligns = load_aligns(z.read(n))
    minalign = min(aligns) if aligns else 0
    abi = n.split('/')[2]
    need16k = (abi == 'arm64-v8a')
    ok = minalign >= 16384
    tag = ("OK " if ok else "BAD") if need16k else "-- "
    print(f"[{tag}] {abi:13} align=0x{minalign:<6x} {n.split('/')[-1]}")
    if need16k and not ok:
        bad.append(n.split('/')[-1])
print()
if bad:
    print("*** NOT 16KB-aligned (arm64-v8a) — これがブロック要因 ***")
    for b in bad: print("   -", b)
else:
    print("All arm64-v8a .so are 16KB-aligned (>=0x4000)")
