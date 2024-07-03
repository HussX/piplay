#!/usr/bin/env bash
if xset q &>/dev/null; then
	echo "Display is available. Ensuring the screen is on and launching the application..."

	export QT_QPA_PLATFORM=eglfs
	export QT_QPA_EGLFS_SWAPINTERVAL=0
	export QT_QPA_EGLFS_HIDECURSOR=1

	python3 /opt/piplay/piplay.py
else
	echo "No display detected. Please turn on the screen and try again."
    exit 1
fi
