#!/usr/bin/env bash
set -euo pipefail

ARCH=arm64
DEFCONFIG=arch/arm64/configs/exynos7870-a2corelte_defconfig

if [[ ! -f "$DEFCONFIG" ]]; then
  echo "ERROR: missing $DEFCONFIG" >&2
  exit 1
fi

# A260G has a 64-bit kernel but Android userspace is 32-bit. Android's
# 32-bit Binder UAPI uses protocol 7; the normal 64-bit UAPI uses protocol 8.
# Force the correct legacy/32-bit Binder ABI in the A260G defconfig.
sed -i '/^CONFIG_ANDROID_BINDER_IPC_32BIT=/d' "$DEFCONFIG"
printf '%s\n' 'CONFIG_ANDROID_BINDER_IPC_32BIT=y' >> "$DEFCONFIG"

# The Samsung Kconfig selects the 32-bit Binder API for Android versions
# newer than P when ANDROID_MAJOR_VERSION is set accordingly.
cat > build_kernel.sh <<'EOF'
#!/usr/bin/env bash
set -e
export ARCH=arm64
export ANDROID_MAJOR_VERSION=q
: "${CROSS_COMPILE:=../PLATFORM/prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9/bin/aarch64-linux-android-}"
export CROSS_COMPILE
make O=out ARCH=arm64 exynos7870-a2corelte_defconfig
make -j"$(nproc)" O=out ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" V=1
EOF
chmod +x build_kernel.sh

echo 'Prepared:'
grep -n 'CONFIG_ANDROID_BINDER_IPC_32BIT' "$DEFCONFIG"
cat build_kernel.sh
