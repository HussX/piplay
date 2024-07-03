# PiPlay: Display Replacement for RTSP Camera Streams

## Disclaimers

- **Screen Output**: If you do not have a screen powered on at service launch time, the service WILL fail!  Eglfs detects the screen capabilities at launch in order to maximize the PyQT6 space usage.
- **Compatibility**: This tool is designed as a replacement for `displaycams` and `omxplayer` on Raspberry Pi 4 and later running Bookworm Lite. It may not function properly if you have a desktop GUI, as it pipes output to the framebuffer.
- **Performance on Pi 3**: While it has been tested on a Raspberry Pi 3B with multiple streams, it is recommended only for viewing one or two streams. It performs smoothly with several streams on a Pi 4.
- **Camera Compatibility**: Initially designed for OpenCV, it has been modified to support Wyze cams and works with other cameras tested so far (e.g., Hik, Geo, Unifi, Wyze via Bridge Docker). Tested with H265!!
- **Development**: This project was a joint effort between myself and AI. It has been refined multiple times to run efficiently in my use cases. While it may have areas for improvement and limitations, it serves as a good starting point for those who need it.
- **Resolution**: The tool downsamples RTSP frames to 640x480 before rendering in PyQt. This provides better performance than direct downsampling to arbitrary panel sizes.
- **Requirements**: The apt packages from the install script have been mostly validated and will be tweaked as I find redundancies.

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
   - If you need to troubleshoot, check `sudo systemctl status piplay` and/or `journalctl -f`.
   - **Note**: If you download `piplay.py` directly and install manually, ensure to pull the framebuffer exports from `startup.sh` along with the `config.yaml`.

## Contributions and Maintenance

- I do not have a plan to actively maintain this project unless I run across active needs, but I am open to recommended changes. Feel free to fork and modify it as needed.
- This project was created to replace `displaycams` and enable running up-to-date OSes on newer Raspberry Pis. After extensive searches, I found no other developed tools that worked well, so I am sharing this solution.
