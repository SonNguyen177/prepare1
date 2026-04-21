#!/bin/bash
# Stop all exchange services

ENGINE_PORT=8000
FIX_PORT=9876
ADMIN_PORT=3001
CLIENT_PORT=3000

echo "Stopping services..."

for entry in "Engine:${ENGINE_PORT}" "FIX:${FIX_PORT}" "Admin:${ADMIN_PORT}" "Client:${CLIENT_PORT}"; do
  name="${entry%%:*}"
  port="${entry##*:}"
  PIDS=$(lsof -ti :${port} 2>/dev/null)
  if [ -n "$PIDS" ]; then
    echo "$PIDS" | xargs kill -9 2>/dev/null
    printf "  %-8s (:%s) stopped\n" "$name" "$port"
  else
    printf "  %-8s (:%s) not running\n" "$name" "$port"
  fi
done

echo "Done."
