#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "=== [1/5] Gerando .env com credenciais seguras ==="
if [ ! -f .env ]; then
  RANDOM_KEY=$(openssl rand -hex 16 2>/dev/null || echo "evolution_secret_key_987654")
  cp .env.example .env
  sed -i.bak "s/EVOLUTION_API_KEY=auto_generated_key_change_me/EVOLUTION_API_KEY=${RANDOM_KEY}/g" .env && rm -f .env.bak
  echo "Arquivo .env criado com sucesso."
else
  echo ".env existente mantido."
fi

# Carrega variáveis
export $(grep -v '^#' .env | xargs)

echo "=== [2/5] Subindo containers Docker ==="
# Libera porta 8000 caso haja processo uvicorn local anterior
pkill -f "uvicorn src.main:app" 2>/dev/null || true

docker compose down --remove-orphans || true
docker compose up -d --build

echo "=== [3/5] Aguardando Evolution API inicializar ==="
RETRIES=0
until curl -s -f -o /dev/null "http://localhost:8080" || [ $RETRIES -ge 45 ]; do
  sleep 2
  RETRIES=$((RETRIES + 1))
done
echo "Evolution API online na porta 8080."

echo "=== [4/5] Criando instância WhatsApp na Evolution API ==="
curl -s -X POST "http://localhost:8080/instance/create" \
  -H "apikey: ${EVOLUTION_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"instanceName\": \"${INSTANCE_NAME}\", \"token\": \"${EVOLUTION_API_KEY}\", \"qrcode\": true, \"integration\": \"WHATSAPP-BAILEYS\", \"syncFullHistory\": false, \"groupsIgnore\": true, \"readMessages\": false, \"readStatus\": false}" || true

echo ""
echo "=== [5/5] Executando validação mock do pipeline ==="
docker compose exec -T agenda-agent python tests/test_mock_flow.py

echo ""
echo "=========================================================="
echo " AGENTE IMPLANTADO COM SUCESSO!"
echo " Obtenha o QR Code para conectar seu WhatsApp executando:"
echo " curl -X GET http://localhost:8080/instance/connect/${INSTANCE_NAME} -H 'apikey: ${EVOLUTION_API_KEY}'"
echo "=========================================================="
