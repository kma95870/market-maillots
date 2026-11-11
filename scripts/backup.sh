#!/bin/sh
# Sauvegarde PostgreSQL + MongoDB dans ./backups/<date>/
# Usage (Git Bash ou WSL) : sh scripts/backup.sh
set -e
. ./.env
STAMP=$(date +%Y%m%d-%H%M%S)
DEST="backups/$STAMP"
mkdir -p "$DEST"

# pg_dump -Fc : format "custom", compressé, restaurable table par table
docker exec maillots-postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$DEST/postgres.dump"

# mongodump --archive : toute la base catalogue dans un seul fichier compressé
docker exec maillots-mongo mongodump --quiet --username "$MONGO_ROOT_USER" --password "$MONGO_ROOT_PASSWORD" \
  --authenticationDatabase admin --db "$MONGO_DB" --archive --gzip > "$DEST/mongo.archive.gz"

ls -lh "$DEST"
echo "Sauvegarde terminée : $DEST"
