#!/bin/sh
# Restaure une sauvegarde créée par backup.sh
# Usage : sh scripts/restore.sh backups/20261111-103000
set -e
. ./.env
SRC="$1"
[ -d "$SRC" ] || { echo "Dossier introuvable : $SRC"; exit 1; }

# --clean --if-exists : supprime les objets avant de les recréer
docker exec -i maillots-postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --clean --if-exists --single-transaction \
  < "$SRC/postgres.dump"

# --drop : vide chaque collection avant de la restaurer
docker exec -i maillots-mongo mongorestore --quiet --username "$MONGO_ROOT_USER" --password "$MONGO_ROOT_PASSWORD" \
  --authenticationDatabase admin --nsInclude "$MONGO_DB.*" --drop --archive --gzip < "$SRC/mongo.archive.gz"

echo "Restauration terminée depuis $SRC"
