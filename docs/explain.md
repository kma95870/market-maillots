# Requêtes EXPLAIN : les index servent-ils vraiment ?

Script : [`db/postgres/queries/explain.sql`](../db/postgres/queries/explain.sql). Mesures relevées le 11/11/2026 sur le jeu de données généré (15 000 commandes, 19 600 lignes).

## Comment lire un plan

`EXPLAIN ANALYZE` exécute la requête et montre **comment** PostgreSQL l'a traitée :
- **Seq Scan** (lecture séquentielle) : il parcourt toute la table, ligne par ligne. Le temps grandit avec la table.
- **Index Scan** / **Bitmap Index Scan** : il utilise un index, comme l'index à la fin d'un livre, pour aller directement aux bonnes lignes.
- **Rows Removed by Filter** : les lignes lues pour rien. Plus le nombre est grand, plus il manque probablement un index.

## Résultats

| # | Usage (onglet) | Index utilisé | Plan | Temps |
|---|---|---|---|---|
| Q1 | 50 dernières commandes (Commandes) | `idx_orders_created_at` | Index Scan | 0,17 ms |
| Q2 | Historique d'un client | `idx_orders_customer` | Bitmap Index Scan | 0,11 ms |
| Q3 | Stock d'un maillot (Catalogue) | `idx_stock_product` | Bitmap Index Scan | 0,08 ms |
| Q4 | Ruptures imminentes (Logistique) | `idx_stock_low` (index partiel) | Bitmap Index Scan | 0,21 ms |
| Q5a | Acheteurs d'un sku, **sans index** | aucun | **Seq Scan**, 19 490 lignes lues pour rien | 1,57 ms |
| Q5b | Même requête **avec index** | `idx_tmp_sku` | Bitmap Index Scan | 0,28 ms |

## Ce qu'on en retient

- **Q5 est la démonstration clé pour le jury** : sans index, PostgreSQL lit 19 653 lignes pour en garder 163. Avec l'index, il va directement aux 163 bonnes lignes, soit un temps divisé par 5,5. Sur 15 millions de lignes au lieu de 19 600, l'écart se compterait en secondes.
- **Q4 utilise un index partiel** : il ne contient que les lignes de stock presque vides. Il est donc beaucoup plus petit, et c'est précisément ce que l'onglet Logistique interroge.
- **Pourquoi ne pas indexer `sku` définitivement ?** Chaque index ralentit les écritures (il faut le mettre à jour à chaque commande) et prend de la place. On ne le crée que si une API en a vraiment besoin. Ce sera à trancher à l'étape 2.
