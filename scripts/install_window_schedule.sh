#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$HOME/.agenda-agent"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
SCRIPT_PATH="${RUNTIME_DIR}/container_window.sh"
LOG_PATH="$HOME/Library/Logs/agenda-agent-window.log"

mkdir -p "$RUNTIME_DIR" "$LAUNCH_AGENTS_DIR" "$HOME/Library/Logs"

# Copia o script para fora de ~/Documents (evita bloqueio TCC "Operation not permitted" do launchd)
cp "${PROJECT_DIR}/scripts/container_window.sh" "$SCRIPT_PATH"
chmod +x "$SCRIPT_PATH"
touch "$LOG_PATH"

START_PLIST="$LAUNCH_AGENTS_DIR/com.agenda-agent.window-start.plist"
STOP_PLIST="$LAUNCH_AGENTS_DIR/com.agenda-agent.window-stop.plist"

cat > "$START_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agenda-agent.window-start</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${SCRIPT_PATH}</string>
        <string>start</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${LOG_PATH}</string>
    <key>StandardErrorPath</key>
    <string>${LOG_PATH}</string>
</dict>
</plist>
EOF

cat > "$STOP_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agenda-agent.window-stop</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${SCRIPT_PATH}</string>
        <string>stop</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>${LOG_PATH}</string>
    <key>StandardErrorPath</key>
    <string>${LOG_PATH}</string>
</dict>
</plist>
EOF

launchctl unload "$START_PLIST" 2>/dev/null || true
launchctl unload "$STOP_PLIST" 2>/dev/null || true
launchctl load "$START_PLIST"
launchctl load "$STOP_PLIST"

echo "Agendamento diário instalado com sucesso no macOS LaunchAgents:"
echo "  - Ligar containers:    todos os dias às 06:00 (com.agenda-agent.window-start)"
echo "  - Desligar containers: todos os dias às 07:00 (com.agenda-agent.window-stop)"
