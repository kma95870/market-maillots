"""Générateur de fausses données pour la plateforme "Maillots".

Remplit :
  * MongoDB  -> le catalogue des maillots
  * PostgreSQL -> entrepôts, stock, clients, commandes (90 derniers jours), paiements, utilisateurs

Le script est rejouable : il vide les tables avant de les remplir.
La graine aléatoire (SEED_RANDOM) rend le résultat identique d'une exécution à l'autre.
"""

import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import psycopg
from faker import Faker
from pymongo import MongoClient

import reference_data as ref

SEED = int(os.getenv("SEED_RANDOM", "42"))
N_CUSTOMERS = int(os.getenv("SEED_CUSTOMERS", "2000"))
N_ORDERS = int(os.getenv("SEED_ORDERS", "15000"))
DAYS_OF_HISTORY = 90
SEASON = "2025/26"

random.seed(SEED)
fake = Faker(["fr_FR", "en_GB", "es_ES", "it_IT", "de_DE"])
Faker.seed(SEED)
NOW = datetime.now(timezone.utc).replace(microsecond=0)


# ---------------------------------------------------------------------
# 1. Catalogue (MongoDB)
# ---------------------------------------------------------------------
def build_catalog():
    """Construit la liste des maillots. Chaque maillot a des 'attributs' différents."""
    products = []
    for code, name, league, country, brand, popularity, players in ref.CLUBS:
        club = {"code": code, "nom": name, "championnat": league, "pays": country}
        season_tag = SEASON.replace("/", "")[2:]  # '2025/26' -> '2526'
        flocage = {
            "disponible": True,
            "prix_centimes": ref.FLOCKING_PRICE_CENTS,
            "joueurs": [{"nom": p, "numero": n} for p, n in players],
        }

        def add(kit_type, version, audience, price_key, attributs, suffix):
            # la cible (adulte ou enfant) se lit dans la liste des tailles
            tailles = ref.KID_SIZES if audience == "kid" else ref.ADULT_SIZES
            products.append({
                "id_produit": f"{code}-{season_tag}-{suffix}",
                "nom": f"Maillot {kit_type_label(kit_type)} {name} {SEASON}"
                       + (" - Authentic" if version == "authentic" else "")
                       + (" - Enfant" if audience == "kid" else ""),
                "club": club, "saison": SEASON, "type_maillot": kit_type,
                "version": version, "marque": brand,
                "prix_centimes": ref.PRICES[price_key],
                "tailles": tailles, "flocage": flocage,
                "attributs": attributs, "actif": True,
                "popularity": popularity * ref.KIT_WEIGHTS[suffix],
                "date_sortie": (NOW - timedelta(days=random.randint(100, 140))).date().isoformat(),
            })

        for kit in ("home", "away", "third"):
            add(kit, "replica", "adult", ("replica", "adult"),
                {"coupe": "regular", "matiere": "100% polyester recyclé"},
                f"{kit.upper()}-REP")
        for kit in ("home", "away"):
            add(kit, "authentic", "adult", ("authentic", "adult"),
                {"coupe": "slim", "technologie": ref.TECHNOLOGIES[brand],
                 "details_match": "écusson thermocollé, coupe joueur"},
                f"{kit.upper()}-AUTH")
        add("home", "replica", "kid", ("replica", "kid"),
            {"coupe": "regular", "short_inclus": random.random() < 0.5},
            "HOME-KID")
        add("goalkeeper", "replica", "adult", ("goalkeeper", "adult"),
            {"manches_longues": True, "coudes_rembourres": random.random() < 0.3},
            "GK-REP")

        if code in ref.RETRO:
            year, story = ref.RETRO[code]
            products.append({
                "id_produit": f"{code}-RETRO-{year}",
                "nom": f"Maillot rétro {name} {year}",
                "club": club, "saison": f"{year}/{str(year + 1)[2:]}",
                "type_maillot": "retro", "version": "replica",
                "marque": "Copa", "prix_centimes": ref.PRICES[("retro", "adult")],
                "tailles": ref.ADULT_SIZES,
                "flocage": {"disponible": False},
                "attributs": {"annee_origine": year, "histoire": story,
                              "matiere": "coton", "edition_limitee": True,
                              "exemplaires_produits": random.choice([500, 1000, 2000])},
                "actif": True, "popularity": popularity * ref.KIT_WEIGHTS["RETRO"],
                "date_sortie": (NOW - timedelta(days=200)).date().isoformat(),
            })
    return products


