#!/usr/bin/env bash

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo"
    exit 1
fi

echo "This installation requires several packages from apt."
echo "The following packages will be installed:"
echo "  - python3-opencv"
echo "  - python3-pyqt6"
echo "  - gstreamer1.0-plugins-good"
echo "  - gstreamer1.0-plugins-bad"
echo "  - gstreamer1.0-plugins-ugly"
echo "  - python3-yaml"
echo ""
echo "Please be patient as there are a lot of involved dependencies!"
echo ""

# Prompt for confirmation to proceed
while true; do
    read -p "Proceed with installation? (y/n): " yn
    case $yn in
        [yY] ) break;;
        [nN] ) echo "Exiting"; exit 0;;
        * ) echo "Invalid response";;
    esac
done

# Update package lists and install required packages
apt-get update
apt-get install -y python3-opencv python3-pyqt6 gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly python3-yaml
echo ""

# Prompt to check if the user has configured piplay.py
while true; do
    read -p "Have you already configured config.yaml? It can be configured later in /opt/piplay. (y/n): " config
    case $config in
        [yY] ) break;;
        [nN] ) echo "Exiting"; exit 0;;
        * ) echo "Invalid response";;
    esac
done

# Move files to /opt/piplay and set permissions
mkdir -p /opt/piplay
mv ./piplay.py /opt/piplay/
mv ./startup.sh /opt/piplay/
mv ./config.yaml /opt/piplay/
chmod +x /opt/piplay/startup.sh

#Set up log rotation
mv ./piplay /etc/logrotate.d/

# Move the service file to /etc/systemd/system/ and enable it
mv ./piplay.service /etc/systemd/system/

echo "Reloading systemctl daemon"
systemctl daemon-reload
sleep 1

echo "Enabling piplay service"
systemctl enable piplay
echo ""

# Provide final instructions to the user
echo "Make sure to read the README for config.yaml basic configurations."
echo "Further modifications can be made to /opt/piplay/config.yaml and then run 'sudo systemctl restart piplay'."
echo "If you are ready to start the service, run 'sudo systemctl start piplay'."
echo "If you need to troubleshoot after starting, please check 'sudo systemctl status piplay' and/or 'journalctl -f'"
sleep 3
