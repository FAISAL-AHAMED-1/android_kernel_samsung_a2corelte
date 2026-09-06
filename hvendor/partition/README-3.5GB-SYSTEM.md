# 3.5 GB SYSTEM plan

The supplied A260G SYSTEM is about 1.2 GB. A target of 3.5 GB requires physical repartitioning.

Required before generating a flashable PIT:

- exact A260G PIT from the same storage/variant
- exact current SYSTEM start/size
- adjacent partition start/size
- boot/recovery/vendor/data layout
- confirmation of how much space can be reclaimed without moving protected partitions

Do NOT flash an A320/J530/J710/J730 or other Exynos 7870 PIT. Same SoC does not mean same partition map.

This H-Vendor package intentionally does not repartition SYSTEM.
