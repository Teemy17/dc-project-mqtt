#!/usr/bin/env python3
"""
Test script for Fish Haven MQTT connectivity
Use this to test connection before running the full application
"""

import time
import json
from datetime import datetime
from mqtt_handler import MQTTHandler
from config import POND_NAME, GROUP_NAME

def test_callback(message_data):
    """Callback for received messages"""
    print(f"\n{'='*60}")
    print(f"RECEIVED MESSAGE")
    print(f"{'='*60}")
    print(f"Topic: {message_data['topic']}")
    print(f"Time: {message_data['timestamp']}")
    print(f"Payload: {message_data['payload']}")
    print(f"{'='*60}\n")

def main():
    """Run MQTT connectivity tests"""
    print("="*60)
    print("Fish Haven - MQTT Connectivity Test")
    print("="*60)
    print(f"Pond Name: {POND_NAME}")
    print(f"Group Name: {GROUP_NAME}")
    print("="*60)
    
    # Create MQTT handler
    print("\n1. Creating MQTT handler...")
    mqtt = MQTTHandler(pond_callback=test_callback)
    
    # Connect
    print("\n2. Connecting to MQTT broker...")
    if mqtt.connect():
        print("✓ Connection initiated")
    else:
        print("✗ Connection failed")
        return
    
    # Wait for connection
    print("\n3. Waiting for connection to establish...")
    time.sleep(2)
    
    if not mqtt.connected:
        print("✗ Failed to connect to MQTT broker")
        print("   Check broker address, port, username, and password in config.py")
        return
    
    print("✓ Connected to MQTT broker!")
    print(f"   Subscribed topics: {', '.join(mqtt.subscribed_topics)}")
    
    # Test 1: Announce pond
    print("\n4. Testing pond announcement...")
    mqtt.announce_pond()
    time.sleep(1)
    
    # Test 2: Send hello message
    print("\n5. Testing hello message...")
    mqtt.send_hello()
    time.sleep(1)
    
    # Test 3: Send test message to stream
    print("\n6. Testing stream message...")
    test_message = {
        'type': 'test',
        'from': POND_NAME,
        'message': 'This is a test message from Fish Haven',
        'timestamp': datetime.now().isoformat()
    }
    mqtt.publish('fishhaven/stream', json.dumps(test_message))
    time.sleep(1)
    
    # Keep listening
    print("\n" + "="*60)
    print("MQTT connection test completed!")
    print("="*60)
    print("\nListening for messages for 30 seconds...")
    print("(Send messages from other ponds to test receiving)")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        # Listen for 30 seconds
        for i in range(30):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                print(f"Still listening... ({30 - i - 1}s remaining)")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    
    # Cleanup
    print("\n7. Disconnecting...")
    mqtt.disconnect()
    print("✓ Disconnected\n")
    
    print("="*60)
    print("Test completed!")
    print("="*60)
    print("\nIf you saw:")
    print("  ✓ Connected to MQTT broker - Connection is working!")
    print("  ✓ Published messages - Sending is working!")
    print("  📨 Received messages - Receiving is working!")
    print("\nYou're ready to run the full pond application!")
    print("Run: python pond.py")
    print("="*60)

if __name__ == "__main__":
    main()
