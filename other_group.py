import json
import random
import time
import uuid

import paho.mqtt.client as mqtt
import pygame

# --- CONFIGURATION ---
BROKER = "localhost"
PORT = 1883
TOPIC = "fishhaven/stream"
MY_POND_NAME = "Pond XX"

# --- PYGAME SETTINGS ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BG_COLOR = (20, 40, 60)  # Dark Blue
FISH_COLOR = (255, 165, 0)  # Orange
FPS = 60

# --- RATES (LOWER = SLOWER) ---
# 0.005 = 0.5% chance per frame. At 60 FPS, this is approx 1 fish every 3-4 seconds.
SPAWN_CHANCE = 0.005
# 0.001 = 0.1% chance per frame. rare migration.
MIGRATE_CHANCE = 0.001


class Fish:
    def __init__(self, genesis, lifetime=60, name=None):
        self.id = str(uuid.uuid4())[:8]
        self.name = name if name else f"Fish-{self.id}"
        self.genesis = genesis
        self.lifetime = lifetime  # Source: 15, 21
        self.postures = ["<><", "><>", "<*><", "><*>"]

        # Physics Properties
        self.radius = 15
        self.x = random.randint(50, SCREEN_WIDTH - 50)
        self.y = random.randint(50, SCREEN_HEIGHT - 50)
        self.vx = random.choice([-2, -1, 1, 2])
        self.vy = random.choice([-2, -1, 1, 2])
        self.color = (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255),
        )

    def move(self):
        self.x += self.vx
        self.y += self.vy

        # --- FIX: Prevent sticking to walls ---
        # If fish hits Left Wall
        if self.x <= self.radius:
            self.x = self.radius + 1
            self.vx = abs(self.vx)
        # If fish hits Right Wall
        elif self.x >= SCREEN_WIDTH - self.radius:
            self.x = SCREEN_WIDTH - self.radius - 1
            self.vx = -abs(self.vx)

        # If fish hits Top Wall
        if self.y <= self.radius:
            self.y = self.radius + 1
            self.vy = abs(self.vy)

        # If fish hits Bottom Wall
        elif self.y >= SCREEN_HEIGHT - self.radius:
            self.y = SCREEN_HEIGHT - self.radius - 1
            self.vy = -abs(self.vy)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "genesis": self.genesis,
            "lifetime": self.lifetime,
            "postures": self.postures,
        }

    @staticmethod
    def from_dict(data):
        fish = Fish(data["genesis"], data["lifetime"], data.get("name"))
        fish.id = data.get("id", fish.id)
        return fish


class Pond:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"Fish Haven: {MY_POND_NAME}")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 16)
        self.title_font = pygame.font.SysFont("Arial", 24, bold=True)

        self.fishes = []

        # MQTT Setup
        self.client = mqtt.Client()
        # Always set credentials (broker requires authentication)
        self.client.username_pw_set("dc25", "kmitl-dc25")
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log(f"✅ Connected to Broker at {BROKER}")
            client.subscribe(TOPIC)
        else:
            self.log(f"❌ Connection Failed with code: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if "genesis" in payload and "lifetime" in payload:
                if payload["genesis"] != MY_POND_NAME:
                    # Check if pond is at maximum capacity
                    if len(self.fishes) >= 10:
                        self.log(
                            f"⚠️  REJECTED: Cannot receive fish - Maximum limit (10) reached"
                        )
                        return

                    new_fish = Fish.from_dict(payload)

                    # Import Logic: Force fish to swim INWARD
                    side = random.choice([0, 1])
                    if side == 0:  # Left
                        new_fish.x = 20
                        new_fish.vx = abs(new_fish.vx)
                    else:  # Right
                        new_fish.x = SCREEN_WIDTH - 20
                        new_fish.vx = -abs(new_fish.vx)

                    self.fishes.append(new_fish)
                    self.log(
                        f"🌊 IMPORT: {new_fish.name} arrived from {new_fish.genesis}"
                    )
        except:
            pass

    def update_logic(self):
        # 1. Spawning (Slower rate, max 10 fish)
        if random.random() < SPAWN_CHANCE and len(self.fishes) < 10:
            fish = Fish(genesis=MY_POND_NAME)
            self.fishes.append(fish)
            self.log(f"✨ SPAWN: {fish.name} created.")

        # 2. Update Fish
        for fish in self.fishes[:]:
            fish.move()

            # Decrease lifetime roughly every second
            if random.random() < (1.0 / 60.0):
                fish.lifetime -= 1

            # Death
            if fish.lifetime <= 0:
                self.fishes.remove(fish)
                self.log(f"💀 DEATH: {fish.name} died of old age.")
                continue

            # Migration (Slower rate)
            if random.random() < MIGRATE_CHANCE:
                self.log(f"🚀 EXPORT: {fish.name} migrated to stream.")
                msg = json.dumps(fish.to_dict())
                self.client.publish(TOPIC, msg)
                self.fishes.remove(fish)

    def draw(self):
        self.screen.fill(BG_COLOR)

        for fish in self.fishes:
            # Draw body
            pygame.draw.ellipse(self.screen, fish.color, (fish.x, fish.y, 40, 25))

            # Draw Tail (Flip based on direction)
            tail_x = fish.x - 10 if fish.vx > 0 else fish.x + 50
            pygame.draw.polygon(
                self.screen,
                fish.color,
                [(fish.x + 20, fish.y + 12), (tail_x, fish.y), (tail_x, fish.y + 25)],
            )

            # --- VISUAL UPDATE: Name + Lifetime + Origin ---
            # Format: "FishName (45s) [OriginPond]"
            label_text = f"{fish.name} ({fish.lifetime}s) [{fish.genesis}]"

            text = self.font.render(label_text, True, (255, 255, 255))
            text_rect = text.get_rect(center=(fish.x + 20, fish.y - 15))
            self.screen.blit(text, text_rect)

        # Draw Title
        title = self.title_font.render(
            f"POND: {MY_POND_NAME} | Population: {len(self.fishes)}", True, (0, 255, 0)
        )
        self.screen.blit(title, (20, 20))

        pygame.display.flip()

    def run(self):
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_start()
        self.log("--- Visual Pond Started ---")

        running = True
        while running:
            self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.update_logic()
            self.draw()

        self.client.loop_stop()
        self.client.disconnect()
        pygame.quit()
        self.log("--- System Shutdown ---")


if __name__ == "__main__":
    pond = Pond()
    pond.run()
