import os
import base64
import json
import urllib.request

api_key = os.environ.get("EVOLUTION_API_KEY", "")
headers = {"apikey": api_key, "Content-Type": "application/json"}

# Check current state
try:
    req = urllib.request.Request("http://localhost:8080/instance/connectionState/agenda-notifier", headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        state_data = json.loads(resp.read().decode("utf-8"))
    state = state_data.get("instance", {}).get("state")
    print("CURRENT_STATE:", state)
except Exception as e:
    state = None
    print("STATE_CHECK_ERR:", e)

if state != "open":
    req = urllib.request.Request("http://localhost:8080/instance/connect/agenda-notifier", headers=headers)
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    b64 = data.get("base64", "") or data.get("qrcode", {}).get("base64", "")
    if b64 and "," in b64:
        png_bytes = base64.b64decode(b64.split(",", 1)[1])
        qr_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "qrcode.png"))
        with open(qr_path, "wb") as f:
            f.write(png_bytes)
        print("QR_UPDATED_OK")
    else:
        print("CONNECT_DATA:", json.dumps(data))
