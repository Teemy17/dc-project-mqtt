#!/bin/bash

# Navigate to project root regardless of where this script is called from
cd "$(dirname "$0")/.."

echo "🐟 Setting up MQTT Broker for Fish Haven Project..."

# Create password file with credentials
echo "Creating password file..."
docker run -it --rm \
  -v $(pwd)/infra/mosquitto/config:/mosquitto/config \
  eclipse-mosquitto mosquitto_passwd -b -c /mosquitto/config/passwd dc25 kmitl-dc25

# Set proper permissions
chmod -R 755 infra/mosquitto/

echo "✓ MQTT broker setup complete!"
echo ""
echo "To start the MQTT broker, run:"
echo "  docker-compose up -d"
echo ""
echo "To stop the broker:"
echo "  docker-compose down"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f mosquitto"
