# ADR-002 : MongoDB pour le catalogue des maillots

- **Statut** : proposée
- **Date** : 2026-11-11
- **Volet** : 1 Stockage

## Contexte
Tous les maillots n'ont pas les mêmes caractéristiques :
- un maillot **authentic** a une technologie de tissu et une coupe « joueur » ;
- un maillot **rétro** a une année d'origine, une histoire, un nombre d'exemplaires produits ;
- un maillot **gardien** a des manches longues, parfois des coudes rembourrés ;
- un maillot **enfant** peut être vendu avec le short.

Le catalogue est surtout **lu** (pages produit, recherche) et rarement modifié. De nouveaux types de produits arriveront (maillots féminins, éditions spéciales).

## Options étudiées
| Option | Points forts | Points faibles |
|---|---|---|
| PostgreSQL, une colonne par caractéristique | Tout au même endroit | Des dizaines de colonnes vides ; chaque nouveau type = migration de la table |
| PostgreSQL + colonne `JSONB` | Souplesse et SQL | Mélange les responsabilités : le catalogue partagerait le serveur des commandes et sa charge |
| **MongoDB** | Un document = un maillot complet ; champs différents d'un document à l'autre ; lecture rapide d'un produit entier | Pas de jointure ni de clé étrangère vers PostgreSQL |

## Décision
**MongoDB**, base `catalog`, collection `products`.
- Les champs **communs** (nom, club, saison, type, version, prix en centimes, tailles) sont imposés par un **validateur JSON Schema** : on garde de la rigueur là où elle compte.
- Le champ `attributes` est **libre** : chaque type de maillot y met ce qui lui est propre.
- Le lien avec PostgreSQL passe par `product_id` (et `sku` = `product_id` + taille). Aucune des deux bases ne le vérifie : **c'est le code qui le fait**.

Pour le catalogue, la **disponibilité** prime : afficher un prix vieux de quelques secondes est acceptable, une page produit qui ne charge pas pendant un pic ne l'est pas.

## Conséquences
- (+) Ajouter un nouveau type de maillot ne demande aucune migration.
- (+) Index texte pour la recherche (« maillot Mbappé »).
- (−) Deux bases à sauvegarder, surveiller et sécuriser.
- (−) Risque d'incohérence : un `product_id` supprimé du catalogue mais encore présent dans le stock. **Parade** : on ne supprime jamais un produit, on le désactive (`is_active: false`).
- **Plan B** : si MongoDB devient trop coûteux à opérer, passage à une colonne `JSONB` dans un schéma `catalog` PostgreSQL.
