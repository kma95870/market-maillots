-- =====================================================================
-- 02 - Tables de chaque service.
-- Conventions :
--   * noms de colonnes en français, sans accent (snake_case)
--   * les prix et montants sont en CENTIMES (entiers) : pas d'erreur d'arrondi
--   * une seule devise : l'euro (pas de colonne devise)
--   * les dates sont en timestamptz (avec fuseau horaire)
--   * id_produit et sku sont des liens VERS D'AUTRES SERVICES :
--     pas de clé étrangère possible, c'est le code qui les vérifie.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Service INVENTORY (stock)
-- ---------------------------------------------------------------------
SET ROLE inventory_svc;

CREATE TABLE inventory.warehouses (
    id_entrepot   SMALLINT  PRIMARY KEY,
    ville         TEXT      NOT NULL,
    capacite      INTEGER   NOT NULL CHECK (capacite > 0)      -- nombre maximum de maillots
);

-- Une ligne = un maillot dans UNE taille, dans UN entrepôt.
-- sku = référence unique "produit + taille", ex. 'PSG-2526-HOME-REP-M'
CREATE TABLE inventory.stock (
    sku                  TEXT         NOT NULL,
    id_entrepot          SMALLINT     NOT NULL REFERENCES inventory.warehouses(id_entrepot),
    id_produit           TEXT         NOT NULL,                  -- lien vers le catalogue (MongoDB)
    taille               TEXT         NOT NULL CHECK (taille IN ('XS','S','M','L','XL','XXL','4A','6A','8A','10A','12A','14A')),
    quantite_physique    INTEGER      NOT NULL CHECK (quantite_physique >= 0),       -- en rayon
    quantite_reservee    INTEGER      NOT NULL DEFAULT 0 CHECK (quantite_reservee >= 0), -- bloquée par des commandes en cours
    quantite_disponible  INTEGER      GENERATED ALWAYS AS (quantite_physique - quantite_reservee) STORED,
    modifie_le           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (sku, id_entrepot),
    -- Garde-fou ultime : on ne peut jamais réserver plus que ce qu'on a.
    CONSTRAINT stock_reserve_inferieure_physique CHECK (quantite_reservee <= quantite_physique)
);
CREATE INDEX idx_stock_produit ON inventory.stock (id_produit);
-- Seuil d'alerte "bientôt en rupture" fixé à 10 pour tous les maillots
CREATE INDEX idx_stock_bas     ON inventory.stock (id_entrepot) WHERE quantite_physique - quantite_reservee <= 10;

-- Une réservation = un morceau de stock bloqué pour une commande (pattern Saga).
CREATE TABLE inventory.reservations (
    id_reservation  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    id_commande     UUID         NOT NULL,                       -- lien vers le service orders
    sku             TEXT         NOT NULL,
    id_entrepot     SMALLINT     NOT NULL,
    quantite        INTEGER      NOT NULL CHECK (quantite > 0),
    statut          TEXT         NOT NULL DEFAULT 'HELD' CHECK (statut IN ('HELD','CONFIRMED','RELEASED')),
    cree_le         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    modifie_le      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    FOREIGN KEY (sku, id_entrepot) REFERENCES inventory.stock(sku, id_entrepot),
    UNIQUE (id_commande, sku)                                    -- idempotence : une seule résa par commande et par sku
);
CREATE INDEX idx_reservations_commande ON inventory.reservations (id_commande);

RESET ROLE;

-- ---------------------------------------------------------------------
-- Service ORDERS (clients et commandes)
-- ---------------------------------------------------------------------
SET ROLE orders_svc;

