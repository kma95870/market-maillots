-- =====================================================================
-- Requêtes EXPLAIN : prouver que les index servent vraiment.
-- Lancer : docker exec -i maillots-postgres psql -U admin -d maillots < db/postgres/queries/explain.sql
--
-- EXPLAIN ANALYZE exécute la requête et affiche le "plan" choisi par PostgreSQL :
--   Seq Scan   = il lit TOUTE la table (lent quand la table grossit)
--   Index Scan / Bitmap Index Scan = il passe par un index (rapide)
-- =====================================================================

\echo '== Q1. Onglet Commandes : les 50 commandes les plus récentes (idx_commandes_cree_le)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT reference, id_client, montant_total_centimes, statut, cree_le
FROM orders.orders ORDER BY cree_le DESC LIMIT 50;

\echo '== Q2. Historique d''un client (idx_commandes_client)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT * FROM orders.orders
WHERE id_client = (SELECT id_client FROM orders.customers LIMIT 1);

\echo '== Q3. Onglet Catalogue : stock d''un maillot, toutes tailles et entrepôts (idx_stock_produit)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT sku, id_entrepot, quantite_disponible FROM inventory.stock
WHERE id_produit = 'PSG-2526-HOME-REP';

\echo '== Q4. Onglet Logistique : ruptures imminentes à Lille (index partiel idx_stock_bas)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT sku, quantite_disponible FROM inventory.stock
WHERE id_entrepot = 4 AND quantite_physique - quantite_reservee <= 10;

\echo '== Q5a. SANS index : qui a acheté le PSG domicile en M ? (Seq Scan attendu)'
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT id_commande, quantite FROM orders.order_lines WHERE sku = 'PSG-2526-HOME-REP-M';

\echo '== Q5b. Même requête AVEC un index temporaire'
BEGIN;
CREATE INDEX idx_tmp_sku ON orders.order_lines (sku);
EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY ON)
SELECT id_commande, quantite FROM orders.order_lines WHERE sku = 'PSG-2526-HOME-REP-M';
ROLLBACK;  -- on annule : l'index n'est pas conservé
