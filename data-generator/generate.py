"""Générateur de fausses données pour la plateforme "Maillots".

Remplit :
  * MongoDB    -> le catalogue des maillots
  * PostgreSQL -> entrepôts, stock, clients, commandes (90 derniers jours), paiements, utilisateurs

Le script est rejouable : il vide les tables avant de les remplir.
La graine aléatoire (SEED_RANDOM) rend le résultat identique d'une exécution à l'autre.
"""

# --- Bibliothèques standard de Python (installées d'office) ---
import os                                   # lire les variables d'environnement (le fichier .env)
import random                               # tirer des nombres au hasard
import uuid                                 # fabriquer des identifiants uuid
from datetime import datetime, timedelta, timezone   # manipuler des dates et des durées

# --- Bibliothèques externes (listées dans requirements.txt) ---
import bcrypt                               # hacher les mots de passe
import psycopg                              # se connecter à PostgreSQL
from faker import Faker                     # inventer des noms, emails, villes crédibles
from pymongo import MongoClient             # se connecter à MongoDB

import reference_data as ref                # notre fichier de données écrites à la main

# --- Réglages, lus dans le fichier .env (avec une valeur par défaut si absente) ---
GRAINE = int(os.getenv("SEED_RANDOM", "42"))           # point de départ du hasard
NB_CLIENTS = int(os.getenv("SEED_CUSTOMERS", "2000"))  # nombre de clients à créer
NB_COMMANDES = int(os.getenv("SEED_ORDERS", "15000"))  # nombre de commandes à créer
JOURS_HISTORIQUE = 90                                  # les commandes couvrent les 90 derniers jours
SAISON = "2025/26"                                     # saison des maillots actuels

random.seed(GRAINE)                         # même graine = mêmes tirages à chaque exécution
fake = Faker(["fr_FR", "en_GB", "es_ES", "it_IT", "de_DE"])  # noms français, anglais, espagnols...
Faker.seed(GRAINE)                          # Faker aussi doit partir de la même graine
MAINTENANT = datetime.now(timezone.utc).replace(microsecond=0)  # l'heure actuelle, sans microsecondes


