#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KERNEL="${1:?usage: package_hvendor.sh path/to/Image [output.zip]}"
OUT="${2:-${ROOT}/H-VENDOR-A2CORELTE-v1.0.zip}"
BASE="${ROOT}/hvendor"
WORK="${ROOT}/.hvendor-work"

rm -rf "$WORK"
mkdir -p "$WORK/device/a2corelte/vendor" \
         "$WORK/META-INF/com/google/android" \
         "$WORK/partition"

[[ -f "$KERNEL" ]] || { echo "ERROR: kernel not found: $KERNEL" >&2; exit 1; }
[[ -f "$BASE/base/vendor.tar.zst" ]] || { echo "ERROR: vendor base missing" >&2; exit 1; }
[[ -f "$BASE/device/a2corelte/boot-stock.img" ]] || { echo "ERROR: stock boot missing" >&2; exit 1; }
[[ -f "$BASE/META-INF/com/google/android/update-binary" ]] || { echo "ERROR: update-binary missing" >&2; exit 1; }

zstd -d -c "$BASE/base/vendor.tar.zst" | tar -xpf - -C "$WORK/device/a2corelte"
cp "$BASE/META-INF/com/google/android/update-binary" "$WORK/META-INF/com/google/android/update-binary"
cp "$BASE/partition/README-3.5GB-SYSTEM.md" "$WORK/partition/"

python3 "$ROOT/tools/replace_kernel_in_boot.py" \
  "$BASE/device/a2corelte/boot-stock.img" \
  "$KERNEL" \
  "$WORK/device/a2corelte/boot.img"

cat > "$WORK/META-INF/com/google/android/updater-script" <<'EOF'
assert(is_substring("A260", getprop("ro.boot.bootloader")) || abort("H-VENDOR-A2CORELTE: unsupported bootloader. This package is for SM-A260G/a2corelte only."));

ui_print("============================================");
ui_print(" H-VENDOR-A2CORELTE v1.0");
ui_print(" ARM32 / A-only / Android 10 target");
ui_print(" SM-A260G / a2corelte");
ui_print(" Binder 32-bit kernel fix");
ui_print("============================================");
ui_print(" ");
ui_print("WARNING: experimental GSI vendor baseline.");
ui_print("Stock A260G hardware blobs are preserved.");
ui_print(" ");

set_progress(0.00);
ifelse(is_mounted("/vendor"), unmount("/vendor"));

set_progress(0.10);
ui_print("- Formatting VENDOR");
format("ext4", "EMMC", "/dev/block/platform/13540000.dwmmc0/by-name/VENDOR", "0", "/vendor");

set_progress(0.20);
ui_print("- Mounting VENDOR");
ifelse(is_mounted("/vendor"), "", mount("ext4", "EMMC", "/dev/block/platform/13540000.dwmmc0/by-name/VENDOR", "/vendor"));

set_progress(0.30);
ui_print("- Installing A260G Android 10 vendor baseline");
package_extract_dir("device/a2corelte/vendor", "/vendor");

set_progress(0.72);
ui_print("- Installing A260G Android 10-compatible kernel boot image");
package_extract_file("device/a2corelte/boot.img", "/dev/block/platform/13540000.dwmmc0/by-name/BOOT");

set_progress(0.88);
ui_print("- Restoring vendor metadata");
set_metadata_recursive("/vendor", "uid", 0, "gid", 0, "dmode", 0755, "fmode", 0644, "capabilities", 0x0, "selabel", "u:object_r:vendor_file:s0");
set_metadata_recursive("/vendor/bin", "uid", 0, "gid", 2000, "dmode", 0755, "fmode", 0755, "capabilities", 0x0, "selabel", "u:object_r:vendor_file:s0");
set_metadata_recursive("/vendor/bin/hw", "uid", 0, "gid", 2000, "dmode", 0755, "fmode", 0755, "capabilities", 0x0, "selabel", "u:object_r:vendor_file:s0");
set_metadata_recursive("/vendor/app", "uid", 0, "gid", 2000, "dmode", 0755, "fmode", 0644, "capabilities", 0x0, "selabel", "u:object_r:vendor_app_file:s0");
set_metadata_recursive("/vendor/etc", "uid", 0, "gid", 2000, "dmode", 0755, "fmode", 0644, "capabilities", 0x0, "selabel", "u:object_r:vendor_configs_file:s0");
set_metadata_recursive("/vendor/firmware", "uid", 0, "gid", 2000, "dmode", 0755, "fmode", 0644, "capabilities", 0x0, "selabel", "u:object_r:vendor_firmware_file:s0");
set_metadata_recursive("/vendor/overlay", "uid", 0, "gid", 2000, "dmode", 0755, "fmode", 0644, "capabilities", 0x0, "selabel", "u:object_r:vendor_overlay_file:s0");
set_metadata("/vendor/build.prop", "uid", 0, "gid", 0, "mode", 0600, "capabilities", 0x0, "selabel", "u:object_r:vendor_file:s0");

set_progress(1.0);
ifelse(is_mounted("/vendor"), unmount("/vendor"));
ui_print(" ");
ui_print("H-VENDOR v1.0 installation complete.");
ui_print("SYSTEM is NOT repartitioned.");
ui_print("A verified A260G PIT is required for any future repartitioning.");
EOF

cat > "$WORK/README.md" <<'EOF'
H-VENDOR-A2CORELTE v1.0

Target: Samsung SM-A260G / a2corelte / Exynos 7870
Target userspace: Android 10 ARM32, A-only GSI

This package is built from the A260G stock vendor baseline used by v0.2 and
uses an A260G kernel built from Samsung's open-source 3.18.91 source.

Important kernel compatibility fix:
  CONFIG_ANDROID_BINDER_IPC_32BIT=y

The A260G uses a 64-bit kernel with 32-bit Android userspace. The Binder UAPI
uses protocol 7 when BINDER_IPC_32BIT is enabled and protocol 8 otherwise.

This package does not repartition SYSTEM and does not include a PIT.
It is experimental and hardware testing is still required.
EOF

cat > "$WORK/VERSION" <<'EOF'
1.0
EOF

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(
  cd "$WORK"
  zip -9 -qr "$OUT" .
)

sha256sum "$OUT" > "${OUT}.sha256"
rm -rf "$WORK"

echo "Created: $OUT"
echo "SHA256:  $(cut -d' ' -f1 "${OUT}.sha256")"
