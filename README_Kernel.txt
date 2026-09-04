    ################################################################################
    1. How to Build
            - get Toolchain
                    From android git server, codesourcery and etc ..
                    - Ex) gcc/linux-x86/aarch64/aarch64-linux-android-4.9/bin/aarch64-linux-android-
            - edit Makefile (or using make option)
                    edit "CROSS_COMPILE" to right toolchain path(You downloaded).
                            Ex)  CROSS_COMPILE=$(android platform directory you download)/android/prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9/bin/aarch64-linux-android-
                            Ex)  CROSS_COMPILE=/usr/local/toolchain/gcc/linux-x86/aarch64/aarch64-linux-android-4.9/bin/aarch64-linux-android- // check the location of toolchain
            - to Build
                    $ export ANDROID_MAJOR_VERSION=o
                    $ make ARCH=arm64 exynos7870-a2corelte_defconfig
                    $ make ARCH=arm64
 
    2. Output files
            - Kernel : arch/arm64/boot/Image
            - module : drivers/*/*.ko
 
    3. How to Clean
            $ make clean
    ################################################################################