def kit_type_label(kit_type):
    return {"home": "Domicile", "away": "Extérieur", "third": "Third",
            "goalkeeper": "Gardien", "retro": "Rétro"}[kit_type]


def load_catalog(products):
    uri = (f"mongodb://{os.environ['MONGO_CATALOG_USER']}:{os.environ['MONGO_CATALOG_PASSWORD']}"
           f"@{os.getenv('MONGO_HOST', 'localhost')}:27017/{os.environ['MONGO_DB']}")
    client = MongoClient(uri)
    coll = client[os.environ["MONGO_DB"]]["products"]
    coll.delete_many({})
    docs = []
    for p in products:
        doc = {k: v for k, v in p.items() if k != "popularity"}  # info interne au générateur
        doc["cree_le"] = NOW
        doc["modifie_le"] = NOW
        docs.append(doc)
    coll.insert_many(docs)
    print(f"[mongo] {coll.count_documents({})} maillots dans le catalogue")
    client.close()


# ---------------------------------------------------------------------
# 2. PostgreSQL
# ---------------------------------------------------------------------
def pg_connect():
    return psycopg.connect(
        host=os.getenv("PG_HOST", "localhost"), port=5432,
        dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def reset_tables(cur):
    cur.execute("""
        TRUNCATE payments.payments, orders.order_lines, orders.orders, orders.customers,
                 inventory.reservations, inventory.stock, inventory.warehouses,
                 auth.user_roles, auth.users RESTART IDENTITY CASCADE
    """)


def load_warehouses_and_stock(cur, products):
    cur.executemany(
        "INSERT INTO inventory.warehouses (id_entrepot, ville, capacite) VALUES (%s,%s,%s)",
        ref.WAREHOUSES)
    rows = []
    for p in products:
        for size in p["tailles"]:
            sku = f"{p['id_produit']}-{size}"
            for wh_id, *_ in ref.WAREHOUSES:
                base = max(4, p["popularity"] * ref.SIZE_WEIGHTS[size] / 10)
                on_hand = max(0, int(random.gauss(base, base / 3)))
                if random.random() < 0.04:       # quelques ruptures dès le départ
                    on_hand = 0
                rows.append((sku, wh_id, p["id_produit"], size, on_hand))
    cur.executemany(
        """INSERT INTO inventory.stock (sku, id_entrepot, id_produit, taille, quantite_physique)
           VALUES (%s,%s,%s,%s,%s)""", rows)
    print(f"[postgres] {len(ref.WAREHOUSES)} entrepôts, {len(rows)} lignes de stock")


def load_customers(cur):
    clubs = [c[0] for c in ref.CLUBS]
    weights = [c[5] for c in ref.CLUBS]
    rows, emails = [], set()
    for _ in range(N_CUSTOMERS):
        profile = fake.simple_profile()
        email = fake.unique.email()
        emails.add(email)
        first, *last = profile["name"].split(" ")
        rows.append((uuid.uuid4(), email, first, " ".join(last) or first,
                     random.choices(["FR", "BE", "ES", "IT", "DE", "GB", "CH"],
                                    [70, 8, 5, 5, 4, 5, 3])[0],
                     fake.city(),
                     random.choices(clubs, weights)[0] if random.random() < 0.7 else None,
                     NOW - timedelta(days=random.randint(DAYS_OF_HISTORY, 900))))
    cur.executemany(
        """INSERT INTO orders.customers (id_client, email, prenom, nom, pays, ville,
                                         club_prefere, cree_le)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", rows)
    print(f"[postgres] {len(rows)} clients")
    return rows


def random_order_time():
    """Plus de commandes le soir et le week-end, comme dans la vraie vie."""
    while True:
        dt = NOW - timedelta(days=random.random() * DAYS_OF_HISTORY)
        hour_weight = 0.3 if dt.hour < 7 else (1.6 if 18 <= dt.hour <= 22 else 1.0)
        day_weight = 1.3 if dt.weekday() >= 5 else 1.0
        if random.random() < hour_weight * day_weight / 2.1:
            return dt


def load_orders_and_payments(cur, customers, products):
    by_club = {}
    for p in products:
        by_club.setdefault(p["club"]["code"], []).append(p)
    product_weights = [p["popularity"] for p in products]

    orders, lines, payments = [], [], []
    for i in range(N_ORDERS):
        cust = random.choice(customers)
        created = random_order_time()
        order_id = uuid.uuid4()
        n_lines = random.choices([1, 2, 3], [75, 20, 5])[0]
        total = 0
        for line_no in range(1, n_lines + 1):
            # 40 % des fans achètent le maillot de leur club préféré
            if cust[6] and random.random() < 0.4:
                p = random.choice(by_club[cust[6]])
            else:
                p = random.choices(products, product_weights)[0]
            size = random.choices(p["tailles"], [ref.SIZE_WEIGHTS[s] for s in p["tailles"]])[0]
            qty = random.choices([1, 2], [92, 8])[0]
            fl_name = fl_num = None
            fl_price = 0
            if p["flocage"].get("disponible") and random.random() < 0.35:
                if random.random() < 0.8:     # un joueur star
                    players = p["flocage"]["joueurs"]
                    # le premier joueur de la liste est la star du club
                    pl = random.choices(players, [3] + [1] * (len(players) - 1))[0]
                    fl_name, fl_num = pl["nom"], pl["numero"]
                else:                          # un nom personnalisé
                    fl_name, fl_num = fake.last_name().upper(), random.randint(1, 99)
                fl_price = p["flocage"]["prix_centimes"]
            total += qty * (p["prix_centimes"] + fl_price)
            lines.append((order_id, line_no, p["id_produit"], f"{p['id_produit']}-{size}", size,
                          qty, p["prix_centimes"], fl_name, fl_num, fl_price))

        # Statut cohérent avec l'âge de la commande
        age = NOW - created
        pay_refused = random.random() < 0.04
        if pay_refused:
            status = "CANCELLED"
        elif age < timedelta(hours=2):
            status = random.choice(["PENDING", "STOCK_RESERVED", "PAID"])
        elif age < timedelta(days=2):
            status = random.choice(["PAID", "SHIPPED"])
        elif age < timedelta(days=5):
            status = random.choice(["SHIPPED", "DELIVERED"])
        else:
            status = random.choices(["DELIVERED", "RETURNED", "CANCELLED"], [93, 5, 2])[0]

        orders.append((order_id, f"MLT-{created:%Y}-{i + 1:06d}", cust[0], status, total, created,
                       created + timedelta(minutes=random.randint(1, 600))))

        if status not in ("PENDING", "STOCK_RESERVED"):
            pay_status = ("REFUSED" if pay_refused else
                          "REFUNDED" if status == "RETURNED" else "CAPTURED")
            payments.append((uuid.uuid4(), order_id, total,
                             random.choices(["card", "paypal", "apple_pay"], [65, 20, 15])[0],
                             pay_status, created + timedelta(seconds=random.randint(5, 120))))

    cur.executemany(
        """INSERT INTO orders.orders (id_commande, reference, id_client, statut, montant_total_centimes,
                                      cree_le, modifie_le)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""", orders)
    cur.executemany(
        """INSERT INTO orders.order_lines (id_commande, num_ligne, id_produit, sku, taille, quantite,
                     prix_unitaire_centimes, flocage_nom, flocage_numero, flocage_prix_centimes)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", lines)
    cur.executemany(
        """INSERT INTO payments.payments (id_paiement, id_commande, montant_centimes, moyen, statut, cree_le)
           VALUES (%s,%s,%s,%s,%s,%s)""", payments)
    print(f"[postgres] {len(orders)} commandes, {len(lines)} lignes, {len(payments)} paiements")


def load_users(cur):
    password = os.environ["SEED_USER_PASSWORD"].encode()
    for email, roles in ref.DEMO_USERS:
        pw_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO auth.users (email, mot_de_passe_hash) VALUES (%s,%s) RETURNING id",
            (email, pw_hash))
        user_id = cur.fetchone()[0]
        cur.executemany(
            "INSERT INTO auth.user_roles (id_utilisateur, id_role) SELECT %s, id FROM auth.roles WHERE nom = %s",
            [(user_id, r) for r in roles])
    print(f"[postgres] {len(ref.DEMO_USERS)} utilisateurs de démo (mot de passe : SEED_USER_PASSWORD)")


def main():
    products = build_catalog()
    load_catalog(products)
    with pg_connect() as conn, conn.cursor() as cur:
        reset_tables(cur)
        load_warehouses_and_stock(cur, products)
        customers = load_customers(cur)
        load_orders_and_payments(cur, customers, products)
        load_users(cur)
        cur.execute("ANALYZE")  # met à jour les statistiques pour l'optimiseur de requêtes
    print("Terminé.")


if __name__ == "__main__":
    main()
