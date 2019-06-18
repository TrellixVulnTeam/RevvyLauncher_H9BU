#!/usr/bin/env bash
cd `dirname $0`

THISDIR=`dirname $0`

echo " creating revvy.img "


echo " copying raspbian "
cp raspbian.img revvy.img



echo " resizing to 2gig "
qemu-img resize -f raw revvy.img 2G

echo " checking partition information "

PART_BOOT_START=$(parted revvy.img -ms unit s print | grep "^1" | cut -f 2 -d: | cut -f 1 -ds)
PART_ROOT_START=$(parted revvy.img -ms unit s print | grep "^2" | cut -f 2 -d: | cut -f 1 -ds)
echo $PART_BOOT_START $PART_ROOT_START

echo " resizing using fdisk "
fdisk revvy.img <<EOF
p
d
2
n
p
2
$PART_ROOT_START

p
w
EOF


./box-mount

echo " enable ssh"
# TODO: IS THIS WORKING?
sudo touch boot/ssh >/dev/null

echo " setup boot config to 720p with no overscan and a 32meg gfx card and uart"
sudo tee boot/config.txt >/dev/null <<EOF

gpu_mem=32

hdmi_force_hotplug=1
hdmi_drive=2
hdmi_group=1
config_hdmi_boost=4

#set 720p with no overscan
hdmi_mode=4
disable_overscan=1

enable_uart=1

EOF

#this is needed to allow qemu to boot
sudo tee root/etc/ld.so.preload.qemu >/dev/null <<EOF

#/usr/lib/arm-linux-gnueabihf/libarmmem.so

EOF
sudo tee root/etc/ld.so.preload.card >/dev/null <<EOF

/usr/lib/arm-linux-gnueabihf/libarmmem.so

EOF

#copy fstab to qemu and card versions
sudo tee root/etc/fstab.card >/dev/null <<EOF

proc            /proc           proc    defaults          0       0
/dev/mmcblk0p1  /boot           vfat    defaults,noatime  0       2
/dev/mmcblk0p2  /               ext4    defaults,noatime  0       1

#/dev/sda2  /               ext4    defaults,noatime  0       1

EOF


#use these for qemu booting
sudo tee root/etc/fstab.qemu >/dev/null <<EOF

proc             /proc           proc    defaults          0       0
#/dev/mmcblk0p1  /boot           vfat    defaults,noatime  0       2
#/dev/mmcblk0p2  /               ext4    defaults,noatime  0       1

/dev/sda2  /               ext4    defaults,noatime  0       1

EOF

./box-umount
