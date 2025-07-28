import mpv
import yaml
import logging
import sys
import signal
import time
from flask import Flask, jsonify, request, make_response
from functools import wraps
from threading import Thread
import subprocess

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

    # Read webhook creds
    webhook_config = config.get('webhook', {})
    WEBHOOK_USER = webhook_config.get('username')
    WEBHOOK_PASS = webhook_config.get('password')
    AUTH_ENABLED = bool(WEBHOOK_USER)
    
    if AUTH_ENABLED:
        logging.info("Webhook authentication is ENABLED.")
    else:
        logging.info("Webhook authentication is DISABLED. Set a username in config.yaml to enable it.")
except KeyError as e:
    logging.warning(f"Missing key in config.yaml: {e}")
    sys.exit(1)

# --- Webhook Server Setup ---
app = Flask(__name__)

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_ENABLED:
            return f(*args, **kwargs)
        auth = request.authorization
        if auth and auth.username == WEBHOOK_USER and auth.password == WEBHOOK_PASS:
            # If credentials match, proceed with the original function
            return f(*args, **kwargs)
        
        # If credentials fail or are missing, send a 401 Unauthorized response
        return make_response(
            'Could not verify your login!', 401, 
            {'WWW-Authenticate': 'Basic realm="Login Required"'}
        )
    return decorated

@app.route('/on', methods=['GET', 'POST'])
@auth_required
def screen_on():
    """Endpoint to turn the screen on via DPMS."""
    for player_wrapper in MPV_INSTANCES_INFO:
        try:
            # Check if the player instance actually exists
            if player_wrapper.player:
                player_wrapper.player.vo = 'gpu'
        except Exception as e:
            logging.error(f"Failed to set VO for {player_wrapper.title}: {e}")
    logging.info("Moved streams back to GPU for screen on.")
    time.sleep(1)
    subprocess.run(['xset', 'dpms', 'force', 'on'])
    subprocess.run(['xset', 's', 'off', 's', 'noblank', '-dpms'])
    return jsonify(status="success", command='Screen On'), 200

@app.route('/off', methods=['GET', 'POST'])
@auth_required
def screen_off():
    """Endpoint to turn the screen off via DPMS."""
    for player_wrapper in MPV_INSTANCES_INFO:
        try:
            # Check if the player instance actually exists
            if player_wrapper.player:
                player_wrapper.player.vo = 'null'
        except Exception as e:
            logging.error(f"Failed to set VO for {player_wrapper.title}: {e}")
    logging.info("Moved streams to null output for screen off.")
    time.sleep(0.5)
    subprocess.run(['xset', 's', 'activate', '+dpms'])
    subprocess.run(['xset', 'dpms', 'force', 'off'])
    return jsonify(status="success", command='Screen Off'), 200

@app.route('/restart', methods=['GET', 'POST'])
@auth_required
def screen_restart():
    """Restart piplay service."""
    subprocess.run(['systemctl', 'restart', 'piplay'])
    return jsonify(status="success", command='restart'), 200

@app.route('/', methods=['GET'])
def index():
    """Root endpoint to check if the server is running."""
    return jsonify(status="ok", message="PiPlay webhook server is running. Use /on, /off, /restart accordingly."), 200

def run_webhook_server():
    """Runs the Flask app using the Waitress production server."""
    logging.info("Starting webhook server on http://0.0.0.0:80")
    from waitress import serve
    serve(app, host='0.0.0.0', port=80)
# --- End Webhook Server Setup ---

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
        self.retry_count = 0
        self.is_playing = False

    def start(self):
        """Terminates any old instance and starts a new one."""
        global RUNNING
        if not RUNNING or not self.should_be_running:
            return

        # Always terminate existing player for a clean restart
        if self.player:
            logging.info(f"[{self.title}] Terminating previous player instance before new attempt.")
            try: 
                self.player.quit()
                time.sleep(0.2)
                if hasattr(self.player, 'terminate') and getattr(self.player, '_handle', None):
                    self.player.terminate()
            except Exception as e:
                logging.error(f"[{self.title}] Error during player termination: {e}", exc_info=False)
            finally:
                self.player = None
                time.sleep(0.1)

        logging.info(f"[{self.title}] Attempting to start stream: {self.url}")
        self.last_attempt_time = time.time()
        self.is_playing = False

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
                demuxer_lavf_o='reconnect=1,reconnect_streamed=1,reconnect_delay_max=5',
                stop_screensaver='no',
                profile='low-latency',
                untimed='yes'
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
        
        is_currently_active = False
        try:
            # A stream is active if the player exists, is not idle, and hasn't aborted.
            if self.player and not self.player.idle_active and getattr(self.player, 'playback_abort_reason', 'no').lower() == 'no':
                is_currently_active = True
        except Exception as e:
            # Any error polling means the player is dead/unresponsive.
            logging.warning(f"[{self.title}] Error polling player: {e}. Assuming dead.")
            self.player = None
            is_currently_active = False

        if is_currently_active:
            if not self.is_playing:
                logging.info(f"[{self.title}] Status: Playback has started/resumed.")
                self.is_playing = True
            # If it's playing, reset the retry counter.
            self.retry_count = 0
            self.last_attempt_time = time.time()
        else:
            # Stream is not active.
            if self.is_playing:
                logging.warning(f"[{self.title}] Status: Playback stopped or failed.")
                self.is_playing = False # Update our state view
                self.last_attempt_time = time.time() # Start the timer for the first retry

            # --- Exponential Backoff Logic ---
            # Calculate how long to wait before the next attempt
            backoff_delay = min(5 * (2 ** self.retry_count), 60) 
            current_time = time.time()

            if current_time - self.last_attempt_time >= backoff_delay:
                logging.warning(f"[{self.title}] Reconnect interval passed ({backoff_delay}s). Restarting...")
                self.retry_count += 1
                self.start()

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

    webhook_thread = Thread(target=run_webhook_server, daemon=True)
    webhook_thread.start()

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
                player_wrapper = MpvPlayerWrapper(i, stream_config_item) # Pass index and config item
                MPV_INSTANCES_INFO.append(player_wrapper)
                player_wrapper.start()
            except ValueError as e:
                logging.error(f"Skipping stream at index {i} due to configuration error: {e}")
            except Exception as e:
                logging.error(f"Failed to prepare MpvPlayerWrapper for index {i}: {e}", exc_info=True)
        else:
            logging.info(f"Grid cell for index {i} has no stream assigned in config (Grid: {GRID_ROWS}x{GRID_COLS}).")

    try:
        subprocess.run(['xset', 'dpms', 'force', 'on'])
        subprocess.run(['xset', 's', 'off', 's', 'noblank', '-dpms'])
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
