# 🐟 Fish Haven - MQTT Pond Simulator

A distributed pond simulation system where fish can migrate between different ponds via MQTT messaging. Each pond can spawn fish that swim with realistic 4-posture animation, and fish can migrate to other ponds through the MQTT broker.

## 🚀 Quick Start (3 Steps)

### 1. Start MQTT Broker

```bash
./setup-mqtt.sh
docker-compose up -d
```

### 2. Run Your Pond

```bash
# Using uv (recommended)
uv run pond.py --pond-name "MyPond" --group-name "MyTeam"

# Or using python
python pond.py --pond-name "MyPond" --group-name "MyTeam"
```

### 3. Click "Start Pond" in GUI

Watch fish spawn, swim with 4-posture animation, and migrate!

## 📋 Requirements

- Python 3.8+
- Docker and Docker Compose
- Dependencies: `tkinter`, `paho-mqtt`, `pillow`

Install Python dependencies:

```bash
pip install -r requirements.txt
# or
uv pip install -r requirements.txt
```

## 🎮 Usage

### Basic Usage

```bash
# Run with custom names (recommended)
python pond.py --pond-name "Crystal Waters" --group-name "Team Crystal"

# Connect to remote broker
python pond.py --pond-name MyPond --broker 192.168.1.100
```

### Run Multiple Ponds Locally

Test fish migration between ponds:

**Terminal 1:**

```bash
uv run pond.py --pond-name "BlueLagoon" --group-name "TeamBlue"
```

**Terminal 2:**

```bash
uv run pond.py --pond-name "RedSea" --group-name "TeamRed"
```

**Terminal 3 (other_group.py - pygame version):**

```bash
uv run other_group.py
```

_Note: Edit `MY_POND_NAME` in `other_group.py` before running_

Watch fish migrate between ponds with their team names visible!

## ⚙️ Configuration

### Method 1: Command-Line Arguments (Recommended)

```bash
python pond.py --pond-name NAME --group-name NAME --broker ADDRESS
```

### Method 2: Edit config.py

```python
# config.py
POND_NAME = 'YourGroupPond'  # Change this
GROUP_NAME = 'GroupX'         # Change this
MQTT_BROKER = "localhost"     # Change to TA's server when needed
```

### Important Settings

```python
# Fish behavior
FISH_SPAWN_INTERVAL = 10      # Seconds between auto-spawns
FISH_LIFETIME = 60            # Seconds (1 minute)
POND_CAPACITY = 20            # Maximum fish (currently set to 10)
MIGRATION_THRESHOLD = 15      # Fish count that triggers migration

# Customize colors (fins auto-darken to 60% of body color)
FISH_COLORS = {
    'body': '#FF6B6B',    # Main body color
    'eye': '#000000'      # Eye color
}
```

## 🎨 Features

### Fish Animation

- **4-Posture Animation**: Realistic swimming motion with body compression/extension
- **Enhanced Graphics**: Body, tail, dorsal/ventral/pectoral fins, eyes with highlights, scales
- **Smooth Movement**: Fish bounce off walls and swim continuously

### Fish Naming & Identity

- **Group-Based Names**: `TeamBlue_Fish_1234` (includes your group name)
- **Genesis Tracking**: Each fish remembers where it was born
- **Visual Display**: Name, lifetime countdown, and origin pond shown

### Intelligent Colors

- **Auto-Darkened Fins**: Fins automatically rendered 40% darker than body color
- **Team Colors**: Each group can set their signature color
- **Cohesive Look**: Professional color harmony

### Migration System

- **Automatic Migration**: When pond is crowded (>15 fish) or random interval (15-45s)
- **Manual Spawn**: Click "Spawn Fish" button
- **Self-Filtering**: Ponds automatically ignore their own fish
- **Max Capacity**: Limited to 10 fish per pond (configurable)

### Statistics & Logging

- **Real-time Stats**: Spawned, Received, Sent, Died
- **Message Log**: All MQTT activity logged
- **Connection Status**: Visual indicator for MQTT connection

## 📡 MQTT Communication

