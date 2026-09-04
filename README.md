# android_kernel_samsung_a2corelte

Stock GPL kernel source for the Samsung Galaxy A2 Core (SM-A260G),
as released by Samsung's Open Source Release Center
(SM-A260G_SEA_OO_Opensource.zip).

Linux 3.18.91, matches build A260GDDSCAUJ1 (Oct 2021).

`arch/arm64/configs/exynos7870-a2corelte_defconfig` has been verified
byte-for-byte identical against the `.config` embedded (via IKCONFIG)
in the actual stock boot.img from a real SM-A260G - this is confirmed
to be the exact source for the exact shipped build, not a generic
SEA-region approximation.

## Build

    export ANDROID_MAJOR_VERSION=o
    make ARCH=arm64 exynos7870-a2corelte_defconfig
    make ARCH=arm64

Needs an aarch64-linux-android-4.9 cross-compiler (AOSP prebuilts).
Output: arch/arm64/boot/Image
