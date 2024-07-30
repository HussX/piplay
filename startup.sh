#!/usr/bin/env bash
export QT_QPA_PLATFORM=eglfs
export QT_QPA_EGLFS_SWAPINTERVAL=0
export QT_QPA_EGLFS_HIDECURSOR=1

systype=$( cat /proc/cpuinfo | grep Model | cut -d ":" -f 2 )
sub='Pi 5'
if [[ "$systype" == *"$sub"* ]]
    then
        echo '{ "device": "/dev/dri/card1" }' > eglfs.json
        export QT_QPA_EGLFS_KMS_CONFIG=eglfs.json
fi

python3 /opt/piplay/piplay.py

