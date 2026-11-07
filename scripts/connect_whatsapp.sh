#!/bin/bash
set -e
cd "$(dirname "$0")/.."

export $(grep -v '^#' .env | xargs)

echo "=== [1/3] Recriando containers com versão WhatsApp Web ${CONFIG_SESSION_PHONE_VERSION} ==="
docker compose up -d --build --force-recreate evolution-api agenda-agent

echo "=== [2/3] Aguardando Evolution API online ==="
RETRIES=0
until curl -s -f -o /dev/null "http://localhost:8080" || [ $RETRIES -ge 30 ]; do
  sleep 1
  RETRIES=$((RETRIES + 1))
done

echo "=== [3/3] Criando instância limpa com versão ${CONFIG_SESSION_PHONE_VERSION} ==="
curl -s -X DELETE "http://localhost:8080/instance/logout/${INSTANCE_NAME}" \
  -H "apikey: ${EVOLUTION_API_KEY}" >/dev/null 2>&1 || true
curl -s -X DELETE "http://localhost:8080/instance/delete/${INSTANCE_NAME}" \
  -H "apikey: ${EVOLUTION_API_KEY}" >/dev/null 2>&1 || true

sleep 1

CREATE_RESP=$(curl -s -X POST "http://localhost:8080/instance/create" \
  -H "apikey: ${EVOLUTION_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"instanceName\": \"${INSTANCE_NAME}\", \"token\": \"${EVOLUTION_API_KEY}\", \"qrcode\": true, \"integration\": \"WHATSAPP-BAILEYS\", \"syncFullHistory\": false, \"groupsIgnore\": true, \"readMessages\": false, \"readStatus\": false}")

echo "$CREATE_RESP" > /tmp/evo_create.json

python3 - << 'EOF'
import json, base64, urllib.request, time

with open("/tmp/evo_create.json") as f:
    data = json.load(f)

b64 = data.get("qrcode", {}).get("base64", "") or data.get("base64", "")

if not b64:
    import os
    url = f"http://localhost:8080/instance/connect/{os.environ.get('INSTANCE_NAME', 'agenda-notifier')}"
    headers = {"apikey": os.environ.get("EVOLUTION_API_KEY", "")}
    for _ in range(10):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                c_data = json.loads(resp.read().decode("utf-8"))
            b64 = c_data.get("base64", "") or c_data.get("qrcode", {}).get("base64", "")
            if b64:
                break
        except Exception:
            pass
        time.sleep(1)

if b64 and "," in b64:
    png_bytes = base64.b64decode(b64.split(",", 1)[1])
    with open("qrcode.png", "wb") as out:
        out.write(png_bytes)
    print("QR_CODE_SAVED=true")
else:
    print("QR_CODE_SAVED=false")
EOF

echo ""
echo "=== Validando leitura real do Google Calendar ==="
docker compose exec -T agenda-agent python tests/test_mock_flow.py