### Ultra-Simple Message Format

Fish data sent directly to `fishhaven/stream` topic:

```json
{
  "id": "MyPond_1738564523123",
  "name": "MyTeam_Fish_1234",
  "genesis": "MyPond",
  "lifetime": 60
}
```

**Just 4 fields!** (~70 bytes per message)

### How It Works

1. Fish spawns or migrates → Pond A sends fish data
2. All ponds receive message on `fishhaven/stream`
3. Each pond checks: Is this my fish? (filters by ID prefix)
4. If not, pond accepts fish and generates visuals locally
5. Fish appears in receiving pond with team name/colors

### Topics

- `fishhaven/stream` - Main fish migration topic
- `fishhaven/hello` - Hello messages (testing)
- `fishhaven/announce` - Pond announcements

## 🐳 Docker MQTT Broker

### Start/Stop Commands

```bash
# Start broker
docker-compose up -d

# Stop broker
docker-compose down

# View logs
docker-compose logs -f mosquitto

# Check status
docker-compose ps

# Restart
docker-compose restart
```

### Broker Details

- **Address**: `localhost:1883`
- **WebSockets**: `localhost:9001`
- **Username**: `dc25`
- **Password**: `kmitl-dc25`
- **Authentication**: Enabled
- **Persistence**: Enabled

## 🧪 Testing

### Test MQTT Connection

```bash
python test_mqtt.py
```

### Test with Multiple Ponds

1. Start 2-3 ponds with different names
2. Click "Start Pond" in each
3. Watch fish spawn and migrate
4. Check message logs for MQTT traffic
5. Verify statistics update correctly

### Subscribe to MQTT Stream (Debug)

```bash
docker exec -it mqtt-broker mosquitto_sub -h localhost -t "fishhaven/#" -u dc25 -P kmitl-dc25 -v
```

## 📁 Project Structure

```
.
├── pond.py              # Main pond (Tkinter GUI) ⭐
├── other_group.py       # Alternative pond (Pygame) ⭐
├── fish.py              # Fish class with 4-posture animation ⭐
├── mqtt_handler.py      # MQTT communication handler ⭐
├── config.py            # Configuration settings ⭐
├── main.py              # Entry point
├── test_mqtt.py         # MQTT connection test
├── docker-compose.yml   # MQTT broker setup
├── setup-mqtt.sh        # Broker initialization script
├── run-pond.sh          # Helper script to run pond
├── requirements.txt     # Python dependencies
├── mosquitto/           # MQTT broker data
│   ├── config/          # Broker configuration
│   ├── data/            # Persistent storage
│   └── log/             # Log files
└── README.md            # This file
```

## 🔧 Troubleshooting

### Connection Refused

**Problem**: `[Errno 61] Connection refused`

**Solution**:

```bash
# Check if broker is running
docker-compose ps

# Start broker if not running
docker-compose up -d

# Check logs
docker-compose logs -f mosquitto
```

### Authentication Failed

**Problem**: MQTT authentication errors

**Solution**:

```bash
# Regenerate password file
docker run -it --rm -v $(pwd)/mosquitto/config:/mosquitto/config \
  eclipse-mosquitto mosquitto_passwd -b -c /mosquitto/config/passwd dc25 kmitl-dc25

# Restart broker
docker-compose restart
```

### Port Already in Use

**Problem**: Port 1883 is occupied

**Solution**:

```bash
# Check what's using the port
lsof -i :1883

# Either stop that service or change port in docker-compose.yml
```

### No Fish Spawning

**Problem**: Fish not appearing

**Solution**:

- Click "Start Pond" button in GUI
- Check MQTT connection status (should be green)
- Verify fish spawn interval in config.py
- Check message log for errors

### Fish Not Migrating

**Problem**: Fish stay in one pond

**Solution**:

- Wait for pond to reach 15+ fish (or change MIGRATION_THRESHOLD)
- Wait for random migration interval (15-45 seconds)
- Check MQTT connection is active

### Other Group Compatibility

**Problem**: other_group.py not receiving fish

