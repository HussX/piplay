# PiPlay: PI Display for RTSP Camera Streams on Bookworm lite!

## Updates

- **Backend**: This is a rework using X and mpv instead of directly decoding every frame. The overhead is the same or better and it leans into existing distro packages.
- **Webhooks**: By request, I added some webhooks that could be useable in HA for basic functionality. http://screenIPaddress/on or /off or /restart
    - off turns off your display
    - on turns back on the display
    - restart issues a systemctl restart

## Disclaimers

- **Compatibility**: This was designed for Raspberry Pi 4 and later running Bookworm Lite. It may not function properly if you have a desktop GUI, or it may... it installs and runs on X as Wayland doesn't allow specific screen placement yet.
- **Performance on Pi 3**: This runs well on a 4.  Needs tested more in depth.
- **Camera Compatibility**: This needs tested in depth. I tested this so far with HV and Unifi. I'm sure the support with mpv is fairly broad.

## Donations

If you like this and feel extra thankful, https://paypal.me/HussX1

## Installation

1. **Clone**:
   - Install git from apt and clone this:
     ```sh
     sudo apt-get install git
     git clone -b mpv https://github.com/HussX/piplay.git
     cd piplay
     ```

2. **Modify `config.yaml`**: 
   - This tool is not built for custom screen locations or multiple screens. Just a generic grid.
   - Ensure you have the correct number of cameras for your grid. For example, a 2x2 grid for 3-4 cameras.
   - **Rotation**: Adjusts the output to the framebuffer to avoid screen rotation issues on the Pi.
   - **FPS**: Not applicable with MPV - left in for backwards compatibility.
   - **Grid Setup**: Set up the grid using the `row` and `column` variables. For instance, 2 rows and 3 columns will be arranged as such in 0 or 180-degree rotation. In 90 or 270-degree rotation, it will be a 3x2 grid. The stream order will fill the grid based on a 0-degree rotation.
   - **Webhook**: Enter a user and password with single quotes to set basic http auth for the webhooks.  To bypass auth, leave only the blank single quotes!
   - **Streams**: Enter the full URL you'd use to access the stream with any other client, inclusive of user/pass if necessary.

3. **Run the Installer**:
   - Once `config.yaml` is modified to your requirements, run the following commands:
     ```sh
     sudo chmod +x ./install.sh
     sudo ./install.sh
     ```
   - This will download the necessary Python packages, move `piplayMPV.py`, `startup.sh`, and `config.yaml` to `/opt/piplay`, and enable the `piplay.service` file. 

4. **Start the service**:
   - Run:
     ```sh
     sudo systemctl start piplay
     ```
   - If you need to troubleshoot, check `sudo systemctl status piplay` and/or `journalctl -f`.  Program logfiles are stored at `/var/log/piplay.log`.

## Contributions and Maintenance

- I do not have a plan to actively maintain this project unless I run across active needs, but I am open to recommended changes. Feel free to fork and modify it as needed.
- This project was created to replace my use of `displaycams` and enable running up-to-date OSes on newer Raspberry Pis. After extensive searches, I found no other developed tools that worked well, so I am sharing this solution. Developed as a joint effort between myself and some AI assistance.
