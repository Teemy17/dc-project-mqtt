"""
Configuration file for Fish Haven Project
"""

# MQTT Settings
MQTT_BROKER = "localhost"  # Change to TA's server address when testing
MQTT_PORT = 1883
MQTT_USERNAME = "dc25"
MQTT_PASSWORD = "kmitl-dc25"

# Topics
TOPIC_BASE = "fishhaven"
TOPIC_STREAM = f"{TOPIC_BASE}/stream"
TOPIC_HELLO = f"{TOPIC_BASE}/hello"
TOPIC_FISH = f"{TOPIC_BASE}/fish"
TOPIC_ANNOUNCE = f"{TOPIC_BASE}/announce"

# Pond Settings
POND_NAME = "YourGroupPond"  # TODO: Change this to your group's pond name
GROUP_NAME = "GroupX"  # TODO: Change this to your group name
POND_WIDTH = 800
POND_HEIGHT = 600
POND_COLOR = "#87CEEB"  # Sky blue water

# Fish Settings
FISH_SPAWN_INTERVAL = 10  # seconds between spawns
FISH_LIFETIME = 60  # seconds (1 minute)
FISH_SIZE = 40
POND_CAPACITY = 20  # Maximum fish before migration is triggered
MIGRATION_THRESHOLD = 15  # Trigger migration when fish count reaches this

# Fish Movement
FISH_SPEED_MIN = 1
FISH_SPEED_MAX = 3
MIGRATION_INTERVAL_MIN = 15  # Minimum seconds before random migration
MIGRATION_INTERVAL_MAX = 45  # Maximum seconds before random migration

# Colors for your group's fish (customize these!)
FISH_COLORS = {
    "body": "#FF6B6B",  # Main body color
    "fins": "#4ECDC4",  # Note: This is now auto-calculated as darker body color (kept for backward compatibility)
    "eye": "#000000",  # Eye color
}
# Note: Fins are automatically rendered as 40% darker than the body color for a cohesive look