**Solution**:

- Make sure MY_POND_NAME is unique in other_group.py
- Both ponds must connect to same broker
- Check if fish genesis matches expected format

## 🎓 For Course Submission

### Connect to TA's Server

```bash
uv run pond.py \
  --broker <TA_SERVER_IP> \
  --pond-name "YourUniquePondName" \
  --group-name "YourGroupName"
```

### What to Demonstrate

1. ✅ Fish spawning with your group name
2. ✅ Fish swimming with 4-posture animation
3. ✅ Fish with your team colors
4. ✅ Fish migrating to/from other ponds
5. ✅ MQTT messages in log panel
6. ✅ Statistics tracking (spawned/received/sent/died)
7. ✅ Maximum 10 fish limit enforced

## 💡 Tips & Best Practices

### Pond Management

- **Use unique pond names** to avoid conflicts in multi-pond setups
- **Choose distinct colors** for your team (makes fish easy to identify)
- **Monitor the message log** for debugging MQTT issues
- **Watch the statistics** to track fish activity
- **Test locally first** before connecting to TA's server

### Performance

- **10 fish limit**: Keeps performance optimal and prevents overcrowding
- **Efficient messages**: Only 70 bytes per fish (no visuals transmitted)
- **Local generation**: Each pond generates fish visuals locally
- **Auto-filtering**: Ponds ignore their own fish automatically

### Color Selection

Suggested team colors (fins auto-darken):

- **Warm**: Red `#FF6B6B`, Orange `#FF9B6B`, Yellow `#FFD700`
- **Cool**: Blue `#6B9FFF`, Cyan `#6BFFFF`, Purple `#9B6BFF`
- **Nature**: Green `#6BFF6B`, Forest `#4C7B4C`, Ocean `#4C7B9B`

## 📝 Technical Details

### Fish Properties

- **Unique ID**: `{POND_NAME}_{timestamp}`
- **Display Name**: `{GROUP_NAME}_Fish_{random}`
- **Lifetime**: 60 seconds default
- **4 Postures**: Neutral, Upward stroke, Neutral return, Downward stroke
- **Animation Speed**: 10 frames per posture cycle

### Message Protocol

- **Version**: 1.0 (Simplified)
- **Size**: ~70 bytes per fish message
- **Backward Compatible**: Works with old and new formats
- **Universal**: Compatible with any MQTT client

### Compatibility

✅ pond.py (Tkinter)  
✅ other_group.py (Pygame)  
✅ Any Python implementation  
✅ Any language that speaks MQTT + JSON

## 🔥 Item 4 – Overload & Crash Testing

This section documents the **testing procedure for overloads and crashes** and explains how to observe the results using Prometheus metrics.

### Observability Metrics Added

| Metric | Type | Description |
|---|---|---|
| `fishhaven_active_fishes` | Gauge | Current fish count in pond |
| `fishhaven_spawned_total` | Counter | Total fish spawned locally |
| `fishhaven_migrated_in_total` | Counter | Fish received from other ponds |
| `fishhaven_migrated_out_total` | Counter | Fish sent to other ponds |
| `fishhaven_deaths_total` | Counter | Fish that died of old age |
| `fishhaven_rejected_fish_total` | Counter | Fish rejected (pond at capacity) |
| `fishhaven_mqtt_connected` | Gauge | MQTT connection status (1=up, 0=down) |
| `stress_messages_sent_total` | Counter | Messages sent by stress tester |
| `stress_messages_failed_total` | Counter | Failed publish attempts |
| `stress_publish_latency_seconds` | Histogram | Per-message publish latency |
| `stress_broker_up` | Gauge | Broker reachability (1=up, 0=down) |
| `stress_test_phase` | Gauge | Current test phase (0=idle, 1=flood, 2=overload, 3=crash) |

All pond metrics are available at **http://localhost:8000/metrics**  
Stress-test metrics are available at **http://localhost:8001/metrics**

---

### Setup: Start Everything

