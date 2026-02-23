"""
MQTT Handler for Fish Haven Project
Handles all MQTT communication between ponds
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime


class MQTTHandler:
    def __init__(self, pond_callback=None):
        """
        Initialize MQTT handler

        Args:
            pond_callback: Callback function for handling received messages
        """
        from config import (
            MQTT_BROKER,
            MQTT_PORT,
            MQTT_USERNAME,
            MQTT_PASSWORD,
            POND_NAME,
        )

        self.broker = MQTT_BROKER
        self.port = MQTT_PORT
        self.username = MQTT_USERNAME
        self.password = MQTT_PASSWORD
        self.pond_name = POND_NAME
        self.pond_callback = pond_callback

        self.client = mqtt.Client(client_id=f"pond_{POND_NAME}")
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self.connected = False
        self.subscribed_topics = []

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print(f"✓ Connected to MQTT broker at {self.broker}:{self.port}")
            was_reconnect = self.connected is False and getattr(self, "reconnect_count", 0) > 0
            self.connected = True
            if was_reconnect:
                print(f"✓ Reconnected successfully (attempt #{self.reconnect_count})")

            # Subscribe to stream topic (for fish migration and messages)
            from config import TOPIC_STREAM

            client.subscribe(TOPIC_STREAM)
            self.subscribed_topics.append(TOPIC_STREAM)
            print(f"✓ Subscribed to {TOPIC_STREAM}")

            # Announce pond existence
            self.announce_pond()
        else:
            print(f"✗ Connection failed with code {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        print(f"✗ Disconnected from MQTT broker (code: {rc})")
        self.connected = False
        if rc != 0:
            # Unexpected disconnect — paho will auto-reconnect; count the attempt
            print("⟳ Unexpected disconnect, paho-mqtt will attempt auto-reconnect...")
            self.reconnect_count = getattr(self, "reconnect_count", 0) + 1

    def _on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")

            print(f"\n📨 Received on {topic}:")
            print(f"   {payload[:100]}..." if len(payload) > 100 else f"   {payload}")

            # Parse message
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                # Plain text message
                data = {"message": payload, "raw": True}

            # Add metadata
            message_data = {
                "topic": topic,
                "payload": payload,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            }

            # Call pond callback
            if self.pond_callback:
                self.pond_callback(message_data)

        except Exception as e:
            print(f"✗ Error processing message: {e}")

    def connect(self):
        """Connect to MQTT broker"""
        try:
            print(f"Connecting to MQTT broker at {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, 60)

            # Start network loop in background thread
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker")

    def announce_pond(self):
        """Announce pond existence to the vivisystem"""
        from config import TOPIC_ANNOUNCE, POND_NAME, GROUP_NAME

        message = {
            "type": "announce",
            "pond_name": POND_NAME,
            "group_name": GROUP_NAME,
            "timestamp": datetime.now().isoformat(),
            "status": "online",
        }

        self.publish(TOPIC_ANNOUNCE, json.dumps(message))
        print(f"✓ Announced pond '{POND_NAME}' to vivisystem")

    def send_hello(self, target_pond=None):
        """Send hello message"""
        from config import TOPIC_HELLO, POND_NAME

        message = {
            "type": "hello",
            "from": POND_NAME,
            "to": target_pond or "all",
            "message": f"Hello from {POND_NAME}!",
            "timestamp": datetime.now().isoformat(),
        }

        self.publish(TOPIC_HELLO, json.dumps(message))
        print(f"✓ Sent hello message to {target_pond or 'all'}")

    def send_fish(self, fish, target_pond=None):
        """
        Send fish to another pond - sends fish data directly to stream

        Args:
            fish: Fish object to send
            target_pond: Target pond name (not used, kept for compatibility)
        """
        from config import TOPIC_STREAM

        # Send fish data directly as payload
        message = json.dumps(fish.to_dict())

        self.publish(TOPIC_STREAM, message)
        print(f"✓ Sent fish '{fish.name}' to stream")

    def publish(self, topic, message):
        """
        Publish message to topic

        Args:
            topic: MQTT topic
            message: Message to publish (string)
        """
        if not self.connected:
            print("✗ Not connected to MQTT broker")
            return False

        try:
            result = self.client.publish(topic, message)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                print(f"✗ Failed to publish to {topic}")
                return False
        except Exception as e:
            print(f"✗ Error publishing: {e}")
            return False

    def get_connection_status(self):
        """Get connection status as string"""
        return "Connected ✓" if self.connected else "Disconnected ✗"
