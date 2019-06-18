#!/usr/bin/env bash
cd `dirname $0`

#update these to get a newer version
RASPBIAN_FILE=2019-04-08-raspbian-stretch-lite
RASPBIAN_URL=https://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-2019-04-09/$RASPBIAN_FILE.zip


if [ -f raspbian.img ] ; then

    echo " raspbian.img exists so skipping download and unpack "

else

    wget -O $RASPBIAN_FILE.zip $RASPBIAN_URL
    unzip -o $RASPBIAN_FILE.zip

    if [ -f $RASPBIAN_FILE.img ] ; then

        rm $RASPBIAN_FILE.zip
        mv $RASPBIAN_FILE.img raspbian.img

    else

        echo "Failed to extract raspbian image"

    fi

fi




if [ -f kernel-qemu ] ; then

    echo " kernel-qemu exists so skipping download "

else

    wget -O versatile-pb.dtb https://github.com/dhruvvyas90/qemu-rpi-kernel/blob/master/versatile-pb.dtb?raw=true
    wget -O kernel-qemu https://github.com/dhruvvyas90/qemu-rpi-kernel/blob/master/kernel-qemu-4.14.79-stretch?raw=true

fi

