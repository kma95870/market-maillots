#!/bin/sh
# Crée un rôle (compte de connexion) par microservice.
# Les mots de passe viennent des variables d'environnement (.env),
# c'est pour ça que ce fichier est un script shell et pas du SQL pur.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE ROLE orders_svc    LOGIN PASSWORD '${ORDERS_DB_PASSWORD}';
  CREATE ROLE inventory_svc LOGIN PASSWORD '${INVENTORY_DB_PASSWORD}';
  CREATE ROLE payments_svc  LOGIN PASSWORD '${PAYMENTS_DB_PASSWORD}';
  CREATE ROLE auth_svc      LOGIN PASSWORD '${AUTH_DB_PASSWORD}';

  -- Personne ne peut créer d'objets dans le schéma "public" par défaut.
  REVOKE CREATE ON SCHEMA public FROM PUBLIC;
  REVOKE ALL ON DATABASE ${POSTGRES_DB} FROM PUBLIC;
  GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO orders_svc, inventory_svc, payments_svc, auth_svc;
EOSQL