```bash
# Terminal 1 – Start MQTT broker
docker-compose up -d

# Terminal 2 – Start the pond (exposes metrics on :8000)
uv run pond.py --pond-name "TestPond" --group-name "TestTeam"
# Click "Start Pond" in the GUI

# Terminal 3 – Run the stress test (exposes metrics on :8001)
uv run stress_test.py --test all
```

---

### Test 1 – Message Flood

**Purpose**: Verify the MQTT broker handles a burst of 100 fish messages without data loss.

**What it does**: Sends 100 fish messages at ~20 messages/second.

**Command**:
```bash
uv run stress_test.py --test flood
```

**Expected outcome**:
- `stress_messages_sent_total` counter rises by 100
- `stress_publish_latency_seconds` histogram stays in the 1–10 ms range
- `stress_messages_failed_total` stays at 0

**What to look for in Prometheus/Grafana**:
- Sharp rising edge on `stress_messages_sent_total` (flood spike)
- Latency histogram showing 99th percentile under 100 ms

---

### Test 2 – Capacity Overload

**Purpose**: Verify the pond enforces the 10-fish limit and records all rejections.

**What it does**: Publishes 10 + 30 = 40 fish messages. Pond accepts the first 10, rejects the rest.

**Command**:
```bash
uv run stress_test.py --test overload
```

**Expected outcome**:
- `fishhaven_active_fishes` plateaus at **10** (never exceeds limit)
- `fishhaven_rejected_fish_total` climbs to **~30**
- Pond GUI message log shows `WARNING: Cannot receive fish: Maximum limit (10) reached`

**What to look for in Prometheus/Grafana**:
- `fishhaven_active_fishes` flat line at 10 despite continuous inflow
- Rising `fishhaven_rejected_fish_total` during the overload window

---

### Test 3 – Broker Crash & Recovery

**Purpose**: Verify the system detects a broker outage and recovers automatically.

**What it does**:
1. Sends 5 normal messages (Phase A)
2. Stops the MQTT broker container (Phase B — simulated crash)
3. Attempts 5 more publishes — all should fail
4. Restarts the broker (Phase C)
5. Waits for paho auto-reconnect, then sends 5 recovery messages

**Command**:
```bash
uv run stress_test.py --test crash
```

**Expected outcome**:
- Phase B: `fishhaven_mqtt_connected` drops to **0**, `stress_broker_up` drops to **0**
- Phase B: `stress_messages_failed_total` increments for each failed publish
- Phase C: `fishhaven_mqtt_connected` returns to **1** after auto-reconnect
- Phase C: 5 post-recovery messages delivered successfully

**What to look for in Prometheus/Grafana**:
- `fishhaven_mqtt_connected` — dip to 0 then return to 1 (visible crash + recovery)
- `stress_broker_up` — matching dip
- `stress_messages_failed_total` — spike during outage window only

---

### Individual Test Commands

```bash
# Run all three tests back-to-back
uv run stress_test.py --test all

# Run only the flood test
uv run stress_test.py --test flood

# Run only the capacity overload test
uv run stress_test.py --test overload

# Run only the crash/recovery test (requires Docker)
uv run stress_test.py --test crash
```

---

### Prometheus Query Examples (for screenshots)

```promql
# Fish count over time
fishhaven_active_fishes

# Rejection rate (per minute)
rate(fishhaven_rejected_fish_total[1m])

# Message flood rate (per second)
rate(stress_messages_sent_total[10s])

# Publish latency 99th percentile
histogram_quantile(0.99, rate(stress_publish_latency_seconds_bucket[1m]))

# MQTT connection status (crash/recovery visibility)
fishhaven_mqtt_connected

# Error rate during crash
rate(stress_messages_failed_total[30s])
```

---

## 🤝 Contributing

This is a course project for **DC25 @ KMITL**.

**Technology Stack**: Python, MQTT, Tkinter/Pygame, Docker, Eclipse Mosquitto

## 📄 License

Educational project for KMITL course.

---

**Enjoy your swimming fish!** 🐟🐠🐡

**Status**: Production Ready ✨  
**Last Updated**: Feb 2026
