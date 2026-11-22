#!/bin/sh
# Wait until PostgreSQL accepts connections, then start the app.
maxcounter=100

host="${1:-${DB_HOST:-dbpolitepol}}"
port="${2:-${DB_PORT:-5432}}"

counter=1
while ! python -c "import socket, sys; socket.create_connection((sys.argv[1], int(sys.argv[2])), 2)" "$host" "$port" > /dev/null 2>&1; do
    sleep 1
    counter=`expr $counter + 1`
    if [ $counter -gt $maxcounter ]; then
        >&2 echo "We have been waiting for PostgreSQL too long already; failing."
        exit 1
    fi;
done

exec /bin/bash ./frontend/start.sh
