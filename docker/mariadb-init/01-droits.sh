#!/bin/bash
# L'appli crée une base par filiale : son compte peut créer et gérer les bases « sdl_* » uniquement.
set -e
mariadb -uroot -p"${MARIADB_ROOT_PASSWORD}" <<SQL
GRANT ALL PRIVILEGES ON \`sdl\\_%\`.* TO '${MARIADB_USER}'@'%';
FLUSH PRIVILEGES;
SQL
