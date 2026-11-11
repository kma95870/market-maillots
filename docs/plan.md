# Plan du projet (soutenance prévue le 18/12/2026, date à confirmer)

| Étape | Dates | Volets | Livrable de fin d'étape |
|---|---|---|---|
| 1. Fondations | 11 au 17/11 | 1 Stockage | Bases remplies, ADR-001 et 002, requêtes EXPLAIN, sauvegarde/restauration testée |
| 2. Services et API | 18/11 au 1/12 | 3 Plateforme & API | Services Commandes, Stock, Paiement, Catalogue ; REST + GraphQL ; JWT + RBAC (401/403/200) ; saga de commande |
| 3. Temps réel et lakehouse | 2 au 8/12 | 4 Temps réel, 2 Lakehouse | Kafka + Spark Structured Streaming (alerte rupture, pic de ventes) ; MinIO en 4 zones avec Delta Lake |
| 4. Observabilité et soutenance | 9 au 17/12 | Transverse | Prometheus/Grafana, démo de panne, mesure du lag, CI, README, dossier technique, répétitions |

## Cas d'usage temps réel principal
**« Le transfert du siècle »** : une star signe à 20 h. Les commandes de son maillot explosent.
La plateforme doit, en quelques secondes :
1. détecter le pic de ventes sur ce produit (fenêtre glissante d'une minute) ;
2. lever une alerte « rupture imminente » par taille et par entrepôt, avant la rupture réelle ;
3. signaler à la logistique les entrepôts proches de la saturation ;
4. repérer les comportements de bots (même carte, même adresse, dizaines de commandes en une minute).

## Rôles et besoin de temps réel
| Rôle | Besoin | Traitement |
|---|---|---|
| logistics | Rupture imminente par taille et entrepôt | Streaming (fenêtre glissante 1 min) |
| service_account (paiement, antifraude) | Bots pendant un pic | Streaming (très faible latence) |
| admin | Santé des services et lag Kafka | Métriques toutes les 5 s |
| analyst | Ventes du jour, top maillots | Micro-batch 30 s à 1 min |
| catalog_manager | Mise à jour des prix | API classique, pas de streaming |