CREATE TABLE orders.customers (
    id_client      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email          TEXT         NOT NULL UNIQUE,
    prenom         TEXT         NOT NULL,
    nom            TEXT         NOT NULL,
    pays           CHAR(2)      NOT NULL,                        -- code ISO, ex. 'FR'
    ville          TEXT,
    club_prefere   TEXT,                                         -- utile pour le marketing
    cree_le        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE orders.orders (
    id_commande             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    reference               TEXT         NOT NULL UNIQUE,        -- lisible, ex. 'MLT-2026-000123'
    id_client               UUID         NOT NULL REFERENCES orders.customers(id_client),
    statut                  TEXT         NOT NULL DEFAULT 'PENDING'
                            CHECK (statut IN ('PENDING','STOCK_RESERVED','PAID','SHIPPED','DELIVERED','CANCELLED','RETURNED')),
    montant_total_centimes  INTEGER      NOT NULL CHECK (montant_total_centimes >= 0),
    cle_idempotence         TEXT         UNIQUE,                 -- évite les commandes en double si le client clique 2 fois
    cree_le                 TIMESTAMPTZ  NOT NULL DEFAULT now(),
    modifie_le              TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_commandes_client  ON orders.orders (id_client);
CREATE INDEX idx_commandes_cree_le ON orders.orders (cree_le DESC);
CREATE INDEX idx_commandes_statut  ON orders.orders (statut) WHERE statut IN ('PENDING','STOCK_RESERVED');

-- Une ligne = un maillot (dans une taille) dans une commande.
-- Le flocage (nom + numéro imprimés) est une OPTION de la ligne :
-- il ne consomme pas de stock, c'est une opération faite à l'expédition.
CREATE TABLE orders.order_lines (
    id_commande             UUID      NOT NULL REFERENCES orders.orders(id_commande) ON DELETE CASCADE,
    num_ligne               SMALLINT  NOT NULL,
    id_produit              TEXT      NOT NULL,                  -- lien vers le catalogue (MongoDB)
    sku                     TEXT      NOT NULL,                  -- lien vers le stock
    taille                  TEXT      NOT NULL,
    quantite                INTEGER   NOT NULL CHECK (quantite BETWEEN 1 AND 10),
    prix_unitaire_centimes  INTEGER   NOT NULL CHECK (prix_unitaire_centimes >= 0), -- figé au moment de l'achat
    flocage_nom             TEXT,
    flocage_numero          SMALLINT  CHECK (flocage_numero BETWEEN 0 AND 99),
    flocage_prix_centimes   INTEGER   NOT NULL DEFAULT 0 CHECK (flocage_prix_centimes >= 0),
    PRIMARY KEY (id_commande, num_ligne),
    -- Flocage : soit nom ET numéro, soit aucun des deux.
    CONSTRAINT flocage_complet CHECK ((flocage_nom IS NULL) = (flocage_numero IS NULL))
);
CREATE INDEX idx_lignes_produit ON orders.order_lines (id_produit);

RESET ROLE;

-- ---------------------------------------------------------------------
-- Service PAYMENTS
-- ---------------------------------------------------------------------
SET ROLE payments_svc;

CREATE TABLE payments.payments (
    id_paiement      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    id_commande      UUID         NOT NULL,                      -- lien vers le service orders
    montant_centimes INTEGER      NOT NULL CHECK (montant_centimes >= 0),
    moyen            TEXT         NOT NULL CHECK (moyen IN ('card','paypal','apple_pay')),
    statut           TEXT         NOT NULL CHECK (statut IN ('AUTHORIZED','CAPTURED','REFUSED','REFUNDED')),
    cle_idempotence  TEXT         UNIQUE,
    cree_le          TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_paiements_commande ON payments.payments (id_commande);
CREATE INDEX idx_paiements_cree_le  ON payments.payments (cree_le DESC);

RESET ROLE;

-- ---------------------------------------------------------------------
-- Service AUTH (rôles APPLICATIFS, à ne pas confondre avec les rôles PostgreSQL)
-- ---------------------------------------------------------------------
SET ROLE auth_svc;

CREATE TABLE auth.users (
    id                 SERIAL       PRIMARY KEY,
    email              TEXT         NOT NULL UNIQUE,             -- sert d'identifiant de connexion
    mot_de_passe_hash  TEXT         NOT NULL,                    -- haché avec bcrypt, jamais en clair
    actif              BOOLEAN      NOT NULL DEFAULT true,
    cree_le            TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE auth.roles (
    id           SERIAL  PRIMARY KEY,
    nom          TEXT    NOT NULL UNIQUE,
    description  TEXT
);

CREATE TABLE auth.user_roles (
    id_utilisateur  INTEGER  NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    id_role         INTEGER  NOT NULL REFERENCES auth.roles(id),
    PRIMARY KEY (id_utilisateur, id_role)
);

INSERT INTO auth.roles (nom, description) VALUES
  ('admin',           'Responsable plateforme : tout lire, tout écrire, gérer les utilisateurs'),
  ('catalog_manager', 'Équipe catalogue : produits et prix'),
  ('analyst',         'BI et marketing : lecture seule'),
  ('logistics',       'Logistique : stocks et entrepôts'),
  ('service_account', 'Compte technique pour les appels entre services');

RESET ROLE;
