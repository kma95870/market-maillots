# Maillots : plateforme data d'un e-commerce de maillots de football

Projet final du Mastère Spécialisé Data & Generative AI Engineering (Bloc 1).

Une boutique en ligne fictive vend des maillots de football (clubs européens, saison 2025/26, maillots rétro, flocage nom + numéro). Ses ventes explosent sur des événements imprévisibles : annonce d'un transfert, but en finale, sortie d'un nouveau maillot. L'objectif est de construire une plateforme data **end-to-end** capable de suivre l'activité en temps réel et d'absorber ces pics.

Plan détaillé : [docs/plan.md](docs/plan.md). Décisions d'architecture : [docs/adr/](docs/adr/).

## Avancement

- [x] **Volet 1, stockage** : PostgreSQL (un schéma et un rôle par service) + MongoDB (catalogue)
- [ ] **Volet 3, services et API** : microservices, REST + GraphQL, JWT + RBAC
- [ ] **Volet 4, temps réel** : Kafka + Spark Structured Streaming
- [ ] **Volet 2, lakehouse** : MinIO, zones raw / staging / curated / consumption
- [ ] **Observabilité** : Prometheus + Grafana

## Architecture des données (étape 1)

```
                ┌──────────────── PostgreSQL (maillots) ────────────────┐
                │ schéma orders     clients, commandes, lignes          │
                │ schéma inventory  entrepôts, stock (sku x entrepôt),  │
                │                   réservations                        │
                │ schéma payments   paiements                           │
                │ schéma auth       utilisateurs, rôles applicatifs     │
                └───────────────────────────────────────────────────────┘
                              ▲  lien par id_produit / sku (vérifié par le code) 
                              ▼
                ┌──────────── MongoDB (catalog.products) ───────────────┐
                │ un document = un maillot, champ "attributs" libre     │
                └───────────────────────────────────────────────────────┘
```

Règles :
- un microservice ne lit **que son schéma** (rôle PostgreSQL dédié, testé : `orders_svc` reçoit `permission denied` sur `inventory`) ;
- les noms de colonnes sont **en français** (sans accent) ;
- les montants sont en **centimes d'euro** (une seule devise, donc pas de colonne devise) ;
- `sku` = `id_produit` + taille, par exemple `PSG-2526-HOME-REP-M` ;
- le flocage est une option de la ligne de commande et ne consomme pas de stock.

## Prérequis

- **Docker Desktop** (Windows : avec le moteur WSL2).
- Au moins **30 Go libres** sur le disque.
- Sur un PC de 16 Go, limiter la mémoire de WSL2 en créant le fichier `C:\Users\<toi>\.wslconfig` :
  ```ini
  [wsl2]
  memory=10GB
  processors=6
  ```
  puis exécuter `wsl --shutdown` dans PowerShell et relancer Docker Desktop.
- **Git sous Windows** : le fichier `.gitattributes` force les fins de ligne Unix sur les scripts. Ne pas le supprimer.

## Démarrage

```bash
# 1. Créer son fichier de configuration (puis changer les mots de passe dedans)
cp .env.example .env

# 2. Lancer les bases (PostgreSQL + MongoDB)
docker compose up -d
docker compose ps            # attendre "healthy" sur les deux

# 3. Remplir les bases avec de fausses données (environ 10 secondes)
docker compose --profile seed run --rm seed
```

Résultat attendu : 125 maillots, 4 entrepôts, environ 2 900 lignes de stock, 2 000 clients, 15 000 commandes sur 90 jours.

### Se connecter aux bases

```bash
docker exec -it maillots-postgres psql -U admin -d maillots
docker exec -it maillots-mongo mongosh -u admin -p <MONGO_ROOT_PASSWORD> --authenticationDatabase admin catalog
```

Quelques requêtes pour vérifier :

```sql
-- Les 5 maillots les plus vendus
SELECT id_produit, SUM(quantite) AS ventes
FROM orders.order_lines GROUP BY 1 ORDER BY 2 DESC LIMIT 5;

-- Taux de remplissage des entrepôts
SELECT w.ville, ROUND(100.0 * SUM(s.quantite_physique) / w.capacite, 1) AS remplissage_pct
FROM inventory.stock s JOIN inventory.warehouses w USING (id_entrepot)
GROUP BY w.ville, w.capacite;
```

### Vérifier les index (EXPLAIN)

```bash
docker exec -i maillots-postgres psql -U admin -d maillots < db/postgres/queries/explain.sql
```

Résultats commentés : [docs/explain.md](docs/explain.md).

### Sauvegarde et restauration

Depuis **Git Bash** (installé avec Git pour Windows), à la racine du projet :

```bash
sh scripts/backup.sh                          # crée backups/<date>/ (PostgreSQL + MongoDB)
sh scripts/restore.sh backups/<date>          # restaure tout depuis ce dossier
```

Test réalisé le 11/11/2026 : sauvegarde, puis suppression volontaire de 4 996 commandes, de tous les paiements et des 8 maillots du PSG, puis restauration. Résultat : 15 000 commandes, 14 991 paiements et 125 maillots retrouvés, et chaque schéma appartient toujours au compte de son service.

### Repartir de zéro

Les scripts d'initialisation ne s'exécutent qu'au **premier** démarrage. Pour les rejouer :

```bash
docker compose down -v      # -v supprime aussi les volumes, donc les données
docker compose up -d
```

## Structure du dépôt

```
db/postgres/init/   scripts de création PostgreSQL (rôles, schémas, tables)
db/mongo/init/      création de la collection catalogue et de son validateur
data-generator/     générateur de fausses données (Python)
db/postgres/queries/  requêtes EXPLAIN
scripts/            sauvegarde et restauration
docs/adr/           fiches de décision d'architecture (ADR)
docs/plan.md        plan du projet
services/           microservices (étape 2)
streaming/          Kafka + Spark (étape 3)
lakehouse/          MinIO + Delta Lake (étape 3)
observability/      Prometheus + Grafana (étape 4)
```

## Sécurité

- Aucun mot de passe dans le dépôt : tout est dans `.env`, ignoré par git.
- Mots de passe des utilisateurs applicatifs hachés avec bcrypt.
