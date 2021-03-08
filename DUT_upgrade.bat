adb reboot bootloader 
fastboot flash sbl1 sbl1.mbn
fastboot flash tz tz.mbn
fastboot flash devcfg devcfg.mbn
fastboot flash rpm rpm.mbn
fastboot flash dsp adspso.bin
fastboot flash aboot emmc_appsboot.mbn
fastboot flash dtbo dtbo.img
fastboot flash vbmeta vbmeta.img
fastboot flash boot boot.img
fastboot flash recovery recovery.img
fastboot flash system system.img
fastboot flash modem NON-HLOS.bin
fastboot flash vendor vendor.img
fastboot flash cache cache.img
fastboot flash mdtp mdtp.img
fastboot flash cmnlib cmnlib_30.mbn
fastboot flash cmnlib64 cmnlib64_30.mbn
fastboot flash keymaster keymaster64.mbn
fastboot flash userdata userdata.img
fastboot reboot