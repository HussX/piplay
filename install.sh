#!/usr/bin/env bash
# Run this as root!
if [ "$EUID" -ne 0 ]
	then echo "Please run with sudo"
	exit
fi
echo  "This installation requires several packages from apt.  I made a point to use repo packages instead of a venv"
echo  "It will install python3-opencv python3-pyqt6 vlc gstreamer1.0-tools gstreamer1.0-plugins-base"
echo  "gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly"
echo ""
while true; do
	read -p "Proceed? (y/n)" yn
	case $yn in
		[yY] ) break;;
		[nN] ) echo "Exiting";
			exit;;
		* ) echo "Invalid response";;
	esac
done
apt-get update
apt-get install -y python3-opencv python3-pyqt6 vlc gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
echo ""
#Prompt if user has configured piplay.py
while true; do
	read -p "Have you already configured piplay.py?  It can be configured later in /opt/piplay. (y/n)" config
	case $config in
		[yY] ) break;;
		[nN] ) echo "Exiting";
			exit;;
		* ) echo "Invalid response";;
	esac
done

#Move things to /opt/piplay
mkdir /opt/piplay
mv ./piplay.py /opt/piplay/
mv ./startup.sh /opt/piplay/

#Move service file to /etc/systemd/system/
mv ./piplay.service /etc/systemd/system/

#Enable service
echo "Reloading systemctl daemon"
systemctl daemon-reload
sleep 3
echo "Enabling piplay service"
systemctl enable piplay

#Explain streams/grid/fps/rotation
echo ""
echo "Make sure to read the README for piplay.py basic configs"
#Explain file location in case of modifications / Do NOT run this again.
echo "Further modification can be made to /opt/piplay/piplay.py and then run sudo systemctl restart piplay"
#Explain to start service
echo "If you are good to go, run sudo systemctl start piplay"
sleep 5

