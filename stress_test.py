"""
Fish Haven - Stress Test Script
Item 4: Testing Procedure for Overloads and Crashes

Three test scenarios:
  1. Message Flood      - Burst 100 fish messages rapidly; observe broker throughput
  2. Capacity Overload  - Hammer pond beyond 10-fish limit; observe rejections
  3. Broker Crash       - Kill broker mid-test; observe disconnect + reconnect metrics

Usage:
  uv run stress_test.py --test all          # Run all tests sequentially
  uv run stress_test.py --test flood        # Test 1 only
  uv run stress_test.py --test overload     # Test 2 only
  uv run stress_test.py --test crash        # Test 3 only (requires Docker)

Prometheus metrics exposed on http://localhost:8001/metrics
"""

import argparse
import json
import random
import subprocess
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
BROKER = "localhost"
PORT = 1883
USERNAME = "dc25"
PASSWORD = "kmitl-dc25"
TOPIC = "fishhaven/stream"

STRESS_METRICS_PORT = 8001   # Prometheus port for THIS script
FLOOD_BURST = 100            # Fish messages sent in the flood test
FLOOD_DELAY = 0.05           # Seconds between each flood message (0.05 = 20 msg/s)
OVERLOAD_ATTEMPTS = 30       # Extra fish sent beyond 10-fish capacity

# ──────────────────────────────────────────────────────────────────────────────
# Prometheus Metrics (stress-test side)
# ──────────────────────────────────────────────────────────────────────────────
SENT_COUNTER     = Counter("stress_messages_sent_total",    "Messages sent during flood")
FAILED_COUNTER   = Counter("stress_messages_failed_total",  "Publish failures")
LATENCY_HIST     = Histogram("stress_publish_latency_seconds", "Publish round-trip latency",
                             buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0])
PHASE_GAUGE      = Gauge("stress_test_phase",
                         "Current test phase: 0=idle, 1=flood, 2=overload, 3=crash")
BROKER_UP_GAUGE  = Gauge("stress_broker_up", "Whether broker is reachable (1=yes, 0=no)")
RECONNECT_COUNTER= Counter("stress_reconnects_total", "Reconnects during crash test")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(msg, level="INFO"):
    icons = {"INFO": "ℹ", "PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌", "TEST": "🧪",
             "SEND": "📤", "RECV": "📥", "CRASH": "💥", "RECOVER": "🔄"}
    icon = icons.get(level, "  ")
    print(f"[{ts()}] {icon}  {msg}")


def make_fish(pond="StressPond", group="StressTeam"):
    """Create a minimal fish payload."""
    uid = f"{pond}_{int(time.time() * 1000)}_{random.randint(0, 9999)}"
    return {
        "id": uid,
        "name": f"{group}_Fish_{random.randint(1000, 9999)}",
        "genesis": pond,
        "lifetime": random.randint(20, 60),
    }


def connect_client(client_id="stress_tester") -> mqtt.Client:
    """Connect and return a paho client, raising on failure."""
    client = mqtt.Client(client_id=client_id)
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()
    time.sleep(0.5)   # Let the network loop start
    BROKER_UP_GAUGE.set(1)
    return client


def disconnect_client(client: mqtt.Client):
    client.loop_stop()
    client.disconnect()


# ──────────────────────────────────────────────────────────────────────────────
# Test 1 – Message Flood
# ──────────────────────────────────────────────────────────────────────────────
def test_flood():
    """
    Publish FLOOD_BURST fish messages as fast as possible.
    Observe: broker throughput, publish latency histogram in Prometheus.
    Expected: all messages delivered; latency stays low (<100 ms each).
    """
    log("=" * 60)
    log("TEST 1 – MESSAGE FLOOD", "TEST")
    log(f"Sending {FLOOD_BURST} fish messages at ~{1/FLOOD_DELAY:.0f} msg/s")
    log("Watch:  stress_messages_sent_total  /  stress_publish_latency_seconds")
    log("=" * 60)

    PHASE_GAUGE.set(1)
    client = connect_client("stress_flood")

    sent = 0
    failed = 0
    t_start = time.time()

    for i in range(FLOOD_BURST):
        payload = json.dumps(make_fish(pond="FloodPond", group="FloodTeam"))
        t0 = time.time()
        result = client.publish(TOPIC, payload, qos=1)
        latency = time.time() - t0

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            sent += 1
            SENT_COUNTER.inc()
            LATENCY_HIST.observe(latency)
            log(f"  [{i+1:3d}/{FLOOD_BURST}] sent  latency={latency*1000:.1f}ms", "SEND")
        else:
            failed += 1
            FAILED_COUNTER.inc()
            log(f"  [{i+1:3d}/{FLOOD_BURST}] FAILED (rc={result.rc})", "FAIL")

        time.sleep(FLOOD_DELAY)

    elapsed = time.time() - t_start
    rate = sent / elapsed if elapsed > 0 else 0

    disconnect_client(client)
    PHASE_GAUGE.set(0)

    log("-" * 60)
    log(f"RESULT: sent={sent}  failed={failed}  elapsed={elapsed:.1f}s  rate={rate:.1f} msg/s",
        "PASS" if failed == 0 else "FAIL")
    log("OBSERVABILITY: Check Prometheus stress_messages_sent_total counter spike")
    log("               Check stress_publish_latency_seconds histogram distribution")
    return failed == 0


