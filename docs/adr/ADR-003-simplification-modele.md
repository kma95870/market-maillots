# ADR-003 : Simplifier le modèle et nommer les colonnes en français

- **Statut** : acceptée
- **Date** : 2026-11-11
- **Volet** : 1 Stockage

## Contexte
La première version du modèle comptait 88 champs. Une relecture champ par champ a montré que plusieurs ne servaient aucun onglet, aucune démonstration ni aucune exigence de l'énoncé. Les noms de colonnes étaient en anglais, alors que l'équipe et le jury travaillent en français.

## Options étudiées
| Option | Points forts | Points faibles |
|---|---|---|
| Garder le modèle complet | Plus réaliste, prêt pour des évolutions | Plus de code à écrire et à tester, plus de choses à justifier à l'oral |
| **Retirer les champs sans usage** | Modèle plus lisible, moins de code | Certaines analyses futures demanderont de rajouter des champs |

## Décision
Champs retirés :
- **devises** (`currency` dans les commandes, les paiements et le catalogue) : la boutique ne vend qu'en euros ;
- **commandes** : `channel` (aucun onglet ne distingue le site de l'application) ;
- **entrepôts** : `code` et `created_at` (la ville suffit à identifier un entrepôt) ;
- **stock** : `reorder_point`, remplacé par un seuil d'alerte unique fixé à 10 ;
- **paiements** : `refusal_reason` (le statut REFUSED suffit) et `fraud_score`, qui pourra revenir avec le cas temps réel antifraude ;
- **catalogue** : `audience` (la liste des tailles indique déjà s'il s'agit d'un maillot adulte ou enfant) ;
- **auth** : `is_service` (le rôle `service_account` dit la même chose). Les identifiants deviennent des entiers auto-incrémentés et la connexion se fait par email.

Toutes les colonnes et tous les champs MongoDB sont renommés en français, sans accent (`id_produit`, `quantite_physique`, `cree_le`...). Les noms de tables et de schémas restent en anglais pour l'instant, tout comme les valeurs de statut (`PAID`, `SHIPPED`...).

## Conséquences
- (+) 78 champs au lieu de 88, chacun avec un usage identifié.
- (+) Un vocabulaire unique entre le code, le dossier et l'oral.
- (−) Mélange de langues entre les noms de tables (anglais) et les colonnes (français), à trancher.
- (−) Le score de fraude devra être rajouté pour le cas d'usage antifraude, avec une migration.
