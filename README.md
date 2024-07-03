# PiPlay: PI Display for RTSP Camera Streams on Bookworm lite!

## Disclaimers

- **Screen Output**: If you do not have a screen powered on at service launch time, the service WILL fail!  Eglfs detects the screen capabilities at launch in order to maximize the PyQT6 space usage.
- **Compatibility**: This was designed for Raspberry Pi 4 and later running Bookworm Lite. It may not function properly if you have a desktop GUI, as it pipes output to the framebuffer.
- **Performance on Pi 3**: I don't recommend more than a couple streams on a PI 3. It performs smoothly with several streams on a Pi 4.  Pi 5 should work well (Will test.)
- **Camera Compatibility**: It works with the handful of cameras tested so far (e.g., Hik, Geo, Unifi, Wyze via Bridge Docker). Tested with H265!!
- **Resolution**: The tool downsamples RTSP frames to 640x480 before rendering in PyQt. This provides better performance than direct downsampling to arbitrary panel sizes.
- **Requirements**: The apt packages from the install script have been mostly validated and will be tweaked as I find redundancies.
- **Wyze Bridge**: If you run the Docker bridge for Wyze, rtsp streams are oddly encoded.  I had to use the m3u8 stream to make them read properly.

## Donations

If you like this and feel extra thankful, https://paypal.me/HussX1

## Installation

1. **Clone**:
   - Install git from apt and clone this:
     ```sh
     sudo apt-get install git
     git clone https://github.com/HussX/piplay.git
     cd piplay
     ```

2. **Modify `config.yaml`**: 
   - This tool is not built for custom screen locations or multiple screens. Just a generic grid.
   - Ensure you have the correct number of cameras for your grid. For example, a 2x2 grid for 3-4 cameras.
   - **Rotation**: Adjusts the output to the framebuffer to avoid screen rotation issues on the Pi.
   - **FPS**: Lowering this value skips more incoming frames, reducing CPU load.
   - **Grid Setup**: Set up the grid using the `row` and `column` variables. For instance, 2 rows and 3 columns will be arranged as such in 0 or 180-degree rotation. In 90 or 270-degree rotation, it will be a 3x2 grid. The stream order will fill the grid based on a 0-degree rotation.

3. **Run the Installer**:
   - Once `config.yaml` is modified to your requirements, run the following commands:
     ```sh
     sudo chmod +x ./install.sh
     sudo ./install.sh
     ```
   - This will download the necessary Python packages, move `piplay.py`, `startup.sh`, and `config.yaml` to `/opt/piplay`, and enable the `piplay.service` file. 

4. **Start the service**:
   - Run:
     ```sh
     sudo systemctl start piplay
     ```
   - If you need to troubleshoot, check `sudo systemctl status piplay` and/or `journalctl -f`.  Program logfiles are stored at `/var/log/piplay.log`.
   - **Note**: If you download `piplay.py` directly and install manually, ensure to pull the framebuffer exports from `startup.sh` along with the `config.yaml`.

## Contributions and Maintenance

- I do not have a plan to actively maintain this project unless I run across active needs, but I am open to recommended changes. Feel free to fork and modify it as needed.
- This project was created to replace my use of `displaycams` and enable running up-to-date OSes on newer Raspberry Pis. After extensive searches, I found no other developed tools that worked well, so I am sharing this solution. Developed as a joint effort between myself and some AI assistance.
