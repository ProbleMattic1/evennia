#!/bin/sh
# Run after evennia-docker-entrypoint.sh (migrate, cwd already /usr/src/game/game via that script).
#
# In Docker, `evennia start -l` sometimes leaves only the Portal listening; the game Server
# never gets an AMP SSTART, so /ui/* returns Twisted 501 until a manual `evennia start`.
# Background nudge: once port 4001 accepts connections, call `evennia start` (idempotent)
# until server.pid exists and the process is alive.

cd /usr/src/game/game || exit 1

(
  i=0
  while [ "$i" -lt 90 ]; do
    i=$((i + 1))
    sleep 2
    if [ -s server/server.pid ] && kill -0 "$(cat server/server.pid)" 2>/dev/null; then
      exit 0
    fi
    if python3 -c "import socket; s=socket.create_connection(('127.0.0.1',4001),2); s.close()" 2>/dev/null; then
      evennia start >>/tmp/evennia_nudge.log 2>&1 || true
    fi
  done
) &

exec evennia start -l
