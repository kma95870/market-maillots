-- =====================================================================
-- Requêtes EXPLAIN : prouver que les index servent vraiment.
-- Lancer : docker exec -i maillots-postgres psql -U admin -d maillots < db/postgres/queries/explain.sql
--
-- EXPLAIN ANALYZE exécute la requête et affiche le "plan" choisi par PostgreSQL :
--   Seq Scan   = il lit TOUTE la table (lent quand la table grossit)
--   Index Scan / Bitmap Index Scan = il passe par un index (rapide)
-- =====================================================================

\echo '== Q1. Onglet Commandes : les 50 commandes les plus récentes (idx_orders_created_at)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT order_ref, customer_id, total_cents, status, created_at
FROM orders.orders ORDER BY created_at DESC LIMIT 50;

\echo '== Q2. Historique d''un client (idx_orders_customer)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT * FROM orders.orders
WHERE customer_id = (SELECT customer_id FROM orders.customers LIMIT 1);

\echo '== Q3. Onglet Catalogue : stock d''un maillot, toutes tailles et entrepôts (idx_stock_product)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT sku, warehouse_id, available FROM inventory.stock
WHERE product_id = 'PSG-2526-HOME-REP';

\echo '== Q4. Onglet Logistique : ruptures imminentes à Lille (index partiel idx_stock_low)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT sku, available FROM inventory.stock
WHERE warehouse_id = 4 AND on_hand - reserved <= 10;

\echo '== Q5a. SANS index : qui a acheté le PSG domicile en M ? (Seq Scan attendu)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT order_id, quantity FROM orders.order_lines WHERE sku = 'PSG-2526-HOME-REP-M';

\echo '== Q5b. Même requête AVEC un index temporaire'
BEGIN;
CREATE INDEX idx_tmp_sku ON orders.order_lines (sku);
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT order_id, quantity FROM orders.order_lines WHERE sku = 'PSG-2526-HOME-REP-M';
ROLLBACK;  -- on annule : l'index n'est pas conservé
