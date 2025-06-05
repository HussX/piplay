import mpv
import yaml
import logging
import sys
import signal
import time

# Configure logging
logging.basicConfig(filename='/var/log/piplay.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
try:
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
except FileNotFoundError:
    logging.warning(f"Error: 'config.yaml' not found.")
    sys.exit(1)
except yaml.YAMLError as e:
    logging.warning(f"Error parsing 'config.yaml': {e}")
    sys.exit(1)

# Read settings from the config file
try:
    ROTATION_ANGLE = config['settings']['rotation_angle']
    GRID_ROWS = config['settings']['grid_rows']
    GRID_COLS = config['settings']['grid_cols']

    # Read streams from the config file
    STREAMS = config['streams']
except KeyError as e:
    logging.warning(f"Missing key in config.yaml: {e}")
    sys.exit(1)


# --- Global State ---
MPV_INSTANCES_INFO = []
RUNNING = True
# --- End Global State ---

def calculate_geometry_string_percentage(stream_index):
    """Calculates mpv geometry string (W%xH%+X%+Y%) using percentages, using global GRID_ROWS/COLS."""
    if GRID_COLS <= 0 or GRID_ROWS <= 0:
        logging.warning("Grid rows or columns is zero or less. Defaulting to fullscreen for first stream.")
        return "100%x100%+0%+0%" if stream_index == 0 else "0%x0%+0%+0%"

    cell_w_exact = 100.0 / GRID_COLS
    cell_h_exact = 100.0 / GRID_ROWS

    row_idx = stream_index // GRID_COLS
    col_idx = stream_index % GRID_COLS

    x_perc = ((100 / (GRID_COLS - 1)) * col_idx) if GRID_COLS > 1 else 0
    y_perc = ((100 / (GRID_ROWS - 1)) * row_idx) if GRID_ROWS > 1 else 0
    
    w_perc = cell_w_exact
        
    h_perc = cell_h_exact

    # mpv expects integer percentages for its geometry string as per user feedback
    return f"{int(w_perc)}%x{int(h_perc)}%+{int(x_perc)}%+{int(y_perc)}%"

class MpvPlayerWrapper:
    def __init__(self, index, stream_url):
        self.index = index
        self.url = stream_url
        self.title = f"MPV_Stream_{index}"
        self.geometry_str = calculate_geometry_string_percentage(self.index)
        
        self.player = None
        self.last_attempt_time = 0
        self.should_be_running = True # Set to False on shutdown

    def start(self):
        """Terminates any old instance and starts a new one. This is the only
           place where a new player instance is created."""
        global RUNNING
        if not RUNNING or not self.should_be_running:
            return

        # Always terminate existing player for a clean restart
        if self.player:
            logging.info(f"[{self.title}] Terminating previous player instance before new attempt.")
            try: self.player.terminate()
            except: pass
            self.player = None
            time.sleep(0.1) # Small pause for resources to free

        logging.info(f"[{self.title}] Attempting to start stream: {self.url}")
        self.last_attempt_time = time.time()

        try:
            self.player = mpv.MPV(
                vo='gpu',
                hwdec='no',
                audio=False,
                geometry=self.geometry_str,
                border=False,
                window_dragging='no',
                osc=False,
                input_default_bindings=False,
                video_rotate=ROTATION_ANGLE,
                keepaspect='no',
                title=self.title,
            )
            
            self.player.play(self.url)
            logging.info(f"[{self.title}] Play command issued.")
        except Exception as e:
            logging.error(f"[{self.title}] Error during MPV instance creation: {e}", exc_info=True)
            self.player = None

    def check_and_reconnect_if_needed(self):
        """The core polling logic. Checks status and restarts if necessary."""
        global RUNNING
        if not RUNNING or not self.should_be_running:
            if self.player: self.stop()
            return
        
        status = 'STOPPED_OR_FAILED' # Default assumption
        try:
            if self.player:
                # Check for definitive failure first
                aborted = getattr(self.player, 'playback_abort_reason', None)
                if aborted and str(aborted).lower() != 'no':
                    status = 'STOPPED_OR_FAILED'
                    logging.warning(f"[{self.title}] Playback aborted: {aborted}.")
                # Check for seeking/connecting state
                elif getattr(self.player, 'seeking', False):
                    status = 'CONNECTING'
                # Check for idle state
                elif self.player.idle_active:
                    status = 'STOPPED_OR_FAILED'
                # If not idle, not aborted, assume it's playing
                elif not self.player.idle_active and (self.player.filename or self.player.path):
                    status = 'PLAYING'

        except (AttributeError, Exception) as e:
            # Any error accessing properties means the player is dead/unresponsive
            status = 'STOPPED_OR_FAILED'
            if self.player is not None:
                 logging.warning(f"[{self.title}] Error polling player: {e}. Assuming dead.")
                 self.player = None # Ensure it's cleared for next restart attempt

        # --- Take Action Based on Polled Status ---
        if status == 'PLAYING':
            # logging.debug(f"[{self.title}] Status: Playing.") # Can be noisy, use debug
            self.last_attempt_time = time.time() # Update time to prevent immediate restart if it briefly drops
        elif status == 'CONNECTING':
            logging.info(f"[{self.title}] Status: Connecting/Seeking...")
            self.last_attempt_time = time.time() # Also update time while connecting
        elif status == 'STOPPED_OR_FAILED':
            # If it's stopped, check if enough time has passed to retry
            current_time = time.time()
            if current_time - self.last_attempt_time >= 5:
                logging.warning(f"[{self.title}] Status: Stopped/Failed. Reconnect interval passed. Restarting...")
                self.start() # Attempt a restart

    def stop(self):
        self.should_be_running = False # Prevent monitor from restarting
        if self.player:
            logging.info(f"[{self.title}] Stopping player instance.")
            try:
                self.player.quit()
                time.sleep(0.2)
                if hasattr(self.player, 'terminate') and getattr(self.player, '_handle', None):
                    self.player.terminate()
            except: pass
            finally: self.player = None

def main():
    global MPV_INSTANCES_INFO, RUNNING

    def shutdown_signal_handler(sig, frame):
        global RUNNING
        if not RUNNING: return
        logging.info(f"Signal {signal.strsignal(sig) if hasattr(signal, 'strsignal') else sig} received. Initiating shutdown...")
        RUNNING = False

    signal.signal(signal.SIGINT, shutdown_signal_handler)
    signal.signal(signal.SIGTERM, shutdown_signal_handler)

    # Initialize players
    num_grid_cells = GRID_ROWS * GRID_COLS
    for i in range(num_grid_cells):
        if i < len(STREAMS):
            stream_config_item = STREAMS[i]
            try:
                player_wrapper = MpvPlayerWrapper(i, stream_config_item) # Pass inde1x and config item
                MPV_INSTANCES_INFO.append(player_wrapper)
                player_wrapper.start()
            except ValueError as e:
                logging.error(f"Skipping stream at index {i} due to configuration error: {e}")
            except Exception as e:
                logging.error(f"Failed to prepare MpvPlayerWrapper for index {i}: {e}", exc_info=True)
        else:
            logging.info(f"Grid cell for index {i} has no stream assigned in config (Grid: {GRID_ROWS}x{GRID_COLS}).")

    try:
        while RUNNING:
            for player_wrapper in MPV_INSTANCES_INFO:
                if not RUNNING: break
                player_wrapper.check_and_reconnect_if_needed()
            if not RUNNING: break
            time.sleep(2) # Monitoring interval (seconds)
    except Exception as e:
        logging.error(f"Unhandled exception in main orchestrator loop: {e}", exc_info=True)
    finally:
        logging.info("Orchestrator main loop ended. Shutting down players...")
        RUNNING = False 
        for player_wrapper in MPV_INSTANCES_INFO:
            player_wrapper.stop()
        logging.info("All MPV players signaled to stop. Orchestrator exited.")

if __name__ == "__main__":
    main()
