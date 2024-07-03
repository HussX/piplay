#!/usr/bin/env bash
export QT_QPA_PLATFORM=eglfs
export QT_QPA_EGLFS_SWAPINTERVAL=0
export QT_QPA_EGLFS_HIDECURSOR=1

python3 /opt/piplay/piplay.py
