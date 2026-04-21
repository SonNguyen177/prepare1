#!/bin/bash
# Launch all three services, wait for them, then open browser

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE_DIR="/usr/local/Cellar/node@20/20.20.2/bin"

# Configurable ports
ENGINE_PORT=8000
ADMIN_PORT=3001
CLIENT_PORT=3000

# Kill any existing processes on our ports
lsof -ti :${ENGINE_PORT} | xargs kill -9 2>/dev/null
lsof -ti :${ADMIN_PORT} | xargs kill -9 2>/dev/null
lsof -ti :${CLIENT_PORT} | xargs kill -9 2>/dev/null
sleep 1

echo "Starting services..."

# Terminal 1: Engine
osascript <<EOF
tell application "Terminal"
  do script "cd '${PROJECT_DIR}/exchange/engine' && echo '=== Exchange Engine (:${ENGINE_PORT}) ===' && uv run uvicorn src.main:app --host 0.0.0.0 --port ${ENGINE_PORT} --reload"
end tell
EOF

# Terminal 2: Admin UI
osascript <<EOF
tell application "Terminal"
  do script "export PATH=${NODE_DIR}:\$PATH && cd '${PROJECT_DIR}/exchange/admin' && echo '=== Admin UI (:${ADMIN_PORT}) ===' && npm run dev -- --port ${ADMIN_PORT}"
end tell
EOF

# Terminal 3: Client UI
osascript <<EOF
tell application "Terminal"
  do script "export PATH=${NODE_DIR}:\$PATH && cd '${PROJECT_DIR}/client' && echo '=== Client UI (:${CLIENT_PORT}) ===' && npm run dev -- --port ${CLIENT_PORT}"
end tell
EOF

# Wait for services to be ready
wait_for_port() {
  local port=$1
  local name=$2
  local max_wait=30
  local waited=0

  printf "  Waiting for %s (:%d)..." "$name" "$port"
  while ! lsof -ti :${port} >/dev/null 2>&1; do
    sleep 1
    waited=$((waited + 1))
    if [ $waited -ge $max_wait ]; then
      echo " TIMEOUT"
      return 1
    fi
  done
  echo " OK"
  return 0
}

echo ""
wait_for_port $ENGINE_PORT "Engine"
engine_ok=$?

wait_for_port $ADMIN_PORT "Admin"
admin_ok=$?

wait_for_port $CLIENT_PORT "Client"
client_ok=$?

echo ""

# Open browser if services are up
if [ $admin_ok -eq 0 ] && [ $client_ok -eq 0 ]; then
  echo "All services running — opening browser..."
  open "http://localhost:${ADMIN_PORT}"
  open "http://localhost:${CLIENT_PORT}"
  echo ""
  echo "  Admin   → http://localhost:${ADMIN_PORT}"
  echo "  Client  → http://localhost:${CLIENT_PORT}"
  echo "  Engine  → http://localhost:${ENGINE_PORT}"
else
  echo "Some services failed to start. Check Terminal windows for errors."
  [ $engine_ok -ne 0 ] && echo "  ✗ Engine (:${ENGINE_PORT})"
  [ $admin_ok -ne 0 ]  && echo "  ✗ Admin  (:${ADMIN_PORT})"
  [ $client_ok -ne 0 ] && echo "  ✗ Client (:${CLIENT_PORT})"
fi
