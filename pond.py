"""
Main Pond Application for Fish Haven Project
GUI-based pond with fish spawning, animation, and migration
"""

import base64
import threading
import time
import tkinter as tk
from datetime import datetime
from io import BytesIO
from tkinter import messagebox, scrolledtext, ttk

from PIL import Image, ImageTk
from prometheus_client import Counter, Gauge, start_http_server

import config
from fish import Fish
from mqtt_handler import MQTTHandler

# Import commonly used values for convenience
POND_WIDTH = config.POND_WIDTH
POND_HEIGHT = config.POND_HEIGHT
POND_COLOR = config.POND_COLOR


# Prometheus Metrics
ACTIVE_FISH_GAUGE = Gauge(
    "fishhaven_active_fishes", "Current number of fishes in the pond"
)
SPAWN_COUNTER = Counter("fishhaven_spawned_total", "Total fishes spawned locally")
MIGRATE_OUT_COUNTER = Counter(
    "fishhaven_migrated_out_total", "Total fishes sent to stream"
)
MIGRATE_IN_COUNTER = Counter(
    "fishhaven_migrated_in_total", "Total fishes received from stream"
)
DEATH_COUNTER = Counter("fishhaven_deaths_total", "Total fishes died of old age")
REJECTED_FISH_COUNTER = Counter(
    "fishhaven_rejected_fish_total", "Total fishes rejected due to pond at capacity"
)
MQTT_RECONNECT_COUNTER = Counter(
    "fishhaven_mqtt_reconnects_total", "Total MQTT reconnection attempts"
)
MQTT_CONNECTED_GAUGE = Gauge(
    "fishhaven_mqtt_connected", "MQTT connection status (1=connected, 0=disconnected)"
)