# ──────────────────────────────────────────────────────────────────────────────
# Test 2 – Capacity Overload
# ──────────────────────────────────────────────────────────────────────────────
def test_overload():
    """
    First fill the pond to capacity (10 fish) then attempt OVERLOAD_ATTEMPTS more.
    The pond's receive_fish() will reject extras and increment fishhaven_rejected_fish_total.
    Observe: fishhaven_active_fishes plateau at 10, fishhaven_rejected_fish_total climbing.
    """
    log("=" * 60)
    log("TEST 2 – CAPACITY OVERLOAD", "TEST")
    log(f"Sending {10 + OVERLOAD_ATTEMPTS} fish to a pond that holds max 10")
    log("Watch:  fishhaven_active_fishes  /  fishhaven_rejected_fish_total")
    log("=" * 60)

    PHASE_GAUGE.set(2)
    client = connect_client("stress_overload")

    total = 10 + OVERLOAD_ATTEMPTS
    for i in range(total):
        payload = json.dumps(make_fish(pond="OverloadSource", group="FloodTeam"))
        result = client.publish(TOPIC, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            SENT_COUNTER.inc()
            status = "→ pond full, expect REJECT" if i >= 10 else "→ pond should accept"
            log(f"  [{i+1:2d}/{total}] published  {status}", "SEND")
        else:
            FAILED_COUNTER.inc()
            log(f"  [{i+1:2d}/{total}] publish FAILED", "FAIL")
        time.sleep(0.3)   # Give pond.py time to process each message

    disconnect_client(client)
    PHASE_GAUGE.set(0)

    log("-" * 60)
    log("RESULT: Published beyond capacity.")
    log("OBSERVABILITY: fishhaven_active_fishes should plateau at 10")
    log("               fishhaven_rejected_fish_total should equal ~OVERLOAD_ATTEMPTS")
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Test 3 – Broker Crash & Recovery
# ──────────────────────────────────────────────────────────────────────────────
def test_crash():
    """
    1. Connect and publish a few fish (normal operation)
    2. Stop the Docker MQTT broker (simulated crash)
    3. Attempt to keep publishing — observe failures + disconnection metrics
    4. Restart the broker — observe auto-reconnect
    5. Resume publishing — verify recovery

    Requires Docker with the mosquitto container named 'mqtt-broker'.
    If Docker is not available the test still runs but skips the container steps.
    """
    log("=" * 60)
    log("TEST 3 – BROKER CRASH & RECOVERY", "TEST")
    log("Watch:  fishhaven_mqtt_connected  /  stress_broker_up  /  stress_reconnects_total")
    log("=" * 60)

    def docker_stop():
        log("Stopping MQTT broker (docker-compose stop mosquitto)...", "CRASH")
        r = subprocess.run(
            ["docker-compose", "stop", "mosquitto"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            log("Broker stopped.", "CRASH")
            BROKER_UP_GAUGE.set(0)
            return True
        else:
            log(f"docker-compose stop failed: {r.stderr.strip()}", "WARN")
            return False

    def docker_start():
        log("Restarting MQTT broker (docker-compose start mosquitto)...", "RECOVER")
        r = subprocess.run(
            ["docker-compose", "start", "mosquitto"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            log("Broker restarted. Waiting 3s for it to become ready...", "RECOVER")
            time.sleep(3)
            BROKER_UP_GAUGE.set(1)
            return True
        else:
            log(f"docker-compose start failed: {r.stderr.strip()}", "WARN")
            return False

    # ── Phase A: Normal operation ──────────────────────────────────────────────
    PHASE_GAUGE.set(3)
    log("Phase A – Normal operation (5 messages)")

    connected_client = connect_client("stress_crash_test")
    for i in range(5):
        payload = json.dumps(make_fish(pond="CrashTestPond", group="CrashTeam"))
        result = connected_client.publish(TOPIC, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            SENT_COUNTER.inc()
            log(f"  Pre-crash message {i+1}/5 sent", "SEND")
        time.sleep(0.5)

    # ── Phase B: Simulate broker crash ────────────────────────────────────────
    log("\nPhase B – Simulating broker crash")
    docker_available = docker_stop()

    if not docker_available:
        log("Docker not available — simulating crash by disconnecting client manually", "WARN")
        connected_client.loop_stop()

    log("Attempting 5 publishes during broker outage...")
    crash_failures = 0
    for i in range(5):
        payload = json.dumps(make_fish(pond="CrashTestPond", group="CrashTeam"))
        try:
            result = connected_client.publish(TOPIC, payload, qos=1)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                crash_failures += 1
                FAILED_COUNTER.inc()
                log(f"  During-crash message {i+1}/5 FAILED (rc={result.rc}) ← expected", "WARN")
            else:
                log(f"  During-crash message {i+1}/5 sent (broker might still be draining)", "SEND")
                SENT_COUNTER.inc()
        except Exception as e:
            crash_failures += 1
            FAILED_COUNTER.inc()
            log(f"  During-crash message {i+1}/5 ERROR: {e} ← expected", "WARN")
        time.sleep(1)

    # ── Phase C: Broker restart & recovery ────────────────────────────────────
    log("\nPhase C – Restarting broker and waiting for reconnect")
    if docker_available:
        docker_start()
    else:
        log("Re-connecting client manually (simulating recovery)...", "RECOVER")
        try:
            connected_client.reconnect()
            connected_client.loop_start()
        except Exception:
            connected_client = connect_client("stress_crash_test_reconnect")
        RECONNECT_COUNTER.inc()

    log("Waiting 5s for paho auto-reconnect to complete...")
    time.sleep(5)

    log("Phase C – Sending 5 post-recovery messages")
    recovered = 0
    for i in range(5):
        payload = json.dumps(make_fish(pond="CrashTestPond", group="CrashTeam"))
        result = connected_client.publish(TOPIC, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            recovered += 1
            SENT_COUNTER.inc()
            log(f"  Post-recovery message {i+1}/5 sent ✓", "SEND")
        else:
            FAILED_COUNTER.inc()
            log(f"  Post-recovery message {i+1}/5 FAILED", "FAIL")
        time.sleep(0.5)

    disconnect_client(connected_client)
    PHASE_GAUGE.set(0)

    log("-" * 60)
    log(f"RESULT: crash_failures={crash_failures}  recovered={recovered}/5",
        "PASS" if recovered >= 4 else "FAIL")
    log("OBSERVABILITY: fishhaven_mqtt_connected dips to 0 then returns to 1")
    log("               stress_messages_failed_total spikes during outage")
    log("               stress_broker_up drops to 0 then returns to 1")
    return recovered >= 4


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Fish Haven Stress Test – Item 4: Overload & Crash Testing"
    )
    parser.add_argument(
        "--test",
        choices=["all", "flood", "overload", "crash"],
        default="all",
        help="Which test scenario to run (default: all)",
    )
    args = parser.parse_args()

    # Start Prometheus metrics server for this script
    start_http_server(STRESS_METRICS_PORT)
    log(f"Stress-test Prometheus metrics: http://localhost:{STRESS_METRICS_PORT}/metrics")
    log(f"Pond Prometheus metrics:        http://localhost:8000/metrics")
    log("")

    results = {}

    if args.test in ("all", "flood"):
        results["flood"] = test_flood()
        print()

    if args.test in ("all", "overload"):
        results["overload"] = test_overload()
        print()

    if args.test in ("all", "crash"):
        results["crash"] = test_crash()
        print()

    # Summary
    log("=" * 60)
    log("FINAL SUMMARY", "TEST")
    for name, passed in results.items():
        log(f"  {name.upper():<12} {'PASSED ✅' if passed else 'FAILED ❌'}")
    log("=" * 60)
    log("Metrics server still running — check Prometheus/Grafana dashboards now.")
    log("Press Ctrl+C when done.")

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        log("Stress test finished.")


if __name__ == "__main__":
    main()