# ---------------------------------------------------------------------
# 1. Catalogue (MongoDB)
# ---------------------------------------------------------------------
def construire_catalogue():
    """Construit la liste des maillots (en mémoire). Chaque type de maillot a des 'attributs' différents."""
    maillots = []                           # la liste qu'on va remplir puis renvoyer
    # On parcourt les clubs ; chaque ligne de ref.CLUBS est "dépliée" dans 7 variables
    for code, nom_club, championnat, pays, marque, popularite, joueurs in ref.CLUBS:
        club = {"code": code, "nom": nom_club, "championnat": championnat, "pays": pays}
        code_saison = SAISON.replace("/", "")[2:]   # '2025/26' -> '202526' -> '2526'
        flocage = {
            "disponible": True,
            "prix_centimes": ref.PRIX_FLOCAGE_CENTIMES,
            # transforme [("DEMBELE", 10), ...] en [{"nom": "DEMBELE", "numero": 10}, ...]
            "joueurs": [{"nom": j, "numero": n} for j, n in joueurs],
        }

        # Petite fonction interne qui ajoute UN maillot du club à la liste.
        # public ("adulte" ou "enfant") n'est PAS stocké en base : il sert seulement
        # à choisir la liste de tailles et à écrire "Enfant" dans le nom.
        def ajouter(type_maillot, version, public, cle_prix, attributs, suffixe):
            tailles = ref.TAILLES_ENFANT if public == "enfant" else ref.TAILLES_ADULTE
            maillots.append({
                "id_produit": f"{code}-{code_saison}-{suffixe}",          # ex. PSG-2526-HOME-REP
                "nom": f"Maillot {libelle_type(type_maillot)} {nom_club} {SAISON}"
                       + (" - Authentic" if version == "authentic" else "")  # suffixe si authentic
                       + (" - Enfant" if public == "enfant" else ""),        # suffixe si enfant
                "club": club, "saison": SAISON, "type_maillot": type_maillot,
                "version": version, "marque": marque,
                "prix_centimes": ref.PRIX[cle_prix],                      # prix lu dans la table PRIX
                "tailles": tailles, "flocage": flocage,
                "attributs": attributs, "actif": True,
                # poids de vente = popularité du club x poids du type de maillot.
                # Le "_" au début signale un champ interne : il ne part PAS dans MongoDB.
                "_popularite": popularite * ref.POIDS_TYPES[suffixe],
                # date de sortie tirée au hasard entre 100 et 140 jours avant aujourd'hui
                "date_sortie": (MAINTENANT - timedelta(days=random.randint(100, 140))).date().isoformat(),
            })

        # 3 maillots replica adulte : domicile, extérieur, third
        for type_maillot in ("home", "away", "third"):
            ajouter(type_maillot, "replica", "adulte", ("replica", "adulte"),
                    {"coupe": "regular", "matiere": "100% polyester recyclé"},
                    f"{type_maillot.upper()}-REP")                       # ex. HOME-REP
        # 2 maillots authentic (version joueur) : domicile et extérieur
        for type_maillot in ("home", "away"):
            ajouter(type_maillot, "authentic", "adulte", ("authentic", "adulte"),
                    {"coupe": "slim", "technologie": ref.TECHNOLOGIES[marque],
                     "details_match": "écusson thermocollé, coupe joueur"},
                    f"{type_maillot.upper()}-AUTH")
        # 1 maillot enfant ; une chance sur deux d'être vendu avec le short
        ajouter("home", "replica", "enfant", ("replica", "enfant"),
                {"coupe": "regular", "short_inclus": random.random() < 0.5},
                "HOME-KID")
        # 1 maillot gardien ; 30 % de chances d'avoir des coudes rembourrés
        ajouter("goalkeeper", "replica", "adulte", ("gardien", "adulte"),
                {"manches_longues": True, "coudes_rembourres": random.random() < 0.3},
                "GK-REP")

        # Si le club a un maillot rétro, on l'ajoute (il ne se floque pas)
        if code in ref.RETRO:
            annee, histoire = ref.RETRO[code]
            maillots.append({
                "id_produit": f"{code}-RETRO-{annee}",
                "nom": f"Maillot rétro {nom_club} {annee}",
                "club": club, "saison": f"{annee}/{str(annee + 1)[2:]}",    # ex. 1993/94
                "type_maillot": "retro", "version": "replica",
                "marque": "Copa", "prix_centimes": ref.PRIX[("retro", "adulte")],
                "tailles": ref.TAILLES_ADULTE,
                "flocage": {"disponible": False},
                "attributs": {"annee_origine": annee, "histoire": histoire,
                              "matiere": "coton", "edition_limitee": True,
                              "exemplaires_produits": random.choice([500, 1000, 2000])},
                "actif": True, "_popularite": popularite * ref.POIDS_TYPES["RETRO"],
                "date_sortie": (MAINTENANT - timedelta(days=200)).date().isoformat(),
            })
    return maillots


def libelle_type(type_maillot):
    """Traduit le type stocké en base (anglais) en libellé affiché (français)."""
    return {"home": "Domicile", "away": "Extérieur", "third": "Third",
            "goalkeeper": "Gardien", "retro": "Rétro"}[type_maillot]


def charger_catalogue(maillots):
    """Vide la collection MongoDB 'products' puis y insère les maillots."""
    # Adresse de connexion : mongodb://utilisateur:motdepasse@serveur:port/base
    adresse = (f"mongodb://{os.environ['MONGO_CATALOG_USER']}:{os.environ['MONGO_CATALOG_PASSWORD']}"
               f"@{os.getenv('MONGO_HOST', 'localhost')}:27017/{os.environ['MONGO_DB']}")
    client = MongoClient(adresse)                          # ouvre la connexion
    collection = client[os.environ["MONGO_DB"]]["products"]
    collection.delete_many({})                             # {} = "tous les documents" : on vide
    documents = []
    for m in maillots:
        # copie du maillot SANS les champs internes (ceux qui commencent par "_")
        doc = {cle: valeur for cle, valeur in m.items() if not cle.startswith("_")}
        doc["cree_le"] = MAINTENANT
        doc["modifie_le"] = MAINTENANT
        documents.append(doc)
    collection.insert_many(documents)                      # une seule insertion pour tout le lot
    print(f"[mongo] {collection.count_documents({})} maillots dans le catalogue")
    client.close()                                         # ferme la connexion


