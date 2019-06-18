How to Build an SD card
=======================

Using Ubuntu/Debian run 00-run-all.sh which will run all the other 
numbered scripts in this directory one after the other.

	./00-run-all.sh

This will all take some time (about 10-20 mins for me) and finally create a 
fully provisioned revvy.img which can then be written to an SD 
card and booted on a Raspberry PI. Other useful scripts that can now be 
run to further manipulate this image are.

	./box-up

Will start a QEMU box. Note that you will no longer be able to use that 
shell while this box runs.

	./box-down

Will stop a QEMU box.

	./ssh

Will log you into the running QEMU box


A note on security, the user pi with password raspberry and with your 
.ssh public key setup to allow passwordless ssh login. So be sure to 
change the password and remove the .ssh key if you want the image to be 
secure.

## Overview of the baking process
The process downloads a raspbian image, makes some filesystem changes, fires it up in an emulator and runs the setup process.

Step by step:

* 01-download: Downloads the Raspbian image and some files required to run QEMU on it
* 02-install: Installs QEMU to the host
* 03-box-init: Applies some filesystem level changes. E.g.: Enabling ssh via touch /boot/ssh, setting up RPi config
* 04-box-softboil: Currenly inactive
* 05-box-up: Starts RPi emulation of the image via QEMU
* 06-box-setup: System wide updates to the image like resizing fs, updating distrib, installing os packages.
* 07-revvy-setup: Updating the application related files and running related setup steps.
* 08-box-down: Terminates QEMU
