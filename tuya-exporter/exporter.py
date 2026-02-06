import time, os
from flask import Flask, Response
from prometheus_client import (
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST
)

from tuya_iot import TuyaOpenAPI, TUYA_LOGGER

# ------------------------
# Tuya Configuration
# ------------------------
TUYA_ENDPOINT = os.getenv("TUYA_ENDPOINT")
ACCESS_ID = os.getenv("TUYA_ACCESS_ID")
ACCESS_SECRET = os.getenv("TUYA_ACCESS_SECRET")

DEVICES = {
    "plug_1": {
        "device_id": "DEVICE_ID_1",
        "name": "standalone_plug"
    },
    "strip_1": {
        "device_id": "DEVICE_ID_2",
        "name": "power_strip"
    }
}

POLL_INTERVAL = 15  # seconds

# ------------------------
# Prometheus Metrics
# ------------------------
power_watts = Gauge(
    "tuya_power_watts",
    "Instantaneous power usage",
    ["device", "channel"]
)

energy_kwh = Gauge(
    "tuya_energy_kwh_total",
    "Total energy consumption",
    ["device", "channel"]
)

voltage_volts = Gauge(
    "tuya_voltage_volts",
    "Voltage",
    ["device", "channel"]
)

current_amps = Gauge(
    "tuya_current_amps",
    "Current",
    ["device", "channel"]
)

# ------------------------
# Tuya Client
# ------------------------
openapi = TuyaOpenAPI(TUYA_ENDPOINT, ACCESS_ID, ACCESS_SECRET)
openapi.connect()

app = Flask(__name__)

# ------------------------
# Helpers
# ------------------------
def parse_status(status_list):
    """
    Convert Tuya status list to dict
    """
    return {item["code"]: item["value"] for item in status_list}


def update_device_metrics(device_key, device):
    resp = openapi.get(f"/v1.0/devices/{device['device_id']}/status")
    if not resp.get("success"):
        print(f"Failed to fetch {device_key}")
        return

    data = parse_status(resp["result"])

    # Common DP codes (Tuya standard)
    power = data.get("cur_power")      # W * 10
    voltage = data.get("cur_voltage")  # V * 10
    current = data.get("cur_current")  # mA
    energy = data.get("add_ele")       # kWh * 100

    channel = "main"

    if power is not None:
        power_watts.labels(device=device["name"], channel=channel).set(power / 10)

    if voltage is not None:
        voltage_volts.labels(device=device["name"], channel=channel).set(voltage / 10)

    if current is not None:
        current_amps.labels(device=device["name"], channel=channel).set(current / 1000)

    if energy is not None:
        energy_kwh.labels(device=device["name"], channel=channel).set(energy / 100)


def poll_loop():
    while True:
        for key, device in DEVICES.items():
            update_device_metrics(key, device)
        time.sleep(POLL_INTERVAL)

# ------------------------
# HTTP Endpoint
# ------------------------
@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    import threading
    t = threading.Thread(target=poll_loop)
    t.daemon = True
    t.start()

    app.run(host="0.0.0.0", port=9109)
