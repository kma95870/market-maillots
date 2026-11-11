# ADR-001 : PostgreSQL pour les commandes, le stock et les paiements

- **Statut** : proposée
- **Date** : 2026-11-11
- **Volet** : 1 Stockage

## Contexte
Lors d'un pic (annonce d'un transfert, sortie d'un nouveau maillot), des milliers de clients veulent le **même maillot dans la même taille** en quelques minutes. Il reste par exemple 300 maillots en taille M : il ne faut **jamais** en vendre 301. Une commande touche aussi plusieurs objets (commande, lignes, réservation de stock, paiement) qui doivent rester cohérents entre eux.

## Options étudiées
| Option | Points forts | Points faibles |
|---|---|---|
| **PostgreSQL** (relationnel) | Transactions ACID, contraintes `CHECK` et clés étrangères, verrouillage de ligne (`SELECT ... FOR UPDATE`), SQL connu de tous | Montée en charge en écriture surtout verticale (une grosse machine) |
| MongoDB | Schéma souple, montée en charge horizontale | Les garanties transactionnelles existent mais sont moins naturelles ; pas de contrainte d'intégrité entre collections |
| Cassandra | Écritures massives, toujours disponible | Cohérence « à terme » : deux clients peuvent acheter le dernier maillot |

## Décision
**PostgreSQL**, avec un **schéma et un rôle par microservice** (`orders`, `inventory`, `payments`, `auth`).

Pour la vente, on privilégie la **cohérence** (le « C » de CAP) : mieux vaut refuser une commande pendant quelques secondes que vendre un maillot qui n'existe pas.

**La taille est modélisée dans le stock PostgreSQL**, pas seulement dans le catalogue : une ligne de `inventory.stock` = un maillot + une taille + un entrepôt (clé `sku` + `warehouse_id`). Ainsi :
- la contrainte `CHECK (reserved <= on_hand)` empêche la survente, même si le code a un bug ;
- deux achats simultanés de la dernière taille M se « disputent » la même ligne, et PostgreSQL les fait passer l'un après l'autre.

Le **flocage** est une option de la ligne de commande (`flocking_name`, `flocking_number`) : il ne consomme pas de stock.

## Conséquences
- (+) Intégrité garantie par la base, pas seulement par le code.
- (+) Requêtes analytiques simples en SQL pour les premiers indicateurs.
- (−) Plus de clé étrangère **entre** services : `product_id` et `order_id` doivent être vérifiés par le code (appel d'API).
- (−) Plus de jointure entre services : afficher le nom du maillot dans une commande demande un appel au service Catalogue.
- (−) Une seule instance : point unique de défaillance. **Plan B** : réplication en lecture (replica), et partitionnement de `orders.orders` par mois si le volume explose.
