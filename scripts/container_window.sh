#!/bin/bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export DOCKER_HOST="unix://$HOME/.docker/run/docker.sock"
unset PS1 PROMPT RPROMPT FPATH

CONTAINERS=(evolution_postgres evolution_redis evolution_api agenda_agent)

ACTION="${1:-}"
FORCE="${2:-}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

ensure_docker_running() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  log "Docker daemon parado. Iniciando Docker Desktop em background..."
  open -g -a Docker || true

  local retries=0
  until docker info >/dev/null 2>&1 || [ $retries -ge 90 ]; do
    sleep 2
    retries=$((retries + 1))
  done

  if ! docker info >/dev/null 2>&1; then
    log "ERRO: Docker daemon não respondeu a tempo."
    return 1
  fi
  log "Docker daemon online."
}

start_stack() {
  ensure_docker_running

  # Inicia os containers na ordem de dependência (usando docker start direto para não depender de ~/Documents no TCC)
  docker start evolution_postgres evolution_redis >/dev/null
  sleep 3
  docker start evolution_api >/dev/null
  sleep 2
  docker start agenda_agent >/dev/null
}

case "$ACTION" in
  start)
    CURRENT_HOUR=$(date +%H)
    CURRENT_MIN=$(date +%M)

    if [ "$FORCE" != "--force" ] && [ "$CURRENT_HOUR" != "06" ]; then
      log "Fora da janela das 06:00-07:00 (hora atual: ${CURRENT_HOUR}:${CURRENT_MIN}). Garantindo containers parados."
      if docker info >/dev/null 2>&1; then
        docker stop "${CONTAINERS[@]}" >/dev/null 2>&1 || true
      fi
      exit 0
    fi

    log "=== Iniciando containers da janela diária (06:00 - 07:00) ==="
    start_stack

    # Caso o Mac tenha acordado após 06:30 (ou com --force), dispara o briefing
    CURRENT_HOUR=$(date +%H)
    CURRENT_MIN=$(date +%M)
    if [ "$FORCE" = "--force" ] || { [ "$CURRENT_HOUR" = "06" ] && [ "$CURRENT_MIN" -ge 30 ]; }; then
      log "Disparo imediato solicitado/após 06:30 (${CURRENT_HOUR}:${CURRENT_MIN}). Aguardando serviços ficarem prontos..."
      sleep 15
      curl -s -X POST "http://127.0.0.1:8000/api/v1/trigger-briefing" 2>&1 || true
      echo ""
    fi

    log "Containers ativos até as 07:00."
    ;;

  stop)
    log "=== Encerrando containers (fim da janela às 07:00) ==="
    if docker info >/dev/null 2>&1; then
      docker stop "${CONTAINERS[@]}" >/dev/null 2>&1 || true
      log "Todos os containers do agenda-agent foram parados com sucesso."
    else
      log "Docker daemon já está parado. Nada a fazer."
    fi
    ;;

  ensure-docker)
    ensure_docker_running
    ;;

  *)
    echo "Uso: $0 {start [--force]|stop|ensure-docker}"
    exit 1
    ;;
esac
