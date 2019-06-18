#!/usr/bin/env bash
cd `dirname $0`

echo " Start installing things that are unique to revvy "

echo "  Enable ttyS0 "
./ssh " sudo systemctl mask serial-getty@ttyS0.service "
./ssh " sudo usermod -a -G tty pi "

echo "  Enable raw sockets for python for BT "
./ssh " sudo setcap 'cap_net_raw,cap_net_admin+eip' \$(readlink -f \$(which python3)) "

echo "  Deploy manager script "
./ssh " mkdir /home/pi/RevvyFramework "
./scp ../src/launch_revvy.py ./RevvyFramework
./scp ../src/version.py ./RevvyFramework

echo " Fetch latest install package "
git clone https://github.com/RevolutionRobotics/RevvyAlphaKit.git
cd RevvyAlphaKit

echo " Build install package "
python3 -m tools.create_package
cd ..

echo " Deploy install package "
./ssh " mkdir /home/pi/RevvyFramework/data "
./ssh " mkdir /home/pi/RevvyFramework/data/ble "
./scp RevvyAlphaKit/install/framework.tar.gz ./RevvyFramework/data/ble/2.data
./scp RevvyAlphaKit/install/framework.meta ./RevvyFramework/data/ble/2.meta

echo " Clean up "
rm -rf RevvyAlphaKit
