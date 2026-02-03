"""
Fish class for Fish Haven Project
Represents a fish with 4 postures for animation
"""

import json
import time
import random
import base64
from io import BytesIO
from PIL import Image, ImageDraw


class Fish:
    def __init__(
        self,
        name=None,
        genesis_pond=None,
        remaining_lifetime=None,
        postures=None,
        x=None,
        y=None,
        fish_id=None,
    ):
        """
        Initialize a fish

        Args:
            name: Optional name for the fish
            genesis_pond: Name of the pond where fish was born
            remaining_lifetime: Remaining lifetime in seconds
            postures: List of 4 posture images (base64 encoded)
            x, y: Position in pond
            fish_id: Unique identifier
        """
        from config import FISH_LIFETIME, POND_WIDTH, POND_HEIGHT, POND_NAME, GROUP_NAME

        self.fish_id = fish_id or f"{POND_NAME}_{int(time.time()*1000)}"
        self.name = name or f"{GROUP_NAME}_Fish_{random.randint(1000, 9999)}"
        self.genesis_pond = genesis_pond or POND_NAME
        self.birth_time = time.time()
        self.remaining_lifetime = remaining_lifetime or FISH_LIFETIME
        self.last_update = time.time()

        # Position and movement
        self.x = x if x is not None else random.randint(50, POND_WIDTH - 50)
        self.y = y if y is not None else random.randint(50, POND_HEIGHT - 50)
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)

        # Animation
        self.current_posture = 0
        self.animation_counter = 0
        self.animation_speed = 10  # Frames before changing posture

        # Migration
        self.next_migration_time = time.time() + random.randint(15, 45)

        # Create postures if not provided
        if postures:
            self.postures = postures
        else:
            self.postures = self._create_default_postures()

    def _darken_color(self, hex_color, factor=0.6):
        """
        Darken a hex color by a factor (0.0 = black, 1.0 = original)

        Args:
            hex_color: Hex color string (e.g., '#FF6B6B')
            factor: Darkening factor (0.6 = 40% darker)

        Returns:
            Darkened hex color string
        """
        # Remove '#' if present
        hex_color = hex_color.lstrip("#")

        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Darken by factor
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def _create_default_postures(self):
        """Create 4 distinct fish postures for swimming animation"""
        from config import FISH_SIZE, FISH_COLORS

        postures = []
        size = FISH_SIZE

        # Calculate darker fin color based on body color
        body_color = FISH_COLORS["body"]
        fin_color = self._darken_color(body_color, factor=0.6)  # 40% darker

        # Four distinct postures for realistic swimming animation
        # Posture 0: Neutral position
        # Posture 1: Tail up, fins compressed
        # Posture 2: Neutral (return)
        # Posture 3: Tail down, fins extended

        for i in range(4):
            # Create image
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Animation parameters for each posture
            tail_offset = [0, -5, 0, 5][i]  # Vertical tail movement
            body_stretch = [0, -1, 0, 1][i]  # Body compression/extension
            fin_height = [0, -2, 0, 2][i]  # Dorsal fin movement

            # Draw fish body (ellipse) with slight stretch
            body_bbox = [
                size * 0.3,
                size * 0.3 - body_stretch,
                size * 0.8 + body_stretch,
                size * 0.7 + body_stretch,
            ]
            draw.ellipse(body_bbox, fill=body_color)

            # Draw tail (triangle) - animates up and down
            tail_points = [
                (size * 0.3, size * 0.5),
                (size * 0.08, size * 0.3 + tail_offset),
                (size * 0.08, size * 0.7 + tail_offset),
            ]
            draw.polygon(tail_points, fill=fin_color)

            # Draw dorsal fin - moves with swimming motion
            fin_points = [
                (size * 0.5, size * 0.3),
                (size * 0.45, size * 0.15 + fin_height),
                (size * 0.6, size * 0.3),
            ]
            draw.polygon(fin_points, fill=fin_color)

            # Draw ventral fin (bottom fin) - opposite movement to dorsal
            ventral_points = [
                (size * 0.5, size * 0.7),
                (size * 0.45, size * 0.85 - fin_height),
                (size * 0.6, size * 0.7),
            ]
            draw.polygon(ventral_points, fill=fin_color)

            # Draw pectoral fin (side fin) - subtle movement
            pectoral_angle = [0, 3, 0, -3][i]
            pectoral_points = [
                (size * 0.55, size * 0.55),
                (size * 0.45, size * 0.6 + pectoral_angle),
                (size * 0.5, size * 0.5),
            ]
            draw.polygon(pectoral_points, fill=fin_color)

            # Draw eye
            eye_x, eye_y = size * 0.65, size * 0.45
            eye_size = 3
            draw.ellipse(
                [
                    eye_x - eye_size,
                    eye_y - eye_size,
                    eye_x + eye_size,
                    eye_y + eye_size,
                ],
                fill=FISH_COLORS["eye"],
            )

            # Add white highlight to eye for more detail
            highlight_size = 1
            draw.ellipse(
                [
                    eye_x - highlight_size,
                    eye_y - highlight_size - 1,
                    eye_x + highlight_size,
                    eye_y + highlight_size - 1,
                ],
                fill="white",
            )

            # Add some scales/texture (optional dots)
            for scale_pos in [(0.45, 0.45), (0.55, 0.5), (0.5, 0.55)]:
                scale_x, scale_y = size * scale_pos[0], size * scale_pos[1]
                draw.ellipse(
                    [scale_x - 1, scale_y - 1, scale_x + 1, scale_y + 1],
                    outline=FISH_COLORS["eye"],
                    width=1,
                )

            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            postures.append(img_str)

        return postures

    def update_lifetime(self):
        """Update remaining lifetime based on time elapsed"""
        current_time = time.time()
        elapsed = current_time - self.last_update
        self.remaining_lifetime -= elapsed
        self.last_update = current_time
        return self.remaining_lifetime > 0

    def update_position(self, width, height):
        """Update fish position with boundary checking"""
        self.x += self.vx
        self.y += self.vy

        # Bounce off walls
        if self.x < 0 or self.x > width:
            self.vx = -self.vx
            self.x = max(0, min(width, self.x))

        if self.y < 0 or self.y > height:
            self.vy = -self.vy
            self.y = max(0, min(height, self.y))

        # Occasionally change direction
        if random.random() < 0.02:
            self.vx += random.uniform(-0.5, 0.5)
            self.vy += random.uniform(-0.5, 0.5)
            # Limit speed
            speed = (self.vx**2 + self.vy**2) ** 0.5
            if speed > 3:
                self.vx = (self.vx / speed) * 3
                self.vy = (self.vy / speed) * 3

    def update_animation(self):
        """Update animation posture"""
        self.animation_counter += 1
        if self.animation_counter >= self.animation_speed:
            self.animation_counter = 0
            self.current_posture = (self.current_posture + 1) % 4

    def should_migrate(self, pond_crowded=False):
        """Check if fish should migrate"""
        current_time = time.time()

        # Migrate if pond is crowded
        if pond_crowded:
            return True

        # Random migration based on time
        if current_time >= self.next_migration_time:
            return True

        return False

    def to_dict(self):
        """Convert fish to dictionary for MQTT transmission (minimal format)"""
        return {
            "id": self.fish_id,
            "name": self.name,
            "genesis": self.genesis_pond,
            "lifetime": int(self.remaining_lifetime),  # Just the number (e.g., 60)
        }

    def to_json(self):
        """Convert fish to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data):
        """Create fish from dictionary (supports both old and new format)"""
        # Support both new simplified format and old format for backward compatibility
        # Note: postures are NOT transmitted - each pond generates its own visuals
        fish = cls(
            name=data.get("name"),
            genesis_pond=data.get("genesis")
            or data.get("genesis_pond"),  # New or old format
            remaining_lifetime=data.get("lifetime")
            or data.get("remaining_lifetime"),  # New or old format
            postures=None,  # Generate new postures locally
            x=data.get("x"),  # Will use random if not provided
            y=data.get("y"),  # Will use random if not provided
            fish_id=data.get("id") or data.get("fish_id"),  # New or old format
        )
        # Old format compatibility
        if "vx" in data:
            fish.vx = data.get("vx")
        if "vy" in data:
            fish.vy = data.get("vy")
        if "birth_time" in data:
            fish.birth_time = data.get("birth_time")

        fish.last_update = time.time()
        return fish

    @classmethod
    def from_json(cls, json_str):
        """Create fish from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __str__(self):
        return f"Fish({self.name}, from {self.genesis_pond}, {self.remaining_lifetime:.1f}s left)"