class PondGUI:
    def __init__(self, root):
        """Initialize the Pond GUI"""
        self.root = root
        self.root.title(f"Fish Haven - {config.POND_NAME}")
        self.root.geometry("1200x800")

        # Data
        self.fishes = []  # List of Fish objects
        self.mqtt_handler = None
        self.running = False
        self.spawn_timer = 0
        self.message_log = []

        # Statistics
        self.stats = {"spawned": 0, "received": 0, "sent": 0, "died": 0}

        # Create UI
        self._create_ui()

        # Initialize MQTT
        self._init_mqtt()

        # Start Prometheus metrics server on port 8000
        start_http_server(8000)
        self.log_message("Prometheus metrics server started on port 8000", "SYSTEM")

    def _create_ui(self):
        """Create the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Top section - Info and Controls
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 5))

        # Pond info
        info_frame = ttk.LabelFrame(top_frame, text="Pond Information", padding=10)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        ttk.Label(
            info_frame,
            text=f"Pond Name: {config.POND_NAME}",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=f"Group: {config.GROUP_NAME}").grid(
            row=1, column=0, sticky=tk.W
        )

        self.connection_label = ttk.Label(
            info_frame, text="Status: Not Connected", foreground="red"
        )
        self.connection_label.grid(row=2, column=0, sticky=tk.W)

        self.fish_count_label = ttk.Label(info_frame, text="Fish Count: 0")
        self.fish_count_label.grid(row=3, column=0, sticky=tk.W)

        # Statistics
        stats_frame = ttk.LabelFrame(top_frame, text="Statistics", padding=10)
        stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))

        self.stats_labels = {}
        for i, (key, value) in enumerate(self.stats.items()):
            label = ttk.Label(stats_frame, text=f"{key.capitalize()}: {value}")
            label.grid(row=i, column=0, sticky=tk.W)
            self.stats_labels[key] = label

        # Controls
        control_frame = ttk.LabelFrame(top_frame, text="Controls", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        self.start_button = ttk.Button(
            control_frame, text="Start Pond", command=self.start_pond
        )
        self.start_button.grid(row=0, column=0, padx=2, pady=2)

        ttk.Button(
            control_frame, text="Spawn Fish", command=self.spawn_fish_manual
        ).grid(row=0, column=1, padx=2, pady=2)

        ttk.Button(control_frame, text="Send Hello", command=self.send_hello).grid(
            row=1, column=0, padx=2, pady=2
        )

        ttk.Button(
            control_frame, text="Announce Pond", command=self.announce_pond
        ).grid(row=1, column=1, padx=2, pady=2)

        # Middle section - Pond Canvas and Messages
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True)

        # Pond canvas
        canvas_frame = ttk.LabelFrame(middle_frame, text="Pond", padding=5)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.canvas = tk.Canvas(
            canvas_frame,
            width=POND_WIDTH,
            height=POND_HEIGHT,
            bg=POND_COLOR,
            highlightthickness=1,
        )
        self.canvas.pack()

        # Message log
        log_frame = ttk.LabelFrame(middle_frame, text="Message Log", padding=5)
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        self.message_text = scrolledtext.ScrolledText(
            log_frame, width=40, height=30, wrap=tk.WORD, state=tk.DISABLED
        )
        self.message_text.pack(fill=tk.BOTH, expand=True)

        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).pack(pady=5)

    def _init_mqtt(self):
        """Initialize MQTT connection"""
        self.mqtt_handler = MQTTHandler(pond_callback=self.handle_mqtt_message)

        # Try to connect
        if self.mqtt_handler.connect():
            self.root.after(1000, self._check_mqtt_connection)
        else:
            self.log_message("Failed to connect to MQTT broker", "ERROR")

    def _check_mqtt_connection(self):
        """Check and update MQTT connection status"""
        if self.mqtt_handler and self.mqtt_handler.connected:
            self.connection_label.config(text="Status: Connected ✓", foreground="green")
            MQTT_CONNECTED_GAUGE.set(1)
        else:
            self.connection_label.config(
                text="Status: Disconnected ✗", foreground="red"
            )
            MQTT_CONNECTED_GAUGE.set(0)

        # Check again in 2 seconds
        self.root.after(2000, self._check_mqtt_connection)

    def handle_mqtt_message(self, message_data):
        """Handle incoming MQTT messages"""
        topic = message_data["topic"]
        data = message_data["data"]

        # Log message
        self.log_message(f"From {topic}: {message_data['payload'][:80]}...")

        # Handle fish data directly from stream
        if "id" in data and "name" in data and "genesis" in data:
            # This is a fish - receive it
            from_pond = data.get("genesis", "Unknown")
            self.receive_fish(data, from_pond)

        # Handle other message types (if any)
        elif "raw" in data:
            # Plain text message
            self.log_message(f"  → {data['message']}", "INFO")

    def log_message(self, message, level="INFO"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"

        self.message_text.config(state=tk.NORMAL)
        self.message_text.insert(tk.END, log_entry)
        self.message_text.see(tk.END)
        self.message_text.config(state=tk.DISABLED)

        self.message_log.append(log_entry)

    def clear_log(self):
        """Clear message log"""
        self.message_text.config(state=tk.NORMAL)
        self.message_text.delete(1.0, tk.END)
        self.message_text.config(state=tk.DISABLED)
        self.message_log = []

    def start_pond(self):
        """Start the pond simulation"""
        if not self.running:
            self.running = True
            self.start_button.config(text="Stop Pond", command=self.stop_pond)
            self.log_message("Pond started!", "SYSTEM")
            threading.Thread(target=self.pond_loop, daemon=True).start()

    def stop_pond(self):
        """Stop the pond simulation"""
        self.running = False
        self.start_button.config(text="Start Pond", command=self.start_pond)
        self.log_message("Pond stopped", "SYSTEM")

    def pond_loop(self):
        """Main pond simulation loop"""
        while self.running:
            # Update spawn timer
            self.spawn_timer += 1

            # Auto-spawn fish (max 10 fish limit)
            if (
                self.spawn_timer >= config.FISH_SPAWN_INTERVAL * 10
            ):  # *10 for 0.1s ticks
                if len(self.fishes) < 10:  # Limit to 10 fish
                    self.spawn_fish()
                self.spawn_timer = 0

            # Update all fish
            fishes_to_remove = []
            for fish in self.fishes[:]:
                # Update lifetime
                if not fish.update_lifetime():
                    fishes_to_remove.append(fish)
                    self.stats["died"] += 1
                    self.log_message(
                        f"Fish '{fish.name}' died (lifetime expired)", "FISH"
                    )
                    continue

                # Update position
                fish.update_position(POND_WIDTH, POND_HEIGHT)

                # Update animation
                fish.update_animation()

                # Check migration
                pond_crowded = len(self.fishes) > config.MIGRATION_THRESHOLD
                if fish.should_migrate(pond_crowded):
                    self.migrate_fish(fish)
                    fishes_to_remove.append(fish)

            # Remove dead or migrated fish
            for fish in fishes_to_remove:
                if fish in self.fishes:
                    self.fishes.remove(fish)

            # Update UI
            self.root.after(0, self.update_canvas)
            self.root.after(0, self.update_stats)

            time.sleep(0.1)  # 10 FPS

    def spawn_fish(self):
        """Spawn a new fish"""
        fish = Fish()
        self.fishes.append(fish)
        self.stats["spawned"] += 1
        self.log_message(f"Spawned new fish: {fish.name}", "FISH")
        SPAWN_COUNTER.inc()  # Increment Prometheus counter
        ACTIVE_FISH_GAUGE.inc()  # Update Prometheus gauge
        ACTIVE_FISH_GAUGE.set(len(self.fishes))  # Set gauge to current fish count

    def spawn_fish_manual(self):
        """Manually spawn a fish"""
        if len(self.fishes) < 10:
            self.spawn_fish()
        else:
            self.log_message("Cannot spawn fish: Maximum limit (10) reached", "WARNING")
            REJECTED_FISH_COUNTER.inc()

    def receive_fish(self, fish_data, from_pond):
        """Receive a fish from another pond"""
        try:
            # Don't receive our own fish
            my_fish_id_prefix = config.POND_NAME + "_"
            if fish_data.get("id", "").startswith(my_fish_id_prefix):
                return  # Skip our own fish

            # Check if pond is at maximum capacity
            if len(self.fishes) >= 10:
                self.log_message(
                    "Cannot receive fish: Maximum limit (10) reached", "WARNING"
                )
                REJECTED_FISH_COUNTER.inc()
                return

            fish = Fish.from_dict(fish_data)
            fish.last_update = time.time()  # Reset update timer
            self.fishes.append(fish)
            self.stats["received"] += 1
            self.log_message(f"Received fish '{fish.name}' from {from_pond}", "FISH")
            MIGRATE_IN_COUNTER.inc()  # Increment Prometheus counter
            ACTIVE_FISH_GAUGE.set(len(self.fishes))  # Update Prometheus gauge
            ACTIVE_FISH_GAUGE.inc()  # Increment for received fish
        except Exception as e:
            self.log_message(f"Error receiving fish: {e}", "ERROR")

    def migrate_fish(self, fish):
        """Migrate fish to another pond"""
        if self.mqtt_handler and self.mqtt_handler.connected:
            # Send to random pond (in real system, you'd have a list of active ponds)
            self.mqtt_handler.send_fish(fish, target_pond=None)
            self.stats["sent"] += 1
            self.log_message(f"Migrated fish '{fish.name}'", "FISH")
            ACTIVE_FISH_GAUGE.set(len(self.fishes))  # Update Prometheus gauge
            ACTIVE_FISH_GAUGE.dec()  # Decrement for migrated fish
            MIGRATE_OUT_COUNTER.inc()  # Increment migration out counter

    def send_hello(self):
        """Send hello message"""
        if self.mqtt_handler and self.mqtt_handler.connected:
            self.mqtt_handler.send_hello()
        else:
            self.log_message("Not connected to MQTT broker", "ERROR")

    def announce_pond(self):
        """Announce pond to vivisystem"""
        if self.mqtt_handler and self.mqtt_handler.connected:
            self.mqtt_handler.announce_pond()
        else:
            self.log_message("Not connected to MQTT broker", "ERROR")

    def update_canvas(self):
        """Update the pond canvas"""
        self.canvas.delete("all")

        # Draw fish
        for fish in self.fishes:
            self.draw_fish(fish)

        # Update fish count
        self.fish_count_label.config(text=f"Fish Count: {len(self.fishes)}")

    def draw_fish(self, fish):
        """Draw a fish on the canvas"""
        try:
            # Get current posture
            posture_b64 = fish.postures[fish.current_posture]

            # Decode base64 image
            img_data = base64.b64decode(posture_b64)
            img = Image.open(BytesIO(img_data))
            photo = ImageTk.PhotoImage(img)

            # Keep reference to prevent garbage collection
            if not hasattr(self, "image_refs"):
                self.image_refs = []
            self.image_refs.append(photo)

            # Draw fish
            self.canvas.create_image(
                fish.x, fish.y, image=photo, tags=f"fish_{fish.fish_id}"
            )

            # Draw fish info
            info_text = f"{fish.name}\n{fish.remaining_lifetime:.0f}s"
            self.canvas.create_text(
                fish.x,
                fish.y - 30,
                text=info_text,
                font=("Arial", 8),
                tags=f"info_{fish.fish_id}",
            )

            # Draw lifetime bar
            bar_width = 40
            bar_height = 4
            lifetime_ratio = fish.remaining_lifetime / config.FISH_LIFETIME
            self.canvas.create_rectangle(
                fish.x - bar_width / 2,
                fish.y - 25,
                fish.x + bar_width / 2,
                fish.y - 25 + bar_height,
                fill="gray",
                outline="black",
                tags=f"bar_{fish.fish_id}",
            )
            self.canvas.create_rectangle(
                fish.x - bar_width / 2,
                fish.y - 25,
                fish.x - bar_width / 2 + bar_width * lifetime_ratio,
                fish.y - 25 + bar_height,
                fill="green",
                outline="",
                tags=f"bar_fill_{fish.fish_id}",
            )

        except Exception:
            # Fallback: draw simple circle
            self.canvas.create_oval(
                fish.x - 15,
                fish.y - 10,
                fish.x + 15,
                fish.y + 10,
                fill=config.FISH_COLORS["body"],
                outline="black",
            )

    def update_stats(self):
        """Update statistics labels"""
        for key, label in self.stats_labels.items():
            label.config(text=f"{key.capitalize()}: {self.stats[key]}")

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.mqtt_handler:
            self.mqtt_handler.disconnect()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Fish Haven - MQTT Pond Simulator")
    parser.add_argument(
        "--pond-name", type=str, help="Name of the pond (overrides config.py)"
    )
    parser.add_argument(
        "--group-name", type=str, help="Name of the group (overrides config.py)"
    )
    parser.add_argument(
        "--broker", type=str, help="MQTT broker address (overrides config.py)"
    )
    args = parser.parse_args()

    # Override config values if provided
    if args.pond_name:
        config.POND_NAME = args.pond_name
        print(f"✓ Using pond name: {args.pond_name}")

    if args.group_name:
        config.GROUP_NAME = args.group_name
        print(f"✓ Using group name: {args.group_name}")

    if args.broker:
        config.MQTT_BROKER = args.broker
        print(f"✓ Using MQTT broker: {args.broker}")

    root = tk.Tk()
    app = PondGUI(root)

    # Handle window close
    def on_closing():
        if messagebox.askokcancel("Quit", "Do you want to quit Fish Haven?"):
            app.cleanup()
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
