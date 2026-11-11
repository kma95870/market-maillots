-- =====================================================================
-- 02 - Tables de chaque service.
-- Conventions :
--   * les prix et montants sont en CENTIMES (entiers) : pas d'erreur d'arrondi
--   * les dates sont en timestamptz (avec fuseau horaire)
--   * product_id et sku sont des liens VERS D'AUTRES SERVICES :
--     pas de clé étrangère possible, c'est le code qui les vérifie.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Service INVENTORY (stock)
-- ---------------------------------------------------------------------
SET ROLE inventory_svc;

CREATE TABLE inventory.warehouses (
    warehouse_id   SMALLINT     PRIMARY KEY,
    code           TEXT         NOT NULL UNIQUE,          -- ex. 'PAR-01'
    city           TEXT         NOT NULL,
    capacity_units INTEGER      NOT NULL CHECK (capacity_units > 0),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Une ligne = un maillot dans UNE taille, dans UN entrepôt.
-- sku = référence unique "produit + taille", ex. 'PSG-2526-HOME-REP-M'
CREATE TABLE inventory.stock (
    sku            TEXT         NOT NULL,
    warehouse_id   SMALLINT     NOT NULL REFERENCES inventory.warehouses(warehouse_id),
    product_id     TEXT         NOT NULL,                 -- lien vers le catalogue (MongoDB)
    size           TEXT         NOT NULL CHECK (size IN ('XS','S','M','L','XL','XXL','4A','6A','8A','10A','12A','14A')),
    on_hand        INTEGER      NOT NULL CHECK (on_hand >= 0),   -- physiquement en rayon
    reserved       INTEGER      NOT NULL DEFAULT 0 CHECK (reserved >= 0), -- bloqué par des commandes en cours
    reorder_point  INTEGER      NOT NULL DEFAULT 10,      -- seuil d'alerte "bientôt en rupture"
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    available      INTEGER      GENERATED ALWAYS AS (on_hand - reserved) STORED,
    PRIMARY KEY (sku, warehouse_id),
    -- Garde-fou ultime : on ne peut jamais réserver plus que ce qu'on a.
    CONSTRAINT stock_reserved_le_on_hand CHECK (reserved <= on_hand)
);
CREATE INDEX idx_stock_product   ON inventory.stock (product_id);
CREATE INDEX idx_stock_low       ON inventory.stock (warehouse_id) WHERE on_hand - reserved <= 10;

-- Une réservation = un morceau de stock bloqué pour une commande (pattern Saga).
CREATE TABLE inventory.reservations (
    reservation_id UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id       UUID         NOT NULL,                 -- lien vers le service orders
    sku            TEXT         NOT NULL,
    warehouse_id   SMALLINT     NOT NULL,
    quantity       INTEGER      NOT NULL CHECK (quantity > 0),
    status         TEXT         NOT NULL DEFAULT 'HELD' CHECK (status IN ('HELD','CONFIRMED','RELEASED')),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    FOREIGN KEY (sku, warehouse_id) REFERENCES inventory.stock(sku, warehouse_id),
    UNIQUE (order_id, sku)                                -- idempotence : une seule résa par commande et par sku
);
CREATE INDEX idx_reservations_order ON inventory.reservations (order_id);

RESET ROLE;

-- ---------------------------------------------------------------------
-- Service ORDERS (clients et commandes)
-- ---------------------------------------------------------------------
SET ROLE orders_svc;

CREATE TABLE orders.customers (
    customer_id    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email          TEXT         NOT NULL UNIQUE,
    first_name     TEXT         NOT NULL,
    last_name      TEXT         NOT NULL,
    country        CHAR(2)      NOT NULL,                 -- code ISO, ex. 'FR'
    city           TEXT,
    favorite_club  TEXT,                                  -- utile pour le marketing
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE orders.orders (
    order_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    order_ref        TEXT        NOT NULL UNIQUE,         -- référence lisible, ex. 'MLT-2026-000123'
    customer_id      UUID        NOT NULL REFERENCES orders.customers(customer_id),
    status           TEXT        NOT NULL DEFAULT 'PENDING'
                     CHECK (status IN ('PENDING','STOCK_RESERVED','PAID','SHIPPED','DELIVERED','CANCELLED','RETURNED')),
    total_cents      INTEGER     NOT NULL CHECK (total_cents >= 0),
    currency         CHAR(3)     NOT NULL DEFAULT 'EUR',
    channel          TEXT        NOT NULL DEFAULT 'web' CHECK (channel IN ('web','app')),
    idempotency_key  TEXT        UNIQUE,                  -- évite les commandes en double si le client clique 2 fois
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_orders_customer   ON orders.orders (customer_id);
CREATE INDEX idx_orders_created_at ON orders.orders (created_at DESC);
CREATE INDEX idx_orders_status     ON orders.orders (status) WHERE status IN ('PENDING','STOCK_RESERVED');

-- Une ligne = un maillot (dans une taille) dans une commande.
-- Le flocage (nom + numéro imprimés) est une OPTION de la ligne :
-- il ne consomme pas de stock, c'est une opération faite à l'expédition.
CREATE TABLE orders.order_lines (
    order_id             UUID     NOT NULL REFERENCES orders.orders(order_id) ON DELETE CASCADE,
    line_no              SMALLINT NOT NULL,
    product_id           TEXT     NOT NULL,               -- lien vers le catalogue (MongoDB)
    sku                  TEXT     NOT NULL,               -- lien vers le stock
    size                 TEXT     NOT NULL,
    quantity             INTEGER  NOT NULL CHECK (quantity BETWEEN 1 AND 10),
    unit_price_cents     INTEGER  NOT NULL CHECK (unit_price_cents >= 0), -- prix figé au moment de l'achat
    flocking_name        TEXT,
    flocking_number      SMALLINT CHECK (flocking_number BETWEEN 0 AND 99),
    flocking_price_cents INTEGER  NOT NULL DEFAULT 0 CHECK (flocking_price_cents >= 0),
    PRIMARY KEY (order_id, line_no),
    -- Flocage : soit nom ET numéro, soit aucun des deux.
    CONSTRAINT flocking_complete CHECK ((flocking_name IS NULL) = (flocking_number IS NULL))
);
CREATE INDEX idx_order_lines_product ON orders.order_lines (product_id);

RESET ROLE;

-- ---------------------------------------------------------------------
-- Service PAYMENTS
-- ---------------------------------------------------------------------
SET ROLE payments_svc;

CREATE TABLE payments.payments (
    payment_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id         UUID        NOT NULL,                -- lien vers le service orders
    amount_cents     INTEGER     NOT NULL CHECK (amount_cents >= 0),
    currency         CHAR(3)     NOT NULL DEFAULT 'EUR',
    method           TEXT        NOT NULL CHECK (method IN ('card','paypal','apple_pay')),
    status           TEXT        NOT NULL CHECK (status IN ('AUTHORIZED','CAPTURED','REFUSED','REFUNDED')),
    refusal_reason   TEXT,
    fraud_score      NUMERIC(4,3) CHECK (fraud_score BETWEEN 0 AND 1),
    idempotency_key  TEXT        UNIQUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_payments_order      ON payments.payments (order_id);
CREATE INDEX idx_payments_created_at ON payments.payments (created_at DESC);

RESET ROLE;

-- ---------------------------------------------------------------------
-- Service AUTH (rôles APPLICATIFS, à ne pas confondre avec les rôles PostgreSQL)
-- ---------------------------------------------------------------------
SET ROLE auth_svc;

CREATE TABLE auth.roles (
    role_name    TEXT PRIMARY KEY,
    description  TEXT NOT NULL
);

CREATE TABLE auth.users (
    user_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    username       TEXT        NOT NULL UNIQUE,
    password_hash  TEXT        NOT NULL,                  -- haché avec bcrypt, jamais en clair
    is_service     BOOLEAN     NOT NULL DEFAULT false,    -- compte technique d'un service
    is_active      BOOLEAN     NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE auth.user_roles (
    user_id    UUID NOT NULL REFERENCES auth.users(user_id) ON DELETE CASCADE,
    role_name  TEXT NOT NULL REFERENCES auth.roles(role_name),
    PRIMARY KEY (user_id, role_name)
);

INSERT INTO auth.roles (role_name, description) VALUES
  ('admin',           'Responsable plateforme : tout lire, tout écrire, gérer les utilisateurs'),
  ('catalog_manager', 'Équipe catalogue : produits et prix'),
  ('analyst',         'BI et marketing : lecture seule'),
  ('logistics',       'Logistique : stocks et entrepôts'),
  ('service_account', 'Compte technique pour les appels entre services');

RESET ROLE;
