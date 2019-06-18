#!/usr/bin/env bash
cd `dirname $0`

./box-up >/dev/null &

while ! ssh -p 5522 pi@localhost " echo BOX UP "
do
    sleep 1
    echo "Retrying ssh login ..."
done

./07-revvy-setup.sh

./box-down
