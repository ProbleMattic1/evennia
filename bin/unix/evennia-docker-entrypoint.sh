#!/bin/sh
# Auto-initialize game directory if missing, then run the given command.
# Used when running docker-compose from the Evennia repo root.

cd /usr/src/game

# If no game exists, create one and run migrations
if [ ! -f server/conf/settings.py ]; then
    if [ ! -d game ]; then
        echo "No game directory found. Creating new game 'game'..."
        evennia --init game
    fi
    cd game
    echo "Running database migrations..."
    evennia migrate --noinput
fi

# Remove leftover .pid files
rm -f server/*.pid 2>/dev/null || true

# Run the given command (default: evennia start -l)
if [ $# -gt 0 ]; then
    echo "Docker starting with argument '$*' ..."
    exec "$@"
else
    echo "Docker starting with argument 'evennia start -l' ..."
    exec evennia start -l
fi
