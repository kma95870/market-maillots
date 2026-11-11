-- =====================================================================
-- 01 - Un schéma par microservice, possédé par le rôle de ce service.
-- Règle : un service ne peut PAS lire les tables d'un autre service.
-- S'il a besoin d'une info, il appelle l'API de l'autre service.
-- =====================================================================

CREATE SCHEMA orders    AUTHORIZATION orders_svc;     -- clients, commandes, lignes
CREATE SCHEMA inventory AUTHORIZATION inventory_svc;  -- entrepôts, stock, réservations
CREATE SCHEMA payments  AUTHORIZATION payments_svc;   -- paiements
CREATE SCHEMA auth      AUTHORIZATION auth_svc;       -- utilisateurs et rôles applicatifs

-- Chaque rôle ne cherche les tables que dans son propre schéma.
ALTER ROLE orders_svc    SET search_path = orders;
ALTER ROLE inventory_svc SET search_path = inventory;
ALTER ROLE payments_svc  SET search_path = payments;
ALTER ROLE auth_svc      SET search_path = auth;

-- Extension utile pour générer des identifiants UUID
CREATE EXTENSION IF NOT EXISTS pgcrypto;