# ---------------------------------------------------------------------
# 2. PostgreSQL
# ---------------------------------------------------------------------
def connexion_postgres():
    """Ouvre une connexion à PostgreSQL avec le compte administrateur (voir README)."""
    return psycopg.connect(
        host=os.getenv("PG_HOST", "localhost"), port=5432,
        dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def vider_tables(cur):
    """Vide toutes les tables, pour pouvoir relancer le script sans doublons."""
    # TRUNCATE = vider une table d'un coup (bien plus rapide que DELETE)
    # RESTART IDENTITY = remet les compteurs "serial" à 1 (tables auth)
    # CASCADE = vide aussi ce qui dépend de ces tables
    cur.execute("""
        TRUNCATE payments.payments, orders.order_lines, orders.orders, orders.customers,
                 inventory.reservations, inventory.stock, inventory.warehouses,
                 auth.user_roles, auth.users RESTART IDENTITY CASCADE
    """)


def charger_entrepots_et_stock(cur, maillots):
    """Crée les entrepôts, puis une ligne de stock par maillot x taille x entrepôt."""
    # executemany = la même requête exécutée pour chaque élément de la liste
    # %s = emplacement rempli par psycopg (jamais de concaténation : risque d'injection SQL)
    cur.executemany(
        "INSERT INTO inventory.warehouses (id_entrepot, ville, capacite) VALUES (%s,%s,%s)",
        ref.ENTREPOTS)
    lignes = []
    for m in maillots:
        for taille in m["tailles"]:
            sku = f"{m['id_produit']}-{taille}"                  # ex. PSG-2526-HOME-REP-M
            for id_entrepot, *_ in ref.ENTREPOTS:                # *_ = on ignore la ville et la capacité
                # stock moyen visé : plus le maillot et la taille se vendent, plus on en a (minimum 4)
                moyenne = max(4, m["_popularite"] * ref.POIDS_TAILLES[taille] / 10)
                # tirage autour de la moyenne (loi normale), jamais négatif
                quantite = max(0, int(random.gauss(moyenne, moyenne / 3)))
                if random.random() < 0.04:                       # 4 % de ruptures dès le départ
                    quantite = 0
                lignes.append((sku, id_entrepot, m["id_produit"], taille, quantite))
    cur.executemany(
        """INSERT INTO inventory.stock (sku, id_entrepot, id_produit, taille, quantite_physique)
           VALUES (%s,%s,%s,%s,%s)""", lignes)
    print(f"[postgres] {len(ref.ENTREPOTS)} entrepôts, {len(lignes)} lignes de stock")


def charger_clients(cur):
    """Crée les clients avec Faker, et renvoie la liste pour s'en servir dans les commandes."""
    codes_clubs = [c[0] for c in ref.CLUBS]                  # ["PSG", "OM", ...]
    poids_clubs = [c[5] for c in ref.CLUBS]                  # [10, 7, ...] : popularité
    clients = []
    for _ in range(NB_CLIENTS):                              # "_" = on n'a pas besoin du compteur
        profil = fake.simple_profile()                       # un faux profil : nom, adresse...
        email = fake.unique.email()                          # unique = jamais deux fois le même
        prenom, *reste = profil["name"].split(" ")           # "Léa Martin" -> "Léa", ["Martin"]
        clients.append((
            uuid.uuid4(),                                    # id_client
            email,
            prenom,
            " ".join(reste) or prenom,                       # nom (ou le prénom si vide)
            # pays tiré avec des poids : 70 % de Français
            random.choices(["FR", "BE", "ES", "IT", "DE", "GB", "CH"], [70, 8, 5, 5, 4, 5, 3])[0],
            fake.city(),                                     # ville
            # 70 % des clients ont un club préféré, choisi selon la popularité
            random.choices(codes_clubs, poids_clubs)[0] if random.random() < 0.7 else None,
            # inscrit entre 90 et 900 jours avant aujourd'hui
            MAINTENANT - timedelta(days=random.randint(JOURS_HISTORIQUE, 900)),
        ))
    cur.executemany(
        """INSERT INTO orders.customers (id_client, email, prenom, nom, pays, ville,
                                         club_prefere, cree_le)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", clients)
    print(f"[postgres] {len(clients)} clients")
    return clients


def date_commande_aleatoire():
    """Tire une date dans les 90 derniers jours, avec plus de commandes le soir et le week-end."""
    while True:                                              # on recommence jusqu'à accepter une date
        date = MAINTENANT - timedelta(days=random.random() * JOURS_HISTORIQUE)
        poids_heure = 0.3 if date.hour < 7 else (1.6 if 18 <= date.hour <= 22 else 1.0)
        poids_jour = 1.3 if date.weekday() >= 5 else 1.0     # weekday() : 5 = samedi, 6 = dimanche
        # plus le poids est fort, plus la date a de chances d'être acceptée
        if random.random() < poids_heure * poids_jour / 2.1:
            return date


def charger_commandes_et_paiements(cur, clients, maillots):
    """Crée les commandes, leurs lignes et leurs paiements."""
    maillots_par_club = {}                                   # {"PSG": [maillots du PSG], ...}
    for m in maillots:
        maillots_par_club.setdefault(m["club"]["code"], []).append(m)
    poids_maillots = [m["_popularite"] for m in maillots]

    commandes, lignes, paiements = [], [], []
    for i in range(NB_COMMANDES):
        client = random.choice(clients)                      # un client au hasard
        cree_le = date_commande_aleatoire()
        id_commande = uuid.uuid4()
        nb_lignes = random.choices([1, 2, 3], [75, 20, 5])[0]   # 75 % des commandes ont 1 maillot
        montant_total = 0
        for num_ligne in range(1, nb_lignes + 1):
            club_prefere = client[6]                         # 7e valeur du tuple client
            # 40 % des fans achètent un maillot de leur club préféré
            if club_prefere and random.random() < 0.4:
                m = random.choice(maillots_par_club[club_prefere])
            else:                                            # sinon, selon la popularité
                m = random.choices(maillots, poids_maillots)[0]
            taille = random.choices(m["tailles"], [ref.POIDS_TAILLES[t] for t in m["tailles"]])[0]
            quantite = random.choices([1, 2], [92, 8])[0]    # 92 % achètent 1 seul exemplaire
            flocage_nom = flocage_numero = None
            flocage_prix = 0
            # 35 % des maillots floquables sont floqués
            if m["flocage"].get("disponible") and random.random() < 0.35:
                if random.random() < 0.8:                    # 80 % : un joueur du club
                    joueurs = m["flocage"]["joueurs"]
                    # la star (1er de la liste) a un poids de 3, les autres de 1
                    joueur = random.choices(joueurs, [3] + [1] * (len(joueurs) - 1))[0]
                    flocage_nom, flocage_numero = joueur["nom"], joueur["numero"]
                else:                                        # 20 % : un nom personnalisé
                    flocage_nom, flocage_numero = fake.last_name().upper(), random.randint(1, 99)
                flocage_prix = m["flocage"]["prix_centimes"]
            montant_total += quantite * (m["prix_centimes"] + flocage_prix)
            lignes.append((id_commande, num_ligne, m["id_produit"], f"{m['id_produit']}-{taille}",
                           taille, quantite, m["prix_centimes"], flocage_nom, flocage_numero, flocage_prix))

        # Statut cohérent avec l'âge de la commande
        age = MAINTENANT - cree_le
        paiement_refuse = random.random() < 0.04             # 4 % de paiements refusés
        if paiement_refuse:
            statut = "CANCELLED"
        elif age < timedelta(hours=2):                       # très récente : pas encore expédiée
            statut = random.choice(["PENDING", "STOCK_RESERVED", "PAID"])
        elif age < timedelta(days=2):
            statut = random.choice(["PAID", "SHIPPED"])
        elif age < timedelta(days=5):
            statut = random.choice(["SHIPPED", "DELIVERED"])
        else:                                                # ancienne : livrée la plupart du temps
            statut = random.choices(["DELIVERED", "RETURNED", "CANCELLED"], [93, 5, 2])[0]

        commandes.append((id_commande, f"MLT-{cree_le:%Y}-{i + 1:06d}",   # référence ex. MLT-2026-000123
                          client[0], statut, montant_total, cree_le,
                          cree_le + timedelta(minutes=random.randint(1, 600))))  # modifie_le

        # Pas de paiement tant que la commande n'est pas allée jusqu'au paiement
        if statut not in ("PENDING", "STOCK_RESERVED"):
            statut_paiement = ("REFUSED" if paiement_refuse else
                               "REFUNDED" if statut == "RETURNED" else "CAPTURED")
            paiements.append((uuid.uuid4(), id_commande, montant_total,
                              random.choices(["card", "paypal", "apple_pay"], [65, 20, 15])[0],
                              statut_paiement,
                              cree_le + timedelta(seconds=random.randint(5, 120))))  # payé 5 à 120 s après

    cur.executemany(
        """INSERT INTO orders.orders (id_commande, reference, id_client, statut, montant_total_centimes,
                                      cree_le, modifie_le)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""", commandes)
    cur.executemany(
        """INSERT INTO orders.order_lines (id_commande, num_ligne, id_produit, sku, taille, quantite,
                     prix_unitaire_centimes, flocage_nom, flocage_numero, flocage_prix_centimes)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", lignes)
    cur.executemany(
        """INSERT INTO payments.payments (id_paiement, id_commande, montant_centimes, moyen, statut, cree_le)
           VALUES (%s,%s,%s,%s,%s,%s)""", paiements)
    print(f"[postgres] {len(commandes)} commandes, {len(lignes)} lignes, {len(paiements)} paiements")


def charger_utilisateurs(cur):
    """Crée les comptes de démo de l'équipe interne et leur donne leurs rôles."""
    mot_de_passe = os.environ["SEED_USER_PASSWORD"].encode()    # bcrypt travaille sur des octets
    for email, roles in ref.UTILISATEURS_DEMO:
        empreinte = bcrypt.hashpw(mot_de_passe, bcrypt.gensalt()).decode()   # hachage + sel aléatoire
        cur.execute(
            # RETURNING id : PostgreSQL nous renvoie l'id serial qu'il vient de créer
            "INSERT INTO auth.users (email, mot_de_passe_hash) VALUES (%s,%s) RETURNING id",
            (email, empreinte))
        id_utilisateur = cur.fetchone()[0]
        cur.executemany(
            # on retrouve l'id du rôle à partir de son nom
            "INSERT INTO auth.user_roles (id_utilisateur, id_role) SELECT %s, id FROM auth.roles WHERE nom = %s",
            [(id_utilisateur, r) for r in roles])
    print(f"[postgres] {len(ref.UTILISATEURS_DEMO)} utilisateurs de démo (mot de passe : SEED_USER_PASSWORD)")


def main():
    """Point d'entrée : enchaîne toutes les étapes dans l'ordre."""
    maillots = construire_catalogue()
    charger_catalogue(maillots)
    # "with" : la transaction est validée (COMMIT) à la fin si tout s'est bien passé,
    # et annulée (ROLLBACK) en cas d'erreur. La connexion est refermée automatiquement.
    with connexion_postgres() as conn, conn.cursor() as cur:
        vider_tables(cur)
        charger_entrepots_et_stock(cur, maillots)
        clients = charger_clients(cur)
        charger_commandes_et_paiements(cur, clients, maillots)
        charger_utilisateurs(cur)
        cur.execute("ANALYZE")   # met à jour les statistiques utilisées par l'optimiseur de requêtes
    print("Terminé.")


# Ce bloc ne s'exécute que si on lance le fichier directement (python generate.py),
# pas si un autre fichier l'importe.
if __name__ == "__main__":
    main()
