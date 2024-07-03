# PiPlay: Display Replacement for RTSP Camera Streams

## Disclaimers

- **Compatibility**: This tool is designed as a replacement for `displaycams` and `omxplayer` on Raspberry Pi 4 and later running Bookworm Lite. It may not function properly if you have a desktop GUI, as it pipes output to the framebuffer.
- **Performance on Pi 3**: While it has been tested on a Raspberry Pi 3B with multiple streams, it is recommended only for viewing one or two streams. It performs smoothly with several streams on a Pi 4.
- **Camera Compatibility**: Initially designed for OpenCV, it has been modified to support Wyze cams and works with other cameras tested so far (e.g., Hik, Geo, Unifi, Wyze via Bridge Docker).
- **Development**: This project was a joint effort between myself and AI. It has been refined multiple times to run efficiently in my use cases. While it may have areas for improvement and limitations, it serves as a good starting point for those who need it.
- **Resolution**: The tool downsamples RTSP frames to 640x480 before rendering in PyQt. This provides better performance than direct downsampling to arbitrary panel sizes.
- **Requirements**: The exact apt requirements will be tested on a fresh image soon and updated accordingly.

## Installation

1. **Modify `piplay.py`**: 
   - This tool is not built for custom screen setups or multiple screens.
   - Ensure you have the correct number of cameras for your grid. For example, a 2x2 grid requires 4 cameras.
   - **Rotation**: Adjusts the output to the framebuffer to avoid screen rotation issues on the Pi.
   - **FPS**: Lowering this value skips more incoming frames, reducing CPU load.
   - **Grid Setup**: Set up the grid using the `row` and `column` variables. For instance, 2 rows and 3 columns will be arranged as such in 0 or 180-degree rotation. In 90 or 270-degree rotation, it will be a 3x2 grid. The stream order will fill the grid based on a 0-degree rotation.

2. **Run the Installer**:
   - Once `piplay.py` is modified to your requirements, run the following commands:
     ```sh
     sudo chmod +x ./install.sh
     sudo ./install.sh
     ```
   - This will download the necessary Python packages, move `piplay.py` and `startup.sh` to `/opt/piplay`, and enable the `piplay.service` file. Start the service with:
     ```sh
     sudo systemctl start piplay
     ```
   - **Note**: If you download `piplay.py` directly and install manually, ensure to pull the framebuffer exports from `startup.sh`.

## Contributions and Maintenance

- I do not have a plan to actively maintain this project but I am open to recommended changes. Feel free to fork and modify it as needed.
- This project was created to replace `displaycams` and enable running up-to-date OSes on newer Raspberry Pis. After extensive searches, I found no other developed tools that worked, so I am sharing this solution.
